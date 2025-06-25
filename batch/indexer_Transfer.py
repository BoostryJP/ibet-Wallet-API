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

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Sequence

from eth_utils import to_checksum_address
from pydantic import ValidationError
from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.exceptions import ABIEventNotFound

from app.config import TOKEN_LIST_CONTRACT_ADDRESS, ZERO_ADDRESS
from app.contracts import AsyncContract
from app.contracts.contract import AsyncContractEventsView
from app.database import BatchAsyncSessionLocal
from app.errors import ServiceUnavailable
from app.model.db import (
    DataMessage,
    IDXTransfer,
    IDXTransferBlockNumber,
    IDXTransferSourceEventType,
    Listing,
)
from app.model.schema.base import TokenType
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import free_malloc, log

UTC = timezone(timedelta(hours=0), "UTC")

process_name = "INDEXER-TRANSFER"
LOG = log.get_logger(process_name=process_name)

async_web3 = AsyncWeb3Wrapper()


class Processor:
    """Processor for indexing Token transfer events"""

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
    token_type_cache: dict[str, TokenType] = {}
    token_contract_cache: dict[str, AsyncContractEventsView] = {}

    def __init__(self):
        self.token_list = self.TargetTokenList()

    @staticmethod
    async def __gen_block_timestamp(event):
        return datetime.fromtimestamp(
            (await async_web3.eth.get_block(event["blockNumber"]))["timestamp"], UTC
        )

    @staticmethod
    async def __gen_block_timestamp_from_block_number(block_number: int):
        return datetime.fromtimestamp(
            (await async_web3.eth.get_block(block_number))["timestamp"], UTC
        )

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
            return (
                latest_registered.created.replace(tzinfo=UTC),
                latest_registered_block_number.latest_block_number,
            )
        elif latest_registered is not None:
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
                validated_data = DataMessage(**data)
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

    async def __get_token_list(self, db_session: AsyncSession):
        self.token_list = self.TargetTokenList()
        list_contract = AsyncContract.get_contract(
            "TokenList", TOKEN_LIST_CONTRACT_ADDRESS
        )
        listed_tokens: Sequence[Listing] = (
            await db_session.scalars(select(Listing))
        ).all()
        for listed_token in listed_tokens:
            # Reuse token type cache
            if listed_token.token_address not in self.token_type_cache:
                token_info = await AsyncContract.call_function(
                    contract=list_contract,
                    function_name="getTokenByAddress",
                    args=(listed_token.token_address,),
                    default_returns=(ZERO_ADDRESS, "", ZERO_ADDRESS),
                )
                self.token_type_cache[listed_token.token_address] = token_info[1]
            token_type = self.token_type_cache[listed_token.token_address]
            if token_type is None or token_type == "":
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
        await self.__sync_transfer(db_session, block_from, block_to)
        await self.__sync_unlock(db_session, block_from, block_to)
        await self.__sync_force_unlock(db_session, block_from, block_to)
        await self.__update_skip_block(db_session)

    async def __sync_transfer(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Sync Transfer events

        :param db_session: ORM session
        :param block_from: From block
        :param block_to: To block
        :return:
        """
        for target in self.token_list:
            token = target.token_contract
            skip_timestamp = target.skip_timestamp
            skip_block = target.skip_block

            # Get "Transfer" logs
            try:
                if skip_block is not None and block_to <= skip_block:
                    # Skip if the token has already been synchronized to block_to.
                    LOG.debug(f"{token.address}: block_to <= skip_block")
                    continue
                elif skip_block is not None and block_from <= skip_block < block_to:
                    # block_from <= skip_block < block_to
                    LOG.debug(f"{token.address}: block_from <= skip_block < block_to")
                    events = await token.events.Transfer.get_logs(
                        from_block=skip_block + 1, to_block=block_to
                    )
                else:
                    # No logs or
                    # skip_block < block_from < block_to
                    LOG.debug(f"{token.address}: skip_block < block_from < block_to")
                    events = await token.events.Transfer.get_logs(
                        from_block=block_from, to_block=block_to
                    )
            except ABIEventNotFound:
                events = []

            # Index logs
            try:
                for event in events:
                    args = event["args"]
                    value = args.get("value", 0)
                    if value > sys.maxsize:
                        pass
                    else:
                        event_created = await self.__gen_block_timestamp(event=event)
                        if (
                            skip_timestamp is not None
                            and event_created <= skip_timestamp
                        ):
                            LOG.debug(
                                f"Skip Registry Transfer data in DB: blockNumber={event['blockNumber']}"
                            )
                            continue
                        self.__insert_idx(
                            db_session=db_session,
                            transaction_hash=event["transactionHash"].to_0x_hex(),
                            token_address=to_checksum_address(token.address),
                            from_account_address=args.get("from", ZERO_ADDRESS),
                            to_account_address=args.get("to", ZERO_ADDRESS),
                            value=value,
                            source_event=IDXTransferSourceEventType.TRANSFER,
                            data_str=None,
                            event_created=event_created,
                        )
            except Exception as e:
                raise e

    async def __sync_unlock(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Synchronize Unlock events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for target in self.token_list:
            token = target.token_contract
            skip_block = target.skip_block

            # Get "Unlock" logs
            try:
                if skip_block is not None and block_to <= skip_block:
                    # Skip if the token has already been synchronized to block_to.
                    LOG.debug(f"{token.address}: block_to <= skip_block")
                    continue
                elif skip_block is not None and block_from <= skip_block < block_to:
                    # block_from <= skip_block < block_to
                    LOG.debug(f"{token.address}: block_from <= skip_block < block_to")
                    events = await token.events.Unlock.get_logs(
                        from_block=skip_block + 1, to_block=block_to
                    )
                else:
                    # No logs or
                    # skip_block < block_from < block_to
                    LOG.debug(f"{token.address}: skip_block < block_from < block_to")
                    events = await token.events.Unlock.get_logs(
                        from_block=block_from, to_block=block_to
                    )
            except ABIEventNotFound:
                events = []

            # Index logs
            try:
                for event in events:
                    args = event["args"]
                    transaction_hash = event["transactionHash"].to_0x_hex()
                    block_timestamp = datetime.fromtimestamp(
                        (await async_web3.eth.get_block(event["blockNumber"]))[
                            "timestamp"
                        ],
                        UTC,
                    ).replace(tzinfo=None)
                    if args["value"] > sys.maxsize:
                        pass
                    else:
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
                                value=args["value"],
                                source_event=IDXTransferSourceEventType.UNLOCK,
                                data_str=data_str,
                                event_created=block_timestamp,
                            )
            except Exception:
                raise

    async def __sync_force_unlock(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Synchronize ForceUnlock events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for target in self.token_list:
            token = target.token_contract
            skip_block = target.skip_block

            # Get "ForceUnlock" logs
            try:
                if skip_block is not None and block_to <= skip_block:
                    # Skip if the token has already been synchronized to block_to.
                    LOG.debug(f"{token.address}: block_to <= skip_block")
                    continue
                elif skip_block is not None and block_from <= skip_block < block_to:
                    # block_from <= skip_block < block_to
                    LOG.debug(f"{token.address}: block_from <= skip_block < block_to")
                    events = await token.events.ForceUnlock.get_logs(
                        from_block=skip_block + 1, to_block=block_to
                    )
                else:
                    # No logs or
                    # skip_block < block_from < block_to
                    LOG.debug(f"{token.address}: skip_block < block_from < block_to")
                    events = await token.events.ForceUnlock.get_logs(
                        from_block=block_from, to_block=block_to
                    )
            except ABIEventNotFound:
                events = []

            # Index logs
            try:
                for event in events:
                    args = event["args"]
                    transaction_hash = event["transactionHash"].to_0x_hex()
                    block_timestamp = datetime.fromtimestamp(
                        (await async_web3.eth.get_block(event["blockNumber"]))[
                            "timestamp"
                        ],
                        UTC,
                    ).replace(tzinfo=None)
                    if args["value"] > sys.maxsize:
                        pass
                    else:
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
                                value=args["value"],
                                source_event=IDXTransferSourceEventType.FORCE_UNLOCK,
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


async def main():
    LOG.info("Service started successfully")
    processor = Processor()

    # Initial sync
    initial_synced_completed = False
    while not initial_synced_completed:
        try:
            await processor.sync_new_logs()
            initial_synced_completed = True
            LOG.info(f"<{process_name}> Initial sync has been completed")
        except Exception:
            LOG.exception("Initial sync failed")
        await asyncio.sleep(5)

    # Sync new logs
    while True:
        try:
            await processor.sync_new_logs()
            LOG.debug("Processed")
        except ServiceUnavailable:
            LOG.notice("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An exception occurred during event synchronization")
        await asyncio.sleep(5)
        free_malloc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
