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
from datetime import (
    datetime,
    timezone,
    timedelta
)

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session
)

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app.config import (
    DATABASE_URL,
    WORKER_COUNT,
    SLEEP_INTERVAL,
    IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
    TOKEN_LIST_CONTRACT_ADDRESS
)
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.db import (
    Notification,
    NotificationType
)
from app.utils.web3_utils import Web3Wrapper
from batch.lib.token import TokenFactory
from app.utils.company_list import CompanyList
from batch.lib.token_list import TokenList
from batch.lib.misc import wait_all_futures
import log

JST = timezone(timedelta(hours=+9), "JST")
LOG = log.get_logger(process_name="PROCESSOR-NOTIFICATIONS-MEMBERSHIP-EXCHANGE")

WORKER_COUNT = int(WORKER_COUNT)
SLEEP_INTERVAL = int(SLEEP_INTERVAL)

web3 = Web3Wrapper()

engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)

token_factory = TokenFactory(web3)

# 起動時のblockNumberを取得
NOW_BLOCKNUMBER = web3.eth.blockNumber

# コントラクトの生成
membership_exchange_contract = Contract.get_contract(
    contract_name="IbetExchange",
    address=IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS
)
list_contract = Contract.get_contract(
    contract_name="TokenList",
    address=TOKEN_LIST_CONTRACT_ADDRESS
)
token_list = TokenList(list_contract, "IbetMembership")


# Watcher
class Watcher:
    def __init__(self, contract, filter_name, filter_params):
        self.contract = contract
        self.filter_name = filter_name
        self.filter_params = filter_params
        self.from_block = 0

    def _gen_notification_id(self, entry, option_type=0):
        return "0x{:012x}{:06x}{:06x}{:02x}".format(
            entry["blockNumber"],
            entry["transactionIndex"],
            entry["logIndex"],
            option_type,
        )

    def _gen_block_timestamp(self, entry):
        return datetime.fromtimestamp(web3.eth.getBlock(entry["blockNumber"])["timestamp"], JST)

    def watch(self, entries):
        pass

    def loop(self):
        start_time = time.time()
        try:
            LOG.info("[{}]: retrieving from {} block".format(self.__class__.__name__, self.from_block))

            self.filter_params["fromBlock"] = self.from_block

            # 最新のブロックナンバーを取得
            _latest_block = web3.eth.blockNumber

            # レスポンスタイムアウト抑止
            # 最新のブロックナンバーと fromBlock の差が 1,000,000 以上の場合は
            # toBlock に fromBlock + 999,999 を設定
            if _latest_block - self.from_block >= 1000000:
                self.filter_params["toBlock"] = self.from_block + 999999
                _next_from = self.from_block + 1000000
            else:
                self.filter_params["toBlock"] = _latest_block
                _next_from = _latest_block + 1

            _event = getattr(self.contract.events, self.filter_name)
            entries = _event.getLogs(
                fromBlock=self.filter_params["fromBlock"],
                toBlock=self.filter_params["toBlock"]
            )
            if len(entries) > 0:
                self.watch(entries)
                db_session.commit()

            self.from_block = _next_from
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except Exception as err:  # Exceptionが発生した場合は処理を継続
            LOG.error(err)
        finally:
            elapsed_time = time.time() - start_time
            LOG.info("[{}] finished in {} secs".format(self.__class__.__name__, elapsed_time))


"""
会員権取引関連（IbetExchange）
"""


# イベント：注文
class WatchMembershipNewOrder(Watcher):
    def __init__(self):
        super().__init__(membership_exchange_contract, "NewOrder", {})

    def watch(self, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_membership(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetMembership"
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotificationType.NEW_ORDER.value
            notification.priority = 0
            notification.address = entry["args"]["accountAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


# イベント：注文取消
class WatchMembershipCancelOrder(Watcher):
    def __init__(self):
        super().__init__(membership_exchange_contract, "CancelOrder", {})

    def watch(self, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_membership(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetMembership"
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotificationType.CANCEL_ORDER.value
            notification.priority = 0
            notification.address = entry["args"]["accountAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


# イベント：強制注文取消
class WatchMembershipForceCancelOrder(Watcher):
    def __init__(self):
        super().__init__(membership_exchange_contract, "ForceCancelOrder", {})

    def watch(self, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_membership(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetMembership"
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotificationType.FORCE_CANCEL_ORDER.value
            notification.priority = 2
            notification.address = entry["args"]["accountAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


# イベント：約定（買）
class WatchMembershipBuyAgreement(Watcher):
    def __init__(self):
        super().__init__(membership_exchange_contract, "Agree", {})

    def watch(self, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_membership(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetMembership"
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 1)
            notification.notification_type = NotificationType.BUY_AGREEMENT.value
            notification.priority = 1
            notification.address = entry["args"]["buyAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


# イベント：約定（売）
class WatchMembershipSellAgreement(Watcher):
    def __init__(self):
        super().__init__(membership_exchange_contract, "Agree", {})

    def watch(self, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_membership(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetMembership"
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 2)
            notification.notification_type = NotificationType.SELL_AGREEMENT.value
            notification.priority = 2
            notification.address = entry["args"]["sellAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


# イベント：決済OK（買）
class WatchMembershipBuySettlementOK(Watcher):
    def __init__(self):
        super().__init__(membership_exchange_contract, "SettlementOK", {})

    def watch(self, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_membership(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetMembership"
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 1)
            notification.notification_type = NotificationType.BUY_SETTLEMENT_OK.value
            notification.priority = 1
            notification.address = entry["args"]["buyAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


# イベント：決済OK（売）
class WatchMembershipSellSettlementOK(Watcher):
    def __init__(self):
        super().__init__(membership_exchange_contract, "SettlementOK", {})

    def watch(self, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_membership(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetMembership"
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 2)
            notification.notification_type = NotificationType.SELL_SETTLEMENT_OK.value
            notification.priority = 1
            notification.address = entry["args"]["sellAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


# イベント：決済NG（買）
class WatchMembershipBuySettlementNG(Watcher):
    def __init__(self):
        super().__init__(membership_exchange_contract, "SettlementNG", {})

    def watch(self, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_membership(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetMembership"
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 1)
            notification.notification_type = NotificationType.BUY_SETTLEMENT_NG.value
            notification.priority = 2
            notification.address = entry["args"]["buyAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


# イベント：決済NG（売）
class WatchMembershipSellSettlementNG(Watcher):
    def __init__(self):
        super().__init__(membership_exchange_contract, "SettlementNG", {})

    def watch(self, entries):
        company_list = CompanyList.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_membership(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_address": token_address,
                "token_name": token.name,
                "exchange_address": IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetMembership"
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 2)
            notification.notification_type = NotificationType.SELL_SETTLEMENT_NG.value
            notification.priority = 2
            notification.address = entry["args"]["sellAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


def main():
    watchers = [
        WatchMembershipNewOrder(),
        WatchMembershipCancelOrder(),
        WatchMembershipForceCancelOrder(),
        WatchMembershipBuyAgreement(),
        WatchMembershipSellAgreement(),
        WatchMembershipBuySettlementOK(),
        WatchMembershipSellSettlementOK(),
        WatchMembershipBuySettlementNG(),
        WatchMembershipSellSettlementNG(),
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
        LOG.info("[LOOP] finished in {} secs".format(elapsed_time))

        time.sleep(max(SLEEP_INTERVAL - elapsed_time, 0))


if __name__ == "__main__":
    main()
