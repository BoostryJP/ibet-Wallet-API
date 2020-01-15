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
from app import log
from app import config
from app.model import Agreement, AgreementStatus, Order, Listing
from app.contracts import Contract
from web3.middleware import geth_poa_middleware

from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=+9), "JST")

LOG = log.get_logger()
log_fmt = 'PROCESSOR-OrderAgree [%(asctime)s] [%(process)d] [%(levelname)s] %(message)s'
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
    @staticmethod
    def on_new_order(token_address, exchange_address,
                     order_id, account_address, is_buy, price, amount, agent_address):
        LOG.info(
            "NewOrder: exchange_address={}, order_id={}".format(
                exchange_address, order_id
            )
        )

    @staticmethod
    def on_cancel_order(exchange_address, order_id):
        LOG.info(
            "CancelOrder: exchange_address={}, order_id={}".format(
                exchange_address, order_id
            )
        )

    @staticmethod
    def on_agree(exchange_address, order_id, agreement_id,
                 buyer_address, seller_address, counterpart_address, amount):
        LOG.info(
            "Agree: exchange_address={}, orderId={}, agreementId={}".format(
                exchange_address, order_id, agreement_id
            )
        )

    @staticmethod
    def on_settlement_ok(exchange_address, order_id, agreement_id, settlement_timestamp):
        LOG.info(
            "SettlementOK: exchange_address={}, orderId={}, agreementId={}".format(
                exchange_address, order_id, agreement_id
            )
        )

    @staticmethod
    def on_settlement_ng(exchange_address, order_id, agreement_id):
        LOG.info(
            "SettlementNG: exchange_address={}, orderId={}, agreementId={}".format(
                exchange_address, order_id, agreement_id
            )
        )

    def flush(self):
        return


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_new_order(self, token_address, exchange_address,
                     order_id, account_address, is_buy,
                     price, amount, agent_address):
        order = self.__get_order(exchange_address, order_id)
        if order is None:
            order = Order()
            order.token_address = token_address
            order.exchange_address = exchange_address
            order.order_id = order_id
            order.unique_order_id = exchange_address + '_' + str(order_id)
            order.account_address = account_address
            order.is_buy = is_buy
            order.price = price
            order.amount = amount
            order.agent_address = agent_address
            order.is_cancelled = False
            self.db.merge(order)

    def on_cancel_order(self, exchange_address, order_id):
        order = self.__get_order(exchange_address, order_id)
        if order is not None:
            order.is_cancelled = True

    def on_agree(self, exchange_address, order_id, agreement_id,
                 buyer_address, seller_address, counterpart_address, amount):
        agreement = self.__get_agreement(
            exchange_address, order_id, agreement_id)
        if agreement is None:
            agreement = Agreement()
            agreement.exchange_address = exchange_address
            agreement.order_id = order_id
            agreement.agreement_id = agreement_id
            agreement.unique_order_id = exchange_address + '_' + str(order_id)
            agreement.buyer_address = buyer_address
            agreement.seller_address = seller_address
            agreement.counterpart_address = counterpart_address
            agreement.amount = amount
            agreement.status = AgreementStatus.PENDING.value
            self.db.merge(agreement)

    def on_settlement_ok(self, exchange_address, order_id, agreement_id, settlement_timestamp):
        agreement = self.__get_agreement(
            exchange_address, order_id, agreement_id)
        if agreement is not None:
            agreement.status = AgreementStatus.DONE.value
            agreement.settlement_timestamp = settlement_timestamp

    def on_settlement_ng(self, exchange_address, order_id, agreement_id):
        agreement = self.__get_agreement(
            exchange_address, order_id, agreement_id)
        if agreement is not None:
            agreement.status = AgreementStatus.CANCELED.value

    def flush(self):
        self.db.commit()

    def __get_order(self, exchange_address, order_id):
        return self.db.query(Order). \
            filter(Order.exchange_address == exchange_address). \
            filter(Order.order_id == order_id). \
            first()

    def __get_agreement(self, exchange_address, order_id, agreement_id):
        return self.db.query(Agreement). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.order_id == order_id). \
            filter(Agreement.agreement_id == agreement_id). \
            first()


