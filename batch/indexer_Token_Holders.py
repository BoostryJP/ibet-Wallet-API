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
import sys
from typing import Dict, Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.eth.async_eth import AsyncContract as Web3AsyncContract
from web3.exceptions import ABIEventNotFound

from app.config import TOKEN_LIST_CONTRACT_ADDRESS, ZERO_ADDRESS
from app.contracts import AsyncContract
from app.database import BatchAsyncSessionLocal
from app.errors import ServiceUnavailable
from app.model.db import TokenHolder, TokenHolderBatchStatus, TokenHoldersList
from app.model.schema.base import TokenType
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import free_malloc, log
from batch.lib.token_list import TokenList

process_name = "INDEXER-TOKEN_HOLDERS"
LOG = log.get_logger(process_name=process_name)

async_web3 = AsyncWeb3Wrapper()


class Processor:
    """Processor for collecting Token Holders at given block number and token."""

    class BalanceBook:
        pages: Dict[str, TokenHolder]

        def __init__(self):
            self.pages = {}

        def store(self, account_address: str, amount: int = 0, locked: int = 0):
            if account_address not in self.pages:
                token_holder = TokenHolder()
                token_holder.hold_balance = 0 + amount
                token_holder.account_address = account_address
                token_holder.locked_balance = 0 + locked
                self.pages[account_address] = token_holder
            else:
                self.pages[account_address].hold_balance += amount
                self.pages[account_address].locked_balance += locked

    target: Optional[TokenHoldersList]
    balance_book: BalanceBook

    tradable_exchange_address: str
    token_owner_address: str
    token_template: str

    token_contract: Optional[Web3AsyncContract]
    exchange_contract: Optional[Web3AsyncContract]
    escrow_contract: Optional[Web3AsyncContract]

    def __init__(self):
        self.target = None
        self.balance_book = self.BalanceBook()
        self.tradable_exchange_address = ""

    @staticmethod
    def __get_db_session() -> AsyncSession:
        return BatchAsyncSessionLocal()

    async def __load_target(self, db_session: AsyncSession) -> bool:
        self.target: TokenHoldersList = (
            await db_session.scalars(
                select(TokenHoldersList)
                .where(
                    TokenHoldersList.batch_status
                    == TokenHolderBatchStatus.PENDING.value
                )
                .limit(1)
            )
        ).first()
        return True if self.target else False

    async def __load_token_info(self) -> bool:
        # Fetch token list information from TokenList Contract
        list_contract = AsyncContract.get_contract(
            contract_name="TokenList", address=TOKEN_LIST_CONTRACT_ADDRESS
        )
        token_info = await TokenList(list_contract).get_token(self.target.token_address)
        self.token_owner_address = token_info[2]
        # Store token contract.
        if token_info[1] == TokenType.IbetCoupon:
            self.token_contract = AsyncContract.get_contract(
                TokenType.IbetCoupon, self.target.token_address
            )
        elif token_info[1] == TokenType.IbetMembership:
            self.token_contract = AsyncContract.get_contract(
                TokenType.IbetMembership, self.target.token_address
            )
        elif token_info[1] == TokenType.IbetStraightBond:
            self.token_contract = AsyncContract.get_contract(
                TokenType.IbetStraightBond, self.target.token_address
            )
        elif token_info[1] == TokenType.IbetShare:
            self.token_contract = AsyncContract.get_contract(
                TokenType.IbetShare, self.target.token_address
            )
        else:
            return False
        self.token_template = token_info[1]

        # Fetch current tradable exchange to store exchange contract.
        self.tradable_exchange_address = await AsyncContract.call_function(
            contract=self.token_contract,
            function_name="tradableExchange",
            args=(),
            default_returns=ZERO_ADDRESS,
        )
        self.exchange_contract = AsyncContract.get_contract(
            contract_name="IbetExchangeInterface",
            address=self.tradable_exchange_address,
        )
        return True

    async def __load_checkpoint(
        self, local_session: AsyncSession, target_token_address: str, block_to: int
    ) -> int:
        _checkpoint: Optional[TokenHoldersList] = (
            await local_session.scalars(
                select(TokenHoldersList)
                .where(TokenHoldersList.token_address == target_token_address)
                .where(TokenHoldersList.block_number < block_to)
                .where(
                    TokenHoldersList.batch_status == TokenHolderBatchStatus.DONE.value
                )
                .order_by(TokenHoldersList.block_number.desc())
                .limit(1)
            )
        ).first()
        if _checkpoint:
            _holders: Sequence[TokenHolder] = (
                await local_session.scalars(
                    select(TokenHolder).where(TokenHolder.holder_list == _checkpoint.id)
                )
            ).all()
            for holder in _holders:
                self.balance_book.store(
                    account_address=holder.account_address,
                    amount=holder.hold_balance,
                    locked=holder.locked_balance,
                )
            block_from = _checkpoint.block_number + 1
            return block_from
        return 0

    async def collect(self):
        local_session = self.__get_db_session()
        try:
            if not await self.__load_target(local_session):
                LOG.debug("There are no pending collect batch")
                return
            if not await self.__load_token_info():
                LOG.debug("Token contract must be listed to TokenList contract.")
                await self.__update_status(local_session, TokenHolderBatchStatus.FAILED)
                await local_session.commit()
                return

            _target_block = self.target.block_number
            _from_block = await self.__load_checkpoint(
                local_session,
                target_token_address=self.target.token_address,
                block_to=_target_block,
            )
            _to_block = 999999 + _from_block
            if _target_block > _to_block:
                while _to_block < _target_block:
                    await self.__process_all(
                        db_session=local_session,
                        block_from=_from_block,
                        block_to=_to_block,
                    )
                    _from_block += 1000000
                    _to_block += 1000000
                await self.__process_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=_target_block,
                )
            else:
                await self.__process_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=_target_block,
                )
            await self.__update_status(local_session, TokenHolderBatchStatus.DONE)
            await local_session.commit()
            LOG.info("Collect job has been completed")
        except Exception as e:
            await local_session.rollback()
            await self.__update_status(local_session, TokenHolderBatchStatus.FAILED)
            await local_session.commit()
            raise e
        finally:
            await local_session.close()

    async def __update_status(
        self, local_session: AsyncSession, status: TokenHolderBatchStatus
    ):
        if status == TokenHolderBatchStatus.DONE:
            # Not to store non-holders
            (
                await local_session.execute(
                    delete(TokenHolder)
                    .where(TokenHolder.holder_list == self.target.id)
                    .where(TokenHolder.hold_balance == 0)
                    .where(TokenHolder.locked_balance == 0)
                )
            )

        self.target.batch_status = status.value
        await local_session.merge(self.target)
        LOG.info(
            f"Token holder list({self.target.list_id}) status changes to be {status.value}."
        )

        self.target = None
        self.balance_book = self.BalanceBook()
        self.tradable_exchange_address = ""
        self.token_owner_address = ""
        self.token_template = ""
        self.token_contract = None
        self.exchange_contract = None
        self.escrow_contract = None

    async def __process_all(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        LOG.info("process from={}, to={}".format(block_from, block_to))

        await self.__process_transfer(block_from, block_to)
        await self.__process_issue(block_from, block_to)
        await self.__process_redeem(block_from, block_to)
        if self.token_template in [TokenType.IbetStraightBond, TokenType.IbetShare]:
            await self.__process_lock(block_from, block_to)
            await self.__process_force_lock(block_from, block_to)
            await self.__process_unlock(block_from, block_to)
            await self.__process_force_unlock(block_from, block_to)
            await self.__process_force_change_locked_account(block_from, block_to)
        if self.token_template == TokenType.IbetCoupon:
            await self.__process_consume(block_from, block_to)

        await self.__save_holders(
            db_session,
            self.balance_book,
            self.target.id,
            self.target.token_address,
            self.token_owner_address,
        )

    async def __process_transfer(self, block_from: int, block_to: int):
        """Process Transfer Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Transfer` event on Token contracts
        - `HolderChanged` event on Exchange contracts

        :param block_from: Block from
        :param block_to: Block to
        :return: None
        """
        try:
            tmp_events = []

            # Get "HolderChanged" events from exchange contract
            exchange_contract: Web3AsyncContract = AsyncContract.get_contract(
                contract_name="IbetExchangeInterface",
                address=self.tradable_exchange_address,
            )
            try:
                holder_changed_events = (
                    await exchange_contract.events.HolderChanged.get_logs(
                        from_block=block_from,
                        to_block=block_to,
                        argument_filters={"token": self.token_contract.address},
                    )
                )
            except ABIEventNotFound:
                holder_changed_events = []

            for _event in holder_changed_events:
                if self.token_contract.address == _event["args"]["token"]:
                    tmp_events.append(
                        {
                            "event": _event["event"],
                            "args": dict(_event["args"]),
                            "transaction_hash": _event["transactionHash"].to_0x_hex(),
                            "block_number": _event["blockNumber"],
                            "log_index": _event["logIndex"],
                        }
                    )

            # Get "Transfer" events from token contract
            try:
                token_transfer_events = (
                    await self.token_contract.events.Transfer.get_logs(
                        from_block=block_from, to_block=block_to
                    )
                )
            except ABIEventNotFound:
                token_transfer_events = []

            for _event in token_transfer_events:
                tmp_events.append(
                    {
                        "event": _event["event"],
                        "args": dict(_event["args"]),
                        "transaction_hash": _event["transactionHash"].to_0x_hex(),
                        "block_number": _event["blockNumber"],
                        "log_index": _event["logIndex"],
                    }
                )

            # Marge & Sort: block_number > log_index
            events = sorted(
                tmp_events, key=lambda x: (x["block_number"], x["log_index"])
            )

            for event in events:
                args = event["args"]
                from_account = args.get("from", ZERO_ADDRESS)
                to_account = args.get("to", ZERO_ADDRESS)
                amount = int(args.get("value"))

                # Skip in case of deposit to exchange or withdrawal from exchange
                if (
                    await async_web3.eth.get_code(from_account)
                ).to_0x_hex() != "0x" or (
                    await async_web3.eth.get_code(to_account)
                ).to_0x_hex() != "0x":
                    continue

                if amount is not None and amount <= sys.maxsize:
                    # Update Balance（from account）
                    self.balance_book.store(
                        account_address=from_account, amount=-amount
                    )
                    # Update Balance（to account）
                    self.balance_book.store(account_address=to_account, amount=+amount)

        except Exception:
            raise

    async def __process_issue(self, block_from: int, block_to: int):
        """Process Issue Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Issue` event on Token contracts

        :param block_from: Block from
        :param block_to: Block to
        :return: None
        """
        try:
            # Get "Issue" events from token contract
            events = await self.token_contract.events.Issue.get_logs(
                from_block=block_from, to_block=block_to
            )
        except ABIEventNotFound:
            events = []
        try:
            for event in events:
                args = event["args"]
                account_address = args.get("targetAddress", ZERO_ADDRESS)
                lock_address = args.get("lockAddress", ZERO_ADDRESS)
                amount = args.get("amount")
                if lock_address == ZERO_ADDRESS:
                    if amount is not None and amount <= sys.maxsize:
                        # Update Balance
                        self.balance_book.store(
                            account_address=account_address, amount=+amount
                        )

        except Exception:
            raise

    async def __process_redeem(self, block_from: int, block_to: int):
        """Process Redeem Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Redeem` event on Token contracts

        :param block_from: Block from
        :param block_to: Block to
        :return: None
        """
        try:
            # Get "Redeem" events from token contract
            events = await self.token_contract.events.Redeem.get_logs(
                from_block=block_from, to_block=block_to
            )
        except ABIEventNotFound:
            events = []
        try:
            for event in events:
                args = event["args"]
                account_address = args.get("targetAddress", ZERO_ADDRESS)
                lock_address = args.get("lockAddress", ZERO_ADDRESS)
                amount = args.get("amount")
                if lock_address == ZERO_ADDRESS:
                    if amount is not None and amount <= sys.maxsize:
                        # Update Balance
                        self.balance_book.store(
                            account_address=account_address, amount=-amount
                        )
        except Exception:
            raise

    async def __process_consume(self, block_from: int, block_to: int):
        """Process Consume Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Consume` event on Token contracts

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            # Get "Consume" events from token contract
            events = await self.token_contract.events.Consume.get_logs(
                from_block=block_from, to_block=block_to
            )
        except ABIEventNotFound:
            events = []
        try:
            for event in events:
                args = event["args"]
                account = args.get("consumer", ZERO_ADDRESS)
                amount = args.get("value", ZERO_ADDRESS)
                self.balance_book.store(account_address=account, amount=-amount)
        except Exception:
            raise

    async def __process_lock(self, block_from: int, block_to: int):
        """Process Lock Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Lock` event on Token contracts

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            # Get "Lock" events from token contract
            events = await self.token_contract.events.Lock.get_logs(
                from_block=block_from, to_block=block_to
            )
        except ABIEventNotFound:
            events = []
        try:
            for event in events:
                args = event["args"]
                account_address = args.get("accountAddress", ZERO_ADDRESS)
                amount = args.get("value")
                if amount is not None and amount <= sys.maxsize:
                    self.balance_book.store(
                        account_address=account_address, amount=-amount, locked=+amount
                    )
        except Exception:
            raise

    async def __process_force_lock(self, block_from: int, block_to: int):
        """Process Force Lock Event

        - The process of updating Hold-Balance data by capturing the following events
        - `ForceLock` event on Token contracts

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            # Get "Lock" events from token contract
            events = await self.token_contract.events.ForceLock.get_logs(
                from_block=block_from, to_block=block_to
            )
        except ABIEventNotFound:
            events = []
        try:
            for event in events:
                args = event["args"]
                account_address = args.get("accountAddress", ZERO_ADDRESS)
                amount = args.get("value")
                if amount is not None and amount <= sys.maxsize:
                    self.balance_book.store(
                        account_address=account_address, amount=-amount, locked=+amount
                    )
        except Exception:
            raise

    async def __process_unlock(self, block_from: int, block_to: int):
        """Process Unlock Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Unlock` event on Token contracts

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            # Get "Unlock" events from token contract
            events = await self.token_contract.events.Unlock.get_logs(
                from_block=block_from, to_block=block_to
            )
        except ABIEventNotFound:
            events = []
        try:
            for event in events:
                args = event["args"]
                account_address = args.get("accountAddress", ZERO_ADDRESS)
                recipient_address = args.get("recipientAddress", ZERO_ADDRESS)
                amount = args.get("value")
                if amount is not None and amount <= sys.maxsize:
                    self.balance_book.store(
                        account_address=account_address, locked=-amount
                    )
                    self.balance_book.store(
                        account_address=recipient_address, amount=+amount
                    )
        except Exception:
            raise

    async def __process_force_unlock(self, block_from: int, block_to: int):
        """Process ForceUnlock Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Unlock` event on Token contracts

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            # Get "ForceUnlock" events from token contract
            events = await self.token_contract.events.ForceUnlock.get_logs(
                from_block=block_from, to_block=block_to
            )
        except ABIEventNotFound:
            events = []
        try:
            for event in events:
                args = event["args"]
                account_address = args.get("accountAddress", ZERO_ADDRESS)
                recipient_address = args.get("recipientAddress", ZERO_ADDRESS)
                amount = args.get("value")
                if amount is not None and amount <= sys.maxsize:
                    self.balance_book.store(
                        account_address=account_address, locked=-amount
                    )
                    self.balance_book.store(
                        account_address=recipient_address, amount=+amount
                    )
        except Exception:
            raise

    async def __process_force_change_locked_account(
        self, block_from: int, block_to: int
    ):
        """Process ForceChangeLockedAccount Event

        - The process of updating Hold-Balance data by capturing the following events
        - `ForceChangeLockedAccount` event on Token contracts

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            # Get "ForceChangeLockedAccount" events from token contract
            events = await self.token_contract.events.ForceChangeLockedAccount.get_logs(
                from_block=block_from, to_block=block_to
            )
        except ABIEventNotFound:
            events = []
        try:
            for event in events:
                args = event["args"]
                before_account_address = args.get("beforeAccountAddress", ZERO_ADDRESS)
                after_account_address = args.get("afterAccountAddress", ZERO_ADDRESS)
                amount = args.get("value")
                if amount is not None and amount <= sys.maxsize:
                    self.balance_book.store(
                        account_address=before_account_address, locked=-amount
                    )
                    self.balance_book.store(
                        account_address=after_account_address, locked=+amount
                    )
        except Exception:
            raise

    @staticmethod
    async def __save_holders(
        db_session: AsyncSession,
        balance_book: BalanceBook,
        holder_list_id: int,
        token_address: str,
        token_owner_address: str,
    ):
        for account_address, page in zip(
            balance_book.pages.keys(), balance_book.pages.values()
        ):
            if page.account_address == token_owner_address:
                # Skip storing data for token owner
                continue
            token_holder: Optional[TokenHolder] = (
                await db_session.scalars(
                    select(TokenHolder)
                    .where(TokenHolder.holder_list == holder_list_id)
                    .where(TokenHolder.account_address == account_address)
                    .limit(1)
                )
            ).first()
            if token_holder is not None:
                token_holder.hold_balance = page.hold_balance
                token_holder.locked_balance = page.locked_balance
                await db_session.merge(token_holder)
            elif page.hold_balance > 0 or page.locked_balance > 0:
                LOG.debug(
                    f"Collection record created : token_address={token_address}, account_address={account_address}"
                )
                page.holder_list = holder_list_id
                db_session.add(page)


async def main():
    LOG.info("Service started successfully")
    processor = Processor()
    while True:
        try:
            await processor.collect()
        except ServiceUnavailable:
            LOG.notice("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An exception occurred during event synchronization")

        await asyncio.sleep(10)
        free_malloc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
