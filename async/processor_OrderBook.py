# -*- coding: utf-8 -*-

import os
import sys

path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(path)

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import time
from web3 import Web3
from eth_utils import to_checksum_address
from app import config
from app.model import Agreement, AgreementStatus, Order
from app.contracts import Contract
from web3.middleware import geth_poa_middleware

logging.basicConfig(level=logging.WARNING)

# 設定の取得
WEB3_HTTP_PROVIDER = os.environ.get("WEB3_HTTP_PROVIDER") or 'http://localhost:8545'
URI = os.environ.get("DATABASE_URL") or 'postgresql://ethuser:ethpass@localhost:5432/ethcache'

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

class ConsoleSink:
    def on_new_order(self, token_address, order_id, account_address, is_buy,
                     price, amount, agent_address):
        logging.info("NewOrder: {}".format(order_id))

    def on_cancel_order(self, order_id):
        logging.info("CancelOrder: {}".format(order_id))

    def on_agree(self, order_id, agreement_id, counterpart_address, amount):
        logging.info("Agree: orderId={}, agreementId={}".format(order_id, agreement_id))

    def on_settlement_ok(self, order_id, agreement_id):
        logging.info("SettlementOK: orderId={}, agreementId={}".format(order_id, agreement_id))

    def on_settlement_ng(self, order_id, agreement_id):
        logging.info("SettlementNG: orderId={}, agreementId={}".format(order_id, agreement_id))

    def flush(self):
        return

class DBSink:
    def __init__(self, db):
        self.db = db

    def on_new_order(self, token_address, order_id, account_address, is_buy,
                     price, amount, agent_address):
        order = Order()
        order.id = order_id
        order.token_address = token_address
        order.account_address = account_address
        order.is_buy = is_buy
        order.price = price
        order.amount = amount
        order.agent_address = agent_address
        order.is_cancelled = False
        self.db.merge(order)

    def on_cancel_order(self, order_id):
        order = self.__get_order(order_id)
        order.is_cancelled = True

    def on_agree(self, order_id, agreement_id, counterpart_address, amount):
        agreement = Agreement()
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.counterpart_address = counterpart_address
        agreement.amount = amount
        agreement.status = AgreementStatus.PENDING.value
        self.db.merge(agreement)

    def on_settlement_ok(self, order_id, agreement_id):
        agreement = self.__get_agreement(order_id, agreement_id)
        agreement.status = AgreementStatus.DONE.value

    def on_settlement_ng(self, order_id, agreement_id):
        agreement = self.__get_agreement(order_id, agreement_id)
        agreement.status = AgreementStatus.CANCELED.value

    def flush(self):
        self.db.commit()

    def __get_order(self, order_id):
        return self.db.query(Order).\
            filter(Order.id==order_id).\
            first()

    def __get_agreement(self, order_id, agreement_id):
        return self.db.query(Agreement).\
            filter(Agreement.order_id==order_id).\
            filter(Agreement.agreement_id==agreement_id).\
            first()

class Processor:
    def __init__(self, web3, sink):
        self.web3 = web3
        self.exchange_contract = Contract.get_contract(
            'IbetStraightBondExchange',
            os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS')
        )
        self.sink = sink
        self.latest_block = web3.eth.blockNumber

    def initial_sync(self):
        self.__sync_all(0, self.latest_block)

    def sync_new_logs(self):
        blockTo = web3.eth.blockNumber
        if blockTo == self.latest_block:
            return

        self.__sync_all(self.latest_block+1, blockTo)
        self.latest_block = blockTo

    def __sync_all(self, block_from, block_to):
        logging.debug("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_new_order(block_from, block_to)
        self.__sync_cancel_order(block_from, block_to)
        self.__sync_agree(block_from, block_to)
        self.__sync_settlement_ok(block_from, block_to)
        self.__sync_settlement_ng(block_from, block_to)
        self.sink.flush()

    def __sync_new_order(self, block_from, block_to):
        event_filter = self.exchange_contract.eventFilter(
            'NewOrder', {
                'fromBlock': block_from,
                'toBlock': block_to,
            }
        )
        for event in event_filter.get_all_entries():
            args = event['args']
            self.sink.on_new_order(
                token_address = args['tokenAddress'],
                order_id = args['orderId'],
                account_address = args['accountAddress'],
                is_buy = args['isBuy'],
                price = args['price'],
                amount = args['amount'],
                agent_address = args['agentAddress'],
            )
        self.web3.eth.uninstallFilter(event_filter.filter_id)

    def __sync_cancel_order(self, block_from, block_to):
        event_filter = self.exchange_contract.eventFilter(
            'CancelOrder', {
                'fromBlock': block_from,
                'toBlock': block_to,
            }
        )
        for event in event_filter.get_all_entries():
            args = event['args']
            self.sink.on_cancel_order(
                event['args']['orderId']
            )
        self.web3.eth.uninstallFilter(event_filter.filter_id)

    def __sync_agree(self, block_from, block_to):
        event_filter = self.exchange_contract.eventFilter(
            'Agree', {
                'fromBlock': block_from,
                'toBlock': block_to,
            }
        )
        for event in event_filter.get_all_entries():
            args = event['args']
            order_id = args['orderId']

            orderbook = self.exchange_contract.functions.orderBook(order_id).call()
            is_buy = orderbook[4]

            counterpart_address = args['buyAddress']
            if is_buy:
                counterpart_address = args['sellAddress']

            self.sink.on_agree(
                order_id = args['orderId'],
                agreement_id = args['agreementId'],
                counterpart_address = counterpart_address,
                amount = args['amount'],
            )
        self.web3.eth.uninstallFilter(event_filter.filter_id)

    def __sync_settlement_ok(self, block_from, block_to):
        event_filter = self.exchange_contract.eventFilter(
            'SettlementOK', {
                'fromBlock': block_from,
                'toBlock': block_to,
            }
        )
        for event in event_filter.get_all_entries():
            args = event['args']
            self.sink.on_settlement_ok(args['orderId'], args['agreementId'])
        self.web3.eth.uninstallFilter(event_filter.filter_id)

    def __sync_settlement_ng(self, block_from, block_to):
        event_filter = self.exchange_contract.eventFilter(
            'SettlementNG', {
                'fromBlock': block_from,
                'toBlock': block_to,
            }
        )
        for event in event_filter.get_all_entries():
            args = event['args']
            self.sink.on_settlement_ng(args['orderId'], args['agreementId'])
        self.web3.eth.uninstallFilter(event_filter.filter_id)


sink = Sinks()
sink.register(ConsoleSink())
sink.register(DBSink(db_session))
processor = Processor(web3, sink)

processor.initial_sync()
while True:
    processor.sync_new_logs()
    time.sleep(1)
