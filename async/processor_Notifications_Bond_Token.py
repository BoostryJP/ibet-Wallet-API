# -*- coding: utf-8 -*-
import json
import os
import sys
import logging
from concurrent.futures import ThreadPoolExecutor
import time
from datetime import datetime, timezone, timedelta

import boto3
from botocore.exceptions import ClientError
from web3 import Web3
from web3.middleware import geth_poa_middleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)
from app import log
from app import config
from app.model import Notification, NotifitationType, Push, Listing, PrivateListing
from app.contracts import Contract
from async.lib.company_list import CompanyListFactory
from async.lib.token_list import TokenList
from async.lib.misc import wait_all_futures

JST = timezone(timedelta(hours=+9), "JST")

LOG = log.get_logger()
log_fmt = 'PROCESSOR-Notifications_Bond_Token [%(asctime)s] [%(process)d] [%(levelname)s] %(message)s'
logging.basicConfig(format=log_fmt)

# 設定の取得
WEB3_HTTP_PROVIDER = config.WEB3_HTTP_PROVIDER
URI = config.DATABASE_URL
WORKER_COUNT = int(config.WORKER_COUNT)
SLEEP_INTERVAL = int(config.SLEEP_INTERVAL)

# 初期化
web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)
engine = create_engine(URI, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)
company_list_factory = CompanyListFactory(config.COMPANY_LIST_URL)

# 起動時のblockNumberを取得
NOW_BLOCKNUMBER = web3.eth.blockNumber

# コントラクトの生成
list_contract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)
token_list = TokenList(list_contract)


# PUSH通知送信
def push_publish(notification_id, account_address, priority, blocknumber, message, detail_link=True):
    # 「対象の優先度」が送信設定（PUSH_PRIORITY）以上 かつ
    # 「対象のblockNumber」が起動時のblockNumber以上の場合は送信
    if priority >= config.PUSH_PRIORITY and blocknumber >= NOW_BLOCKNUMBER:
        # 通知tableの情報取得
        query_notification = db_session.query(Notification).filter(Notification.notification_id == notification_id)
        notification = query_notification.first()

        # PUSH通知先デバイス情報の取得
        if account_address is None:
            query = db_session.query(Push)
        else:
            query = db_session.query(Push).filter(Push.account_address == account_address)
        devices = query.all()

        for device_data in devices:
            # 通知json作成。iosとandroidでjsonの構造を変更。
            send_data = ''
            if device_data.platform == 'ios':
                message_dict = {
                    "aps": {
                        "alert": message
                    },
                    "data": {
                        "notification_id": notification.notification_id,
                        "detail_link": detail_link
                    }
                }
                send_data = json.dumps({"APNS": json.dumps(message_dict)})
            elif device_data.platform == 'android':
                message_dict = {
                    "data": {
                        "message": message, "notification_id": notification.notification_id, "detail_link": detail_link
                    }
                }
                send_data = json.dumps({"GCM": json.dumps(message_dict)})
            try:
                client = boto3.client('sns', 'ap-northeast-1')
                client.publish(
                    TargetArn=device_data.device_endpoint_arn,
                    Message=send_data,
                    MessageStructure='json'
                )
            except ClientError:
                LOG.warning('device_endpoint_arn does not found.')


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

    def _get_bond_token_public_list(self):
        res = []
        registered_token_list = db_session.query(Listing).all()
        for registered_token in registered_token_list:
            if not token_list.is_registered(registered_token.token_address):
                continue
            elif token_list.get_token(registered_token.token_address)[1] == 'IbetStraightBond':
                res.append(registered_token)
        return res

    def _get_bond_token_all_list(self):
        res = []
        registered_token_list = db_session.query(Listing).union_all(db_session.query(PrivateListing)).all()
        for registered_token in registered_token_list:
            if not token_list.is_registered(registered_token.token_address):
                continue
            elif token_list.get_token(registered_token.token_address)[1] == 'IbetStraightBond':
                res.append(registered_token)
        return res

    def loop(self):
        start_time = time.time()
        try:
            print("[{}]: retrieving from {} block".format(self.__class__.__name__, self.from_block))
            self.filter_params["fromBlock"] = self.from_block

            # 登録済みの債券リストを取得
            if self.__class__.__name__ == "WatchTransfer":
                bond_token_list = self._get_bond_token_all_list()
            else:
                bond_token_list = self._get_bond_token_public_list()

            # イベント処理
            for bond_token in bond_token_list:
                try:
                    # イベント取得
                    bond_contract = Contract.get_contract('IbetStraightBond', bond_token.token_address)
                    event_filter = bond_contract.eventFilter(self.filter_name, self.filter_params)
                    entries = event_filter.get_all_entries()
                    web3.eth.uninstallFilter(event_filter.filter_id)
                except Exception as e:
                    LOG.warning(e)
                    continue
                if len(entries) == 0:  # イベントが0件の場合は何も処理しない
                    continue
                else:
                    # DB登録
                    self.db_merge(bond_contract, entries)
                    self.from_block = max(map(lambda e: e["blockNumber"], entries)) + 1
                    db_session.commit()
                    # Push通知
                    self.push(bond_contract, entries)
        finally:
            elapsed_time = time.time() - start_time
            print("[{}] finished in {} secs".format(self.__class__.__name__, elapsed_time))


