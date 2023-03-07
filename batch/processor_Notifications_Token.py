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
from concurrent.futures import ThreadPoolExecutor
import time
from datetime import datetime

from sqlalchemy import create_engine, and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from web3.contract import Contract as Web3Contract
from web3.types import EventData

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app.config import (
    DATABASE_URL,
    WORKER_COUNT,
    NOTIFICATION_PROCESS_INTERVAL,
    TOKEN_LIST_CONTRACT_ADDRESS
)
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.db import (
    Notification,
    NotificationType,
    NotificationBlockNumber,
    Listing,
    IDXTokenListItem
)
from app.utils.web3_utils import Web3Wrapper
from app.utils.company_list import CompanyList
from batch.lib.token_list import TokenList
from batch.lib.misc import wait_all_futures
import log

LOG = log.get_logger(process_name="PROCESSOR-NOTIFICATIONS-TOKEN")

WORKER_COUNT = int(WORKER_COUNT)
NOTIFICATION_PROCESS_INTERVAL = int(NOTIFICATION_PROCESS_INTERVAL)

web3 = Web3Wrapper()

db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

# Get TokenList contract
list_contract = Contract.get_contract(
    contract_name="TokenList",
    address=TOKEN_LIST_CONTRACT_ADDRESS
)
token_list = TokenList(list_contract)


# Watcher
class Watcher:
    contract_cache: dict[str, Web3Contract] = {}

    def __init__(self, filter_name: str, filter_params: dict, notification_type: str):
        self.filter_name = filter_name
        self.filter_params = filter_params
        self.notification_type = notification_type

    @staticmethod
    def _gen_notification_id(entry, option_type=0):
        return "0x{:012x}{:06x}{:06x}{:02x}".format(
            entry["blockNumber"],
            entry["transactionIndex"],
            entry["logIndex"],
            option_type,
        )

    @staticmethod
    def _gen_block_timestamp(entry):
        return datetime.utcfromtimestamp(web3.eth.get_block(entry["blockNumber"])["timestamp"])

    @staticmethod
    def _get_token_all_list(db_session: Session):
        _tokens = []
        registered_tokens: list[IDXTokenListItem] = (
            db_session.query(IDXTokenListItem).
            join(Listing, and_(Listing.token_address == IDXTokenListItem.token_address)).all()
        )
        for registered_token in registered_tokens:
            _tokens.append({
                "token": registered_token,
                "token_type": registered_token.token_template
            })
        return _tokens

    def db_merge(
        self, db_session: Session,
        token_contract: Web3Contract, token_type: str,
        log_entries: list[EventData], token_owner_address: str
    ):
        pass

    def loop(self):
        start_time = time.time()
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)

        try:
            # Get listed tokens
            _token_list = self._get_token_all_list(db_session)
            latest_block_number = web3.eth.block_number

            for _token in _token_list:
                # Get synchronized block number
                from_block_number = self.__get_synchronized_block_number(
                    db_session=db_session,
                    contract_address=_token["token"].token_address,
                    notification_type=self.notification_type
                ) + 1

                # Get the latest block number
                if from_block_number > latest_block_number:
                    LOG.info(f"<{self.__class__.__name__}> skip processing")
                    return

                # If the difference between the latest block number and fromBlock is 1,000,000 or more,
                # set toBlock to fromBlock + 999,999
                if latest_block_number - from_block_number >= 1000000:
                    to_block_number = from_block_number + 999999
                else:
                    to_block_number = latest_block_number

                # Get event logs
                try:
                    token_contract = self.contract_cache.get(_token["token"].token_address, None)
                    if token_contract is None:
                        token_contract = Contract.get_contract(
                            contract_name=_token["token_type"],
                            address=_token["token"].token_address
                        )
                        self.contract_cache[_token["token"].token_address] = token_contract
                    _event = getattr(token_contract.events, self.filter_name)
                    entries = _event.getLogs(
                        fromBlock=from_block_number,
                        toBlock=to_block_number
                    )
                except FileNotFoundError:
                    continue
                except Exception as err:  # If an Exception occurs, processing continues
                    LOG.error(err)
                    continue

                # Register notifications
                if len(entries) > 0:
                    self.db_merge(
                        db_session=db_session,
                        token_contract=token_contract,
                        token_type=_token["token_type"],
                        log_entries=entries,
                        token_owner_address=_token["token"].owner_address
                    )

                # Update synchronized block number
                self.__set_synchronized_block_number(
                    db_session=db_session,
                    contract_address=_token["token"].token_address,
                    notification_type=self.notification_type,
                    block_number=to_block_number
                )

                db_session.commit()

        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        finally:
            db_session.close()
            elapsed_time = time.time() - start_time
            LOG.info("<{}> finished in {} secs".format(self.__class__.__name__, elapsed_time))

    @staticmethod
    def __get_synchronized_block_number(db_session: Session, contract_address: str, notification_type: str):
        """Get latest synchronized blockNumber"""
        notification_block_number: NotificationBlockNumber | None = db_session.query(NotificationBlockNumber). \
            filter(NotificationBlockNumber.notification_type == notification_type). \
            filter(NotificationBlockNumber.contract_address == contract_address).\
            first()
        if notification_block_number is None:
            return -1
        else:
            return notification_block_number.latest_block_number

    @staticmethod
    def __set_synchronized_block_number(db_session: Session, contract_address: str, notification_type: str, block_number: int):
        """Set latest synchronized blockNumber"""
        notification_block_number: NotificationBlockNumber | None = db_session.query(NotificationBlockNumber). \
            filter(NotificationBlockNumber.notification_type == notification_type). \
            filter(NotificationBlockNumber.contract_address == contract_address). \
            first()
        if notification_block_number is None:
            notification_block_number = NotificationBlockNumber()
        notification_block_number.notification_type = notification_type
        notification_block_number.contract_address = contract_address
        notification_block_number.latest_block_number = block_number
        db_session.merge(notification_block_number)


