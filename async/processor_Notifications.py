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
import json
from async.lib.token import TokenFactory
from async.lib.company_list import CompanyList
from async.lib.misc import wait_all_futures
from concurrent.futures import ThreadPoolExecutor
import time


#logging.basicConfig(level=logging.DEBUG)

# 設定の取得
WEB3_HTTP_PROVIDER = os.environ.get("WEB3_HTTP_PROVIDER") or "http://localhost:8545"
URI = os.environ.get("DATABASE_URL") or "postgresql://ethuser:ethpass@localhost:5432/ethcache"
IBET_EXCHANGE_CONTRACT_ADDRESS = os.environ.get("IBET_SB_EXCHANGE_CONTRACT_ADDRESS")
IBET_EXCHANGE_CONTRACT_ABI = json.loads(config.IBET_EXCHANGE_CONTRACT_ABI)
WHITE_LIST_CONTRACT_ADDRESS = os.environ.get("WHITE_LIST_CONTRACT_ADDRESS")
WHITE_LIST_CONTRACT_ABI = json.loads(config.WHITE_LIST_CONTRACT_ABI)
TOKEN_LIST_CONTRACT_ADDRESS = os.environ.get("TOKEN_LIST_CONTRACT_ADDRESS")
TOKEN_LIST_CONTRACT_ABI = json.loads(config.TOKEN_LIST_CONTRACT_ABI)

# 初期化
web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)
engine = create_engine(URI, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)
tokenFactory = TokenFactory(web3)

# コントラクトの生成
exchangeContract = web3.eth.contract(
    address = to_checksum_address(IBET_EXCHANGE_CONTRACT_ADDRESS),
    abi = IBET_EXCHANGE_CONTRACT_ABI,
)
whiteListContract = web3.eth.contract(
    address = to_checksum_address(WHITE_LIST_CONTRACT_ADDRESS),
    abi = WHITE_LIST_CONTRACT_ABI,
)
listContract = web3.eth.contract(
    address = to_checksum_address(TOKEN_LIST_CONTRACT_ADDRESS),
    abi = TOKEN_LIST_CONTRACT_ABI,
)

class Watcher:
    def __init__(self, contract, filter_name, filter_params):
        self.contract = contract
        self.filter_name = filter_name
        self.filter_params = filter_params
        self.from_block = 0

    def gen_notification_id(self, entry):
        return "0x{:012x}{:06x}{:06x}".format(
            entry["blockNumber"],
            entry["transactionIndex"],
            entry["logIndex"],
        )

    def loop(self):
        print("[{}]: retrieving from {} block".format(self.__class__.__name__, self.from_block))
        self.filter_params["fromBlock"] = self.from_block
        event_filter = self.contract.eventFilter(self.filter_name, self.filter_params)
        entries = event_filter.get_all_entries()
        if len(entries) == 0:
            return
        
        self.watch(entries)
        self.from_block = max(map(lambda e: e["blockNumber"], entries)) + 1
        db_session.commit()

class WatchWhiteListRegister(Watcher):
    def __init__(self):
        super().__init__(whiteListContract, "Register", {})
    
    def watch(self, entries):
        for entry in entries:
            print(entry)
            notification = Notification()
            notification.notification_id = self.gen_notification_id(entry)
            notification.notification_type = "Register"
            notification.priority = 0
            notification.address = entry["args"]["account_address"]
            notification.is_read = False
            notification.is_flagged = False
            notification.is_deleted = False
            notification.deleted_at = None
            notification.args = dict(entry["args"])
            notification.metainfo = {}
            print(notification)
            db_session.merge(notification)
        

def main():
    watchers = [WatchWhiteListRegister()]
    
    e = ThreadPoolExecutor(max_workers = 2)
    while True:
        fs = []
        for watcher in watchers:
            fs.append(e.submit(watcher.loop))
        wait_all_futures(fs)
        time.sleep(3)
    
    print("OK")

if __name__ == "__main__":
    main()
