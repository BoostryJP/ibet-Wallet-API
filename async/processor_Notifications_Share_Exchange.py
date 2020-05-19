# -*- coding: utf-8 -*-
import os
import sys
import logging
from concurrent.futures import ThreadPoolExecutor
import time
from datetime import datetime, timezone, timedelta

from web3 import Web3
from web3.middleware import geth_poa_middleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)
from app import log
from app import config
from app.model import Notification, NotificationType
from app.contracts import Contract
from async.lib.token import TokenFactory
from async.lib.company_list import CompanyListFactory
from async.lib.token_list import TokenList
from async.lib.misc import wait_all_futures

JST = timezone(timedelta(hours=+9), "JST")

LOG = log.get_logger()
log_fmt = 'PROCESSOR-Notifications_Share_Exchange [%(asctime)s] [%(process)d] [%(levelname)s] %(message)s'
logging.basicConfig(format=log_fmt)

# 設定の取得
WEB3_HTTP_PROVIDER = config.WEB3_HTTP_PROVIDER
URI = config.DATABASE_URL
WORKER_COUNT = int(config.WORKER_COUNT)
SLEEP_INTERVAL = int(config.SLEEP_INTERVAL)
IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS

# 初期化
web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)
engine = create_engine(URI, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)
token_factory = TokenFactory(web3)
company_list_factory = CompanyListFactory(config.COMPANY_LIST_URL)

# 起動時のblockNumberを取得
NOW_BLOCKNUMBER = web3.eth.blockNumber

# コントラクトの生成
share_exchange_contract = Contract.get_contract('IbetOTCExchange', IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS)
list_contract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)
token_list = TokenList(list_contract)


# Watcher
class Watcher:
    def __init__(self, contract, filter_name, filter_params):
        self.contract = contract
        self.filter_name = filter_name
        self.filter_params = filter_params
        self.from_block = 0

    def watch(self, entries):
        pass

    def _gen_notification_id(self, entry, option_type=0):
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
            LOG.info("[{}]: retrieving from {} block".format(self.__class__.__name__, self.from_block))

            self.filter_params["fromBlock"] = self.from_block
            event_filter = self.contract.eventFilter(self.filter_name, self.filter_params)
            entries = event_filter.get_all_entries()
            web3.eth.uninstallFilter(event_filter.filter_id)
            if len(entries) == 0:
                return
            # DB登録
            self.watch(entries)
            self.from_block = max(map(lambda e: e["blockNumber"], entries)) + 1
            db_session.commit()
        finally:
            elapsed_time = time.time() - start_time
            LOG.info("[{}] finished in {} secs".format(self.__class__.__name__, elapsed_time))


'''
株式取引（相対）関連（IbetOTCExchange）
'''


# イベント：注文
class WatchShareNewOrder(Watcher):
    def __init__(self):
        super().__init__(share_exchange_contract, "NewOrder", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            # NOTE: OTCExchangeはShare以外のトークンでも利用される可能性があるため、
            #       token_templateがShareではない場合処理をスキップする
            if token_list.get_token(token_address)[1] != "IbetShare":
                continue

            token = token_factory.get_share(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetShare"
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
class WatchShareCancelOrder(Watcher):
    def __init__(self):
        super().__init__(share_exchange_contract, "CancelOrder", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            # NOTE: OTCExchangeはShare以外のトークンでも利用される可能性があるため、
            #       token_templateがShareではない場合処理をスキップする
            if token_list.get_token(token_address)[1] != "IbetShare":
                continue

            token = token_factory.get_share(token_address)
            
            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetShare"
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


# イベント：約定（買）
class WatchShareBuyAgreement(Watcher):
    def __init__(self):
        super().__init__(share_exchange_contract, "Agree", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            # NOTE: OTCExchangeはShare以外のトークンでも利用される可能性があるため、
            #       token_templateがShareではない場合処理をスキップする
            if token_list.get_token(token_address)[1] != "IbetShare":
                continue

            token = token_factory.get_share(token_address)
            
            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetShare"
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
class WatchShareSellAgreement(Watcher):
    def __init__(self):
        super().__init__(share_exchange_contract, "Agree", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            # NOTE: OTCExchangeはShare以外のトークンでも利用される可能性があるため、
            #       token_templateがShareではない場合処理をスキップする
            if token_list.get_token(token_address)[1] != "IbetShare":
                continue

            token = token_factory.get_share(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetShare"
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
class WatchShareBuySettlementOK(Watcher):
    def __init__(self):
        super().__init__(share_exchange_contract, "SettlementOK", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            # NOTE: OTCExchangeはShare以外のトークンでも利用される可能性があるため、
            #       token_templateがShareではない場合処理をスキップする
            if token_list.get_token(token_address)[1] != "IbetShare":
                continue

            token = token_factory.get_share(token_address)
            
            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetShare"
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
class WatchShareSellSettlementOK(Watcher):
    def __init__(self):
        super().__init__(share_exchange_contract, "SettlementOK", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            # NOTE: OTCExchangeはShare以外のトークンでも利用される可能性があるため、
            #       token_templateがShareではない場合処理をスキップする
            if token_list.get_token(token_address)[1] != "IbetShare":
                continue

            token = token_factory.get_share(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetShare"
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
class WatchShareBuySettlementNG(Watcher):
    def __init__(self):
        super().__init__(share_exchange_contract, "SettlementNG", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            # NOTE: OTCExchangeはShare以外のトークンでも利用される可能性があるため、
            #       token_templateがShareではない場合処理をスキップする
            if token_list.get_token(token_address)[1] != "IbetShare":
                continue

            token = token_factory.get_share(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetShare"
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
class WatchShareSellSettlementNG(Watcher):
    def __init__(self):
        super().__init__(share_exchange_contract, "SettlementNG", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            token_address = entry["args"]["tokenAddress"]

            if not token_list.is_registered(token_address):
                continue

            # NOTE: OTCExchangeはShare以外のトークンでも利用される可能性があるため、
            #       token_templateがShareではない場合処理をスキップする
            if token_list.get_token(token_address)[1] != "IbetShare":
                continue
            
            token = token_factory.get_share(token_address)

            company = company_list.find(token.owner_address)

            metadata = {
                "company_name": company.corporate_name,
                "token_name": token.name,
                "exchange_address": IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS,
                "token_type": "IbetShare"
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
        WatchShareNewOrder(),
        WatchShareCancelOrder(),
        WatchShareBuyAgreement(),
        WatchShareSellAgreement(),
        WatchShareBuySettlementOK(),
        WatchShareSellSettlementOK(),
        WatchShareBuySettlementNG(),
        WatchShareSellSettlementNG(),
    ]

    e = ThreadPoolExecutor(max_workers=WORKER_COUNT)
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
