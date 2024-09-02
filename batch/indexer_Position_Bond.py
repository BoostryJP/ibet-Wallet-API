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
from itertools import groupby
from typing import List, Optional, Sequence

from eth_utils import to_checksum_address
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.exceptions import ABIEventFunctionNotFound
from web3.types import LogReceipt

from app.config import TOKEN_LIST_CONTRACT_ADDRESS, ZERO_ADDRESS
from app.contracts import AsyncContract
from app.database import BatchAsyncSessionLocal
from app.errors import ServiceUnavailable
from app.model.db import (
    IDXLock,
    IDXLockedPosition,
    IDXPosition,
    IDXPositionBondBlockNumber,
    IDXUnlock,
    Listing,
)
from app.model.schema.base import TokenType
from app.utils.asyncio_utils import SemaphoreTaskGroup
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import log

UTC = timezone(timedelta(hours=0), "UTC")

process_name = "INDEXER-POSITION-BOND"
LOG = log.get_logger(process_name=process_name)

async_web3 = AsyncWeb3Wrapper()


class Processor:
    """Processor for indexing Bond balances"""

    class TargetTokenList:
        class TargetToken:
            """
            Attributes:
                token_contract: contract object
                exchange_address: address of associated exchange
                start_block_number(int): block number that the processor first reads
                cursor(int): pointer where next process should be start
            """

            def __init__(
                self, token_contract, exchange_address: str, block_number: int
            ):
                self.token_contract = token_contract
                self.exchange_address = exchange_address
                self.start_block_number = block_number
                self.cursor = block_number

        target_token_list: List[TargetToken]

        def __init__(self):
            self.target_token_list = []

        def append(self, token_contract, exchange_address: str, block_number: int):
            is_duplicate = False
            for i, t in enumerate(self.target_token_list):
                if t.token_contract.address == token_contract.address:
                    is_duplicate = True
                    if self.target_token_list[i].start_block_number > block_number:
                        self.target_token_list[i].start_block_number = block_number
                        self.target_token_list[i].cursor = block_number
            if not is_duplicate:
                target_token = self.TargetToken(
                    token_contract, exchange_address, block_number
                )
                self.target_token_list.append(target_token)

        def get_cursor(self, token_address: str) -> int:
            for t in self.target_token_list:
                if t.token_contract.address == token_address:
                    return t.cursor
            return 0

        def __iter__(self):
            return iter(self.target_token_list)

        def __len__(self):
            return len(self.target_token_list)

    class TargetExchangeList:
        class TargetExchange:
            """
            Attributes:
                exchange_address: contract address of exchange, escrow or dvp
                start_block_number(int): block number that the processor first reads
                cursor(int): pointer where next process should be start
            """

            def __init__(self, exchange_address: str, block_number: int):
                self.exchange_address = exchange_address
                self.start_block_number = block_number
                self.cursor = block_number

        target_exchange_list: List[TargetExchange]

        def __init__(self):
            self.target_exchange_list = []

        def append(self, exchange_address: str, block_number: int):
            is_duplicate = False
            for i, e in enumerate(self.target_exchange_list):
                if e.exchange_address == exchange_address:
                    is_duplicate = True
                    if self.target_exchange_list[i].start_block_number > block_number:
                        self.target_exchange_list[i].start_block_number = block_number
                        self.target_exchange_list[i].cursor = block_number
            if not is_duplicate:
                target_exchange = self.TargetExchange(exchange_address, block_number)
                self.target_exchange_list.append(target_exchange)

        def __iter__(self):
            return iter(self.target_exchange_list)

    token_list: TargetTokenList
    exchange_list: TargetExchangeList

    def __init__(self):
        self.token_list = self.TargetTokenList()
        self.exchange_list = self.TargetExchangeList()

    @staticmethod
    def __get_db_session():
        return BatchAsyncSessionLocal()

    async def initial_sync(self):
        local_session = self.__get_db_session()
        try:
            await self.__get_contract_list(local_session)
            # Synchronize 1,000,000 blocks each
            # if some blocks have already synced, sync starting from next block
            latest_block = await async_web3.eth.block_number
            _from_block = self.__get_oldest_cursor(self.token_list, latest_block)
            _to_block = 999999 + _from_block
            if latest_block > _to_block:
                while _to_block < latest_block:
                    await self.__sync_all(
                        db_session=local_session,
                        block_to=_to_block,
                    )
                    _to_block += 1000000
                await self.__sync_all(db_session=local_session, block_to=latest_block)
            else:
                await self.__sync_all(db_session=local_session, block_to=latest_block)
            await self.__set_idx_position_block_number(
                local_session, self.token_list, latest_block
            )
            await local_session.commit()
        except Exception as e:
            await local_session.rollback()
            raise e
        finally:
            await local_session.close()
            self.token_list = self.TargetTokenList()
            self.exchange_list = self.TargetExchangeList()
        LOG.info("Initial sync has been completed")

    async def sync_new_logs(self):
        local_session = self.__get_db_session()
        try:
            await self.__get_contract_list(local_session)
            # Synchronize 1,000,000 blocks each
            # if some blocks have already synced, sync starting from next block
            latest_block = await async_web3.eth.block_number
            _from_block = self.__get_oldest_cursor(self.token_list, latest_block)
            _to_block = 999999 + _from_block
            if latest_block > _to_block:
                while _to_block < latest_block:
                    await self.__sync_all(
                        db_session=local_session,
                        block_to=_to_block,
                    )
                    _to_block += 1000000
                await self.__sync_all(db_session=local_session, block_to=latest_block)
            else:
                await self.__sync_all(db_session=local_session, block_to=latest_block)
            await self.__set_idx_position_block_number(
                local_session, self.token_list, latest_block
            )
            await local_session.commit()
        except Exception as e:
            await local_session.rollback()
            raise e
        finally:
            await local_session.close()
            self.token_list = self.TargetTokenList()
            self.exchange_list = self.TargetExchangeList()
        LOG.info("Sync job has been completed")

    async def __get_contract_list(self, db_session: AsyncSession):
        self.token_list = self.TargetTokenList()
        self.exchange_list = self.TargetExchangeList()

        list_contract = AsyncContract.get_contract(
            contract_name="TokenList", address=TOKEN_LIST_CONTRACT_ADDRESS
        )
        listed_tokens: Sequence[Listing] = (
            await db_session.scalars(select(Listing))
        ).all()

        _exchange_list_tmp = []
        for listed_token in listed_tokens:
            token_info = await AsyncContract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(listed_token.token_address,),
                default_returns=(ZERO_ADDRESS, "", ZERO_ADDRESS),
            )
            if token_info[1] == TokenType.IbetStraightBond:
                token_contract = AsyncContract.get_contract(
                    contract_name=TokenType.IbetStraightBond,
                    address=listed_token.token_address,
                )
                tradable_exchange_address = await AsyncContract.call_function(
                    contract=token_contract,
                    function_name="tradableExchange",
                    args=(),
                    default_returns=ZERO_ADDRESS,
                )
                synced_block_number = await self.__get_idx_position_block_number(
                    db_session=db_session,
                    token_address=listed_token.token_address,
                    exchange_address=tradable_exchange_address,
                )
                block_from = synced_block_number + 1
                self.token_list.append(
                    token_contract, tradable_exchange_address, block_from
                )
                if tradable_exchange_address != ZERO_ADDRESS:
                    self.exchange_list.append(tradable_exchange_address, block_from)

    async def __sync_all(self, db_session: AsyncSession, block_to: int):
        LOG.info("Syncing to={}".format(block_to))

        await self.__sync_transfer(db_session, block_to)
        await self.__sync_lock(db_session, block_to)
        await self.__sync_unlock(db_session, block_to)
        await self.__sync_issue(db_session, block_to)
        await self.__sync_redeem(db_session, block_to)
        await self.__sync_apply_for_transfer(db_session, block_to)
        await self.__sync_cancel_transfer(db_session, block_to)
        await self.__sync_approve_transfer(db_session, block_to)
        await self.__sync_exchange(db_session, block_to)
        await self.__sync_escrow(db_session, block_to)
        await self.__sync_dvp(db_session, block_to)

        self.__update_cursor(block_to + 1)

    def __update_cursor(self, block_number):
        """Memorize the block number where next processing should start from

        :param block_number: block number to be set
        :return: None
        """
        for target in self.token_list:
            if block_number > target.start_block_number:
                target.cursor = block_number
        for exchange in self.exchange_list:
            if block_number > exchange.start_block_number:
                exchange.cursor = block_number

    async def __sync_transfer(self, db_session: AsyncSession, block_to: int):
        """Sync Transfer Events

        :param db_session: ORM session
        :param block_to: To block
        :return: None
        """
        for target in self.token_list:
            token = target.token_contract
            block_from = target.cursor
            if block_from > block_to:
                continue
            try:
                events: list[LogReceipt] = await token.events.Transfer.get_logs(
                    from_block=block_from, to_block=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                accounts_filtered = self.remove_duplicate_event_by_token_account_desc(
                    events=events, account_keys=["from", "to"]
                )
                if len(accounts_filtered) == 0:
                    continue

                all_eoa_list = [
                    _account
                    for _account in accounts_filtered
                    if _account != target.exchange_address
                ]
                chunked_eoa_list: list[list[str]] = [
                    all_eoa_list[i : i + 1000]
                    for i in range(0, len(all_eoa_list), 1000)
                ]
                for eoa_list in chunked_eoa_list:
                    balances_list = await self.get_bulk_account_balance_for_transfer(
                        token=token,
                        exchange_address=target.exchange_address,
                        accounts=eoa_list,
                    )
                    for balances in balances_list:
                        (
                            _account_address,
                            _balance,
                            _pending_transfer,
                            _exchange_balance,
                        ) = balances
                        await self.__sink_on_position(
                            db_session=db_session,
                            token_address=to_checksum_address(token.address),
                            account_address=_account_address,
                            balance=_balance,
                            pending_transfer=_pending_transfer,
                            exchange_balance=_exchange_balance,
                        )
                    # Commit every 1000 EOAs for bulk transfer
                    await db_session.commit()
            except Exception as e:
                raise e

    async def __sync_lock(self, db_session: AsyncSession, block_to: int):
        """Sync Lock Events

        :param db_session: ORM session
        :param block_to: To block
        :return: None
        """
        for target in self.token_list:
            token = target.token_contract
            block_from = target.cursor
            if block_from > block_to:
                continue
            try:
                events = await token.events.Lock.get_logs(
                    from_block=block_from, to_block=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                lock_map: dict[str, dict[str, True]] = {}
                for event in events:
                    args = event["args"]
                    account_address = args.get("accountAddress", "")
                    lock_address = args.get("lockAddress", "")
                    value = args.get("value", 0)
                    data = args.get("data", "")
                    event_created = await self.__gen_block_timestamp(event=event)
                    tx = await async_web3.eth.get_transaction(event["transactionHash"])
                    msg_sender = tx["from"]

                    # Index Lock event
                    self.__insert_lock_idx(
                        db_session=db_session,
                        transaction_hash=event["transactionHash"].to_0x_hex(),
                        msg_sender=msg_sender,
                        block_number=event["blockNumber"],
                        token_address=token.address,
                        lock_address=lock_address,
                        account_address=account_address,
                        value=value,
                        data_str=data,
                        block_timestamp=event_created,
                    )
                    if lock_address not in lock_map:
                        lock_map[lock_address] = {}
                    lock_map[lock_address][account_address] = True

                for lock_address in lock_map:
                    for account_address in lock_map[lock_address]:
                        # Update Locked Position
                        value = await self.__get_account_locked_token(
                            token, lock_address, account_address
                        )
                        await self.__sink_on_locked_position(
                            db_session=db_session,
                            token_address=to_checksum_address(token.address),
                            lock_address=lock_address,
                            account_address=account_address,
                            value=value,
                        )
            except Exception:
                pass
            try:
                accounts_filtered = self.remove_duplicate_event_by_token_account_desc(
                    events=events, account_keys=["accountAddress"]
                )
                balances_list = await self.get_bulk_account_balance_token(
                    token=token,
                    accounts=accounts_filtered,
                )
                for balances in balances_list:
                    (account, balance, pending_transfer) = balances
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                    )
            except Exception as e:
                raise e

    async def __sync_unlock(self, db_session: AsyncSession, block_to: int):
        """Sync Unlock Events

        :param db_session: ORM session
        :param block_to: To block
        :return: None
        """
        for target in self.token_list:
            token = target.token_contract
            block_from = target.cursor
            if block_from > block_to:
                continue
            try:
                events = await token.events.Unlock.get_logs(
                    from_block=block_from, to_block=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                lock_map: dict[str, dict[str, True]] = {}
                for event in events:
                    args = event["args"]
                    account_address = args.get("accountAddress", "")
                    lock_address = args.get("lockAddress", "")
                    recipient_address = args.get("recipientAddress", "")
                    value = args.get("value", 0)
                    data = args.get("data", "")
                    event_created = await self.__gen_block_timestamp(event=event)
                    tx = await async_web3.eth.get_transaction(event["transactionHash"])
                    msg_sender = tx["from"]

                    # Index Unlock event
                    self.__insert_unlock_idx(
                        db_session=db_session,
                        transaction_hash=event["transactionHash"].to_0x_hex(),
                        msg_sender=msg_sender,
                        block_number=event["blockNumber"],
                        token_address=token.address,
                        lock_address=lock_address,
                        account_address=account_address,
                        recipient_address=recipient_address,
                        value=value,
                        data_str=data,
                        block_timestamp=event_created,
                    )
                    if lock_address not in lock_map:
                        lock_map[lock_address] = {}
                    lock_map[lock_address][account_address] = True

                for lock_address in lock_map:
                    for account_address in lock_map[lock_address]:
                        # Update Locked Position
                        value = await self.__get_account_locked_token(
                            token, lock_address, account_address
                        )
                        await self.__sink_on_locked_position(
                            db_session=db_session,
                            token_address=to_checksum_address(token.address),
                            lock_address=lock_address,
                            account_address=account_address,
                            value=value,
                        )
            except Exception:
                pass
            try:
                accounts_filtered = self.remove_duplicate_event_by_token_account_desc(
                    events=events, account_keys=["recipientAddress"]
                )
                balances_list = await self.get_bulk_account_balance_token(
                    token=token,
                    accounts=accounts_filtered,
                )
                for balances in balances_list:
                    (account, balance, pending_transfer) = balances
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                    )
            except Exception as e:
                raise e

    async def __sync_issue(self, db_session: AsyncSession, block_to: int):
        """Sync Issue Events

        :param db_session: ORM session
        :param block_to: To block
        :return: None
        """
        for target in self.token_list:
            token = target.token_contract
            block_from = target.cursor
            if block_from > block_to:
                continue
            try:
                events = await token.events.Issue.get_logs(
                    from_block=block_from, to_block=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                accounts_filtered = self.remove_duplicate_event_by_token_account_desc(
                    events=events, account_keys=["targetAddress"]
                )
                balances_list = await self.get_bulk_account_balance_token(
                    token=token,
                    accounts=accounts_filtered,
                )
                for balances in balances_list:
                    (account, balance, pending_transfer) = balances
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                    )
            except Exception as e:
                raise e

    async def __sync_redeem(self, db_session: AsyncSession, block_to: int):
        """Sync Redeem Events

        :param db_session: ORM session
        :param block_to: To block
        :return: None
        """
        for target in self.token_list:
            token = target.token_contract
            block_from = target.cursor
            if block_from > block_to:
                continue
            try:
                events = await token.events.Redeem.get_logs(
                    from_block=block_from, to_block=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                accounts_filtered = self.remove_duplicate_event_by_token_account_desc(
                    events=events, account_keys=["targetAddress"]
                )
                balances_list = await self.get_bulk_account_balance_token(
                    token=token,
                    accounts=accounts_filtered,
                )
                for balances in balances_list:
                    (account, balance, pending_transfer) = balances
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                    )
            except Exception as e:
                raise e

    async def __sync_apply_for_transfer(self, db_session: AsyncSession, block_to: int):
        """Sync ApplyForTransfer Events

        :param db_session: ORM session
        :param block_to: To block
        :return: None
        """
        for target in self.token_list:
            token = target.token_contract
            block_from = target.cursor
            if block_from > block_to:
                continue
            try:
                events = await token.events.ApplyForTransfer.get_logs(
                    from_block=block_from, to_block=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                accounts_filtered = self.remove_duplicate_event_by_token_account_desc(
                    events=events, account_keys=["from"]
                )
                balances_list = await self.get_bulk_account_balance_token(
                    token=token,
                    accounts=accounts_filtered,
                )
                for balances in balances_list:
                    (account, balance, pending_transfer) = balances
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                    )
            except Exception as e:
                raise e

    async def __sync_cancel_transfer(self, db_session: AsyncSession, block_to: int):
        """Sync CancelTransfer Events

        :param db_session: ORM session
        :param block_to: To block
        :return: None
        """
        for target in self.token_list:
            token = target.token_contract
            block_from = target.cursor
            if block_from > block_to:
                continue
            try:
                events = await token.events.CancelTransfer.get_logs(
                    from_block=block_from, to_block=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                accounts_filtered = self.remove_duplicate_event_by_token_account_desc(
                    events=events, account_keys=["from"]
                )
                balances_list = await self.get_bulk_account_balance_token(
                    token=token,
                    accounts=accounts_filtered,
                )
                for balances in balances_list:
                    (account, balance, pending_transfer) = balances
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                    )
            except Exception as e:
                raise e

    async def __sync_approve_transfer(self, db_session: AsyncSession, block_to: int):
        """Sync ApproveTransfer Events

        :param db_session: ORM session
        :param block_to: To block
        :return: None
        """
        for target in self.token_list:
            token = target.token_contract
            block_from = target.cursor
            if block_from > block_to:
                continue
            try:
                events = await token.events.ApproveTransfer.get_logs(
                    from_block=block_from, to_block=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                accounts_filtered = self.remove_duplicate_event_by_token_account_desc(
                    events=events, account_keys=["from", "to"]
                )
                balances_list = await self.get_bulk_account_balance_token(
                    token=token,
                    accounts=accounts_filtered,
                )
                for balances in balances_list:
                    (account, balance, pending_transfer) = balances
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                    )
            except Exception as e:
                raise e

    async def __sync_exchange(self, db_session: AsyncSession, block_to: int):
        """Sync Events from IbetExchange

        :param db_session: ORM session
        :param block_to: To block
        :return: None
        """
        for exchange in self.exchange_list:
            block_from = exchange.cursor
            if block_from > block_to:
                continue
            exchange_address = exchange.exchange_address
            try:
                exchange = AsyncContract.get_contract(
                    contract_name="IbetExchange", address=exchange_address
                )

                account_list_tmp = []

                # NewOrder event
                try:
                    _event_list = await exchange.events.NewOrder.get_logs(
                        from_block=block_from, to_block=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("tokenAddress", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "accountAddress", ZERO_ADDRESS
                            ),
                        }
                    )

                # CancelOrder event
                try:
                    _event_list = await exchange.events.CancelOrder.get_logs(
                        from_block=block_from, to_block=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("tokenAddress", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "accountAddress", ZERO_ADDRESS
                            ),
                        }
                    )

                # ForceCancelOrder event
                try:
                    _event_list = await exchange.events.ForceCancelOrder.get_logs(
                        from_block=block_from, to_block=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("tokenAddress", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "accountAddress", ZERO_ADDRESS
                            ),
                        }
                    )

                # Agree event
                try:
                    _event_list = await exchange.events.Agree.get_logs(
                        from_block=block_from, to_block=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("tokenAddress", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "sellAddress", ZERO_ADDRESS
                            ),  # only seller has changed
                        }
                    )

                # SettlementOK event
                try:
                    _event_list = await exchange.events.SettlementOK.get_logs(
                        from_block=block_from, to_block=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("tokenAddress", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "buyAddress", ZERO_ADDRESS
                            ),
                        }
                    )
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "sellAddress", ZERO_ADDRESS
                            ),
                        }
                    )

                # SettlementNG event
                try:
                    _event_list = await exchange.events.SettlementNG.get_logs(
                        from_block=block_from, to_block=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("tokenAddress", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "sellAddress", ZERO_ADDRESS
                            ),  # only seller has changed
                        }
                    )

                # Make temporary list unique
                account_list_tmp.sort(
                    key=lambda x: (x["token_address"], x["account_address"])
                )
                account_list_unfiltered = []
                for k, g in groupby(
                    account_list_tmp,
                    lambda x: (x["token_address"], x["account_address"]),
                ):
                    account_list_unfiltered.append(
                        {"token_address": k[0], "account_address": k[1]}
                    )

                # Filter account_list by listed token
                token_address_list = [t.token_contract.address for t in self.token_list]
                account_list = []
                for _account in account_list_unfiltered:
                    if _account["token_address"] in token_address_list:
                        account_list.append(_account)

                balances_list = await self.get_bulk_account_balance_exchange(
                    exchange_address=exchange_address,
                    accounts=account_list,
                )
                # Update position
                for balances in balances_list:
                    (
                        token_address,
                        account_address,
                        exchange_balance,
                        exchange_commitment,
                    ) = balances
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=token_address,
                        account_address=account_address,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment,
                    )
            except Exception as e:
                raise e

    async def __sync_escrow(self, db_session: AsyncSession, block_to: int):
        """Sync Events from IbetSecurityTokenEscrow

        :param db_session: ORM session
        :param block_to: To block
        :return: None
        """
        for exchange in self.exchange_list:
            block_from = exchange.cursor
            if block_from > block_to:
                continue
            exchange_address = exchange.exchange_address
            try:
                escrow = AsyncContract.get_contract(
                    "IbetSecurityTokenEscrow", exchange_address
                )

                account_list_tmp = []

                # EscrowCreated event
                try:
                    _event_list = await escrow.events.EscrowCreated.get_logs(
                        from_block=block_from, to_block=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("token", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get(
                                "sender", ZERO_ADDRESS
                            ),  # only sender has changed
                        }
                    )

                # EscrowCanceled event
                try:
                    _event_list = await escrow.events.EscrowCanceled.get_logs(
                        from_block=block_from, to_block=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("token", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get(
                                "sender", ZERO_ADDRESS
                            ),  # only sender has changed
                        }
                    )

                # HolderChanged event
                try:
                    _event_list = await escrow.events.HolderChanged.get_logs(
                        from_block=block_from, to_block=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("token", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get("from", ZERO_ADDRESS),
                        }
                    )
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get("to", ZERO_ADDRESS),
                        }
                    )

                # Make temporary list unique
                account_list_tmp.sort(
                    key=lambda x: (x["token_address"], x["account_address"])
                )
                account_list_unfiltered = []
                for k, g in groupby(
                    account_list_tmp,
                    lambda x: (x["token_address"], x["account_address"]),
                ):
                    account_list_unfiltered.append(
                        {"token_address": k[0], "account_address": k[1]}
                    )

                # Filter account_list by listed token
                token_address_list = [t.token_contract.address for t in self.token_list]
                account_list = []
                for _account in account_list_unfiltered:
                    if _account["token_address"] in token_address_list:
                        account_list.append(_account)

                balances_list = await self.get_bulk_account_balance_exchange(
                    exchange_address=exchange_address,
                    accounts=account_list,
                )
                # Update position
                for balances in balances_list:
                    (
                        token_address,
                        account_address,
                        exchange_balance,
                        exchange_commitment,
                    ) = balances
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=token_address,
                        account_address=account_address,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment,
                    )
            except Exception as e:
                raise e

    async def __sync_dvp(self, db_session: AsyncSession, block_to: int):
        """Sync Events from IbetSecurityTokenDVP

        :param db_session: ORM session
        :param block_to: To block
        :return: None
        """
        for exchange in self.exchange_list:
            block_from = exchange.cursor
            if block_from > block_to:
                continue
            exchange_address = exchange.exchange_address
            try:
                dvp = AsyncContract.get_contract(
                    "IbetSecurityTokenDVP", exchange_address
                )

                account_list_tmp = []

                # DeliveryCreated event
                try:
                    _event_list = await dvp.events.DeliveryCreated.get_logs(
                        from_block=block_from, to_block=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("token", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get(
                                "seller", ZERO_ADDRESS
                            ),  # only seller has changed
                        }
                    )

                # DeliveryCanceled event
                try:
                    _event_list = await dvp.events.DeliveryCanceled.get_logs(
                        from_block=block_from, to_block=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("token", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get(
                                "seller", ZERO_ADDRESS
                            ),  # only seller has changed
                        }
                    )

                # DeliveryAborted event
                try:
                    _event_list = await dvp.events.DeliveryAborted.get_logs(
                        from_block=block_from, to_block=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("token", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get(
                                "seller", ZERO_ADDRESS
                            ),  # only seller has changed
                        }
                    )

                    # HolderChanged event
                try:
                    _event_list = await dvp.events.HolderChanged.get_logs(
                        from_block=block_from, to_block=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("token", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get("from", ZERO_ADDRESS),
                        }
                    )
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get("to", ZERO_ADDRESS),
                        }
                    )

                # Make temporary list unique
                account_list_tmp.sort(
                    key=lambda x: (x["token_address"], x["account_address"])
                )
                account_list_unfiltered = []
                for k, g in groupby(
                    account_list_tmp,
                    lambda x: (x["token_address"], x["account_address"]),
                ):
                    account_list_unfiltered.append(
                        {"token_address": k[0], "account_address": k[1]}
                    )

                # Filter account_list by listed token
                token_address_list = [t.token_contract.address for t in self.token_list]
                account_list = []
                for _account in account_list_unfiltered:
                    if _account["token_address"] in token_address_list:
                        account_list.append(_account)

                balances_list = await self.get_bulk_account_balance_exchange(
                    exchange_address=exchange_address,
                    accounts=account_list,
                )
                # Update position
                for balances in balances_list:
                    (
                        token_address,
                        account_address,
                        exchange_balance,
                        exchange_commitment,
                    ) = balances
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=token_address,
                        account_address=account_address,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment,
                    )
            except Exception as e:
                raise e

    @staticmethod
    async def __gen_block_timestamp(event):
        return datetime.fromtimestamp(
            (await async_web3.eth.get_block(event["blockNumber"]))["timestamp"], UTC
        )

    @staticmethod
    def __get_oldest_cursor(target_token_list: TargetTokenList, block_to: int) -> int:
        """Get the oldest block number for given target token list"""
        oldest_block_number = block_to
        if len(target_token_list) == 0:
            return 0
        for target_token in target_token_list:
            if target_token.cursor < oldest_block_number:
                oldest_block_number = target_token.cursor
        return oldest_block_number

    @staticmethod
    async def __get_idx_position_block_number(
        db_session: AsyncSession, token_address: str, exchange_address: str
    ):
        """Get position index for Bond"""
        _idx_position_block_number = (
            await db_session.scalars(
                select(IDXPositionBondBlockNumber)
                .where(IDXPositionBondBlockNumber.token_address == token_address)
                .where(IDXPositionBondBlockNumber.exchange_address == exchange_address)
                .limit(1)
            )
        ).first()
        if _idx_position_block_number is None:
            return -1
        else:
            return _idx_position_block_number.latest_block_number

    @staticmethod
    async def __set_idx_position_block_number(
        db_session: AsyncSession, target_token_list: TargetTokenList, block_number: int
    ):
        """Set position index for Bond"""
        for target_token in target_token_list:
            _idx_position_block_number = (
                await db_session.scalars(
                    select(IDXPositionBondBlockNumber)
                    .where(
                        IDXPositionBondBlockNumber.token_address
                        == target_token.token_contract.address
                    )
                    .where(
                        IDXPositionBondBlockNumber.exchange_address
                        == target_token.exchange_address
                    )
                    .limit(1)
                )
            ).first()
            if _idx_position_block_number is None:
                _idx_position_block_number = IDXPositionBondBlockNumber()
            _idx_position_block_number.latest_block_number = block_number
            _idx_position_block_number.token_address = (
                target_token.token_contract.address
            )
            _idx_position_block_number.exchange_address = target_token.exchange_address
            await db_session.merge(_idx_position_block_number)

    @staticmethod
    async def __get_account_balance_for_transfer(
        token_contract, exchange_address: str, account_address: str
    ):
        """Get balance"""
        try:

            async def return_zero():
                return 0

            tasks = await SemaphoreTaskGroup.run(
                AsyncContract.call_function(
                    contract=token_contract,
                    function_name="balanceOf",
                    args=(account_address,),
                    default_returns=0,
                ),
                AsyncContract.call_function(
                    contract=token_contract,
                    function_name="pendingTransfer",
                    args=(account_address,),
                    default_returns=0,
                ),
                AsyncContract.call_function(
                    contract=AsyncContract.get_contract(
                        "IbetExchangeInterface", exchange_address
                    ),
                    function_name="balanceOf",
                    args=(
                        account_address,
                        token_contract.address,
                    ),
                    default_returns=0,
                )
                if exchange_address != ZERO_ADDRESS
                else return_zero(),
                max_concurrency=3,
            )
            balance, pending_transfer, exchange_balance = (
                tasks[0].result(),
                tasks[1].result(),
                tasks[2].result(),
            )
        except ExceptionGroup:
            raise ServiceUnavailable

        return (
            account_address,
            balance,
            pending_transfer,
            exchange_balance,
        )

    @staticmethod
    async def __get_account_balance_token(token_contract, account_address: str):
        """Get balance on token"""
        try:
            tasks = await SemaphoreTaskGroup.run(
                AsyncContract.call_function(
                    contract=token_contract,
                    function_name="balanceOf",
                    args=(account_address,),
                    default_returns=0,
                ),
                AsyncContract.call_function(
                    contract=token_contract,
                    function_name="pendingTransfer",
                    args=(account_address,),
                    default_returns=0,
                ),
                max_concurrency=3,
            )
            balance, pending_transfer = (tasks[0].result(), tasks[1].result())
        except ExceptionGroup:
            raise ServiceUnavailable
        return account_address, balance, pending_transfer

    @staticmethod
    async def __get_account_locked_token(
        token_contract, lock_address: str, account_address: str
    ):
        """Get locked on token"""
        value = await AsyncContract.call_function(
            contract=token_contract,
            function_name="lockedOf",
            args=(
                lock_address,
                account_address,
            ),
            default_returns=0,
        )
        return value

    @staticmethod
    async def __get_account_balance_exchange(
        exchange_address: str, token_address: str, account_address: str
    ):
        """Get balance on exchange"""
        exchange_contract = AsyncContract.get_contract(
            contract_name="IbetExchangeInterface", address=exchange_address
        )
        try:
            tasks = await SemaphoreTaskGroup.run(
                AsyncContract.call_function(
                    contract=exchange_contract,
                    function_name="balanceOf",
                    args=(
                        account_address,
                        token_address,
                    ),
                    default_returns=0,
                ),
                AsyncContract.call_function(
                    contract=exchange_contract,
                    function_name="commitmentOf",
                    args=(
                        account_address,
                        token_address,
                    ),
                    default_returns=0,
                ),
                max_concurrency=3,
            )
            exchange_balance, exchange_commitment = (
                tasks[0].result(),
                tasks[1].result(),
            )
        except ExceptionGroup:
            raise ServiceUnavailable
        return token_address, account_address, exchange_balance, exchange_commitment

    @staticmethod
    def __insert_lock_idx(
        db_session: AsyncSession,
        transaction_hash: str,
        msg_sender: str,
        block_number: int,
        token_address: str,
        lock_address: str,
        account_address: str,
        value: int,
        data_str: str,
        block_timestamp: datetime,
    ):
        """Registry Lock data in DB

        :param transaction_hash: transaction hash
        :param msg_sender: message sender
        :param token_address: token address
        :param lock_address: lock address
        :param account_address: account address
        :param value: amount
        :param data_str: data string
        :param block_timestamp: block timestamp
        :return: None
        """
        try:
            data = json.loads(data_str)
        except Exception:
            data = {}
        lock = IDXLock()
        lock.transaction_hash = transaction_hash
        lock.msg_sender = msg_sender
        lock.block_number = block_number
        lock.token_address = token_address
        lock.lock_address = lock_address
        lock.account_address = account_address
        lock.value = value
        lock.data = data
        lock.block_timestamp = block_timestamp
        db_session.add(lock)

    @staticmethod
    def __insert_unlock_idx(
        db_session: AsyncSession,
        transaction_hash: str,
        msg_sender: str,
        block_number: int,
        token_address: str,
        lock_address: str,
        account_address: str,
        recipient_address: str,
        value: int,
        data_str: str,
        block_timestamp: datetime,
    ):
        """Registry Unlock data in DB

        :param transaction_hash: transaction hash
        :param msg_sender: message sender
        :param token_address: token address
        :param lock_address: lock address
        :param account_address: account address
        :param recipient_address: recipient address
        :param value: amount
        :param data_str: data string
        :param block_timestamp: block timestamp
        :return: None
        """
        try:
            data = json.loads(data_str)
        except:
            data = {}
        unlock = IDXUnlock()
        unlock.transaction_hash = transaction_hash
        unlock.msg_sender = msg_sender
        unlock.block_number = block_number
        unlock.token_address = token_address
        unlock.lock_address = lock_address
        unlock.account_address = account_address
        unlock.recipient_address = recipient_address
        unlock.value = value
        unlock.data = data
        unlock.block_timestamp = block_timestamp
        db_session.add(unlock)

    @staticmethod
    async def __sink_on_position(
        db_session: AsyncSession,
        token_address: str,
        account_address: str,
        balance: Optional[int] = None,
        pending_transfer: Optional[int] = None,
        exchange_balance: Optional[int] = None,
        exchange_commitment: Optional[int] = None,
    ):
        """Update Position data in DB

        :param db_session: ORM session
        :param token_address: token address
        :param account_address: account address
        :param balance: updated balance
        :param pending_transfer: updated pending_transfer
        :param exchange_balance: balance on exchange
        :param exchange_commitment: commitment volume on exchange
        :return: None
        """
        position = (
            await db_session.scalars(
                select(IDXPosition)
                .where(IDXPosition.token_address == token_address)
                .where(IDXPosition.account_address == account_address)
                .limit(1)
            )
        ).first()
        if position is not None:
            if balance is not None:
                position.balance = balance
            if pending_transfer is not None:
                position.pending_transfer = pending_transfer
            if exchange_balance is not None:
                position.exchange_balance = exchange_balance
            if exchange_commitment is not None:
                position.exchange_commitment = exchange_commitment
            await db_session.merge(position)
        elif any(
            value is not None and value > 0
            for value in [
                balance,
                pending_transfer,
                exchange_balance,
                exchange_commitment,
            ]
        ):
            LOG.debug(
                f"Position created (Bond): token_address={token_address}, account_address={account_address}"
            )
            position = IDXPosition()
            position.token_address = token_address
            position.account_address = account_address
            position.balance = balance or 0
            position.pending_transfer = pending_transfer or 0
            position.exchange_balance = exchange_balance or 0
            position.exchange_commitment = exchange_commitment or 0
            db_session.add(position)

    @staticmethod
    async def __sink_on_locked_position(
        db_session: AsyncSession,
        token_address: str,
        lock_address: str,
        account_address: str,
        value: int,
    ):
        """Update Locked position in DB

        :param db_session: ORM session
        :param token_address: token address
        :param lock_address: account address
        :param account_address: account address
        :param value: updated locked amount
        :return: None
        """
        locked = (
            await db_session.scalars(
                select(IDXLockedPosition)
                .where(IDXLockedPosition.token_address == token_address)
                .where(IDXLockedPosition.lock_address == lock_address)
                .where(IDXLockedPosition.account_address == account_address)
                .limit(1)
            )
        ).first()
        if locked is not None:
            locked.value = value
            await db_session.merge(locked)
        else:
            locked = IDXLockedPosition()
            locked.token_address = token_address
            locked.lock_address = lock_address
            locked.account_address = account_address
            locked.value = value
            db_session.add(locked)

    @staticmethod
    def remove_duplicate_event_by_token_account_desc(
        events: List, account_keys: List[str]
    ) -> List[str]:
        """Remove duplicate account from event list.
        Events that have same account key will be removed.

        :param events: event list
        :param account_keys: keys in which event contains account address
        :return: account_list: account_list list filtered
        """
        event_account_list = []

        # reversed events loop for removing duplicates from the front
        for event in reversed(events):
            args = event["args"]
            for arg_key in account_keys:
                account_address = args.get(arg_key, ZERO_ADDRESS)
                if account_address != ZERO_ADDRESS:
                    event_account_list.append(account_address)
        seen = set()
        remove_duplicate_list = []
        for record in event_account_list:
            if record not in seen:
                remove_duplicate_list.append(record)
                seen.add(record)

        # return events in original order
        return list(reversed(remove_duplicate_list))

    async def get_bulk_account_balance_for_transfer(
        self, token, exchange_address, accounts
    ):
        coroutines = [
            self.__get_account_balance_for_transfer(token, exchange_address, _account)
            for _account in accounts
        ]
        if not coroutines:
            return []

        try:
            tasks = await SemaphoreTaskGroup.run(*coroutines, max_concurrency=5)
            return [task.result() for task in tasks]
        except ExceptionGroup:
            raise ServiceUnavailable

    async def get_bulk_account_balance_token(self, token, accounts):
        coroutines = [
            self.__get_account_balance_token(token, _account) for _account in accounts
        ]
        if not coroutines:
            return []

        try:
            tasks = await SemaphoreTaskGroup.run(*coroutines, max_concurrency=5)
            return [task.result() for task in tasks]
        except ExceptionGroup:
            raise ServiceUnavailable

    async def get_bulk_account_balance_exchange(self, exchange_address, accounts):
        coroutines = [
            self.__get_account_balance_exchange(
                exchange_address, _account["token_address"], _account["account_address"]
            )
            for _account in accounts
        ]
        if not coroutines:
            return []

        try:
            tasks = await SemaphoreTaskGroup.run(*coroutines, max_concurrency=5)
            return [task.result() for task in tasks]
        except ExceptionGroup:
            raise ServiceUnavailable


async def main():
    LOG.info("Service started successfully")
    processor = Processor()

    initial_synced_completed = False
    while not initial_synced_completed:
        try:
            await processor.initial_sync()
            initial_synced_completed = True
        except Exception:
            LOG.exception("Initial sync failed")

        await asyncio.sleep(10)

    while True:
        try:
            await processor.sync_new_logs()
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception("An exception occurred during event synchronization")

        await asyncio.sleep(10)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