class Processor:
    def __init__(self, web3, sink, db):
        self.web3 = web3
        self.bond_exchange_contract = Contract.get_contract(
            'IbetStraightBondExchange',
            config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        )
        self.membership_exchange_contract = Contract.get_contract(
            'IbetMembershipExchange',
            config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS
        )
        self.coupon_exchange_contract = Contract.get_contract(
            'IbetCouponExchange',
            config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS
        )
        self.exchange_list = [
            self.bond_exchange_contract,
            self.membership_exchange_contract,
            self.coupon_exchange_contract
        ]
        self.sink = sink
        self.latest_block = web3.eth.blockNumber
        self.db = db

    def initial_sync(self):
        self.__sync_all(0, self.latest_block)

    def sync_new_logs(self):
        blockTo = web3.eth.blockNumber
        if blockTo == self.latest_block:
            return

        self.__sync_all(self.latest_block + 1, blockTo)
        self.latest_block = blockTo

    def __sync_all(self, block_from, block_to):
        LOG.debug("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_new_order(block_from, block_to)
        self.__sync_cancel_order(block_from, block_to)
        self.__sync_agree(block_from, block_to)
        self.__sync_settlement_ok(block_from, block_to)
        self.__sync_settlement_ng(block_from, block_to)
        self.sink.flush()

    def __sync_new_order(self, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                event_filter = exchange_contract.eventFilter(
                    'NewOrder', {
                        'fromBlock': block_from,
                        'toBlock': block_to,
                    }
                )
                for event in event_filter.get_all_entries():
                    args = event['args']
                    if args['price'] > sys.maxsize or args['amount'] > sys.maxsize:
                        pass
                    else:
                        available_token = self.db.query(Listing). \
                            filter(Listing.token_address == args['tokenAddress'])
                        if available_token is not None:
                            self.sink.on_new_order(
                                token_address=args['tokenAddress'],
                                exchange_address=exchange_contract.address,
                                order_id=args['orderId'],
                                account_address=args['accountAddress'],
                                is_buy=args['isBuy'],
                                price=args['price'],
                                amount=args['amount'],
                                agent_address=args['agentAddress'],
                            )

                self.web3.eth.uninstallFilter(event_filter.filter_id)

            except Exception as e:
                LOG.error(e)
                pass

    def __sync_cancel_order(self, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                event_filter = exchange_contract.eventFilter(
                    'CancelOrder', {
                        'fromBlock': block_from,
                        'toBlock': block_to,
                    }
                )
                for event in event_filter.get_all_entries():
                    self.sink.on_cancel_order(
                        exchange_address=exchange_contract.address,
                        order_id=event['args']['orderId']
                    )

                self.web3.eth.uninstallFilter(event_filter.filter_id)

            except Exception as e:
                LOG.error(e)
                pass

    def __sync_agree(self, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                event_filter = exchange_contract.eventFilter(
                    'Agree', {
                        'fromBlock': block_from,
                        'toBlock': block_to,
                    }
                )
                for event in event_filter.get_all_entries():
                    args = event['args']
                    if args['amount'] > sys.maxsize:
                        pass
                    else:
                        order_id = args['orderId']
                        orderbook = exchange_contract.functions.getOrder(order_id).call()
                        is_buy = orderbook[4]
                        counterpart_address = args['buyAddress']
                        if is_buy:
                            counterpart_address = args['sellAddress']

                        self.sink.on_agree(
                            exchange_address=exchange_contract.address,
                            order_id=args['orderId'],
                            agreement_id=args['agreementId'],
                            buyer_address=args['buyAddress'],
                            seller_address=args['sellAddress'],
                            counterpart_address=counterpart_address,
                            amount=args['amount'],
                        )

                self.web3.eth.uninstallFilter(event_filter.filter_id)

            except Exception as e:
                LOG.error(e)
                pass

    def __sync_settlement_ok(self, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                event_filter = exchange_contract.eventFilter(
                    'SettlementOK', {
                        'fromBlock': block_from,
                        'toBlock': block_to,
                    }
                )
                for event in event_filter.get_all_entries():
                    args = event['args']
                    settlement_timestamp = datetime.fromtimestamp(
                        web3.eth.getBlock(event['blockNumber'])['timestamp'],
                        JST
                    )
                    self.sink.on_settlement_ok(
                        exchange_address=exchange_contract.address,
                        order_id=args['orderId'],
                        agreement_id=args['agreementId'],
                        settlement_timestamp=settlement_timestamp
                    )

                self.web3.eth.uninstallFilter(event_filter.filter_id)

            except Exception as e:
                LOG.error(e)
                pass

    def __sync_settlement_ng(self, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                event_filter = exchange_contract.eventFilter(
                    'SettlementNG', {
                        'fromBlock': block_from,
                        'toBlock': block_to,
                    }
                )
                for event in event_filter.get_all_entries():
                    args = event['args']
                    self.sink.on_settlement_ng(
                        exchange_address=exchange_contract.address,
                        order_id=args['orderId'],
                        agreement_id=args['agreementId']
                    )

                self.web3.eth.uninstallFilter(event_filter.filter_id)

            except Exception as e:
                LOG.error(e)
                pass


sink = Sinks()
sink.register(ConsoleSink())
sink.register(DBSink(db_session))
processor = Processor(web3, sink, db_session)

processor.initial_sync()
while True:
    processor.sync_new_logs()
    time.sleep(1)
