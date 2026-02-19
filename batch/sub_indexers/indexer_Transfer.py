"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Sequence, cast

from eth_utils.address import to_checksum_address
from hexbytes import HexBytes
from pydantic import ValidationError
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3
from web3.contract.async_contract import AsyncContractEvent
from web3.exceptions import ABIEventNotFound
from web3.types import EventData, FilterParams

from app.config import TOKEN_LIST_CONTRACT_ADDRESS, ZERO_ADDRESS
from app.contracts import AsyncContract
from app.contracts.contract import AsyncContractEventsView
from app.database import BatchAsyncSessionLocal
from app.model.db import (
    IDXTransfer,
    IDXTransferBlockNumber,
    IDXTransferSourceEventType,
    Listing,
    TransferDataMessage,
)
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import log

UTC = timezone(timedelta(hours=0), "UTC")

process_name = "SUB:TRANSFER"
LOG = log.get_logger(process_name=process_name)

async_web3 = AsyncWeb3Wrapper()


class Processor:
    """Processor for indexing Token transfer events"""

    # Maximum number of contract addresses in one eth_getLogs request.
    # This is a trade-off between request count and payload size.
    ADDRESS_CHUNK_SIZE = 200

    class TargetTokenList:
        class TargetToken:
            """
            Attributes:
                token_contract: token contract object
                skip_timestamp: skippable datetime
                skip_block: skippable block
            """

            def __init__(
                self,
                token_contract: AsyncContractEventsView,
                skip_timestamp: Optional[datetime],
                skip_block: Optional[int],
            ):
                self.token_contract = token_contract
                self.skip_timestamp = skip_timestamp
                self.skip_block = skip_block

        target_token_list: List[TargetToken]

        def __init__(self):
            self.target_token_list = []

        def append(
            self,
            token_contract: AsyncContractEventsView,
            skip_timestamp: Optional[datetime],
            skip_block: Optional[int],
        ):
            target_token = self.TargetToken(token_contract, skip_timestamp, skip_block)
            self.target_token_list.append(target_token)

        def __iter__(self):
            return iter(self.target_token_list)

        def __len__(self):
            return len(self.target_token_list)

    # Index target
    token_list: TargetTokenList

    # On memory cache
    token_type_cache: dict[str, str] = {}
    token_contract_cache: dict[str, AsyncContractEventsView] = {}

    def __init__(self):
        self.token_list = self.TargetTokenList()

    @staticmethod
    async def __gen_block_timestamp(
        event: EventData,
    ) -> datetime | None:
        block_data = await async_web3.eth.get_block(event["blockNumber"])
        assert "timestamp" in block_data
        return datetime.fromtimestamp(block_data["timestamp"], UTC)

    @staticmethod
    async def __get_latest_synchronized(
        db_session: AsyncSession, token_address: str
    ) -> tuple[datetime | None, int | None]:
        """Get latest synchronized data

        :param db_session: db session
        :param token_address: token address
        :return: latest timestamp, latest block number
        """
        latest_registered: Optional[IDXTransfer] = (
            await db_session.scalars(
                select(IDXTransfer)
                .where(IDXTransfer.token_address == token_address)
                .order_by(desc(IDXTransfer.created))
                .limit(1)
            )
        ).first()
        latest_registered_block_number: Optional[IDXTransferBlockNumber] = (
            await db_session.scalars(
                select(IDXTransferBlockNumber)
                .where(IDXTransferBlockNumber.contract_address == token_address)
                .limit(1)
            )
        ).first()
        if latest_registered is not None and latest_registered_block_number is not None:
            assert latest_registered.created is not None
            return (
                latest_registered.created.replace(tzinfo=UTC),
                latest_registered_block_number.latest_block_number,
            )
        elif latest_registered is not None:
            assert latest_registered.created is not None
            return latest_registered.created.replace(tzinfo=UTC), None
        elif latest_registered_block_number is not None:
            return None, latest_registered_block_number.latest_block_number
        else:
            return None, None

    @staticmethod
    def __insert_idx(
        db_session: AsyncSession,
        transaction_hash: str,
        token_address: str,
        from_account_address: str,
        to_account_address: str,
        value: int,
        source_event: IDXTransferSourceEventType,
        data_str: str | None,
        event_created: datetime,
    ):
        """Registry Transfer data in DB

        :param transaction_hash: transaction hash (same value for bulk transfer of token contract)
        :param token_address: token address
        :param from_account_address: from address
        :param to_account_address: to address
        :param value: transfer amount
        :param source_event: source event of transfer
        :param data_str: event data string
        :param event_created: block timestamp (same value for bulk transfer of token contract)
        :return: None
        """
        if data_str is not None:
            try:
                data = json.loads(data_str)
                validated_data = TransferDataMessage(**data)
                message = validated_data.message
            except ValidationError:
                data = {}
                message = None
            except json.JSONDecodeError:
                data = {}
                message = None
            except:
                data = {}
                message = None
        else:
            data = None
            message = None
        transfer = IDXTransfer()
        transfer.transaction_hash = transaction_hash
        transfer.token_address = token_address
        transfer.from_address = from_account_address
        transfer.to_address = to_account_address
        transfer.value = value
        transfer.created = event_created
        transfer.modified = event_created
        transfer.source_event = source_event
        transfer.data = data
        transfer.message = message
        db_session.add(transfer)

    @staticmethod
    async def __update_idx_latest_block(
        db_session: AsyncSession, token_list: TargetTokenList, block_number: int
    ):
        for target in token_list:
            token = target.token_contract
            idx_block_number: Optional[IDXTransferBlockNumber] = (
                await db_session.scalars(
                    select(IDXTransferBlockNumber)
                    .where(IDXTransferBlockNumber.contract_address == token.address)
                    .limit(1)
                )
            ).first()
            if idx_block_number is None:
                idx_block_number = IDXTransferBlockNumber()
                idx_block_number.contract_address = token.address
                idx_block_number.latest_block_number = block_number
                db_session.add(idx_block_number)
            else:
                idx_block_number.latest_block_number = block_number
                await db_session.merge(idx_block_number)

    """
    Sync logs
    """

    async def sync_new_logs(self):
        local_session = BatchAsyncSessionLocal()
        latest_block = await async_web3.eth.block_number
        try:
            LOG.info("Syncing to={}".format(latest_block))

            # Refresh listed tokens
            await self.__get_token_list(local_session)

            # Synchronize 1,000,000 blocks each
            _to_block = 999_999
            _from_block = 0
            if latest_block > 999_999:
                while _to_block < latest_block:
                    await self.__sync_all(local_session, _from_block, _to_block)
                    _to_block += 1_000_000
                    _from_block += 1_000_000
                await self.__sync_all(local_session, _from_block, latest_block)
            else:
                await self.__sync_all(local_session, _from_block, latest_block)

            # Update latest synchronized block numbers
            await self.__update_idx_latest_block(
                db_session=local_session,
                token_list=self.token_list,
                block_number=latest_block,
            )
            await local_session.commit()

        except Exception as e:
            await local_session.rollback()
            raise e
        finally:
            await local_session.close()
        LOG.info("Sync job completed successfully")

    async def __get_token_list(self, db_session: AsyncSession):
        self.token_list = self.TargetTokenList()
        if TOKEN_LIST_CONTRACT_ADDRESS is None:
            return
        list_contract = AsyncContract.get_contract(
            "TokenList", TOKEN_LIST_CONTRACT_ADDRESS
        )
        listed_tokens: Sequence[Listing] = (
            await db_session.scalars(select(Listing))
        ).all()
        for listed_token in listed_tokens:
            assert listed_token.token_address is not None
            # Reuse token type cache
            if listed_token.token_address not in self.token_type_cache:
                token_info: tuple[str, str, str] = await AsyncContract.call_function(
                    contract=list_contract,
                    function_name="getTokenByAddress",
                    args=(listed_token.token_address,),
                    default_returns=(ZERO_ADDRESS, "", ZERO_ADDRESS),
                )
                self.token_type_cache[listed_token.token_address] = str(token_info[1])
            token_type = self.token_type_cache[listed_token.token_address]
            if not token_type:
                # Skip if token is not listed in the TokenList contract
                continue

            skip_timestamp, skip_block_number = await self.__get_latest_synchronized(
                db_session, listed_token.token_address
            )
            # Reuse token contract cache
            if listed_token.token_address not in self.token_contract_cache:
                token_contract = AsyncContract.get_contract(
                    token_type, listed_token.token_address
                )
                self.token_contract_cache[listed_token.token_address] = (
                    AsyncContractEventsView(
                        token_contract.address, token_contract.events
                    )
                )
            token_contract = self.token_contract_cache[listed_token.token_address]

            self.token_list.append(
                token_contract,
                skip_timestamp,
                skip_block_number,
            )

    async def __sync_all(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        # Filter active targets that may still have unsynchronized logs up to block_to.
        active_targets = self.__filter_active_targets(block_to)
        if len(active_targets) == 0:
            return

        # Sync each event type
        await self.__sync_transfer(db_session, block_from, block_to, active_targets)
        await self.__sync_unlock(db_session, block_from, block_to, active_targets)
        await self.__sync_force_unlock(db_session, block_from, block_to, active_targets)
        await self.__sync_force_change_locked_account(
            db_session, block_from, block_to, active_targets
        )
        await self.__update_skip_block(db_session)

    def __filter_active_targets(
        self, block_to: int
    ) -> list[TargetTokenList.TargetToken]:
        """Return tokens that may still have unsynchronized logs up to block_to."""
        return [
            target
            for target in self.token_list
            if target.skip_block is None or block_to > target.skip_block
        ]

    @staticmethod
    def __chunked(values: list[str], chunk_size: int) -> list[list[str]]:
        """Split a list into fixed-size chunks."""
        return [values[i : i + chunk_size] for i in range(0, len(values), chunk_size)]

    @staticmethod
    def __build_topic0(event_name: str, event_abi: Any) -> str:
        """Build topic0 (= event signature hash) from event ABI."""
        input_types = ",".join(
            [input_param["type"] for input_param in event_abi.get("inputs", [])]
        )
        signature = f"{event_name}({input_types})"
        return Web3.keccak(text=signature).to_0x_hex()

    async def __get_logs_by_event(
        self,
        event_name: str,
        block_from: int,
        block_to: int,
        targets: Sequence[TargetTokenList.TargetToken],
    ) -> list[tuple[TargetTokenList.TargetToken, EventData]]:
        """Fetch logs once per event type, then decode and map to each target token.

        Flow:
        1) Build target token/decoder maps
        2) Query logs in address chunks with shared topic0 filter
        3) Filter out already synchronized logs by per-token skip_block
        4) Decode and return logs sorted by (blockNumber, logIndex)
        """
        target_by_address: dict[str, Processor.TargetTokenList.TargetToken] = {}
        event_decoder_by_address: dict[str, AsyncContractEvent] = {}
        topic0: str | None = None

        for target in targets:
            token = target.token_contract

            event_class: Any = getattr(token.events, event_name, None)
            if event_class is None:
                continue
            event_decoder = event_class()
            if not isinstance(event_decoder, AsyncContractEvent):
                continue

            token_address = to_checksum_address(token.address)
            target_by_address[token_address] = target
            event_decoder_by_address[token_address] = event_decoder
            if topic0 is None:
                topic0 = self.__build_topic0(event_name, event_decoder.abi)

        if len(target_by_address) == 0 or topic0 is None:
            return []

        logs: list[tuple[Processor.TargetTokenList.TargetToken, EventData]] = []
        target_addresses = list(target_by_address.keys())
        topics = [[topic0]]

        for address_chunk in self.__chunked(target_addresses, self.ADDRESS_CHUNK_SIZE):
            # One eth_getLogs request per event type + address chunk.
            filter_params = cast(
                FilterParams,
                {
                    "fromBlock": block_from,
                    "toBlock": block_to,
                    "address": address_chunk,
                    "topics": topics,
                },
            )
            raw_logs = await async_web3.eth.get_logs(filter_params)
            for raw_log in raw_logs:
                # Map log to target token by address.
                token_address = to_checksum_address(raw_log["address"])
                target = target_by_address.get(token_address)
                if target is None:
                    continue

                # Skip logs that are already synchronized based on per-token skip_block.
                if (
                    target.skip_block is not None
                    and raw_log["blockNumber"] <= target.skip_block
                ):
                    continue

                # Decode log with corresponding event decoder.
                event_decoder = event_decoder_by_address.get(token_address)
                if event_decoder is None:
                    continue

                try:
                    event = event_decoder.process_log(raw_log)
                    logs.append((target, event))
                except Exception:
                    continue

        # Sort logs by (blockNumber, logIndex) to ensure correct processing order.
        logs.sort(
            key=lambda log_data: (log_data[1]["blockNumber"], log_data[1]["logIndex"])
        )
        return logs

    async def __sync_transfer(
        self,
        db_session: AsyncSession,
        block_from: int,
        block_to: int,
        targets: Sequence[TargetTokenList.TargetToken],
    ):
        """Sync Transfer events

        :param db_session: ORM session
        :param block_from: From block
        :param block_to: To block
        :return:
        """
        # Fetch once by event type and process per-token with skip guards.
        try:
            events = await self.__get_logs_by_event(
                "Transfer", block_from, block_to, targets
            )
        except ABIEventNotFound:
            events = []

        try:
            for target, event in events:
                token = target.token_contract
                skip_timestamp = target.skip_timestamp
                args = event["args"]
                value = args.get("value", 0)
                if value > sys.maxsize:
                    continue

                event_created = await self.__gen_block_timestamp(event=event)
                if event_created is None:
                    continue
                if skip_timestamp is not None and event_created <= skip_timestamp:
                    LOG.debug(
                        f"Skip Registry Transfer data in DB: blockNumber={event['blockNumber']}"
                    )
                    continue

                # Judge whether the transfer is a reallocation
                transaction_hash = event["transactionHash"].to_0x_hex()
                is_reallocation = False
                tx = await AsyncContract.get_transaction(
                    event["transactionHash"], event["blockNumber"]
                )
                if tx is not None:
                    tx_data: HexBytes | None = tx.get("input")
                    # Check if the transaction data contains the reallocation marker("c0ffee00")
                    if tx_data is not None and "c0ffee00" in tx_data.hex():
                        try:
                            raw_call_data = tx_data.hex().split("c0ffee00", 1)[1]
                            call_data = json.loads(bytes.fromhex(raw_call_data))
                            if call_data.get("purpose") == "Reallocation":
                                is_reallocation = True
                        except (ValueError, json.JSONDecodeError):
                            # If decoding fails, treat it as a normal transfer
                            pass

                self.__insert_idx(
                    db_session=db_session,
                    transaction_hash=transaction_hash,
                    token_address=to_checksum_address(token.address),
                    from_account_address=args.get("from", ZERO_ADDRESS),
                    to_account_address=args.get("to", ZERO_ADDRESS),
                    value=value,
                    source_event=IDXTransferSourceEventType.REALLOCATION
                    if is_reallocation is True
                    else IDXTransferSourceEventType.TRANSFER,
                    data_str=None,
                    event_created=event_created,
                )
        except Exception as e:
            raise e

    async def __sync_unlock(
        self,
        db_session: AsyncSession,
        block_from: int,
        block_to: int,
        targets: Sequence[TargetTokenList.TargetToken],
    ):
        """Synchronize Unlock events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        # Fetch once by event type and process per-token with skip guards.
        try:
            events = await self.__get_logs_by_event(
                "Unlock", block_from, block_to, targets
            )
        except ABIEventNotFound:
            events = []

        try:
            for target, event in events:
                token = target.token_contract
                args = event["args"]
                transaction_hash = event["transactionHash"].to_0x_hex()
                block_data = await async_web3.eth.get_block(event["blockNumber"])
                assert "timestamp" in block_data
                block_timestamp = datetime.fromtimestamp(
                    block_data["timestamp"],
                    UTC,
                ).replace(tzinfo=None)
                if args.get("value", 0) > sys.maxsize:
                    continue

                from_address = args.get("accountAddress", ZERO_ADDRESS)
                to_address = args.get("recipientAddress", ZERO_ADDRESS)
                data_str = args.get("data", "")
                if from_address != to_address:
                    self.__insert_idx(
                        db_session=db_session,
                        transaction_hash=transaction_hash,
                        token_address=to_checksum_address(token.address),
                        from_account_address=from_address,
                        to_account_address=to_address,
                        value=args.get("value", 0),
                        source_event=IDXTransferSourceEventType.UNLOCK,
                        data_str=data_str,
                        event_created=block_timestamp,
                    )
        except Exception:
            raise

    async def __sync_force_unlock(
        self,
        db_session: AsyncSession,
        block_from: int,
        block_to: int,
        targets: Sequence[TargetTokenList.TargetToken],
    ):
        """Synchronize ForceUnlock events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        # Fetch once by event type and process per-token with skip guards.
        try:
            events = await self.__get_logs_by_event(
                "ForceUnlock", block_from, block_to, targets
            )
        except ABIEventNotFound:
            events = []

        try:
            for target, event in events:
                token = target.token_contract
                args = event["args"]
                transaction_hash = event["transactionHash"].to_0x_hex()
                block_data = await async_web3.eth.get_block(event["blockNumber"])
                assert "timestamp" in block_data
                block_timestamp = datetime.fromtimestamp(
                    block_data["timestamp"],
                    UTC,
                ).replace(tzinfo=None)
                if args.get("value", 0) > sys.maxsize:
                    continue

                # Only insert if from and to addresses are different.
                from_address = args.get("accountAddress", ZERO_ADDRESS)
                to_address = args.get("recipientAddress", ZERO_ADDRESS)
                data_str = args.get("data", "")
                if from_address != to_address:
                    self.__insert_idx(
                        db_session=db_session,
                        transaction_hash=transaction_hash,
                        token_address=to_checksum_address(token.address),
                        from_account_address=from_address,
                        to_account_address=to_address,
                        value=args.get("value", 0),
                        source_event=IDXTransferSourceEventType.FORCE_UNLOCK,
                        data_str=data_str,
                        event_created=block_timestamp,
                    )
        except Exception:
            raise

    async def __sync_force_change_locked_account(
        self,
        db_session: AsyncSession,
        block_from: int,
        block_to: int,
        targets: Sequence[TargetTokenList.TargetToken],
    ):
        """Synchronize ForceChangeLockedAccount events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        # Fetch once by event type and process per-token with skip guards.
        try:
            events = await self.__get_logs_by_event(
                "ForceChangeLockedAccount", block_from, block_to, targets
            )
        except ABIEventNotFound:
            events = []

        try:
            for target, event in events:
                token = target.token_contract
                args = event["args"]
                transaction_hash = event["transactionHash"].to_0x_hex()
                block_data = await async_web3.eth.get_block(event["blockNumber"])
                assert "timestamp" in block_data
                block_timestamp = datetime.fromtimestamp(
                    block_data["timestamp"],
                    UTC,
                ).replace(tzinfo=None)
                if args.get("value", 0) > sys.maxsize:
                    continue

                # Only insert if from and to addresses are different.
                from_address = args.get("beforeAccountAddress", ZERO_ADDRESS)
                to_address = args.get("afterAccountAddress", ZERO_ADDRESS)
                data_str = args.get("data", "")
                if from_address != to_address:
                    self.__insert_idx(
                        db_session=db_session,
                        transaction_hash=transaction_hash,
                        token_address=to_checksum_address(token.address),
                        from_account_address=from_address,
                        to_account_address=to_address,
                        value=args.get("value", 0),
                        source_event=IDXTransferSourceEventType.FORCE_CHANGE_LOCKED_ACCOUNT,
                        data_str=data_str,
                        event_created=block_timestamp,
                    )
        except Exception:
            raise

    async def __update_skip_block(self, db_session: AsyncSession):
        """Memorize the block number where next processing should start from

        :param db_session: ORM session
        :return: None
        """
        for target in self.token_list:
            (
                target.skip_timestamp,
                target.skip_block,
            ) = await self.__get_latest_synchronized(
                db_session, target.token_contract.address
            )
