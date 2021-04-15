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
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session
)
from web3 import Web3
from web3.middleware import (
    geth_poa_middleware,
    local_filter_middleware
)
from eth_utils import to_checksum_address

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app.config import (
    WEB3_HTTP_PROVIDER,
    DATABASE_URL,
    TOKEN_LIST_CONTRACT_ADDRESS,
    ZERO_ADDRESS
)
from app.model import (
    Listing,
    IDXPosition
)
from app.contracts import Contract
import log

process_name = "INDEXER-POSITION-SHARE"
LOG = log.get_logger(process_name=process_name)

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)
web3.middleware_onion.add(local_filter_middleware)

engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)


class Sinks:
    def __init__(self):
        self.sinks = []

    def register(self, _sink):
        self.sinks.append(_sink)

    def on_position(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_position(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_position(self, token_address: str, account_address: str, balance: int):
        """Update Position data in DB

        :param token_address: token address
        :param account_address: account address
        :param balance: updated balance
        :return: None
        """
        position = self.db.query(IDXPosition). \
            filter(IDXPosition.token_address == token_address). \
            filter(IDXPosition.account_address == account_address). \
            first()
        if position is None:
            LOG.info(f"Position created (Share): token_address={token_address}, account_address={account_address}")
            position = IDXPosition()
            position.token_address = token_address
            position.account_address = account_address
            position.balance = balance
        else:
            position.balance = balance
        self.db.merge(position)

    def flush(self):
        self.db.commit()


class Processor:
    def __init__(self, sink, db):
        self.sink = sink
        self.latest_block = web3.eth.blockNumber
        self.db = db
        self.token_list = []

    def get_token_list(self):
        self.token_list = []
        ListContract = Contract.get_contract("TokenList", TOKEN_LIST_CONTRACT_ADDRESS)
        listed_tokens = self.db.query(Listing).all()
        for listed_token in listed_tokens:
            token_info = ListContract.functions.getTokenByAddress(listed_token.token_address).call()
            if token_info[1] == "IbetShare":
                token_contract = Contract.get_contract("IbetShare", listed_token.token_address)
                self.token_list.append(token_contract)

    def initial_sync(self):
        self.get_token_list()
        # 1,000,000ブロックずつ同期処理を行う
        _to_block = 999999
        _from_block = 0
        if self.latest_block > 999999:
            while _to_block < self.latest_block:
                self.__sync_all(_from_block, _to_block)
                _to_block += 1000000
                _from_block += 1000000
            self.__init_sync_all(_from_block, self.latest_block)
        else:
            self.__init_sync_all(_from_block, self.latest_block)
        self.sink.flush()
        LOG.info(f"<{process_name}> Initial sync has been completed")

    def sync_new_logs(self):
        self.get_token_list()
        blockTo = web3.eth.blockNumber
        if blockTo == self.latest_block:
            return
        self.__sync_all(self.latest_block + 1, blockTo)
        self.latest_block = blockTo

    def __init_sync_all(self, block_from: int, block_to: int):
        LOG.debug("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_transfer(block_from, block_to)
        self.__sync_lock(block_from, block_to)
        self.__sync_unlock(block_from, block_to)
        self.__sync_issue(block_from, block_to)
        self.__sync_redeem(block_from, block_to)

    def __sync_all(self, block_from: int, block_to: int):
        LOG.debug("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_transfer(block_from, block_to)
        self.__sync_lock(block_from, block_to)
        self.__sync_unlock(block_from, block_to)
        self.__sync_issue(block_from, block_to)
        self.__sync_redeem(block_from, block_to)
        self.sink.flush()

    def __sync_transfer(self, block_from: int, block_to: int):
        """Sync Transfer Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                _build_filter = token.events.Transfer.build_filter()
                _build_filter.fromBlock = block_from
                _build_filter.toBlock = block_to
                event_filter = _build_filter.deploy(web3)
                for event in event_filter.get_all_entries():
                    args = event["args"]
                    # from address
                    from_account = args.get("from", ZERO_ADDRESS)
                    from_account_balance = token.functions.balanceOf(from_account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=from_account,
                        balance=from_account_balance
                    )
                    # to address
                    to_account = args.get("to", ZERO_ADDRESS)
                    to_account_balance = token.functions.balanceOf(to_account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=to_account,
                        balance=to_account_balance,
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_lock(self, block_from: int, block_to: int):
        """Sync Lock Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                _build_filter = token.events.Lock.build_filter()
                _build_filter.fromBlock = block_from
                _build_filter.toBlock = block_to
                event_filter = _build_filter.deploy(web3)
                for event in event_filter.get_all_entries():
                    args = event["args"]
                    account = args.get("from", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_unlock(self, block_from: int, block_to: int):
        """Sync Unlock Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                _build_filter = token.events.Unlock.build_filter()
                _build_filter.fromBlock = block_from
                _build_filter.toBlock = block_to
                event_filter = _build_filter.deploy(web3)
                for event in event_filter.get_all_entries():
                    args = event["args"]
                    account = args.get("to", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_issue(self, block_from: int, block_to: int):
        """Sync Issue Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                _build_filter = token.events.Issue.build_filter()
                _build_filter.fromBlock = block_from
                _build_filter.toBlock = block_to
                event_filter = _build_filter.deploy(web3)
                for event in event_filter.get_all_entries():
                    args = event["args"]
                    account = args.get("target_address", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_redeem(self, block_from: int, block_to: int):
        """Sync Redeem Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                _build_filter = token.events.Redeem.build_filter()
                _build_filter.fromBlock = block_from
                _build_filter.toBlock = block_to
                event_filter = _build_filter.deploy(web3)
                for event in event_filter.get_all_entries():
                    args = event["args"]
                    account = args.get("target_address", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance
                    )
            except Exception as e:
                LOG.exception(e)


_sink = Sinks()
_sink.register(DBSink(db_session))
processor = Processor(_sink, db_session)
LOG.info("Service started successfully")

processor.initial_sync()
while True:
    processor.sync_new_logs()
    time.sleep(10)
