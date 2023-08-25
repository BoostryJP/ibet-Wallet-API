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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

import log

from app.config import (
    DATABASE_URL,
    IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
    NOTIFICATION_PROCESS_INTERVAL,
    TOKEN_LIST_CONTRACT_ADDRESS,
    WORKER_COUNT,
)
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.db import Notification, NotificationBlockNumber, NotificationType
from app.model.schema.base import TokenType
from app.utils.company_list import CompanyList
from app.utils.web3_utils import Web3Wrapper
from batch.lib.misc import wait_all_futures
from batch.lib.token import TokenFactory
from batch.lib.token_list import TokenList

LOG = log.get_logger(process_name="PROCESSOR-NOTIFICATIONS-COUPON-EXCHANGE")

WORKER_COUNT = int(WORKER_COUNT)
NOTIFICATION_PROCESS_INTERVAL = int(NOTIFICATION_PROCESS_INTERVAL)

web3 = Web3Wrapper()

db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

token_factory = TokenFactory(web3)

# Get coupon IbetExchange contract
cp_exchange_contract = Contract.get_contract(
    contract_name="IbetExchange", address=IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS
)

# Get TokenList contract
list_contract = Contract.get_contract(
    contract_name="TokenList", address=TOKEN_LIST_CONTRACT_ADDRESS
)
token_list = TokenList(list_contract, TokenType.IbetCoupon)


# Watcher
class Watcher:
    def __init__(
        self, contract, filter_name: str, filter_params: dict, notification_type: str
    ):
        self.contract = contract
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
        return datetime.utcfromtimestamp(
            web3.eth.get_block(entry["blockNumber"])["timestamp"]
        )

    def watch(self, db_session: Session, entries):
        pass

    def loop(self):
        start_time = time.time()
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)

        try:
            # Get synchronized block number
            from_block_number = (
                self.__get_synchronized_block_number(
                    db_session=db_session,
                    contract_address=self.contract.address,
                    notification_type=self.notification_type,
                )
                + 1
            )

            # Get the latest block number
            latest_block_number = web3.eth.block_number
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
            _event = getattr(self.contract.events, self.filter_name)
            entries = _event.get_logs(
                fromBlock=from_block_number, toBlock=to_block_number
            )

            # Register notifications
            if len(entries) > 0:
                self.watch(db_session=db_session, entries=entries)

            # Update synchronized block number
            self.__set_synchronized_block_number(
                db_session=db_session,
                contract_address=self.contract.address,
                notification_type=self.notification_type,
                block_number=to_block_number,
            )

            db_session.commit()

        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as err:  # Exceptionが発生した場合は処理を継続
            LOG.exception(err)
        finally:
            db_session.close()
            elapsed_time = time.time() - start_time
        LOG.info(
            "<{}> finished in {} secs".format(self.__class__.__name__, elapsed_time)
        )

    @staticmethod
    def __get_synchronized_block_number(
        db_session: Session, contract_address: str, notification_type: str
    ):
        """Get latest synchronized blockNumber"""
        notification_block_number: NotificationBlockNumber | None = db_session.scalars(
            select(NotificationBlockNumber)
            .where(NotificationBlockNumber.notification_type == notification_type)
            .where(NotificationBlockNumber.contract_address == contract_address)
            .limit(1)
        ).first()
        if notification_block_number is None:
            return -1
        else:
            return notification_block_number.latest_block_number

    @staticmethod
    def __set_synchronized_block_number(
        db_session: Session,
        contract_address: str,
        notification_type: str,
        block_number: int,
    ):
        """Set latest synchronized blockNumber"""
        notification_block_number: NotificationBlockNumber | None = db_session.scalars(
            select(NotificationBlockNumber)
            .where(NotificationBlockNumber.notification_type == notification_type)
            .where(NotificationBlockNumber.contract_address == contract_address)
            .limit(1)
        ).first()
        if notification_block_number is None:
            notification_block_number = NotificationBlockNumber()
        notification_block_number.notification_type = notification_type
        notification_block_number.contract_address = contract_address
        notification_block_number.latest_block_number = block_number
        db_session.merge(notification_block_number)


