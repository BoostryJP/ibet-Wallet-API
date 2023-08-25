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
import os
import sys
import time
from typing import Dict, Optional, Sequence

import log
from sqlalchemy import create_engine, delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from web3.contract import Contract
from web3.exceptions import ABIEventFunctionNotFound

from app.model.schema.base import TokenType

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app.config import DATABASE_URL, TOKEN_LIST_CONTRACT_ADDRESS, ZERO_ADDRESS
from app.contracts import Contract as ContractOperator
from app.errors import ServiceUnavailable
from app.model.db import TokenHolder, TokenHolderBatchStatus, TokenHoldersList
from app.utils.web3_utils import Web3Wrapper
from batch.lib.token_list import TokenList

process_name = "INDEXER-TOKEN_HOLDERS"
LOG = log.get_logger(process_name=process_name)

web3 = Web3Wrapper()
db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


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

    token_contract: Optional[Contract]
    exchange_contract: Optional[Contract]
    escrow_contract: Optional[Contract]

    def __init__(self):
        self.target = None
        self.balance_book = self.BalanceBook()
        self.tradable_exchange_address = ""

    @staticmethod
    def __get_db_session() -> Session:
        return Session(autocommit=False, autoflush=True, bind=db_engine)

    def __load_target(self, db_session: Session) -> bool:
        self.target: TokenHoldersList = db_session.scalars(
            select(TokenHoldersList)
            .where(
                TokenHoldersList.batch_status == TokenHolderBatchStatus.PENDING.value
            )
            .limit(1)
        ).first()
        return True if self.target else False

    def __load_token_info(self) -> bool:
        # Fetch token list information from TokenList Contract
        list_contract = ContractOperator.get_contract(
            contract_name="TokenList", address=TOKEN_LIST_CONTRACT_ADDRESS
        )
        token_info = TokenList(list_contract).get_token(self.target.token_address)
        self.token_owner_address = token_info[2]
        # Store token contract.
        if token_info[1] == TokenType.IbetCoupon:
            self.token_contract = ContractOperator.get_contract(
                TokenType.IbetCoupon, self.target.token_address
            )
        elif token_info[1] == TokenType.IbetMembership:
            self.token_contract = ContractOperator.get_contract(
                TokenType.IbetMembership, self.target.token_address
            )
        elif token_info[1] == TokenType.IbetStraightBond:
            self.token_contract = ContractOperator.get_contract(
                TokenType.IbetStraightBond, self.target.token_address
            )
        elif token_info[1] == TokenType.IbetShare:
            self.token_contract = ContractOperator.get_contract(
                TokenType.IbetShare, self.target.token_address
            )
        else:
            return False
        self.token_template = token_info[1]

        # Fetch current tradable exchange to store exchange contract.
        self.tradable_exchange_address = ContractOperator.call_function(
            contract=self.token_contract,
            function_name="tradableExchange",
            args=(),
            default_returns=ZERO_ADDRESS,
        )
        self.exchange_contract = ContractOperator.get_contract(
            contract_name="IbetExchangeInterface",
            address=self.tradable_exchange_address,
        )
        return True

    def __load_checkpoint(
        self, local_session: Session, target_token_address: str, block_to: int
    ) -> int:
        _checkpoint: Optional[TokenHoldersList] = local_session.scalars(
            select(TokenHoldersList)
            .where(TokenHoldersList.token_address == target_token_address)
            .where(TokenHoldersList.block_number < block_to)
            .where(TokenHoldersList.batch_status == TokenHolderBatchStatus.DONE.value)
            .order_by(TokenHoldersList.block_number.desc())
            .limit(1)
        ).first()
        if _checkpoint:
            _holders: Sequence[TokenHolder] = local_session.scalars(
                select(TokenHolder).where(TokenHolder.holder_list == _checkpoint.id)
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

    def collect(self):
        local_session = self.__get_db_session()
        try:
            if not self.__load_target(local_session):
                LOG.debug(f"There are no pending collect batch")
                return
            if not self.__load_token_info():
                LOG.debug(f"Token contract must be listed to TokenList contract.")
                self.__update_status(local_session, TokenHolderBatchStatus.FAILED)
                local_session.commit()
                return

            _target_block = self.target.block_number
            _from_block = self.__load_checkpoint(
                local_session,
                target_token_address=self.target.token_address,
                block_to=_target_block,
            )
            _to_block = 999999 + _from_block
            if _target_block > _to_block:
                while _to_block < _target_block:
                    self.__process_all(
                        db_session=local_session,
                        block_from=_from_block,
                        block_to=_to_block,
                    )
                    _from_block += 1000000
                    _to_block += 1000000
                self.__process_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=_target_block,
                )
            else:
                self.__process_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=_target_block,
                )
            self.__update_status(local_session, TokenHolderBatchStatus.DONE)
            local_session.commit()
            LOG.info("Collect job has been completed")
        except Exception as e:
            local_session.rollback()
            self.__update_status(local_session, TokenHolderBatchStatus.FAILED)
            local_session.commit()
            raise e
        finally:
            local_session.close()

    def __update_status(self, local_session: Session, status: TokenHolderBatchStatus):
        if status == TokenHolderBatchStatus.DONE:
            # Not to store non-holders
            (
                local_session.execute(
                    delete(TokenHolder)
                    .where(TokenHolder.holder_list == self.target.id)
                    .where(TokenHolder.hold_balance == 0)
                    .where(TokenHolder.locked_balance == 0)
                )
            )

        self.target.batch_status = status.value
        local_session.merge(self.target)
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

    def __process_all(self, db_session: Session, block_from: int, block_to: int):
        LOG.info("process from={}, to={}".format(block_from, block_to))

        self.__process_transfer(block_from, block_to)
        self.__process_issue(block_from, block_to)
        self.__process_redeem(block_from, block_to)
        if self.token_template in [TokenType.IbetStraightBond, TokenType.IbetShare]:
            self.__process_lock(block_from, block_to)
            self.__process_unlock(block_from, block_to)
        if self.token_template == TokenType.IbetCoupon:
            self.__process_consume(block_from, block_to)

        self.__save_holders(
            db_session,
            self.balance_book,
            self.target.id,
            self.target.token_address,
            self.token_owner_address,
        )

    def __process_transfer(self, block_from: int, block_to: int):
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
            exchange_contract = ContractOperator.get_contract(
                contract_name="IbetExchangeInterface",
                address=self.tradable_exchange_address,
            )
            try:
                holder_changed_events = exchange_contract.events.HolderChanged.get_logs(
                    fromBlock=block_from,
                    toBlock=block_to,
                    argument_filters={"token": self.token_contract.address},
                )
            except ABIEventFunctionNotFound:
                holder_changed_events = []

            for _event in holder_changed_events:
                if self.token_contract.address == _event["args"]["token"]:
                    tmp_events.append(
                        {
                            "event": _event["event"],
                            "args": dict(_event["args"]),
                            "transaction_hash": _event["transactionHash"].hex(),
                            "block_number": _event["blockNumber"],
                            "log_index": _event["logIndex"],
                        }
                    )

            # Get "Transfer" events from token contract
            try:
                token_transfer_events = self.token_contract.events.Transfer.get_logs(
                    fromBlock=block_from, toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                token_transfer_events = []

            for _event in token_transfer_events:
                tmp_events.append(
                    {
                        "event": _event["event"],
                        "args": dict(_event["args"]),
                        "transaction_hash": _event["transactionHash"].hex(),
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
                amount = args.get("value")

                # Skip in case of deposit to exchange or withdrawal from exchange
                if (
                    web3.eth.get_code(from_account).hex() != "0x"
                    or web3.eth.get_code(to_account).hex() != "0x"
                ):
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

    def __process_issue(self, block_from: int, block_to: int):
        """Process Issue Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Issue` event on Token contracts

        :param block_from: Block from
        :param block_to: Block to
        :return: None
        """
        try:
            # Get "Issue" events from token contract
            events = self.token_contract.events.Issue.get_logs(
                fromBlock=block_from, toBlock=block_to
            )
        except ABIEventFunctionNotFound:
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

    def __process_redeem(self, block_from: int, block_to: int):
        """Process Redeem Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Redeem` event on Token contracts

        :param block_from: Block from
        :param block_to: Block to
        :return: None
        """
        try:
            # Get "Redeem" events from token contract
            events = self.token_contract.events.Redeem.get_logs(
                fromBlock=block_from, toBlock=block_to
            )
        except ABIEventFunctionNotFound:
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

    def __process_consume(self, block_from: int, block_to: int):
        """Process Consume Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Consume` event on Token contracts

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            # Get "Consume" events from token contract
            events = self.token_contract.events.Consume.get_logs(
                fromBlock=block_from, toBlock=block_to
            )
        except ABIEventFunctionNotFound:
            events = []
        try:
            for event in events:
                args = event["args"]
                account = args.get("consumer", ZERO_ADDRESS)
                amount = args.get("value", ZERO_ADDRESS)
                self.balance_book.store(account_address=account, amount=-amount)
        except Exception:
            raise

    def __process_lock(self, block_from: int, block_to: int):
        """Process Lock Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Lock` event on Token contracts

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            # Get "Lock" events from token contract
            events = self.token_contract.events.Lock.get_logs(
                fromBlock=block_from, toBlock=block_to
            )
        except ABIEventFunctionNotFound:
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

    def __process_unlock(self, block_from: int, block_to: int):
        """Process Unlock Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Unlock` event on Token contracts

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            # Get "Unlock" events from token contract
            events = self.token_contract.events.Unlock.get_logs(
                fromBlock=block_from, toBlock=block_to
            )
        except ABIEventFunctionNotFound:
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

    @staticmethod
    def __save_holders(
        db_session: Session,
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
            token_holder: Optional[TokenHolder] = db_session.scalars(
                select(TokenHolder)
                .where(TokenHolder.holder_list == holder_list_id)
                .where(TokenHolder.account_address == account_address)
                .limit(1)
            ).first()
            if token_holder is not None:
                token_holder.hold_balance = page.hold_balance
                token_holder.locked_balance = page.locked_balance
                db_session.merge(token_holder)
            elif page.hold_balance > 0 or page.locked_balance > 0:
                LOG.debug(
                    f"Collection record created : token_address={token_address}, account_address={account_address}"
                )
                page.holder_list = holder_list_id
                db_session.add(page)


def main():
    LOG.info("Service started successfully")
    processor = Processor()
    while True:
        try:
            processor.collect()
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An exception occurred during event synchronization")

        time.sleep(10)


if __name__ == "__main__":
    main()
