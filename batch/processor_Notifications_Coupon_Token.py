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
    TOKEN_LIST_CONTRACT_ADDRESS,
    COMPANY_LIST_URL
)
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.db import (
    Notification,
    NotificationType,
    Listing
)
from app.utils.web3_utils import Web3Wrapper
from batch.lib.company_list import CompanyListFactory
from batch.lib.token_list import TokenList
from batch.lib.misc import wait_all_futures
import log

JST = timezone(timedelta(hours=+9), "JST")
LOG = log.get_logger(process_name="PROCESSOR-NOTIFICATIONS-COUPON-TOKEN")

WORKER_COUNT = int(WORKER_COUNT)
SLEEP_INTERVAL = int(SLEEP_INTERVAL)

web3 = Web3Wrapper()

engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)

company_list_factory = CompanyListFactory(COMPANY_LIST_URL)

# 起動時のblockNumberを取得
NOW_BLOCKNUMBER = web3.eth.blockNumber

# コントラクトの生成
list_contract = Contract.get_contract(
    contract_name="TokenList",
    address=TOKEN_LIST_CONTRACT_ADDRESS
)
token_list = TokenList(list_contract)


# Watcher
class Watcher:
    def __init__(self, filter_name, filter_params):
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

    def _get_coupon_token_public_list(self):
        res = []
        registered_token_list = db_session.query(Listing).filter(Listing.is_public == True).all()
        for registered_token in registered_token_list:
            if not token_list.is_registered(registered_token.token_address):
                continue
            elif token_list.get_token(registered_token.token_address)[1] == "IbetCoupon":
                res.append(registered_token)
        return res

    def _get_coupon_token_all_list(self):
        res = []
        registered_token_list = db_session.query(Listing).all()
        for registered_token in registered_token_list:
            if not token_list.is_registered(registered_token.token_address):
                continue
            elif token_list.get_token(registered_token.token_address)[1] == "IbetCoupon":
                res.append(registered_token)
        return res

    def db_merge(self, token_contract, entries):
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

            # 登録済みの債券リストを取得
            if self.__class__.__name__ == "WatchTransfer":
                coupon_token_list = self._get_coupon_token_all_list()
            else:
                coupon_token_list = self._get_coupon_token_public_list()

            # レスポンスタイムアウト抑止
            # 最新のブロックナンバーと fromBlock の差が 1,000,000 以上の場合は
            # toBlock に fromBlock + 999,999 を設定
            if _latest_block - self.from_block >= 1000000:
                self.filter_params["toBlock"] = self.from_block + 999999
                _next_from = self.from_block + 1000000
            else:
                self.filter_params["toBlock"] = _latest_block
                _next_from = _latest_block + 1

            # イベント処理
            for coupon_token in coupon_token_list:
                try:
                    coupon_contract = Contract.get_contract(
                        contract_name="IbetCoupon",
                        address=coupon_token.token_address
                    )
                    _event = getattr(coupon_contract.events, self.filter_name)
                    entries = _event.getLogs(
                        fromBlock=self.filter_params["fromBlock"],
                        toBlock=self.filter_params["toBlock"]
                    )
                except Exception as err:  # Exception が発生した場合は処理を継続
                    LOG.error(err)
                    continue
                if len(entries) > 0:
                    self.db_merge(coupon_contract, entries)
                    db_session.commit()

            self.from_block = _next_from
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        finally:
            elapsed_time = time.time() - start_time
            LOG.info("[{}] finished in {} secs".format(self.__class__.__name__, elapsed_time))


# イベント：トークン移転（受領時）
class WatchTransfer(Watcher):
    def __init__(self):
        super().__init__("Transfer", {})

    def db_merge(self, token_contract, entries):
        company_list = company_list_factory.get()
        for entry in entries:
            # Exchangeアドレスが移転元の場合、処理をSKIPする
            tradable_exchange = token_contract.functions.tradableExchange().call()
            if entry["args"]["from"] == tradable_exchange:
                continue
            token_owner_address = token_contract.functions.owner().call()
            token_name = token_contract.functions.name().call()
            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": "IbetCoupon"
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotificationType.TRANSFER.value
            notification.priority = 0
            notification.address = entry["args"]["to"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


# メイン処理
def main():
    watchers = [
        WatchTransfer(),
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
