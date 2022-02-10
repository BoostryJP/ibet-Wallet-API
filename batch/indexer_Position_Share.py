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
from typing import Optional
import os
import sys
import time

from eth_utils import to_checksum_address
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app.config import (
    DATABASE_URL,
    TOKEN_LIST_CONTRACT_ADDRESS,
    ZERO_ADDRESS
)
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.db import (
    Listing,
    IDXPosition
)
from app.utils.web3_utils import Web3Wrapper
import log

process_name = "INDEXER-POSITION-SHARE"
LOG = log.get_logger(process_name=process_name)

web3 = Web3Wrapper()
db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    def __init__(self):
        self.latest_block = web3.eth.blockNumber
        self.token_list = []

    @staticmethod
    def __get_db_session():
        return Session(autocommit=False, autoflush=True, bind=db_engine)
    
    def initial_sync(self):
        local_session = self.__get_db_session()
        try:
            self.__get_token_list(local_session)

            # Synchronize 1,000,000 blocks at a time
            _to_block = 999999
            _from_block = 0
            if self.latest_block > 999999:
                while _to_block < self.latest_block:
                    self.__sync_all(
                        db_session=local_session,
                        block_from=_from_block,
                        block_to=_to_block
                    )
                    _to_block += 1000000
                    _from_block += 1000000
                self.__sync_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=self.latest_block
                )
            else:
                self.__sync_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=self.latest_block
                )
            local_session.commit()
        finally:
            local_session.close()

        LOG.info(f"<{process_name}> Initial sync has been completed")

    def sync_new_logs(self):
        local_session = self.__get_db_session()
        try:
            self.__get_token_list(local_session)

            blockTo = web3.eth.blockNumber
            if blockTo == self.latest_block:
                return

            self.__sync_all(
                db_session=local_session,
                block_from=self.latest_block + 1,
                block_to=blockTo
            )
            self.latest_block = blockTo
            local_session.commit()
        finally:
            local_session.close()

    def __get_token_list(self, db_session: Session):
        self.token_list = []
        ListContract = Contract.get_contract("TokenList", TOKEN_LIST_CONTRACT_ADDRESS)
        listed_tokens = db_session.query(Listing).all()
        for listed_token in listed_tokens:
            token_info = ListContract.functions.getTokenByAddress(listed_token.token_address).call()
            if token_info[1] == "IbetShare":
                token_contract = Contract.get_contract("IbetShare", listed_token.token_address)
                self.token_list.append(token_contract)

    def __sync_all(self, db_session: Session, block_from: int, block_to: int):
        LOG.info("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_transfer(db_session, block_from, block_to)
        self.__sync_lock(db_session, block_from, block_to)
        self.__sync_unlock(db_session, block_from, block_to)
        self.__sync_issue(db_session, block_from, block_to)
        self.__sync_redeem(db_session, block_from, block_to)
        self.__sync_apply_for_transfer(db_session, block_from, block_to)
        self.__sync_cancel_transfer(db_session, block_from, block_to)
        self.__sync_approve_transfer(db_session, block_from, block_to)

    def __sync_transfer(self, db_session: Session, block_from: int, block_to: int):
        """Sync Transfer Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.Transfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    # from address
                    from_account = args.get("from", ZERO_ADDRESS)
                    from_account_balance = token.functions.balanceOf(from_account).call()
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=from_account,
                        balance=from_account_balance
                    )
                    # to address
                    to_account = args.get("to", ZERO_ADDRESS)
                    to_account_balance = token.functions.balanceOf(to_account).call()
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=to_account,
                        balance=to_account_balance,
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_lock(self, db_session: Session, block_from: int, block_to: int):
        """Sync Lock Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.Lock.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    account = args.get("from", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_unlock(self, db_session: Session, block_from: int, block_to: int):
        """Sync Unlock Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.Unlock.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    account = args.get("to", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_issue(self, db_session: Session, block_from: int, block_to: int):
        """Sync Issue Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.Issue.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    account = args.get("target_address", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_redeem(self, db_session: Session, block_from: int, block_to: int):
        """Sync Redeem Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.Redeem.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    account = args.get("target_address", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_apply_for_transfer(self, db_session: Session, block_from: int, block_to: int):
        """Sync ApplyForTransfer Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.ApplyForTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    account = args.get("from", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    pending_transfer = token.functions.pendingTransfer(account).call()
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_cancel_transfer(self, db_session: Session, block_from: int, block_to: int):
        """Sync CancelTransfer Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.CancelTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    account = args.get("from", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    pending_transfer = token.functions.pendingTransfer(account).call()
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_approve_transfer(self, db_session: Session, block_from: int, block_to: int):
        """Sync ApproveTransfer Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.ApproveTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    # from address
                    from_account = args.get("from", ZERO_ADDRESS)
                    from_balance = token.functions.balanceOf(from_account).call()
                    from_pending_transfer = token.functions.pendingTransfer(from_account).call()
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=from_account,
                        balance=from_balance,
                        pending_transfer=from_pending_transfer
                    )
                    # to address
                    to_account = args.get("to", ZERO_ADDRESS)
                    to_balance = token.functions.balanceOf(to_account).call()
                    to_pending_transfer = token.functions.pendingTransfer(to_account).call()
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=to_account,
                        balance=to_balance,
                        pending_transfer=to_pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    @staticmethod
    def __sink_on_position(db_session: Session,
                           token_address: str,
                           account_address: str,
                           balance: Optional[int] = None,
                           pending_transfer: Optional[int] = None):
        """Update position

        :param db_session: orm session
        :param token_address: token address
        :param account_address: account address
        :param balance: updated balance
        :param pending_transfer: updated pending_transfer
        :return: None
        """
        position = db_session.query(IDXPosition). \
            filter(IDXPosition.token_address == token_address). \
            filter(IDXPosition.account_address == account_address). \
            first()
        if position is None:
            LOG.debug(f"Position created (Share): token_address={token_address}, account_address={account_address}")
            position = IDXPosition()
            position.token_address = token_address
            position.account_address = account_address
            position.balance = balance
            position.pending_transfer = pending_transfer
        else:
            if balance is not None:
                position.balance = balance
            if pending_transfer is not None:
                position.pending_transfer = pending_transfer
        db_session.merge(position)


def main():
    LOG.info("Service started successfully")
    processor = Processor()
    processor.initial_sync()
    while True:
        try:
            processor.sync_new_logs()
            LOG.debug("Processed")
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception(ex)

        time.sleep(10)


if __name__ == "__main__":
    main()
