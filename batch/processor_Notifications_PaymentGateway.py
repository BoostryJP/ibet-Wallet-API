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
    PAYMENT_GATEWAY_CONTRACT_ADDRESS
)
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.db import (
    Notification,
    NotificationType
)
from app.utils.web3_utils import Web3Wrapper
from batch.lib.misc import wait_all_futures
import log

JST = timezone(timedelta(hours=+9), "JST")
LOG = log.get_logger(process_name="PROCESSOR-NOTIFICATIONS-PAYMENTGATEWAY")

WORKER_COUNT = int(WORKER_COUNT)
SLEEP_INTERVAL = int(SLEEP_INTERVAL)

web3 = Web3Wrapper()

engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)

# 起動時のblockNumberを取得
NOW_BLOCKNUMBER = web3.eth.blockNumber

# コントラクトの生成
payment_gateway_contract = Contract.get_contract(
    contract_name="PaymentGateway",
    address=PAYMENT_GATEWAY_CONTRACT_ADDRESS
)


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
            if self.from_block > _latest_block:
                LOG.info(f"[{self.__class__.__name__}]: skip processing")
                return

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
受領用銀行口座認可関連（PaymentGateway）
"""


# イベント：受領用銀行口座登録
class WatchPaymentAccountRegister(Watcher):
    def __init__(self):
        super().__init__(payment_gateway_contract, "Register", {})

    def watch(self, entries):
        for entry in entries:
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotificationType.PAYMENT_ACCOUNT_REGISTER.value
            notification.priority = 2
            notification.address = entry["args"]["account_address"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = {}
            db_session.merge(notification)


# イベント：受領用銀行口座承認
class WatchPaymentAccountApprove(Watcher):
    def __init__(self):
        super().__init__(payment_gateway_contract, "Approve", {})

    def watch(self, entries):
        for entry in entries:
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotificationType.PAYMENT_ACCOUNT_APPROVE.value
            notification.priority = 0
            notification.address = entry["args"]["account_address"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = {}
            db_session.merge(notification)


# イベント：受領用銀行口座警告
class WatchPaymentAccountWarn(Watcher):
    def __init__(self):
        super().__init__(payment_gateway_contract, "Warn", {})

    def watch(self, entries):
        for entry in entries:
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotificationType.PAYMENT_ACCOUNT_WARN.value
            notification.priority = 0
            notification.address = entry["args"]["account_address"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = {}
            db_session.merge(notification)


# イベント：受領用銀行口座非承認
class WatchPaymentAccountDisapprove(Watcher):
    def __init__(self):
        super().__init__(payment_gateway_contract, "Disapprove", {})

    def watch(self, entries):
        for entry in entries:
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotificationType.PAYMENT_ACCOUNT_UNAPPROVE.value
            notification.priority = 0
            notification.address = entry["args"]["account_address"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = {}
            db_session.merge(notification)


# イベント：受領用銀行口座アカウント停止
class WatchPaymentAccountBan(Watcher):
    def __init__(self):
        super().__init__(payment_gateway_contract, "Ban", {})

    def watch(self, entries):
        for entry in entries:
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotificationType.PAYMENT_ACCOUNT_BAN.value
            notification.priority = 2
            notification.address = entry["args"]["account_address"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = {}
            db_session.merge(notification)


def main():
    watchers = [
        WatchPaymentAccountRegister(),
        WatchPaymentAccountApprove(),
        WatchPaymentAccountWarn(),
        WatchPaymentAccountDisapprove(),
        WatchPaymentAccountBan(),
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
