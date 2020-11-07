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
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(path)

from app import log
from app import config
from app.model import Listing, Position
from app.contracts import Contract

LOG = log.get_logger()
log_fmt = 'INDEXER-POSITION-COUPON [%(asctime)s] [%(process)d] [%(levelname)s] %(message)s'
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

    def register(self, _sink):
        self.sinks.append(_sink)

    def on_position(self, *args, **kwargs):
        for _sink in self.sinks:
            _sink.on_position(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for _sink in self.sinks:
            _sink.flush(*args, **kwargs)


class ConsoleSink:
    @staticmethod
    def on_position(token_address, account_address, balance):
        LOG.info("Position updated (Coupon): token_address={}, account_address={}, balance={}".format(
            token_address, account_address, balance
        ))

    def flush(self):
        return


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_position(self, token_address: str, account_address: str, balance: int):
        """残高更新

        :param token_address: token address
        :param account_address: account address
        :param balance: 更新後の残高
        :return: None
        """
        position = self.db.query(Position). \
            filter(Position.token_address == token_address). \
            filter(Position.account_address == account_address). \
            first()
        if position is None:
            position = Position()
            position.token_address = token_address
            position.account_address = account_address
            position.balance = balance
        else:
            position.balance = balance
        self.db.merge(position)

    def flush(self):
        self.db.commit()


class Processor:
    def __init__(self, _web3, _sink, _db):
        self.web3 = _web3
        self.sink = _sink
        self.latest_block = _web3.eth.blockNumber
        self.db = _db
        self.token_list = []

    def get_token_list(self):
        self.token_list = []
        ListContract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)
        listed_tokens = self.db.query(Listing).all()
        for listed_token in listed_tokens:
            token_info = ListContract.functions.getTokenByAddress(listed_token.token_address).call()
            if token_info[1] == "IbetCoupon":
                token_contract = Contract.get_contract('IbetCoupon', listed_token.token_address)
                self.token_list.append(token_contract)

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

    def __sync_all(self, block_from: int, block_to: int):
        LOG.debug("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_transfer(block_from, block_to)
        self.sink.flush()

    def __sync_transfer(self, block_from: int, block_to: int):
        """Transferイベントの同期

        :param block_from: From ブロック
        :param block_to: To ブロック
        :return: None
        """
        for token in self.token_list:
            try:
                event_filter = token.eventFilter(
                    'Transfer', {
                        'fromBlock': block_from,
                        'toBlock': block_to,
                    }
                )
                for event in event_filter.get_all_entries():
                    args = event['args']
                    # from address
                    from_account = args.get("from", config.ZERO_ADDRESS)
                    from_account_balance = token.functions.balanceOf(from_account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=from_account,
                        balance=from_account_balance
                    )
                    # to address
                    to_account = args.get("to", config.ZERO_ADDRESS)
                    to_account_balance = token.functions.balanceOf(to_account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=to_account,
                        balance=to_account_balance,
                    )
                self.web3.eth.uninstallFilter(event_filter.filter_id)
            except Exception as e:
                LOG.exception(e)
                pass


sink = Sinks()
sink.register(ConsoleSink())
sink.register(DBSink(db_session))
processor = Processor(web3, sink, db_session)

processor.initial_sync()
while True:
    processor.sync_new_logs()
    time.sleep(10)