# イベント：募集申込開始
class WatchStartInitialOffering(Watcher):
    def __init__(self):
        super().__init__("ChangeInitialOfferingStatus", {'filter': {'status': True}} )

    def db_merge(self, token_contract, entries):
        company_list = company_list_factory.get()
        for entry in entries:
            token_owner_address = token_contract.functions.owner().call()
            token_name = token_contract.functions.name().call()
            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_name": token_name,
                "exchange_address": "",
                "token_type": "IbetStraightBond"
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotifitationType.START_INITIAL_OFFERING
            notification.priority = 0
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)

    def push(self, token_contract, entries):
        for entry in entries:
            token_name = token_contract.functions.name().call()
            push_publish(
                self._gen_notification_id(entry),
                None,
                0,
                entry["blockNumber"],
                token_name + 'の募集申込が開始されました。',
                detail_link=False
            )


# イベント：募集申込終了
class WatchStopInitialOffering(Watcher):
    def __init__(self):
        super().__init__("ChangeInitialOfferingStatus", {'filter': {'status': False}})

    def db_merge(self, token_contract, entries):
        company_list = company_list_factory.get()
        for entry in entries:
            token_owner_address = token_contract.functions.owner().call()
            token_name = token_contract.functions.name().call()
            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_name": token_name,
                "exchange_address": "",
                "token_type": "IbetStraightBond"
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotifitationType.STOP_INITIAL_OFFERING
            notification.priority = 0
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)

    def push(self, token_contract, entries):
        for entry in entries:
            token_name = token_contract.functions.name().call()
            push_publish(
                self._gen_notification_id(entry),
                None,
                0,
                entry["blockNumber"],
                token_name + 'の募集申込が終了しました。',
                detail_link=False
            )


# イベント：償還
class WatchRedeem(Watcher):
    def __init__(self):
        super().__init__("Redeem", {} )

    def db_merge(self, token_contract, entries):
        company_list = company_list_factory.get()
        for entry in entries:
            token_owner_address = token_contract.functions.owner().call()
            token_name = token_contract.functions.name().call()
            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_name": token_name,
                "exchange_address": "",
                "token_type": "IbetStraightBond"
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotifitationType.REDEEM
            notification.priority = 0
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)

    def push(self, token_contract, entries):
        for entry in entries:
            token_name = token_contract.functions.name().call()
            push_publish(
                self._gen_notification_id(entry),
                None,
                0,
                entry["blockNumber"],
                token_name + 'が償還されました。',
                detail_link=False
            )


# イベント：募集申込
class WatchApplyForOffering(Watcher):
    def __init__(self):
        super().__init__("ApplyFor", {})

    def db_merge(self, token_contract, entries):
        company_list = company_list_factory.get()
        for entry in entries:
            token_owner_address = token_contract.functions.owner().call()
            token_name = token_contract.functions.name().call()
            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_name": token_name,
                "exchange_address": "",
                "token_type": "IbetStraightBond"
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotifitationType.APPLY_FOR_OFFERING
            notification.priority = 0
            notification.address = entry["args"]["accountAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)

    def push(self, token_contract, entries):
        for entry in entries:
            token_name = token_contract.functions.name().call()
            push_publish(
                self._gen_notification_id(entry),
                entry["args"]["accountAddress"],
                0,
                entry["blockNumber"],
                token_name + 'の募集申込が完了しました。',
            )

# イベント：募集割当確定
class WatchAllot(Watcher):
    def __init__(self):
        super().__init__("Allot", {})

    def db_merge(self, token_contract, entries):
        company_list = company_list_factory.get()
        for entry in entries:
            token_owner_address = token_contract.functions.owner().call()
            token_name = token_contract.functions.name().call()
            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_name": token_name,
                "exchange_address": "",
                "token_type": "IbetStraightBond"
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotifitationType.ALLOT
            notification.priority = 1
            notification.address = entry["args"]["accountAddress"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)

    def push(self, token_contract, entries):
        for entry in entries:
            token_name = token_contract.functions.name().call()
            push_publish(
                self._gen_notification_id(entry),
                entry["args"]["accountAddress"],
                0,
                entry["blockNumber"],
                token_name + 'の募集割当が確定しました。',
            )


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
                "token_name": token_name,
                "exchange_address": "",
                "token_type": "IbetStraightBond"
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = NotifitationType.TRANSFER
            notification.priority = 0
            notification.address = entry["args"]["to"]
            notification.block_timestamp = self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            db_session.merge(notification)

    def push(self, token_contract, entries):
        for entry in entries:
            # Exchangeアドレスが移転元の場合、処理をSKIPする
            tradable_exchange = token_contract.functions.tradableExchange().call()
            if entry["args"]["from"] == tradable_exchange:
                continue
            token_name = token_contract.functions.name().call()
            push_publish(
                self._gen_notification_id(entry),
                entry["args"]["to"],
                0,
                entry["blockNumber"],
                token_name + 'を受領しました。',
            )


# メイン処理
def main():
    watchers = [
        WatchStartInitialOffering(),
        WatchStopInitialOffering(),
        WatchRedeem(),
        WatchApplyForOffering(),
        WatchTransfer(),
        WatchAllot(),
    ]

    e = ThreadPoolExecutor(max_workers=WORKER_COUNT)
    while True:
        start_time = time.time()

        fs = []
        for watcher in watchers:
            fs.append(e.submit(watcher.loop))
        wait_all_futures(fs)

        elapsed_time = time.time() - start_time
        print("[LOOP] finished in {} secs".format(elapsed_time))

        time.sleep(max(SLEEP_INTERVAL - elapsed_time, 0))


if __name__ == "__main__":
    main()
