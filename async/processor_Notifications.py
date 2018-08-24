# -*- coding: utf-8 -*-

import os
import sys

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

import logging
from web3 import Web3
from web3.middleware import geth_poa_middleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from eth_utils import to_checksum_address
from app import config
from app.model import Notification
from app.contracts import Contract
import json
from async.lib.token import TokenFactory
from async.lib.company_list import CompanyListFactory
from async.lib.token_list import TokenList
from async.lib.misc import wait_all_futures
from concurrent.futures import ThreadPoolExecutor
import time
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=+9), "JST")

#logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# 設定の取得
WEB3_HTTP_PROVIDER = os.environ.get("WEB3_HTTP_PROVIDER") or "http://localhost:8545"
URI = os.environ.get("DATABASE_URL") or "postgresql://ethuser:ethpass@localhost:5432/ethcache"
WORKER_COUNT = int(os.environ.get("WORKER_COUNT") or 8)
SLEEP_INTERVAL = int(os.environ.get("SLEEP_INTERVAL") or 3)
IBET_SB_EXCHANGE_CONTRACT_ADDRESS = os.environ.get("IBET_SB_EXCHANGE_CONTRACT_ADDRESS")
IBET_CP_EXCHANGE_CONTRACT_ADDRESS = os.environ.get("IBET_CP_EXCHANGE_CONTRACT_ADDRESS")

# 初期化
web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)
engine = create_engine(URI, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)
token_factory = TokenFactory(web3)
company_list_factory = CompanyListFactory(config.COMPANY_LIST_URL)

