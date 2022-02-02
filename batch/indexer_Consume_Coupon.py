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
from datetime import (
    datetime, 
    timezone, 
    timedelta
)

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker, 
    scoped_session
)
from eth_utils import to_checksum_address

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app.config import (
    DATABASE_URL,
    TOKEN_LIST_CONTRACT_ADDRESS,
    ZERO_ADDRESS
)
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.db import (
    Listing,
    IDXConsumeCoupon
)
from app.utils.web3_utils import Web3Wrapper
import log

JST = timezone(timedelta(hours=+9), "JST")

process_name = "INDEXER-CONSUME-COUPON"
LOG = log.get_logger(process_name=process_name)

web3 = Web3Wrapper()

engine = create_engine(DATABASE_URL, echo=False)
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
            LOG.debug(f"Consume: transaction_hash={transaction_hash}")
            consume_coupon = IDXConsumeCoupon()
            consume_coupon.transaction_hash = transaction_hash
            consume_coupon.token_address = token_address
            consume_coupon.account_address = account_address
            consume_coupon.amount = amount
            consume_coupon.block_timestamp = block_timestamp
            self.db.merge(consume_coupon)

    def flush(self):
        self.db.commit()

    def __get_record(self, transaction_hash, token_address, account_address):
        return self.db.query(IDXConsumeCoupon). \
            filter(IDXConsumeCoupon.transaction_hash == transaction_hash). \
            filter(IDXConsumeCoupon.token_address == token_address). \
            filter(IDXConsumeCoupon.account_address == account_address). \
            first()


class Processor:
    def __init__(self, sink, db):
        self.sink = sink
        self.latest_block = web3.eth.blockNumber
        self.db = db
        self.token_list = []

    def get_token_list(self):
        self.token_list = []
        list_contract = Contract.get_contract("TokenList", TOKEN_LIST_CONTRACT_ADDRESS)
        listed_tokens = self.db.query(Listing).all()
        for listed_token in listed_tokens:
            token_info = Contract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(listed_token.token_address,),
                default_returns=(ZERO_ADDRESS, "", ZERO_ADDRESS)
            )
            if token_info[1] == "IbetCoupon":
                coupon_token_contract = Contract.get_contract("IbetCoupon", listed_token.token_address)
                self.token_list.append(coupon_token_contract)

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
            self.__sync_all(_from_block, self.latest_block)
        else:
            self.__sync_all(_from_block, self.latest_block)
        LOG.info(f"<{process_name}> Initial sync has been completed")

    def sync_new_logs(self):
        self.get_token_list()
        blockTo = web3.eth.blockNumber
        if blockTo == self.latest_block:
            return
        self.__sync_all(self.latest_block + 1, blockTo)
        self.latest_block = blockTo

    def __sync_all(self, block_from, block_to):
        LOG.info("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_consume(block_from, block_to)
        self.sink.flush()

    def __sync_consume(self, block_from, block_to):
        for token in self.token_list:
            try:
                events = token.events.Consume.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    transaction_hash = event["transactionHash"].hex()
                    block_timestamp = datetime.fromtimestamp(web3.eth.getBlock(event["blockNumber"])["timestamp"], JST)
                    amount = args.get("value", 0)
                    consumer = args.get("consumer", ZERO_ADDRESS)
                    if amount > sys.maxsize:
                        pass
                    else:
                        if consumer != ZERO_ADDRESS:
                            self.sink.on_consume(
                                transaction_hash=transaction_hash,
                                token_address=to_checksum_address(token.address),
                                account_address=consumer,
                                amount=amount,
                                block_timestamp=block_timestamp
                            )
            except Exception as e:
                LOG.exception(e)


_sink = Sinks()
_sink.register(DBSink(db_session))
processor = Processor(_sink, db_session)


def main():
    LOG.info("Service started successfully")

    processor.initial_sync()
    while True:
        try:
            processor.sync_new_logs()
            LOG.debug("Processed")
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except Exception as ex:
            LOG.exception(ex)

        time.sleep(10)


if __name__ == "__main__":
    main()
