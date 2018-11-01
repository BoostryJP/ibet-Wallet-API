# -*- coding: utf-8 -*-

import os
import sys
import boto3
from botocore.exceptions import ClientError

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

import logging
from web3 import Web3
from web3.middleware import geth_poa_middleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from eth_utils import to_checksum_address
from app import log
from app import config
from app.model import Notification, Push
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
LOG = log.get_logger()

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

# 起動時のblockNumberを取得
NOW_BLOCKNUMBER = web3.eth.blockNumber

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

def push_publish(notification_id, address, priority, blocknumber,subject, message):
    # 「対象の優先度」が送信設定（PUSH_PRIORITY）以上 かつ
    # 「対象のblockNumer」が起動時のblockNumer以上の場合は送信
    if priority >= config.PUSH_PRIORITY and blocknumber >= NOW_BLOCKNUMBER:
        # 通知tableの情報取得
        query_notification = db_session.query(Notification). \
            filter(Notification.notification_id == notification_id)
        notification = query_notification.first()
        # 通知json作成
        message_dict = {
            "aps":{ 
                "alert":message
            }
        }
        message_dict['notification_id'] = notification.notification_id
        print(message_dict)
        if config.APP_ENV == 'live':
            send_data = json.dumps({"APNS": json.dumps(message_dict}))
        else:
            send_data = json.dumps({"APNS_SANDBOX": json.dumps(message_dict}))
        print(send_data)
        # pushの情報取得
        query = db_session.query(Push). \
            filter(Push.account_address == address)
        devices = query.all()
        for device_data in devices:
            try:
                client = boto3.client('sns', 'ap-northeast-1')
                response = client.publish(
                    TargetArn=device_data.device_endpoint_arn,
                    Message=send_data,
                    MessageStructure='json'
                )
            except ClientError:
                LOG.error('device_endpoint_arn does not found.')


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
            # DB登録
            self.watch(entries)
            self.from_block = max(map(lambda e: e["blockNumber"], entries)) + 1
            db_session.commit()
            # Push通知
            self.push(entries)
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

    def push(self, entries):
        for entry in entries:
            push_publish(self._gen_notification_id(entry), entry["args"]["account_address"], 2, entry["blockNumber"],
                '決済用口座情報登録完了', 
                '決済用口座情報登録が完了しました。指定口座まで振り込みを実施してください。',
                )

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

    def push(self, entries):
        for entry in entries:
            push_publish(self._gen_notification_id(entry), entry["args"]["account_address"], 0, entry["blockNumber"],
                '決済用口座情報承認完了', 
                '決済用の口座が承認されました。取引を始めることができます。',
                )

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

    def push(self, entries):
        for entry in entries:
            push_publish(self._gen_notification_id(entry), entry["args"]["account_address"], 0, entry["blockNumber"],
                '決済用口座の確認', 
                '決済用の口座の情報が確認できませんでした。',
                )

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

    def push(self, entries):
        for entry in entries:
            push_publish(self._gen_notification_id(entry), entry["args"]["account_address"], 0, entry["blockNumber"],
                '決済用口座情報再登録', 
                '決済用口座情報が変更されました。指定口座まで振り込みを実施してください。',
                )

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

    def push(self, entries):
        for entry in entries:
            push_publish(self._gen_notification_id(entry), entry["args"]["account_address"], 2, entry["blockNumber"],
                '決済用口座の認証取消', 
                '決済用の口座の認証が取り消されました。',
                )


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

    def push(self, entries):
        for entry in entries:
            push_publish(self._gen_notification_id(entry), entry["args"]["accountAddress"], 0, entry["blockNumber"],
                '新規注文完了', 
                '新規注文が完了しました。',
                )


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

    def push(self, entries):
        for entry in entries:
            push_publish(self._gen_notification_id(entry), entry["args"]["accountAddress"], 0, entry["blockNumber"],
                '注文キャンセル完了', 
                '注文のキャンセルが完了しました。',
                )


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

    def push(self, entries):
        for entry in entries:
            push_publish(self._gen_notification_id(entry, 1), entry["args"]["buyAddress"], 1, entry["blockNumber"],
                '約定完了', 
                '買い注文が約定しました。指定口座へ振り込みを実施してください。',
                )

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

    def push(self, entries):
        for entry in entries:
            push_publish(self._gen_notification_id(entry, 2), entry["args"]["sellAddress"], 2, entry["blockNumber"],
                '約定完了', 
                '売り注文が約定しました。代金が振り込まれるまでしばらくお待ち下さい。',
                )

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

    def push(self, entries):
        for entry in entries:
            push_publish(self._gen_notification_id(entry, 1), entry["args"]["buyAddress"], 1, entry["blockNumber"],
                '決済完了', 
                '注文の決済が完了しました。',
                )

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

    def push(self, entries):
        for entry in entries:
            push_publish(self._gen_notification_id(entry, 2), entry["args"]["sellAddress"], 1, entry["blockNumber"],
                '決済完了', 
                '注文の決済が完了しました。',
                )

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

    def push(self, entries):
        for entry in entries:
            push_publish(self._gen_notification_id(entry, 1), entry["args"]["buyAddress"], 2, entry["blockNumber"],
                '決済失敗', 
                '注文の決済が失敗しました。再度振り込み内容をご確認ください。',
                )

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

    def push(self, entries):
        for entry in entries:
            push_publish(self._gen_notification_id(entry, 2), entry["args"]["sellAddress"], 2, entry["blockNumber"],
                '決済失敗', 
                '注文の決済が失敗しました。再度振り込み内容をご確認ください。',
                )

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
                "value": entry["args"]["value"],
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

    def push(self, entries):
        for entry in entries:
            push_publish(self._gen_notification_id(entry), entry["args"]["to"], 0, entry["blockNumber"],
                'クーポン発行完了', 
                'クーポンが発行されました。保有トークンの一覧からご確認ください。',
                )

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
