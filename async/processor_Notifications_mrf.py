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
from app import log
from app import config
from app.model import Notification, Push
from app.contracts import Contract
import json
from async.lib.token import TokenFactory
from async.lib.company_list import CompanyListFactory
from async.lib.misc import wait_all_futures
from concurrent.futures import ThreadPoolExecutor
import time
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=+9), "JST")
from eth_utils import to_checksum_address

# logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)
LOG = log.get_logger()

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
token_factory = TokenFactory(web3)
company_list_factory = CompanyListFactory(config.COMPANY_LIST_URL)

# 起動時のblockNumberを取得
NOW_BLOCKNUMBER = web3.eth.blockNumber

# コントラクトの生成
mrf_token_address = to_checksum_address(config.IBET_MRF_TOKEN_ADDRESS)
mrf_token = Contract.get_contract('IbetMRF', mrf_token_address)


########################################
# PUSH
########################################
def push_publish(notification_id, address, priority, blocknumber, subject, message):
    # 「対象の優先度」が送信設定（PUSH_PRIORITY）以上 かつ
    # 「対象のblockNumber」が起動時のblockNumber以上の場合は送信
    if priority >= config.PUSH_PRIORITY and blocknumber >= NOW_BLOCKNUMBER:
        # pushの情報取得
        query = db_session.query(Push). \
            filter(Push.account_address == address)
        devices = query.all()
        for device_data in devices:
            # 通知json作成。iosとandroidでjsonの構造を変更。
            if device_data.platform == 'ios':
                message_dict = {
                    "aps": {
                        "alert": message
                    },
                    "data": {
                        "notification_id": notification_id
                    }
                }
                send_data = json.dumps({"APNS": json.dumps(message_dict)})
            elif device_data.platform == 'android':
                message_dict = {
                    "data": {
                        "message": message, "notification_id": notification_id
                    }
                }
                send_data = json.dumps({"GCM": json.dumps(message_dict)})
            try:
                client = boto3.client('sns', 'ap-northeast-1')
                response = client.publish(
                    TargetArn=device_data.device_endpoint_arn,
                    Message=send_data,
                    MessageStructure='json'
                )
            except ClientError:
                LOG.error('device_endpoint_arn does not found.')


########################################
# Watcher
########################################
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


########################################
# Event
########################################
class WatchMRFTransfer(Watcher):
    def __init__(self):
        super().__init__(mrf_token, "Transfer", {})

    def watch(self, entries):
        company_list = company_list_factory.get()

        for entry in entries:
            if entry["args"]["from"] == to_checksum_address(config.IBET_JDR_SWAP_CONTRACT_ADDRESS):
                continue
            else:
                token = token_factory.get_mrf(mrf_token_address)
                company = company_list.find(token.owner_address)

                metadata = {
                    "company_name": company.corporate_name,
                    "token_name": token.name,
                    "from": entry["args"]["from"],
                    "value": entry["args"]["value"],
                }

                # 通知DB登録
                notification = Notification()
                notification.notification_id = self._gen_notification_id(entry)
                notification.notification_type = "MRFTransfer"
                notification.priority = 0
                notification.address = entry["args"]["to"]
                notification.block_timestamp = self._gen_block_timestamp(entry)
                notification.args = dict(entry["args"])
                notification.metainfo = metadata
                db_session.merge(notification)

    def push(self, entries):
        for entry in entries:
            push_publish(
                self._gen_notification_id(entry),
                entry["args"]["to"],
                0,
                entry["blockNumber"],
                'ポイントを受領しました。',
                'ポイントを受領しました。保有一覧からご確認ください。',
            )


def main():
    watchers = [
        WatchMRFTransfer(),
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
