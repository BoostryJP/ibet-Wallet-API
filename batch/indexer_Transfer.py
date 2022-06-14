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
from datetime import (
    datetime,
    timezone,
    timedelta
)
from typing import List

from eth_utils import to_checksum_address
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from web3.exceptions import ABIEventFunctionNotFound

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
    IDXTransfer, IDXTransferBlockNumber
)
from app.utils.web3_utils import Web3Wrapper
import log

UTC = timezone(timedelta(hours=0), "UTC")

process_name = "INDEXER-TRANSFER"
LOG = log.get_logger(process_name=process_name)

web3 = Web3Wrapper()
db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    """Processor for indexing Token transfer events"""
    class TargetTokenList:
        class TargetToken:
            """
            Attributes:
                token_contract: contract object
                start_block_number(int): block number that the processor first reads
                cursor(int): pointer where next process should be start
            """
            def __init__(self, token_contract, block_number: int):
                self.token_contract = token_contract
                self.start_block_number = block_number
                self.cursor = block_number

        target_token_list: List[TargetToken]

        def __init__(self):
            self.target_token_list = []

        def append(self, token_contract, block_number: int):
            is_duplicate = False
            for i, t in enumerate(self.target_token_list):
                if t.token_contract.address == token_contract.address:
                    is_duplicate = True
                    if self.target_token_list[i].start_block_number > block_number:
                        self.target_token_list[i].start_block_number = block_number
                        self.target_token_list[i].cursor = block_number
            if not is_duplicate:
                target_token = self.TargetToken(token_contract, block_number)
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

    token_list: TargetTokenList

    def __init__(self):
        self.token_list = self.TargetTokenList()

    @staticmethod
    def __gen_block_timestamp(event):
        return datetime.fromtimestamp(
            web3.eth.getBlock(event["blockNumber"])["timestamp"],
            UTC
        )

    def __get_token_list(self, db_session: Session):
        self.token_list = self.TargetTokenList()
        list_contract = Contract.get_contract("TokenList", TOKEN_LIST_CONTRACT_ADDRESS)
        listed_tokens = db_session.query(Listing).all()
        for listed_token in listed_tokens:
            token_info = Contract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(listed_token.token_address,),
                default_returns=(ZERO_ADDRESS, "", ZERO_ADDRESS)
            )
            synced_block_number = self.__get_idx_transfer_block_number(
                db_session=db_session,
                token_address=listed_token.token_address
            )
            block_from = synced_block_number + 1
            if token_info[1] == "IbetCoupon":
                token_contract = Contract.get_contract("IbetCoupon", listed_token.token_address)
                self.token_list.append(token_contract, block_from)
            elif token_info[1] == "IbetMembership":
                token_contract = Contract.get_contract("IbetMembership", listed_token.token_address)
                self.token_list.append(token_contract, block_from)
            elif token_info[1] == "IbetStraightBond":
                token_contract = Contract.get_contract("IbetStraightBond", listed_token.token_address)
                self.token_list.append(token_contract, block_from)
            elif token_info[1] == "IbetShare":
                token_contract = Contract.get_contract("IbetShare", listed_token.token_address)
                self.token_list.append(token_contract, block_from)

    @staticmethod
    def __get_db_session():
        return Session(autocommit=False, autoflush=True, bind=db_engine)

    def initial_sync(self):
        local_session = self.__get_db_session()
        try:
            self.__get_token_list(local_session)
            latest_block = web3.eth.blockNumber
            _from_block = self.__get_oldest_cursor(self.token_list, latest_block)
            _to_block = 999999 + _from_block
            if latest_block > _to_block:
                while _to_block < latest_block:
                    self.__sync_all(
                        db_session=local_session,
                        block_to=_to_block,
                    )
                    _to_block += 1000000
                self.__sync_all(
                    db_session=local_session,
                    block_to=latest_block,
                )
            else:
                self.__sync_all(
                    db_session=local_session,
                    block_to=latest_block,
                )
            self.__set_idx_transfer_block_number(local_session, self.token_list, latest_block)
            local_session.commit()
        except Exception as e:
            LOG.exception("An exception occurred during event synchronization")
            local_session.rollback()
            raise e
        finally:
            local_session.close()
            self.token_list = self.TargetTokenList()
        LOG.info(f"<{process_name}> Initial sync has been completed")

    def sync_new_logs(self):
        local_session = self.__get_db_session()
        try:
            self.__get_token_list(local_session)
            latest_block = web3.eth.blockNumber
            _from_block = self.__get_oldest_cursor(self.token_list, latest_block)
            _to_block = 999999 + _from_block
            if latest_block > _to_block:
                while _to_block < latest_block:
                    self.__sync_all(
                        db_session=local_session,
                        block_to=_to_block,
                    )
                    _to_block += 1000000
                self.__sync_all(
                    db_session=local_session,
                    block_to=self.latest_block,
                )
            else:
                self.__sync_all(
                    db_session=local_session,
                    block_to=latest_block,
                )
            self.__set_idx_transfer_block_number(local_session, self.token_list, latest_block)
            local_session.commit()
        except Exception as e:
            LOG.exception("An exception occurred during event synchronization")
            local_session.rollback()
            raise e
        finally:
            local_session.close()
            self.token_list = self.TargetTokenList()

    def __sync_all(self, db_session: Session, block_to: int):
        LOG.info("syncing to={}".format(block_to))
        self.__sync_transfer(db_session, block_to)

    def __update_cursor(self, block_number):
        """Memorize the block number where next processing should start from

        :param block_number: block number to be set
        :return: None
        """
        for target in self.token_list:
            if block_number > target.start_block_number:
                target.cursor = block_number

    def __sync_transfer(self, db_session: Session, block_to: int):
        """Sync Transfer events

        :param db_session: ORM session
        :param block_to: To block
        :return:
        """
        for target in self.token_list:
            token = target.token_contract
            block_from = target.cursor
            if block_from > block_to:
                continue
            try:
                events = token.events.Transfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                for event in events:
                    args = event["args"]
                    value = args.get("value", 0)
                    if value > sys.maxsize:
                        pass
                    else:
                        event_created = self.__gen_block_timestamp(event=event)
                        self.__sink_on_transfer(
                            db_session=db_session,
                            transaction_hash=event["transactionHash"].hex(),
                            token_address=to_checksum_address(token.address),
                            from_account_address=args.get("from", ZERO_ADDRESS),
                            to_account_address=args.get("to", ZERO_ADDRESS),
                            value=value,
                            event_created=event_created
                        )
            except Exception as e:
                raise e

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
    def __get_idx_transfer_block_number(db_session: Session, token_address: str) -> int:
        """Get transfer index """
        _idx_transfer_block_number = db_session.query(IDXTransferBlockNumber).\
            filter(IDXTransferBlockNumber.token_address == token_address).first()
        if _idx_transfer_block_number is None:
            return -1
        else:
            return _idx_transfer_block_number.latest_block_number

    @staticmethod
    def __set_idx_transfer_block_number(db_session: Session, target_token_list: TargetTokenList, block_number: int):
        """Set transfer index """
        for target_token in target_token_list:
            _idx_transfer_block_number = db_session.query(IDXTransferBlockNumber). \
                filter(IDXTransferBlockNumber.token_address == target_token.token_contract.address).first()
            if _idx_transfer_block_number is None:
                _idx_transfer_block_number = IDXTransferBlockNumber()
            _idx_transfer_block_number.latest_block_number = block_number
            _idx_transfer_block_number.token_address = target_token.token_contract.address
            db_session.merge(_idx_transfer_block_number)

    @staticmethod
    def __sink_on_transfer(db_session: Session,
                           transaction_hash: str,
                           token_address: str,
                           from_account_address: str,
                           to_account_address: str,
                           value: int,
                           event_created: datetime):
        """Registry Transfer data in DB

        :param transaction_hash: transaction hash (same value for bulk transfer of token contract)
        :param token_address: token address
        :param from_account_address: from address
        :param to_account_address: to address
        :param value: transfer amount
        :param event_created: block timestamp (same value for bulk transfer of token contract)
        :return: None
        """
        LOG.debug(f"Transfer: transaction_hash={transaction_hash}")
        transfer = IDXTransfer()
        transfer.transaction_hash = transaction_hash
        transfer.token_address = token_address
        transfer.from_address = from_account_address
        transfer.to_address = to_account_address
        transfer.value = value
        transfer.created = event_created
        transfer.modified = event_created
        db_session.add(transfer)


def main():
    LOG.info("Service started successfully")
    processor = Processor()

    initial_synced_completed = False
    while not initial_synced_completed:
        try:
            processor.initial_sync()
            LOG.debug("Initial sync is processed successfully")
            initial_synced_completed = True
        except Exception:
            LOG.exception("Initial sync failed")

        time.sleep(5)

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

        time.sleep(5)


if __name__ == "__main__":
    main()
