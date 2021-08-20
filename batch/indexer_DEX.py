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
from sqlalchemy.orm import sessionmaker, scoped_session
from web3 import Web3
from web3.middleware import geth_poa_middleware

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app.config import (
    WEB3_HTTP_PROVIDER,
    DATABASE_URL,
    IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
    IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
    IBET_CP_EXCHANGE_CONTRACT_ADDRESS,
    IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS
)
from app.model import (
    IDXAgreement as Agreement,
    AgreementStatus,
    IDXOrder as Order,
    Listing
)
from app.contracts import Contract
import log

JST = timezone(timedelta(hours=+9), "JST")

process_name = "INDEXER-DEX"
LOG = log.get_logger(process_name=process_name)

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)


class Sinks:
    def __init__(self):
        self.sinks = []

    def register(self, sink):
        self.sinks.append(sink)

    def on_new_order(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_new_order(*args, **kwargs)

    def on_cancel_order(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_cancel_order(*args, **kwargs)

    def on_agree(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_agree(*args, **kwargs)

    def on_settlement_ok(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_settlement_ok(*args, **kwargs)

    def on_settlement_ng(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_settlement_ng(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_new_order(self, transaction_hash: str, token_address: str, exchange_address: str,
                     order_id: int, account_address: str, counterpart_address: str, is_buy: bool, price: int,
                     amount: int,
                     agent_address: str, order_timestamp: datetime):
        order = self.__get_order(exchange_address, order_id)
        if order is None:
            LOG.debug(f"NewOrder: exchange_address={exchange_address}, order_id={order_id}")
            order = Order()
            order.transaction_hash = transaction_hash
            order.token_address = token_address
            order.exchange_address = exchange_address
            order.order_id = order_id
            order.unique_order_id = exchange_address + "_" + str(order_id)
            order.account_address = account_address
            order.counterpart_address = counterpart_address
            order.is_buy = is_buy
            order.price = price
            order.amount = amount
            order.agent_address = agent_address
            order.is_cancelled = False
            order.order_timestamp = order_timestamp
            self.db.merge(order)

    def on_cancel_order(self, exchange_address: str, order_id: int):
        order = self.__get_order(exchange_address, order_id)
        if order is not None:
            LOG.debug(f"CancelOrder: exchange_address={exchange_address}, order_id={order_id}")
            order.is_cancelled = True

    def on_agree(self, transaction_hash: str, exchange_address: str, order_id: int, agreement_id: int,
                 buyer_address: str, seller_address: str, counterpart_address: str,
                 amount: int, agreement_timestamp: datetime):
        agreement = self.__get_agreement(exchange_address, order_id, agreement_id)
        if agreement is None:
            LOG.debug(f"Agree: exchange_address={exchange_address}, orderId={order_id}, agreementId={agreement_id}")
            agreement = Agreement()
            agreement.transaction_hash = transaction_hash
            agreement.exchange_address = exchange_address
            agreement.order_id = order_id
            agreement.agreement_id = agreement_id
            agreement.unique_order_id = exchange_address + "_" + str(order_id)
            agreement.buyer_address = buyer_address
            agreement.seller_address = seller_address
            agreement.counterpart_address = counterpart_address
            agreement.amount = amount
            agreement.status = AgreementStatus.PENDING.value
            agreement.agreement_timestamp = agreement_timestamp
            self.db.merge(agreement)

    def on_settlement_ok(self, exchange_address: str, order_id: int, agreement_id: int, settlement_timestamp: datetime):
        agreement = self.__get_agreement(exchange_address, order_id, agreement_id)
        if agreement is not None:
            LOG.debug(f"SettlementOK: exchange_address={exchange_address}, orderId={order_id}, agreementId={agreement_id}")
            agreement.status = AgreementStatus.DONE.value
            agreement.settlement_timestamp = settlement_timestamp

    def on_settlement_ng(self, exchange_address: str, order_id: int, agreement_id: int):
        agreement = self.__get_agreement(exchange_address, order_id, agreement_id)
        if agreement is not None:
            LOG.debug(f"SettlementNG: exchange_address={exchange_address}, orderId={order_id}, agreementId={agreement_id}")
            agreement.status = AgreementStatus.CANCELED.value

    def flush(self):
        self.db.commit()

    def __get_order(self, exchange_address: str, order_id: int):
        return self.db.query(Order). \
            filter(Order.exchange_address == exchange_address). \
            filter(Order.order_id == order_id). \
            first()

    def __get_agreement(self, exchange_address: str, order_id: int, agreement_id: int):
        return self.db.query(Agreement). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.order_id == order_id). \
            filter(Agreement.agreement_id == agreement_id). \
            first()


class Processor:
    def __init__(self, sink, db):
        self.exchange_list = []
        # 債券取引コントラクト登録
        if IBET_SB_EXCHANGE_CONTRACT_ADDRESS is not None:
            bond_exchange_contract = Contract.get_contract(
                "IbetExchange",
                IBET_SB_EXCHANGE_CONTRACT_ADDRESS
            )
            self.exchange_list.append(bond_exchange_contract)
        # 会員権取引コントラクト登録
        if IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS is not None:
            membership_exchange_contract = Contract.get_contract(
                "IbetExchange",
                IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS
            )
            self.exchange_list.append(membership_exchange_contract)
        # クーポン取引コントラクト登録
        if IBET_CP_EXCHANGE_CONTRACT_ADDRESS is not None:
            coupon_exchange_contract = Contract.get_contract(
                "IbetExchange",
                IBET_CP_EXCHANGE_CONTRACT_ADDRESS
            )
            self.exchange_list.append(coupon_exchange_contract)
        # 株式取引コントラクト登録
        if IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS is not None:
            self.share_exchange_contract = Contract.get_contract(
                "IbetExchange",
                IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS
            )
            self.exchange_list.append(self.share_exchange_contract)
        else:
            self.share_exchange_contract = ""
        self.sink = sink
        self.latest_block = web3.eth.blockNumber
        self.db = db

    def initial_sync(self):
        # 1,000,000ブロックずつ同期処理を行う
        _to_block = 999999
        _from_block = 0
        if self.latest_block > 999999:
            while _to_block < self.latest_block:
                self.__init_sync_all(_from_block, _to_block)
                _to_block += 1000000
                _from_block += 1000000
            self.__init_sync_all(_from_block, self.latest_block)
        else:
            self.__init_sync_all(_from_block, self.latest_block)
        self.sink.flush()
        LOG.info(f"<{process_name}> Initial sync has been completed")

    def sync_new_logs(self):
        blockTo = web3.eth.blockNumber
        if blockTo == self.latest_block:
            return

        self.__sync_all(self.latest_block + 1, blockTo)
        self.latest_block = blockTo

    def __init_sync_all(self, block_from, block_to):
        LOG.info("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_new_order(block_from, block_to)
        self.__sync_cancel_order(block_from, block_to)
        self.__sync_agree(block_from, block_to)
        self.__sync_settlement_ok(block_from, block_to)
        self.__sync_settlement_ng(block_from, block_to)

    def __sync_all(self, block_from, block_to):
        LOG.info("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_new_order(block_from, block_to)
        self.__sync_cancel_order(block_from, block_to)
        self.__sync_agree(block_from, block_to)
        self.__sync_settlement_ok(block_from, block_to)
        self.__sync_settlement_ng(block_from, block_to)
        self.sink.flush()

    def __sync_new_order(self, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                events = exchange_contract.events.NewOrder.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    if args["price"] > sys.maxsize or args["amount"] > sys.maxsize:
                        pass
                    else:
                        available_token = self.db.query(Listing). \
                            filter(Listing.token_address == args["tokenAddress"]). \
                            first()
                        transaction_hash = event["transactionHash"].hex()
                        order_timestamp = datetime.fromtimestamp(
                            web3.eth.getBlock(event["blockNumber"])["timestamp"],
                            JST
                        )
                        if available_token is not None:
                            account_address = args["accountAddress"]
                            counterpart_address = ""
                            is_buy = args["isBuy"]

                            self.sink.on_new_order(
                                transaction_hash=transaction_hash,
                                token_address=args["tokenAddress"],
                                exchange_address=exchange_contract.address,
                                order_id=args["orderId"],
                                account_address=account_address,
                                counterpart_address=counterpart_address,
                                is_buy=is_buy,
                                price=args["price"],
                                amount=args["amount"],
                                agent_address=args["agentAddress"],
                                order_timestamp=order_timestamp
                            )
            except Exception as e:
                LOG.exception(e)

    def __sync_cancel_order(self, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                events = exchange_contract.events.CancelOrder.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    self.sink.on_cancel_order(
                        exchange_address=exchange_contract.address,
                        order_id=event["args"]["orderId"]
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_agree(self, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                events = exchange_contract.events.Agree.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    if args["amount"] > sys.maxsize:
                        pass
                    else:
                        order_id = args["orderId"]
                        orderbook = exchange_contract.functions.getOrder(order_id).call()
                        is_buy = orderbook[4]
                        if is_buy:
                            counterpart_address = args["sellAddress"]
                        else:
                            counterpart_address = args["buyAddress"]
                        transaction_hash = event["transactionHash"].hex()
                        agreement_timestamp = datetime.fromtimestamp(
                            web3.eth.getBlock(event["blockNumber"])["timestamp"],
                            JST
                        )
                        self.sink.on_agree(
                            transaction_hash=transaction_hash,
                            exchange_address=exchange_contract.address,
                            order_id=args["orderId"],
                            agreement_id=args["agreementId"],
                            buyer_address=args["buyAddress"],
                            seller_address=args["sellAddress"],
                            counterpart_address=counterpart_address,
                            amount=args["amount"],
                            agreement_timestamp=agreement_timestamp
                        )
            except Exception as e:
                LOG.exception(e)

    def __sync_settlement_ok(self, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                events = exchange_contract.events.SettlementOK.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    settlement_timestamp = datetime.fromtimestamp(
                        web3.eth.getBlock(event["blockNumber"])["timestamp"],
                        JST
                    )
                    self.sink.on_settlement_ok(
                        exchange_address=exchange_contract.address,
                        order_id=args["orderId"],
                        agreement_id=args["agreementId"],
                        settlement_timestamp=settlement_timestamp
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_settlement_ng(self, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                events = exchange_contract.events.SettlementNG.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    self.sink.on_settlement_ng(
                        exchange_address=exchange_contract.address,
                        order_id=args["orderId"],
                        agreement_id=args["agreementId"]
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
        processor.sync_new_logs()
        time.sleep(1)


if __name__ == "__main__":
    main()
