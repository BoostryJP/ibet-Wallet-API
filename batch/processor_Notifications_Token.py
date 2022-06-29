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
    TOKEN_LIST_CONTRACT_ADDRESS
)
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.db import (
    Notification,
    NotificationType,
    Listing
)
from app.utils.web3_utils import Web3Wrapper
from app.utils.company_list import CompanyList
from batch.lib.token_list import TokenList
from batch.lib.misc import wait_all_futures
import log

JST = timezone(timedelta(hours=+9), "JST")
LOG = log.get_logger(process_name="PROCESSOR-NOTIFICATIONS-TOKEN")

WORKER_COUNT = int(WORKER_COUNT)
SLEEP_INTERVAL = int(SLEEP_INTERVAL)

web3 = Web3Wrapper()

db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

# 起動時のblockNumberを取得
NOW_BLOCKNUMBER = web3.eth.block_number

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
        return datetime.fromtimestamp(web3.eth.get_block(entry["blockNumber"])["timestamp"], JST)

    @staticmethod
    def _get_token_all_list(db_session: Session):
        _tokens = []
        listed_tokens = db_session.query(Listing).all()
        for listed_token in listed_tokens:
            if not token_list.is_registered(listed_token.token_address):
                continue
            else:
                token_type = token_list.get_token(listed_token.token_address)[1]
                _tokens.append({
                    "token": listed_token,
                    "token_type": token_type
                })
        return _tokens

    def db_merge(self, db_session: Session, token_contract, token_type, log_entries):
        pass

    def loop(self):
        start_time = time.time()
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            LOG.info("[{}]: retrieving from {} block".format(self.__class__.__name__, self.from_block))

            self.filter_params["fromBlock"] = self.from_block

            # 最新のブロックナンバーを取得
            _latest_block = web3.eth.block_number
            if self.from_block > _latest_block:
                LOG.info(f"[{self.__class__.__name__}]: skip processing")
                return

            # リスティング済みトークンを取得
            _token_list = self._get_token_all_list(db_session)

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
            for _token in _token_list:
                try:
                    token_contract = Contract.get_contract(
                        contract_name=_token["token_type"],
                        address=_token["token"].token_address
                    )
                    _event = getattr(token_contract.events, self.filter_name)
                    entries = _event.getLogs(
                        fromBlock=self.filter_params["fromBlock"],
                        toBlock=self.filter_params["toBlock"]
                    )
                except FileNotFoundError:
                    continue
                except Exception as err:  # Exception が発生した場合は処理を継続
                    LOG.error(err)
                    continue
                if len(entries) > 0:
                    self.db_merge(
                        db_session=db_session,
                        token_contract=token_contract,
                        token_type=_token["token_type"],
                        log_entries=entries
                    )
                    db_session.commit()

            self.from_block = _next_from
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        finally:
            db_session.close()
            elapsed_time = time.time() - start_time
            LOG.info("[{}] finished in {} secs".format(self.__class__.__name__, elapsed_time))


# イベント：トークン移転（受領時）
class WatchTransfer(Watcher):
    """Watch Token Receive Event

    - Process for registering a notification when a token is received
    - Register a notification only if the account address (private key address) is the source of the transfer.
    """
    def __init__(self):
        super().__init__("Transfer", {})

    def db_merge(self, db_session: Session, token_contract, token_type, log_entries):
        company_list = CompanyList.get()
        for entry in log_entries:
            # If the contract address is the source of the transfer, skip the process
            if web3.eth.get_code(entry["args"]["from"]).hex() != "0x":
                continue

            token_owner_address = Contract.call_function(
                contract=token_contract,
                function_name="owner",
                args=(),
                default_returns=""
            )
            token_name = Contract.call_function(
                contract=token_contract,
                function_name="name",
                args=(),
                default_returns=""
            )
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
