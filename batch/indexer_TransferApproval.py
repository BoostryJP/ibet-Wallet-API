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
from typing import Optional, List
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
    IDXTransferApproval,
    IDXTransferApprovalBlockNumber
)
from app.utils.web3_utils import Web3Wrapper
import log

process_name = "INDEXER-TRANSFER-APPROVAL"
LOG = log.get_logger(process_name=process_name)

web3 = Web3Wrapper()
db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

"""
Batch process for indexing security token transfer approval events

ibetSecurityToken
  - ApplyForTransfer: 'ApplyFor'
  - CancelTransfer: 'Cancel'
  - ApproveTransfer: 'Approve'

ibetSecurityTokenEscrow
  - ApplyForTransfer: 'ApplyFor'
  - CancelTransfer: 'Cancel'
  - EscrowFinished: 'EscrowFinish'
  - ApproveTransfer: 'Approve'

"""


class Processor:
    """Processor for indexing Token transfer approval events"""
    class TargetTokenList:
        class TargetToken:
            """
            Attributes:
                token_contract: contract object
                exchange_address: address of associated exchange
                start_block_number(int): block number that the processor first reads
                cursor(int): pointer where next process should be start
            """
            def __init__(self, token_contract, exchange_address: str, block_number: int):
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
                target_token = self.TargetToken(token_contract, exchange_address, block_number)
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
                exchange_contract: contract object
                exchange_address: contract address of exchange or escrow
                start_block_number(int): block number that the processor first reads
                cursor(int): pointer where next process should be start
            """
            def __init__(self, exchange_contract, exchange_address: str, block_number: int):
                self.exchange_contract = exchange_contract
                self.exchange_address = exchange_address
                self.start_block_number = block_number
                self.cursor = block_number

        target_exchange_list: List[TargetExchange]

        def __init__(self):
            self.target_exchange_list = []

        def append(self, exchange_contract, exchange_address: str, block_number: int):
            is_duplicate = False
            for i, e in enumerate(self.target_exchange_list):
                if e.exchange_address == exchange_address:
                    is_duplicate = True
                    if self.target_exchange_list[i].start_block_number > block_number:
                        self.target_exchange_list[i].start_block_number = block_number
                        self.target_exchange_list[i].cursor = block_number
            if not is_duplicate:
                target_exchange = self.TargetExchange(exchange_contract, exchange_address, block_number)
                self.target_exchange_list.append(target_exchange)

        def __iter__(self):
            return iter(self.target_exchange_list)

    token_list: TargetTokenList
    exchange_list: TargetExchangeList

    def __init__(self):
        self.token_list = self.TargetTokenList()
        self.exchange_list = self.TargetExchangeList()

    @staticmethod
    def get_block_timestamp(event) -> int:
        block_timestamp = web3.eth.get_block(event["blockNumber"])["timestamp"]
        return block_timestamp

    def __get_contract_list(self, db_session: Session):
        self.token_list = self.TargetTokenList()
        self.exchange_list = self.TargetExchangeList()

        list_contract = Contract.get_contract(
            contract_name="TokenList",
            address=TOKEN_LIST_CONTRACT_ADDRESS
        )
        listed_tokens = db_session.query(Listing).all()

        _exchange_list_tmp = []
        for listed_token in listed_tokens:
            token_info = Contract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(listed_token.token_address,),
                default_returns=(ZERO_ADDRESS, "", ZERO_ADDRESS)
            )
            token_type = token_info[1]
            if token_type == "IbetShare" or token_type == "IbetStraightBond":
                token_contract = Contract.get_contract(
                    contract_name="IbetSecurityTokenInterface",
                    address=listed_token.token_address
                )
                tradable_exchange_address = Contract.call_function(
                    contract=token_contract,
                    function_name="tradableExchange",
                    args=(),
                    default_returns=ZERO_ADDRESS
                )
                synced_block_number = self.__get_idx_transfer_approval_block_number(
                    db_session=db_session,
                    token_address=listed_token.token_address,
                    exchange_address=tradable_exchange_address
                )
                block_from = synced_block_number + 1
                self.token_list.append(token_contract, tradable_exchange_address, block_from)
                if tradable_exchange_address != ZERO_ADDRESS:
                    if tradable_exchange_address not in [e.exchange_address for e in self.exchange_list]:
                        exchange_contract = Contract.get_contract(
                            contract_name="IbetSecurityTokenEscrow",
                            address=tradable_exchange_address
                        )
                        self.exchange_list.append(exchange_contract, tradable_exchange_address, block_from)

    @staticmethod
    def __get_db_session():
        return Session(autocommit=False, autoflush=True, bind=db_engine)

    def initial_sync(self):
        local_session = self.__get_db_session()
        try:
            self.__get_contract_list(local_session)
            # Synchronize 1,000,000 blocks each
            latest_block = web3.eth.block_number
            _from_block = self.__get_oldest_cursor(self.token_list, latest_block)
            _to_block = 999999 + _from_block
            if latest_block > _to_block:
                while _to_block < latest_block:
                    self.__sync_all(
                        db_session=local_session,
                        block_to=_to_block
                    )
                    _to_block += 1000000
                self.__sync_all(
                    db_session=local_session,
                    block_to=latest_block
                )
            else:
                self.__sync_all(
                    db_session=local_session,
                    block_to=latest_block
                )
            self.__set_idx_transfer_approval_block_number(local_session, self.token_list, latest_block)
            local_session.commit()
        except Exception as e:
            local_session.rollback()
            raise e
        finally:
            local_session.close()
            self.token_list = self.TargetTokenList()
            self.exchange_list = self.TargetExchangeList()
        LOG.info(f"<{process_name}> Initial sync has been completed")

    def sync_new_logs(self):
        local_session = self.__get_db_session()
        try:
            self.__get_contract_list(local_session)
            # Synchronize 1,000,000 blocks each
            latest_block = web3.eth.block_number
            _from_block = self.__get_oldest_cursor(self.token_list, latest_block)
            _to_block = 999999 + _from_block
            if latest_block > _to_block:
                while _to_block < latest_block:
                    self.__sync_all(
                        db_session=local_session,
                        block_to=_to_block
                    )
                    _to_block += 1000000
                self.__sync_all(
                    db_session=local_session,
                    block_to=latest_block
                )
            else:
                self.__sync_all(
                    db_session=local_session,
                    block_to=latest_block
                )
            self.__set_idx_transfer_approval_block_number(local_session, self.token_list, latest_block)
            local_session.commit()
        except Exception as e:
            local_session.rollback()
            raise e
        finally:
            local_session.close()
            self.token_list = self.TargetTokenList()
            self.exchange_list = self.TargetExchangeList()
        LOG.info("Sync job has been completed")

    def __sync_all(self, db_session: Session, block_to: int):
        LOG.info("Syncing to={}".format(block_to))
        self.__sync_token_apply_for_transfer(db_session, block_to)
        self.__sync_token_cancel_transfer(db_session, block_to)
        self.__sync_token_approve_transfer(db_session, block_to)
        self.__sync_exchange_apply_for_transfer(db_session, block_to)
        self.__sync_exchange_cancel_transfer(db_session, block_to)
        self.__sync_exchange_escrow_finished(db_session, block_to)
        self.__sync_exchange_approve_transfer(db_session, block_to)

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

    def __sync_token_apply_for_transfer(self, db_session: Session, block_to: int):
        """Sync ApplyForTransfer events of tokens
        :param db_session: ORM session
        :param block_to: To Block
        :return: None
        """
        for target in self.token_list:
            token = target.token_contract
            block_from = target.cursor
            if block_from > block_to:
                continue
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
                        block_timestamp = self.get_block_timestamp(event=event)
                        self.__sink_on_transfer_approval(
                            db_session=db_session,
                            event_type="ApplyFor",
                            token_address=token.address,
                            exchange_address=None,
                            application_id=args.get("index"),
                            from_address=args.get("from", ZERO_ADDRESS),
                            to_address=args.get("to", ZERO_ADDRESS),
                            value=args.get("value"),
                            optional_data_applicant=args.get("data"),
                            block_timestamp=block_timestamp
                        )
            except Exception as e:
                raise e

    def __sync_token_cancel_transfer(self, db_session: Session, block_to: int):
        """Sync CancelTransfer events of tokens
        :param db_session: ORM session
        :param block_to: To Block
        :return: None
        """
        for target in self.token_list:
            token = target.token_contract
            block_from = target.cursor
            if block_from > block_to:
                continue
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
                        exchange_address=None,
                        application_id=args.get("index"),
                        from_address=args.get("from", ZERO_ADDRESS),
                        to_address=args.get("to", ZERO_ADDRESS),
                    )
            except Exception as e:
                raise e

    def __sync_token_approve_transfer(self, db_session: Session, block_to: int):
        """Sync ApproveTransfer events of tokens
        :param db_session: ORM session
        :param block_to: To Block
        :return: None
        """
        for target in self.token_list:
            token = target.token_contract
            block_from = target.cursor
            if block_from > block_to:
                continue
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
                    block_timestamp = self.get_block_timestamp(event=event)
                    self.__sink_on_transfer_approval(
                        db_session=db_session,
                        event_type="Approve",
                        token_address=token.address,
                        exchange_address=None,
                        application_id=args.get("index"),
                        from_address=args.get("from", ZERO_ADDRESS),
                        to_address=args.get("to", ZERO_ADDRESS),
                        optional_data_approver=args.get("data"),
                        block_timestamp=block_timestamp
                    )
            except Exception as e:
                raise e

    def __sync_exchange_apply_for_transfer(self, db_session: Session, block_to: int):
        """Sync ApplyForTransfer events of exchanges
        :param db_session: ORM session
        :param block_to: To Block
        :return: None
        """
        for target in self.exchange_list:
            block_from = target.cursor
            if block_from > block_to:
                continue
            exchange = target.exchange_contract
            try:
                events = exchange.events.ApplyForTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                # Filter events by listed token
                events_filtered = []
                token_address_list = [t.token_contract.address for t in self.token_list]
                for event in events:
                    args = event["args"]
                    if args.get("token", ZERO_ADDRESS) in token_address_list:
                        events_filtered.append(event)
                for event in events_filtered:
                    args = event["args"]
                    value = args.get("value", 0)
                    if value > sys.maxsize:  # suppress overflow
                        pass
                    else:
                        block_timestamp = self.get_block_timestamp(event=event)
                        self.__sink_on_transfer_approval(
                            db_session=db_session,
                            event_type="ApplyFor",
                            token_address=args.get("token", ZERO_ADDRESS),
                            exchange_address=exchange.address,
                            application_id=args.get("escrowId"),
                            from_address=args.get("from", ZERO_ADDRESS),
                            to_address=args.get("to", ZERO_ADDRESS),
                            value=args.get("value"),
                            optional_data_applicant=args.get("data"),
                            block_timestamp=block_timestamp
                        )
            except Exception as e:
                raise e

    def __sync_exchange_cancel_transfer(self, db_session: Session, block_to: int):
        """Sync CancelTransfer events of exchanges
        :param db_session: ORM session
        :param block_to: To Block
        :return: None
        """
        for target in self.exchange_list:
            block_from = target.cursor
            if block_from > block_to:
                continue
            exchange = target.exchange_contract
            try:
                events = exchange.events.CancelTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                # Filter events by listed token
                events_filtered = []
                token_address_list = [t.token_contract.address for t in self.token_list]
                for event in events:
                    args = event["args"]
                    if args.get("token", ZERO_ADDRESS) in token_address_list:
                        events_filtered.append(event)
                for event in events_filtered:
                    args = event["args"]
                    self.__sink_on_transfer_approval(
                        db_session=db_session,
                        event_type="Cancel",
                        token_address=args.get("token", ZERO_ADDRESS),
                        exchange_address=exchange.address,
                        application_id=args.get("escrowId"),
                        from_address=args.get("from", ZERO_ADDRESS),
                        to_address=args.get("to", ZERO_ADDRESS),
                    )
            except Exception as e:
                raise e

    def __sync_exchange_escrow_finished(self, db_session: Session, block_to: int):
        """Sync EscrowFinished events of exchanges
        :param db_session: ORM session
        :param block_to: To Block
        :return: None
        """
        for target in self.exchange_list:
            block_from = target.cursor
            if block_from > block_to:
                continue
            exchange = target.exchange_contract
            try:
                events = exchange.events.EscrowFinished.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to,
                    argument_filters={"transferApprovalRequired": True}
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                # Filter events by listed token
                events_filtered = []
                token_address_list = [t.token_contract.address for t in self.token_list]
                for event in events:
                    args = event["args"]
                    if args.get("token", ZERO_ADDRESS) in token_address_list:
                        events_filtered.append(event)
                for event in events_filtered:
                    args = event["args"]
                    self.__sink_on_transfer_approval(
                        db_session=db_session,
                        event_type="EscrowFinish",
                        token_address=args.get("token", ZERO_ADDRESS),
                        exchange_address=exchange.address,
                        application_id=args.get("escrowId"),
                        from_address=args.get("sender", ZERO_ADDRESS),
                        to_address=args.get("recipient", ZERO_ADDRESS)
                    )
            except Exception as e:
                raise e

    def __sync_exchange_approve_transfer(self, db_session: Session, block_to: int):
        """Sync ApproveTransfer events of exchanges
        :param db_session: ORM session
        :param block_to: To Block
        :return: None
        """
        for target in self.exchange_list:
            block_from = target.cursor
            if block_from > block_to:
                continue
            exchange = target.exchange_contract
            try:
                events = exchange.events.ApproveTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                # Filter events by listed token
                events_filtered = []
                token_address_list = [t.token_contract.address for t in self.token_list]
                for event in events:
                    args = event["args"]
                    if args.get("token", ZERO_ADDRESS) in token_address_list:
                        events_filtered.append(event)
                for event in events_filtered:
                    args = event["args"]
                    block_timestamp = self.get_block_timestamp(event=event)
                    self.__sink_on_transfer_approval(
                        db_session=db_session,
                        event_type="Approve",
                        token_address=args.get("token", ZERO_ADDRESS),
                        exchange_address=exchange.address,
                        application_id=args.get("escrowId"),
                        optional_data_approver=args.get("data"),
                        block_timestamp=block_timestamp
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
    def __get_idx_transfer_approval_block_number(db_session: Session, token_address: str, exchange_address: str):
        """Get position index for Bond """
        _idx_transfer_approval_block_number = db_session.query(IDXTransferApprovalBlockNumber).\
            filter(IDXTransferApprovalBlockNumber.token_address == token_address).\
            filter(IDXTransferApprovalBlockNumber.exchange_address == exchange_address).first()
        if _idx_transfer_approval_block_number is None:
            return -1
        else:
            return _idx_transfer_approval_block_number.latest_block_number

    @staticmethod
    def __set_idx_transfer_approval_block_number(db_session: Session, target_token_list: TargetTokenList, block_number: int):
        """Set position index for Bond """
        for target_token in target_token_list:
            _idx_transfer_approval_block_number = db_session.query(IDXTransferApprovalBlockNumber). \
                filter(IDXTransferApprovalBlockNumber.token_address == target_token.token_contract.address).\
                filter(IDXTransferApprovalBlockNumber.exchange_address == target_token.exchange_address).first()
            if _idx_transfer_approval_block_number is None:
                _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
            _idx_transfer_approval_block_number.latest_block_number = block_number
            _idx_transfer_approval_block_number.token_address = target_token.token_contract.address
            _idx_transfer_approval_block_number.exchange_address = target_token.exchange_address
            db_session.merge(_idx_transfer_approval_block_number)

    @staticmethod
    def __sink_on_transfer_approval(db_session: Session,
                                    event_type: str,
                                    token_address: str,
                                    application_id: int,
                                    exchange_address: str = None,
                                    from_address: Optional[str] = None,
                                    to_address: Optional[str] = None,
                                    value: Optional[int] = None,
                                    optional_data_applicant: Optional[str] = None,
                                    optional_data_approver: Optional[str] = None,
                                    block_timestamp: Optional[int] = None):
        """Update Transfer Approval data in DB
        :param db_session: ORM session
        :param event_type: event type [ApplyFor, Cancel, Approve, Finish]
        :param token_address: token address
        :param exchange_address: exchange address (value is set if the event is from exchange)
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
            filter(IDXTransferApproval.exchange_address == exchange_address). \
            filter(IDXTransferApproval.application_id == application_id). \
            first()
        if event_type == "ApplyFor":
            if transfer_approval is None:
                transfer_approval = IDXTransferApproval()
                transfer_approval.token_address = token_address
                transfer_approval.exchange_address = exchange_address
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
            if transfer_approval is not None:
                transfer_approval.cancelled = True
        elif event_type == "EscrowFinish":
            if transfer_approval is not None:
                transfer_approval.escrow_finished = True
        elif event_type == "Approve":
            if transfer_approval is not None:
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
                transfer_approval.transfer_approved = True
        db_session.merge(transfer_approval)


def main():
    LOG.info("Service started successfully")
    processor = Processor()

    initial_synced_completed = False
    while not initial_synced_completed:
        try:
            processor.initial_sync()
            initial_synced_completed = True
        except Exception:
            LOG.exception("Initial sync failed")

        time.sleep(5)

    while True:
        try:
            processor.sync_new_logs()
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception("An exception occurred during event synchronization")

        time.sleep(5)


if __name__ == "__main__":
    main()