class WatchTransfer(Watcher):
    """Watch Token Receive Event

    - Process for registering a notification when a token is received
    - Register a notification only if the account address (private key address) is the source of the transfer.
    """
    def __init__(self):
        super().__init__("Transfer", {}, NotificationType.TRANSFER)

    def db_merge(
        self, db_session: Session,
        token_contract: Web3Contract, token_type: str,
        log_entries: list[EventData], token_owner_address: str
    ):
        company_list = CompanyList.get()
        token_name = Contract.call_function(
            contract=token_contract,
            function_name="name",
            args=(),
            default_returns=""
        )
        for entry in log_entries:
            # If the contract address is the source of the transfer, skip the process
            if web3.eth.get_code(entry["args"]["from"]).hex() != "0x":
                continue

            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": token_type
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = entry["args"]["to"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


class WatchApplyForTransfer(Watcher):
    """Watch Token ApplyForTransfer Event

    - Process for registering a notification when application for transfer is submitted
    - Register a notification only if the account address (private key address) is the source of the transfer.
    """
    def __init__(self):
        super().__init__("ApplyForTransfer", {}, NotificationType.APPLY_FOR_TRANSFER)

    def db_merge(
        self, db_session: Session,
        token_contract: Web3Contract, token_type: str,
        log_entries: list[EventData], token_owner_address: str
    ):
        company_list = CompanyList.get()
        token_name = Contract.call_function(
            contract=token_contract,
            function_name="name",
            args=(),
            default_returns=""
        )
        for entry in log_entries:
            if not token_list.is_registered(entry["address"]):
                continue

            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": token_type
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = entry["args"]["to"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


class WatchApproveTransfer(Watcher):
    """Watch Token ApproveTransfer Event

    - Process for registering a notification when application for transfer is approved
    - Register a notification only if the account address (private key address) is the source of the transfer.
    """
    def __init__(self):
        super().__init__("ApproveTransfer", {}, NotificationType.APPROVE_TRANSFER)

    def db_merge(
        self, db_session: Session,
        token_contract: Web3Contract, token_type: str,
        log_entries: list[EventData], token_owner_address: str
    ):
        company_list = CompanyList.get()
        token_name = Contract.call_function(
            contract=token_contract,
            function_name="name",
            args=(),
            default_returns=""
        )
        for entry in log_entries:
            if not token_list.is_registered(entry["address"]):
                continue

            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": token_type
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = entry["args"]["from"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


class WatchCancelTransfer(Watcher):
    """Watch Token CancelTransfer Event

    - Process for registering a notification when application for transfer is canceled
    - Register a notification only if the account address (private key address) is the source of the transfer.
    """
    def __init__(self):
        super().__init__("CancelTransfer", {}, NotificationType.CANCEL_TRANSFER)

    def db_merge(
        self, db_session: Session,
        token_contract: Web3Contract, token_type: str,
        log_entries: list[EventData], token_owner_address: str
    ):
        company_list = CompanyList.get()
        token_name = Contract.call_function(
            contract=token_contract,
            function_name="name",
            args=(),
            default_returns=""
        )
        for entry in log_entries:
            if not token_list.is_registered(entry["address"]):
                continue

            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": token_type
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = entry["args"]["from"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


# メイン処理
def main():
    watchers = [
        WatchTransfer(),
        WatchApplyForTransfer(),
        WatchApproveTransfer(),
        WatchCancelTransfer()
    ]

    e = ThreadPoolExecutor(max_workers=WORKER_COUNT)
    LOG.info("Service started successfully")

    while True:
        start_time = time.time()

        fs = []
        for watcher in watchers:
            fs.append(e.submit(watcher.loop))
        wait_all_futures(fs)

        elapsed_time = time.time() - start_time
        LOG.info("<LOOP> finished in {} secs".format(elapsed_time))

        time.sleep(max(NOTIFICATION_PROCESS_INTERVAL - elapsed_time, 0))


if __name__ == "__main__":
    main()
