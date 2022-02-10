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

from eth_utils import to_checksum_address
from sqlalchemy import (
    create_engine,
    desc
)
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
    IDXTransfer
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

    def __init__(self):
        self.latest_block = web3.eth.blockNumber
        self.token_list = []

    @staticmethod
    def __gen_block_timestamp(event):
        return datetime.fromtimestamp(
            web3.eth.getBlock(event["blockNumber"])["timestamp"],
            UTC
        )

    def __get_token_list(self, db_session: Session):
        self.token_list = []
        list_contract = Contract.get_contract("TokenList", TOKEN_LIST_CONTRACT_ADDRESS)
        listed_tokens = db_session.query(Listing).all()
        for listed_token in listed_tokens:
            token_info = Contract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(listed_token.token_address,),
                default_returns=(ZERO_ADDRESS, "", ZERO_ADDRESS)
            )
            if token_info[1] == "IbetCoupon":
                token_contract = Contract.get_contract("IbetCoupon", listed_token.token_address)
                self.token_list.append(token_contract)
            elif token_info[1] == "IbetMembership":
                token_contract = Contract.get_contract("IbetMembership", listed_token.token_address)
                self.token_list.append(token_contract)
            elif token_info[1] == "IbetStraightBond":
                token_contract = Contract.get_contract("IbetStraightBond", listed_token.token_address)
                self.token_list.append(token_contract)
            elif token_info[1] == "IbetShare":
                token_contract = Contract.get_contract("IbetShare", listed_token.token_address)
                self.token_list.append(token_contract)

    @staticmethod
    def __get_latest_registered_block_timestamp(db_session: Session):
        latest_registered = db_session.query(IDXTransfer). \
            order_by(desc(IDXTransfer.created)). \
            first()
        if latest_registered is not None:
            return latest_registered.created
        else:
            return None

    @staticmethod
    def __get_db_session():
        return Session(autocommit=False, autoflush=True, bind=db_engine)

    def initial_sync(self):
        local_session = self.__get_db_session()
        try:
            self.__get_token_list(local_session)
            skip_timestamp = self.__get_latest_registered_block_timestamp(local_session)
            # Synchronize 1,000,000 blocks each
            _to_block = 999999
            _from_block = 0
            if self.latest_block > 999999:
                while _to_block < self.latest_block:
                    self.__sync_all(
                        db_session=local_session,
                        block_from=_from_block,
                        block_to=_to_block,
                        skip_timestamp=skip_timestamp
                    )
                    _to_block += 1000000
                    _from_block += 1000000
                    local_session.commit()
                self.__sync_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=self.latest_block,
                    skip_timestamp=skip_timestamp
                )
                local_session.commit()
            else:
                self.__sync_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=self.latest_block,
                    skip_timestamp=skip_timestamp
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

    def __sync_all(self,
                   db_session: Session,
                   block_from: int,
                   block_to: int,
                   skip_timestamp: datetime = None):
        LOG.info("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_transfer(db_session, block_from, block_to, skip_timestamp)

    def __sync_transfer(self,
                        db_session: Session,
                        block_from: int,
                        block_to: int,
                        skip_timestamp: datetime):
        """Sync Transfer events

        :param db_session: ORM session
        :param block_from: From block
        :param block_to: To block
        :param skip_timestamp: Skip synchronisation before timestamp
        :return:
        """
        for token in self.token_list:
            try:
                events = token.events.Transfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    value = args.get("value", 0)
                    if value > sys.maxsize:
                        pass
                    else:
                        event_created = self.__gen_block_timestamp(event=event)
                        if skip_timestamp is not None and event_created <= skip_timestamp.replace(tzinfo=UTC):
                            LOG.debug(f"Skip Registry Transfer data in DB: blockNumber={event['blockNumber']}")
                            continue
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
                LOG.exception(e)

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

        time.sleep(5)


if __name__ == "__main__":
    main()