class WatchCouponNewOrder(Watcher):
    """Watch NewOrder event"""

    def __init__(self):
        super().__init__(
            cp_exchange_contract, "NewOrder", {}, NotificationType.NEW_ORDER
        )

    def watch(self, db_session: Session, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_coupon(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": TokenType.IbetCoupon,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = entry["args"]["accountAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


class WatchCouponCancelOrder(Watcher):
    """Watch CancelOrder event"""

    def __init__(self):
        super().__init__(
            cp_exchange_contract, "CancelOrder", {}, NotificationType.CANCEL_ORDER
        )

    def watch(self, db_session: Session, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_coupon(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": TokenType.IbetCoupon,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = entry["args"]["accountAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


class WatchCouponForceCancelOrder(Watcher):
    """Watch ForceCancelOrder event"""

    def __init__(self):
        super().__init__(
            cp_exchange_contract,
            "ForceCancelOrder",
            {},
            NotificationType.FORCE_CANCEL_ORDER,
        )

    def watch(self, db_session: Session, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_coupon(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": TokenType.IbetCoupon,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 2
            notification.address = entry["args"]["accountAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


class WatchCouponBuyAgreement(Watcher):
    """Watch Agree event (BUY)"""

    def __init__(self):
        super().__init__(
            cp_exchange_contract, "Agree", {}, NotificationType.BUY_AGREEMENT
        )

    def watch(self, db_session: Session, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_coupon(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": TokenType.IbetCoupon,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 1)
            notification.notification_type = self.notification_type
            notification.priority = 1
            notification.address = entry["args"]["buyAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


class WatchCouponSellAgreement(Watcher):
    """Watch Agree event (SELL)"""

    def __init__(self):
        super().__init__(
            cp_exchange_contract, "Agree", {}, NotificationType.SELL_AGREEMENT
        )

    def watch(self, db_session: Session, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_coupon(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": TokenType.IbetCoupon,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 2)
            notification.notification_type = self.notification_type
            notification.priority = 2
            notification.address = entry["args"]["sellAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


class WatchCouponBuySettlementOK(Watcher):
    """Watch SettlementOK event (BUY)"""

    def __init__(self):
        super().__init__(
            cp_exchange_contract, "SettlementOK", {}, NotificationType.BUY_SETTLEMENT_OK
        )

    def watch(self, db_session: Session, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_coupon(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": TokenType.IbetCoupon,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 1)
            notification.notification_type = self.notification_type
            notification.priority = 1
            notification.address = entry["args"]["buyAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


class WatchCouponSellSettlementOK(Watcher):
    """Watch SettlementOK event (SELL)"""

    def __init__(self):
        super().__init__(
            cp_exchange_contract,
            "SettlementOK",
            {},
            NotificationType.SELL_SETTLEMENT_OK,
        )

    def watch(self, db_session: Session, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_coupon(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": TokenType.IbetCoupon,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 2)
            notification.notification_type = self.notification_type
            notification.priority = 1
            notification.address = entry["args"]["sellAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


class WatchCouponBuySettlementNG(Watcher):
    """Watch SettlementNG event (BUY)"""

    def __init__(self):
        super().__init__(
            cp_exchange_contract, "SettlementNG", {}, NotificationType.BUY_SETTLEMENT_NG
        )

    def watch(self, db_session: Session, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_coupon(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": TokenType.IbetCoupon,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 1)
            notification.notification_type = self.notification_type
            notification.priority = 2
            notification.address = entry["args"]["buyAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


class WatchCouponSellSettlementNG(Watcher):
    """Watch SettlementNG event (SELL)"""

    def __init__(self):
        super().__init__(
            cp_exchange_contract,
            "SettlementNG",
            {},
            NotificationType.SELL_SETTLEMENT_NG,
        )

    def watch(self, db_session: Session, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_coupon(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": TokenType.IbetCoupon,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 2)
            notification.notification_type = self.notification_type
            notification.priority = 2
            notification.address = entry["args"]["sellAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


def main():
    watchers = [
        WatchCouponNewOrder(),
        WatchCouponCancelOrder(),
        WatchCouponForceCancelOrder(),
        WatchCouponBuyAgreement(),
        WatchCouponSellAgreement(),
        WatchCouponBuySettlementOK(),
        WatchCouponSellSettlementOK(),
        WatchCouponBuySettlementNG(),
        WatchCouponSellSettlementNG(),
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
