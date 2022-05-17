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
from datetime import (
    datetime,
    timezone
)

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
    IDXTransferApproval
)
from app.utils.web3_utils import Web3Wrapper
import log

process_name = "INDEXER-TRANSFER-APPROVAL"
LOG = log.get_logger(process_name=process_name)

web3 = Web3Wrapper()
db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    """Processor for indexing Token transfer approval events"""
    latest_block = 0

    def __init__(self):
        self.token_list = []

    @staticmethod
    def __get_db_session():
        return Session(autocommit=False, autoflush=True, bind=db_engine)

    def initial_sync(self):
        local_session = self.__get_db_session()
        latest_block_at_start = self.latest_block
        self.latest_block = web3.eth.blockNumber
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
        except Exception as e:
            LOG.exception("An exception occurred during event synchronization")
            local_session.rollback()
            self.latest_block = latest_block_at_start
            raise e
        finally:
            local_session.close()

        LOG.info(f"<{process_name}> Initial sync has been completed")

    def sync_new_logs(self):
        local_session = self.__get_db_session()
        latest_block_at_start = self.latest_block
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
        except Exception as e:
            LOG.exception("An exception occurred during event synchronization")
            local_session.rollback()
            self.latest_block = latest_block_at_start
            raise e
        finally:
            local_session.close()

    @staticmethod
    def __get_block_timestamp(event) -> int:
        return web3.eth.getBlock(event["blockNumber"])["timestamp"]

    def __get_token_list(self, db_session: Session):
        self.token_list = []
        ListContract = Contract.get_contract(
            contract_name="TokenList",
            address=TOKEN_LIST_CONTRACT_ADDRESS
        )
        listed_tokens = db_session.query(Listing).all()
        for listed_token in listed_tokens:
            token_info = ListContract.functions.getTokenByAddress(listed_token.token_address).call()
            if token_info[1] == "IbetShare":
                token_contract = Contract.get_contract(
                    contract_name="IbetShare",
                    address=listed_token.token_address
                )
                self.token_list.append(token_contract)

    def __sync_all(self, db_session: Session, block_from: int, block_to: int):
        LOG.info("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_apply_for_transfer(db_session, block_from, block_to)
        self.__sync_cancel_transfer(db_session, block_from, block_to)
        self.__sync_approve_transfer(db_session, block_from, block_to)

    def __sync_apply_for_transfer(self, db_session, block_from, block_to):
        """Sync ApplyForTransfer Events

        :param block_from: From Block
        :param block_to: To Block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.ApplyForTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                for event in events:
                    args = event["args"]
                    value = args.get("value", 0)
                    if value > sys.maxsize:  # suppress overflow
                        pass
                    else:
                        block_timestamp = self.__get_block_timestamp(event=event)
                        self.__sink_on_transfer_approval(
                            db_session=db_session,
                            event_type="ApplyFor",
                            token_address=token.address,
                            application_id=args.get("index"),
                            from_address=args.get("from", ZERO_ADDRESS),
                            to_address=args.get("to", ZERO_ADDRESS),
                            value=args.get("value"),
                            optional_data_applicant=args.get("data"),
                            block_timestamp=block_timestamp
                        )
            except Exception as e:
                raise e

    def __sync_cancel_transfer(self, db_session, block_from, block_to):
        """Sync CancelTransfer Events

        :param block_from: From Block
        :param block_to: To Block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.CancelTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                for event in events:
                    args = event["args"]
                    self.__sink_on_transfer_approval(
                        db_session=db_session,
                        event_type="Cancel",
                        token_address=token.address,
                        application_id=args.get("index"),
                        from_address=args.get("from", ZERO_ADDRESS),
                        to_address=args.get("to", ZERO_ADDRESS),
                    )
            except Exception as e:
                raise e

    def __sync_approve_transfer(self, db_session, block_from, block_to):
        """Sync ApproveTransfer Events

        :param block_from: From Block
        :param block_to: To Block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.ApproveTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                for event in events:
                    args = event["args"]
                    block_timestamp = self.__get_block_timestamp(event=event)
                    self.__sink_on_transfer_approval(
                        db_session=db_session,
                        event_type="Approve",
                        token_address=token.address,
                        application_id=args.get("index"),
                        from_address=args.get("from", ZERO_ADDRESS),
                        to_address=args.get("to", ZERO_ADDRESS),
                        optional_data_approver=args.get("data"),
                        block_timestamp=block_timestamp
                    )
            except Exception as e:
                raise e

    @staticmethod
    def __sink_on_transfer_approval(db_session: Session,
                                    event_type: str,
                                    token_address: str,
                                    application_id: int,
                                    from_address: Optional[str] = None,
                                    to_address: Optional[str] = None,
                                    value: Optional[int] = None,
                                    optional_data_applicant: Optional[str] = None,
                                    optional_data_approver: Optional[str] = None,
                                    block_timestamp: Optional[int] = None):
        """Update Transfer Approval data in DB

        :param event_type: event type [ApplyFor, Cancel, Approve]
        :param token_address: token address
        :param application_id: application id
        :param from_address: transfer from
        :param to_address: transfer to
        :param value: transfer amount
        :param optional_data_applicant: optional data (ApplyForTransfer)
        :param optional_data_approver: optional data (ApproveTransfer)
        :param block_timestamp: block timestamp
        :return: None
        """
        transfer_approval = db_session.query(IDXTransferApproval). \
            filter(IDXTransferApproval.token_address == token_address). \
            filter(IDXTransferApproval.application_id == application_id). \
            first()
        if event_type == "ApplyFor":
            if transfer_approval is None:
                transfer_approval = IDXTransferApproval()
                transfer_approval.token_address = token_address
                transfer_approval.application_id = application_id
                transfer_approval.from_address = from_address
                transfer_approval.to_address = to_address
            transfer_approval.value = value
            try:
                transfer_approval.application_datetime = datetime.fromtimestamp(
                    float(optional_data_applicant),
                    tz=timezone.utc
                )
            except ValueError:
                transfer_approval.application_datetime = None
            transfer_approval.application_blocktimestamp = datetime.fromtimestamp(
                block_timestamp,
                tz=timezone.utc
            )
        elif event_type == "Cancel":
            if transfer_approval is None:
                transfer_approval = IDXTransferApproval()
                transfer_approval.token_address = token_address
                transfer_approval.application_id = application_id
                transfer_approval.from_address = from_address
                transfer_approval.to_address = to_address
            transfer_approval.cancelled = True
        elif event_type == "Approve":
            if transfer_approval is None:
                transfer_approval = IDXTransferApproval()
                transfer_approval.token_address = token_address
                transfer_approval.application_id = application_id
                transfer_approval.from_address = from_address
                transfer_approval.to_address = to_address
            try:
                transfer_approval.approval_datetime = datetime.fromtimestamp(
                    float(optional_data_approver),
                    tz=timezone.utc
                )
            except ValueError:
                transfer_approval.approval_datetime = None
            transfer_approval.approval_blocktimestamp = datetime.fromtimestamp(
                block_timestamp,
                tz=timezone.utc
            )
        db_session.merge(transfer_approval)


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
