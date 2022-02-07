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
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

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
LOG = log.get_logger(process_name="PROCESSOR-NOTIFICATIONS-SHARE-TOKEN")

WORKER_COUNT = int(WORKER_COUNT)
SLEEP_INTERVAL = int(SLEEP_INTERVAL)

web3 = Web3Wrapper()
db_engine = create_engine(DATABASE_URL, echo=False)

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

    def _get_share_token_public_list(self, db_session: Session):
        res = []
        registered_token_list = db_session.query(Listing).filter(Listing.is_public == True).all()
        for registered_token in registered_token_list:
            if not token_list.is_registered(registered_token.token_address):
                continue
            elif token_list.get_token(registered_token.token_address)[1] == "IbetShare":
                res.append(registered_token)
        return res

    def _get_share_token_all_list(self, db_session: Session):
        res = []
        registered_token_list = db_session.query(Listing).all()
        for registered_token in registered_token_list:
            if not token_list.is_registered(registered_token.token_address):
                continue
            elif token_list.get_token(registered_token.token_address)[1] == "IbetShare":
                res.append(registered_token)
        return res

    @staticmethod
    def __get_db_session():
        return Session(autocommit=False, autoflush=True, bind=db_engine)

    def db_merge(self, db_session: Session, token_contract, entries):
        pass

    def loop(self):
        start_time = time.time()
        local_session = self.__get_db_session()
        try:
            LOG.info("[{}]: retrieving from {} block".format(self.__class__.__name__, self.from_block))

            self.filter_params["fromBlock"] = self.from_block

            # 最新のブロックナンバーを取得
            _latest_block = web3.eth.blockNumber
            if self.from_block > _latest_block:
                LOG.info(f"[{self.__class__.__name__}]: skip processing")
                return

            # 登録済みの株式リストを取得
            if self.__class__.__name__ == "WatchTransfer":
                share_token_list = self._get_share_token_all_list(local_session)
            else:
                share_token_list = self._get_share_token_public_list(local_session)

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
            for share_token in share_token_list:
                try:
                    share_contract = Contract.get_contract(
                        contract_name="IbetShare",
                        address=share_token.token_address
                    )
                    _event = getattr(share_contract.events, self.filter_name)
                    entries = _event.getLogs(
                        fromBlock=self.filter_params["fromBlock"],
                        toBlock=self.filter_params["toBlock"]
                    )
                except Exception as err:  # Exception が発生した場合は処理を継続
                    LOG.error(err)
                    continue
                if len(entries) > 0:
                    self.db_merge(
                        db_session=local_session,
                        token_contract=share_contract,
                        entries=entries
                    )
                    local_session.commit()

            self.from_block = _next_from
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        finally:
            local_session.close()
            elapsed_time = time.time() - start_time
            LOG.info("[{}] finished in {} secs".format(self.__class__.__name__, elapsed_time))


# イベント：募集申込開始
class WatchStartOffering(Watcher):
    def __init__(self):
        super().__init__("ChangeOfferingStatus", {"filter": {"status": True}})

    def db_merge(self, db_session: Session, token_contract, entries):
        company_list = company_list_factory.get()
        for entry in entries:
            token_owner_address = token_contract.functions.owner().call()
            token_name = token_contract.functions.name().call()
            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": "IbetShare"
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotificationType.START_OFFERING.value
            notification.priority = 0
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


# イベント：募集申込終了
class WatchStopOffering(Watcher):
    def __init__(self):
        super().__init__("ChangeOfferingStatus", {"filter": {"status": False}})

    def db_merge(self, db_session: Session, token_contract, entries):
        company_list = company_list_factory.get()
        for entry in entries:
            token_owner_address = token_contract.functions.owner().call()
            token_name = token_contract.functions.name().call()
            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": "IbetShare"
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotificationType.STOP_OFFERING.value
            notification.priority = 0
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


# イベント：取扱停止
class WatchSuspend(Watcher):
    def __init__(self):
        super().__init__("ChangeStatus", {"filter": {"status": False}})

    def db_merge(self, db_session: Session, token_contract, entries):
        company_list = company_list_factory.get()
        for entry in entries:
            token_owner_address = token_contract.functions.owner().call()
            token_name = token_contract.functions.name().call()
            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": "IbetShare"
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotificationType.SUSPEND.value
            notification.priority = 0
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


# イベント：募集申込
class WatchApplyForOffering(Watcher):
    def __init__(self):
        super().__init__("ApplyFor", {})

    def db_merge(self, db_session: Session, token_contract, entries):
        company_list = company_list_factory.get()
        for entry in entries:
            token_owner_address = token_contract.functions.owner().call()
            token_name = token_contract.functions.name().call()
            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": "IbetShare"
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotificationType.APPLY_FOR_OFFERING.value
            notification.priority = 0
            notification.address = entry["args"]["accountAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


# イベント：募集割当確定
class WatchAllot(Watcher):
    def __init__(self):
        super().__init__("Allot", {})

    def db_merge(self, db_session: Session, token_contract, entries):
        company_list = company_list_factory.get()
        for entry in entries:
            token_owner_address = token_contract.functions.owner().call()
            token_name = token_contract.functions.name().call()
            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": "IbetShare"
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotificationType.ALLOT.value
            notification.priority = 1
            notification.address = entry["args"]["accountAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)


# イベント：トークン移転（受領時）
class WatchTransfer(Watcher):
    """Watch Token Receive Event

    - Process for registering a notification when a token is received
    - Register a notification only if the account address (private key address) is the source of the transfer.
    """
    def __init__(self):
        super().__init__("Transfer", {})

    def db_merge(self, db_session: Session, token_contract, entries):
        company_list = company_list_factory.get()
        for entry in entries:
            # If the contract address is the source of the transfer, skip the process
            if web3.eth.getCode(entry["args"]["from"]).hex() != "0x":
                continue

            token_owner_address = token_contract.functions.owner().call()
            token_name = token_contract.functions.name().call()
            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": "IbetShare"
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
        WatchStartOffering(),
        WatchStopOffering(),
        WatchSuspend(),
        WatchApplyForOffering(),
        WatchTransfer(),
        WatchAllot(),
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
