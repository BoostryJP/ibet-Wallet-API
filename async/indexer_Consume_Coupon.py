"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed onan "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

import os
import sys
import time

path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(path)

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from web3 import Web3
from eth_utils import to_checksum_address
from web3.middleware import geth_poa_middleware

from app import log
from app import config
from app.model import Listing, ConsumeCoupon
from app.contracts import Contract

from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=+9), "JST")

LOG = log.get_logger()
log_fmt = 'INDEXER-Consume-Coupon [%(asctime)s] [%(process)d] [%(levelname)s] %(message)s'
logging.basicConfig(format=log_fmt)

# 設定の取得
WEB3_HTTP_PROVIDER = config.WEB3_HTTP_PROVIDER
URI = config.DATABASE_URL

# 初期化
web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)
engine = create_engine(URI, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)


class Sinks:
    def __init__(self):
        self.sinks = []

    def register(self, sink):
        self.sinks.append(sink)

    def on_consume(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_consume(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_consume(self, transaction_hash, token_address, account_address, amount, block_timestamp):
        consume_coupon = self.__get_record(transaction_hash, token_address, account_address)
        if consume_coupon is None:
            LOG.info(f"Consume: transaction_hash={transaction_hash}")
            consume_coupon = ConsumeCoupon()
            consume_coupon.transaction_hash = transaction_hash
            consume_coupon.token_address = token_address
            consume_coupon.account_address = account_address
            consume_coupon.amount = amount
            consume_coupon.block_timestamp = block_timestamp
            self.db.merge(consume_coupon)

    def flush(self):
        self.db.commit()

    def __get_record(self, transaction_hash, token_address, account_address):
        return self.db.query(ConsumeCoupon). \
            filter(ConsumeCoupon.transaction_hash == transaction_hash). \
            filter(ConsumeCoupon.token_address == token_address). \
            filter(ConsumeCoupon.account_address == account_address). \
            first()


class Processor:
    def __init__(self, sink, db):
        self.sink = sink
        self.latest_block = web3.eth.blockNumber
        self.db = db
        self.token_list = []

    def get_token_list(self):
        self.token_list = []
        ListContract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)
        listed_tokens = self.db.query(Listing).all()
        for listed_token in listed_tokens:
            token_info = ListContract.functions.getTokenByAddress(listed_token.token_address).call()
            if token_info[1] == "IbetCoupon":
                coupon_token_contract = Contract.get_contract('IbetCoupon', listed_token.token_address)
                self.token_list.append(coupon_token_contract)

    def initial_sync(self):
        self.get_token_list()
        self.__sync_all(0, self.latest_block)

    def sync_new_logs(self):
        self.get_token_list()
        blockTo = web3.eth.blockNumber
        if blockTo == self.latest_block:
            return
        self.__sync_all(self.latest_block + 1, blockTo)
        self.latest_block = blockTo

    def __sync_all(self, block_from, block_to):
        LOG.debug("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_consume(block_from, block_to)
        self.sink.flush()

    def __sync_consume(self, block_from, block_to):
        for token in self.token_list:
            try:
                event_filter = token.eventFilter(
                    'Consume', {
                        'fromBlock': block_from,
                        'toBlock': block_to,
                    }
                )
                for event in event_filter.get_all_entries():
                    args = event['args']
                    transaction_hash = event['transactionHash'].hex()
                    block_timestamp = datetime.fromtimestamp(web3.eth.getBlock(event['blockNumber'])['timestamp'], JST)
                    amount = args.get("value", 0)
                    consumer = args.get("consumer", config.ZERO_ADDRESS)
                    if amount > sys.maxsize:
                        pass
                    else:
                        if consumer != config.ZERO_ADDRESS:
                            self.sink.on_consume(
                                transaction_hash=transaction_hash,
                                token_address=to_checksum_address(token.address),
                                account_address=consumer,
                                amount=amount,
                                block_timestamp=block_timestamp
                            )
                web3.eth.uninstallFilter(event_filter.filter_id)
            except Exception as e:
                LOG.exception(e)


_sink = Sinks()
_sink.register(DBSink(db_session))
processor = Processor(_sink, db_session)

processor.initial_sync()
while True:
    processor.sync_new_logs()
    time.sleep(10)