# コントラクトの生成
sb_exchange_contract = Contract.get_contract(
    'IbetStraightBondExchange', os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS'))
cp_exchange_contract = Contract.get_contract(
    'IbetCouponExchange', os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS'))
white_list_contract = Contract.get_contract(
    'WhiteList', os.environ.get('WHITE_LIST_CONTRACT_ADDRESS'))
list_contract = Contract.get_contract(
    'TokenList', os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS'))

token_list = TokenList(list_contract)

class Watcher:
    def __init__(self, contract, filter_name, filter_params):
        self.contract = contract
        self.filter_name = filter_name
        self.filter_params = filter_params
        self.from_block = 0

    def _gen_notification_id(self, entry, option_type = 0):
        return "0x{:012x}{:06x}{:06x}{:02x}".format(
            entry["blockNumber"],
            entry["transactionIndex"],
            entry["logIndex"],
            option_type,
        )

    def _gen_block_timestamp(self, entry):
        return datetime.fromtimestamp(web3.eth.getBlock(entry["blockNumber"])["timestamp"], JST)

    def loop(self):
        start_time = time.time()
        try:
            print("[{}]: retrieving from {} block".format(self.__class__.__name__, self.from_block))

            self.filter_params["fromBlock"] = self.from_block
            event_filter = self.contract.eventFilter(self.filter_name, self.filter_params)
            entries = event_filter.get_all_entries()
            web3.eth.uninstallFilter(event_filter.filter_id)
            if len(entries) == 0:
                return

            self.watch(entries)
            self.from_block = max(map(lambda e: e["blockNumber"], entries)) + 1
            db_session.commit()
        finally:
            elapsed_time = time.time() - start_time
            print("[{}] finished in {} secs".format(self.__class__.__name__, elapsed_time))

# イベント：決済用口座登録
class WatchWhiteListRegister(Watcher):
    def __init__(self):
        super().__init__(white_list_contract, "Register", {})

    def watch(self, entries):
        for entry in entries:
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = "WhiteListRegister"
            notification.priority = 2
            notification.address = entry["args"]["account_address"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = {}
            db_session.merge(notification)

# イベント：決済用口座承認
class WatchWhiteListApprove(Watcher):
    def __init__(self):
        super().__init__(white_list_contract, "Approve", {})

    def watch(self, entries):
        for entry in entries:
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = "WhiteListApprove"
            notification.priority = 0
            notification.address = entry["args"]["account_address"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = {}
            db_session.merge(notification)

# イベント：決済用口座警告
class WatchWhiteListWarn(Watcher):
    def __init__(self):
        super().__init__(white_list_contract, "Warn", {})

    def watch(self, entries):
        for entry in entries:
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = "WhiteListWarn"
            notification.priority = 0
            notification.address = entry["args"]["account_address"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = {}
            db_session.merge(notification)

# イベント：決済用口座非承認
class WatchWhiteListUnapprove(Watcher):
    def __init__(self):
        super().__init__(white_list_contract, "Unapprove", {})

    def watch(self, entries):
        for entry in entries:
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = "WhiteListUnapprove"
            notification.priority = 0
            notification.address = entry["args"]["account_address"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = {}
            db_session.merge(notification)

# イベント：決済用口座アカウント停止
class WatchWhiteListBan(Watcher):
    def __init__(self):
        super().__init__(white_list_contract, "Ban", {})

    def watch(self, entries):
        for entry in entries:
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = "WhiteListBan"
            notification.priority = 2
            notification.address = entry["args"]["account_address"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = {}
            db_session.merge(notification)

# イベント：注文
class WatchExchangeNewOrder(Watcher):
    def __init__(self):
        super().__init__(sb_exchange_contract, "NewOrder", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_straight_bond(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = "NewOrder"
            notification.priority = 0
            notification.address = entry["args"]["accountAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)

# イベント：注文取消
class WatchExchangeCancelOrder(Watcher):
    def __init__(self):
        super().__init__(sb_exchange_contract, "CancelOrder", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_straight_bond(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = "CancelOrder"
            notification.priority = 0
            notification.address = entry["args"]["accountAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)

# イベント：約定（買）
class WatchExchangeBuyAgreement(Watcher):
    def __init__(self):
        super().__init__(sb_exchange_contract, "Agree", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_straight_bond(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 1)
            notification.notification_type = "BuyAgreement"
            notification.priority = 1
            notification.address = entry["args"]["buyAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)

# イベント：約定（売）
class WatchExchangeSellAgreement(Watcher):
    def __init__(self):
        super().__init__(sb_exchange_contract, "Agree", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_straight_bond(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 2)
            notification.notification_type = "SellAgreement"
            notification.priority = 2
            notification.address = entry["args"]["sellAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)

# イベント：決済OK（買）
class WatchExchangeBuySettlementOK(Watcher):
    def __init__(self):
        super().__init__(sb_exchange_contract, "SettlementOK", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_straight_bond(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 1)
            notification.notification_type = "BuySettlementOK"
            notification.priority = 1
            notification.address = entry["args"]["buyAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)

# イベント：決済OK（売）
class WatchExchangeSellSettlementOK(Watcher):
    def __init__(self):
        super().__init__(sb_exchange_contract, "SettlementOK", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_straight_bond(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 2)
            notification.notification_type = "SellSettlementOK"
            notification.priority = 1
            notification.address = entry["args"]["sellAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)

# イベント：決済NG（買）
class WatchExchangeBuySettlementNG(Watcher):
    def __init__(self):
        super().__init__(sb_exchange_contract, "SettlementNG", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_straight_bond(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 1)
            notification.notification_type = "BuySettlementNG"
            notification.priority = 2
            notification.address = entry["args"]["buyAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)

# イベント：決済NG（売）
class WatchExchangeSellSettlementNG(Watcher):
    def __init__(self):
        super().__init__(sb_exchange_contract, "SettlementNG", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            token = token_factory.get_straight_bond(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry, 2)
            notification.notification_type = "SellSettlementNG"
            notification.priority = 2
            notification.address = entry["args"]["sellAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)

# イベント：クーポン割当・譲渡
class WatchCouponTransfer(Watcher):
    def __init__(self):
        super().__init__(cp_exchange_contract, "Transfer", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]
            token = token_factory.get_coupon(token_address)
            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_CP_EXCHANGE_CONTRACT_ADDRESS,
                "from": entry["args"]["from"],
            }

            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = "CouponTransfer"
            notification.priority = 0
            notification.address = entry["args"]["to"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)

def main():
    watchers = [
        WatchWhiteListRegister(),
        WatchWhiteListApprove(),
        WatchWhiteListWarn(),
        WatchWhiteListUnapprove(),
        WatchWhiteListBan(),
        WatchExchangeNewOrder(),
        WatchExchangeCancelOrder(),
        WatchExchangeBuyAgreement(),
        WatchExchangeSellAgreement(),
        WatchExchangeBuySettlementOK(),
        WatchExchangeSellSettlementOK(),
        WatchExchangeBuySettlementNG(),
        WatchExchangeSellSettlementNG(),
        WatchCouponTransfer(),
    ]

    e = ThreadPoolExecutor(max_workers = WORKER_COUNT)
    while True:
        start_time = time.time()

        fs = []
        for watcher in watchers:
            fs.append(e.submit(watcher.loop))
        wait_all_futures(fs)

        elapsed_time = time.time() - start_time
        print("[LOOP] finished in {} secs".format(elapsed_time))

        time.sleep(max(SLEEP_INTERVAL - elapsed_time, 0))

    print("OK")

if __name__ == "__main__":
    main()
