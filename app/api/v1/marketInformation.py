# -*- coding: utf-8 -*-
import json
import requests
import os
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=+9), 'JST')

from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from web3 import Web3
from web3.middleware import geth_poa_middleware

from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.model import Order, Agreement
from app.errors import AppError, InvalidParameterError, DataNotExistsError
from app import config
from app.contracts import Contract

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)

'''
Straight Bond Token （普通社債）
'''
# ------------------------------
# [普通社債]板情報取得
# ------------------------------
class OrderBook(BaseResource):

    '''
    Handle for endpoint: /v1/OrderBook
    '''
    def on_post(self, req, res):
        LOG.info('v1.marketInformation.OrderBook')
        session = req.context['session']

        # 入力値チェック
        request_json = OrderBook.validate(req)

        # 入力値を抽出
        token_address = to_checksum_address(request_json['token_address'])

        # 注文を抽出
        is_buy = request_json['order_type'] == 'buy'  # 相対注文が買い注文かどうか
        exchange_address = \
            to_checksum_address(
                os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS'))
        if 'account_address' in request_json:
            account_address = to_checksum_address(request_json['account_address'])

            if is_buy == True:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                #  5) 指定したアカウントアドレス以外            
                orders = session.query(
                    Order.order_id, Order.amount, Order.price, \
                    Order.exchange_address, Order.account_address, \
                    func.sum(Agreement.amount)).\
                    outerjoin(
                        Agreement,
                        Order.unique_order_id == Agreement.unique_order_id).\
                    group_by(
                        Order.order_id, Order.amount,
                        Order.price, Order.exchange_address,
                        Order.account_address).\
                    filter(Order.exchange_address == exchange_address).\
                    filter(Order.token_address == token_address).\
                    filter(Order.is_buy == False).\
                    filter(Order.is_cancelled == False).\
                    filter(Order.account_address != account_address).\
                    filter(Order.agent_address == os.environ.get('AGENT_ADDRESS')).\
                    all()
            else:  # 売注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以上
                #  5) 指定したアカウントアドレス以外
                orders = session.query(
                    Order.order_id, Order.amount, Order.price, \
                    Order.exchange_address, Order.account_address, \
                    func.sum(Agreement.amount)).\
                    outerjoin(
                        Agreement,
                        Order.unique_order_id == Agreement.unique_order_id).\
                    group_by(
                        Order.order_id, Order.amount,
                        Order.price, Order.exchange_address,
                        Order.account_address).\
                    filter(Order.exchange_address == exchange_address).\
                    filter(Order.token_address == token_address).\
                    filter(Order.is_buy == True).\
                    filter(Order.is_cancelled == False).\
                    filter(Order.account_address != account_address).\
                    filter(Order.agent_address == os.environ.get('AGENT_ADDRESS')).\
                    all()
        else:
            if is_buy == True:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                orders = session.query(Order, func.sum(Agreement.amount)).\
                         outerjoin(
                            Agreement,
                            Order.exchange_address == Agreement.exchange_address,
                            Order.order_id == Agreement.order_id).\
                         group_by(Order.exchange_address, Order.order_id).\
                         filter(Order.exchange_address == exchange_address).\
                         filter(Order.token_address == token_address).\
                         filter(Order.is_buy == False).\
                         filter(Order.is_cancelled == False).\
                         all()

            else:  # 売注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以上
                orders = session.query(Order, func.sum(Agreement.amount)).\
                         outerjoin(
                            Agreement,
                            Order.exchange_address == Agreement.exchange_address,
                            Order.order_id == Agreement.order_id).\
                         group_by(Order.exchange_address, Order.order_id).\
                         filter(Order.exchange_address == exchange_address).\
                         filter(Order.token_address == token_address).\
                         filter(Order.is_buy == True).\
                         filter(Order.is_cancelled == False).\
                         all()

        # レスポンス用の注文一覧を構築
        order_list_tmp = []
        for (order_id, amount, price, exchange_address,
            account_address, agreement_amount) in orders:
            # 残存注文数量 = 発注数量 - 約定済み数量
            if not (agreement_amount is None):
                amount -= int(agreement_amount)

            # 残注文ありの注文のみを抽出する
            if amount <= 0:
                continue

            order_list_tmp.append({
                'order_id': order_id,
                'price': price,
                'amount': amount,
                'account_address': account_address,
            })

        # 買い注文の場合は価格で昇順に、売り注文の場合は価格で降順にソートする
        if request_json['order_type'] == 'buy':
            order_list = sorted(order_list_tmp, key=lambda x: x['price'])
        else:
            order_list = sorted(order_list_tmp, key=lambda x: -x['price'])

        self.on_success(res, order_list)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'account_address': {
                'type': 'string'
            },
            'token_address': {
                'type': 'string',
                'empty': False,
                'required': True
            },
            'order_type': {
                'type': 'string',
                'empty': False,
                'required': True,
                'allowed': ['buy', 'sell']
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(request_json['token_address']):
            raise InvalidParameterError

        if not Web3.isAddress(request_json['account_address']):
            raise InvalidParameterError

        return request_json

# ------------------------------
# [普通社債]現在値取得
# ------------------------------
class LastPrice(BaseResource):
    '''
    Handle for endpoint: /v1/LastPrice
    '''

    def on_post(self, req, res):
        LOG.info('v1.marketInformation.LastPrice')

        request_json = LastPrice.validate(req)

        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange',
            os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS')
        )

        price_list = []
        for token_address in request_json['address_list']:
            try:
                last_price = ExchangeContract.functions.lastPrice(
                    to_checksum_address(token_address)).call()
            except:
                last_price = 0
            price_list.append({
                'token_address': token_address,
                'last_price': last_price
            })

        self.on_success(res, price_list)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'address_list': {
                'type': 'list',
                'empty': False,
                'required': True,
                'schema': {
                    'type': 'string',
                    'required': True,
                    'empty': False,
                }
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for token_address in request_json['address_list']:
            if not Web3.isAddress(token_address):
                raise InvalidParameterError

        return request_json

# ------------------------------
# [普通社債]歩み値取得
# ------------------------------
class Tick(BaseResource):
    '''
    Handle for endpoint: /v1/Tick
    '''

    def on_post(self, req, res):
        LOG.info('v1.marketInformation.Tick')

        request_json = Tick.validate(req)

        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange',
            os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS')
        )

        tick_list = []
        for token_address in request_json['address_list']:
            tick = []
            try:
                event_filter = ExchangeContract.events.Agree.createFilter(
                    fromBlock='earliest',
                    argument_filters={'tokenAddress': to_checksum_address(token_address)}
                )
                entries = event_filter.get_all_entries()
                web3.eth.uninstallFilter(event_filter.filter_id)

                for entry in entries:
                    tick.append({
                        'block_timestamp': datetime.fromtimestamp(
                            web3.eth.getBlock(entry['blockNumber'])['timestamp'],JST).\
                            strftime("%Y/%m/%d %H:%M:%S"),
                        'buy_address': entry['args']['buyAddress'],
                        'sell_address': entry['args']['sellAddress'],
                        'order_id': entry['args']['orderId'],
                        'agreement_id': entry['args']['agreementId'],
                        'price': entry['args']['price'],
                        'amount': entry['args']['amount'],
                    })
                tick_list.append({
                    'token_address': token_address,
                    'tick': tick
                })
            except:
                tick_list = []

        self.on_success(res, tick_list)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'address_list': {
                'type': 'list',
                'empty': False,
                'required': True,
                'schema': {
                    'type': 'string',
                    'required': True,
                    'empty': False,
                }
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for token_address in request_json['address_list']:
            if not Web3.isAddress(token_address):
                raise InvalidParameterError

        return request_json


'''
Membership Token （会員権）
'''
# ------------------------------
# [会員権]板情報取得
# ------------------------------
class MembershipOrderBook(BaseResource):

    '''
    Handle for endpoint: /v1/Membership/OrderBook
    '''
    def on_post(self, req, res):
        LOG.info('v1.marketInformation.MembershipOrderBook')
        session = req.context['session']

        # 入力値チェック
        request_json = MembershipOrderBook.validate(req)

        # 入力値を抽出
        token_address = to_checksum_address(request_json['token_address'])

        # 注文を抽出
        is_buy = request_json['order_type'] == 'buy'  # 相対注文が買い注文かどうか
        exchange_address = \
            to_checksum_address(
                os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS'))
        if 'account_address' in request_json:
            account_address = to_checksum_address(request_json['account_address'])

            if is_buy == True:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                #  5) 指定したアカウントアドレス以外
                orders = session.query(
                    Order.order_id, Order.amount, Order.price, \
                    Order.exchange_address, Order.account_address, \
                    func.sum(Agreement.amount)).\
                    outerjoin(
                        Agreement,
                        Order.unique_order_id == Agreement.unique_order_id).\
                    group_by(
                        Order.order_id, Order.amount,
                        Order.price, Order.exchange_address,
                        Order.account_address).\
                    filter(Order.exchange_address == exchange_address).\
                    filter(Order.token_address == token_address).\
                    filter(Order.is_buy == False).\
                    filter(Order.is_cancelled == False).\
                    filter(Order.account_address != account_address).\
                    all()
            else:  # 売注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以上
                #  5) 指定したアカウントアドレス以外
                orders = session.query(
                    Order.order_id, Order.amount, Order.price, \
                    Order.exchange_address, Order.account_address, \
                    func.sum(Agreement.amount)).\
                    outerjoin(
                        Agreement,
                        Order.unique_order_id == Agreement.unique_order_id).\
                    group_by(
                        Order.order_id, Order.amount,
                        Order.price, Order.exchange_address,
                        Order.account_address).\
                    filter(Order.exchange_address == exchange_address).\
                    filter(Order.token_address == token_address).\
                    filter(Order.is_buy == True).\
                    filter(Order.is_cancelled == False).\
                    filter(Order.account_address != account_address).\
                    all()
        else:
            if is_buy == True:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                orders = session.query(Order, func.sum(Agreement.amount)).\
                         outerjoin(
                            Agreement,
                            Order.exchange_address == Agreement.exchange_address,
                            Order.order_id == Agreement.order_id).\
                         group_by(Order.exchange_address, Order.order_id).\
                         filter(Order.exchange_address == exchange_address).\
                         filter(Order.token_address == token_address).\
                         filter(Order.is_buy == False).\
                         filter(Order.is_cancelled == False).\
                         all()

            else:  # 売注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以上
                orders = session.query(Order, func.sum(Agreement.amount)).\
                         outerjoin(
                            Agreement,
                            Order.exchange_address == Agreement.exchange_address,
                            Order.order_id == Agreement.order_id).\
                         group_by(Order.exchange_address, Order.order_id).\
                         filter(Order.exchange_address == exchange_address).\
                         filter(Order.token_address == token_address).\
                         filter(Order.is_buy == True).\
                         filter(Order.is_cancelled == False).\
                         all()

        # レスポンス用の注文一覧を構築
        order_list_tmp = []
        for (order_id, amount, price, exchange_address,
            account_address, agreement_amount) in orders:
            # 残存注文数量 = 発注数量 - 約定済み数量
            if not (agreement_amount is None):
                amount -= int(agreement_amount)

            # 残注文ありの注文のみを抽出する
            if amount <= 0:
                continue

            order_list_tmp.append({
                'order_id': order_id,
                'price': price,
                'amount': amount,
                'account_address': account_address,
            })

        # 買い注文の場合は価格で昇順に、売り注文の場合は価格で降順にソートする
        if request_json['order_type'] == 'buy':
            order_list = sorted(order_list_tmp, key=lambda x: x['price'])
        else:
            order_list = sorted(order_list_tmp, key=lambda x: -x['price'])

        self.on_success(res, order_list)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'account_address': {
                'type': 'string'
            },
            'token_address': {
                'type': 'string',
                'empty': False,
                'required': True
            },
            'order_type': {
                'type': 'string',
                'empty': False,
                'required': True,
                'allowed': ['buy', 'sell']
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(request_json['token_address']):
            raise InvalidParameterError

        if not Web3.isAddress(request_json['account_address']):
            raise InvalidParameterError

        return request_json

# ------------------------------
# [会員権]現在値取得
# ------------------------------
class MembershipLastPrice(BaseResource):
    '''
    Handle for endpoint: /v1/Membership/LastPrice
    '''

    def on_post(self, req, res):
        LOG.info('v1.marketInformation.MembershipLastPrice')

        request_json = MembershipLastPrice.validate(req)

        ExchangeContract = Contract.get_contract(
            'IbetMembershipExchange',
            os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS')
        )

        price_list = []
        for token_address in request_json['address_list']:
            try:
                last_price = ExchangeContract.functions.\
                    lastPrice(to_checksum_address(token_address)).call()
            except:
                last_price = 0

            price_list.append({
                'token_address': token_address,
                'last_price': last_price
            })

        self.on_success(res, price_list)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'address_list': {
                'type': 'list',
                'empty': False,
                'required': True,
                'schema': {
                    'type': 'string',
                    'required': True,
                    'empty': False,
                }
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for token_address in request_json['address_list']:
            if not Web3.isAddress(token_address):
                raise InvalidParameterError

        return request_json

# ------------------------------
# [会員権]歩み値取得
# ------------------------------
class MembershipTick(BaseResource):
    '''
    Handle for endpoint: /v1/Membership/Tick
    '''

    def on_post(self, req, res):
        LOG.info('v1.marketInformation.MembershipTick')

        request_json = MembershipTick.validate(req)

        ExchangeContract = Contract.get_contract(
            'IbetMembershipExchange',
            os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS')
        )

        tick_list = []
        # TokenごとにTickを取得
        for token_address in request_json['address_list']:
            token = to_checksum_address(token_address)
            tick = []
            try:
                event_filter = ExchangeContract.events.Agree.\
                    createFilter(
                        fromBlock='earliest',
                        argument_filters={'tokenAddress': token}
                    )
                entries = event_filter.get_all_entries()
                web3.eth.uninstallFilter(event_filter.filter_id)

                for entry in entries:
                    tick.append({
                        'block_timestamp': datetime.\
                            fromtimestamp(web3.eth.getBlock(entry['blockNumber'])['timestamp'],JST).\
                            strftime("%Y/%m/%d %H:%M:%S"),
                        'buy_address': entry['args']['buyAddress'],
                        'sell_address': entry['args']['sellAddress'],
                        'order_id': entry['args']['orderId'],
                        'agreement_id': entry['args']['agreementId'],
                        'price': entry['args']['price'],
                        'amount': entry['args']['amount'],
                    })
                tick_list.append({
                    'token_address': token_address,
                    'tick': tick
                })
            except:
                tick_list = []

        self.on_success(res, tick_list)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'address_list': {
                'type': 'list',
                'empty': False,
                'required': True,
                'schema': {
                    'type': 'string',
                    'required': True,
                    'empty': False,
                }
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for token_address in request_json['address_list']:
            if not Web3.isAddress(token_address):
                raise InvalidParameterError

        return request_json


'''
Coupon Token （クーポン）
'''
# ------------------------------
# [クーポン]板情報取得
# ------------------------------
class CouponOrderBook(BaseResource):

    '''
    Handle for endpoint: /v1/Coupon/OrderBook
    '''
    def on_post(self, req, res):
        LOG.info('v1.marketInformation.CouponOrderBook')
        session = req.context['session']

        # 入力値チェック
        request_json = MembershipOrderBook.validate(req)

        # 入力値を抽出
        token_address = to_checksum_address(request_json['token_address'])

        # 注文を抽出
        is_buy = request_json['order_type'] == 'buy'  # 相対注文が買い注文かどうか
        exchange_address = \
            to_checksum_address(
                os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS'))
        if 'account_address' in request_json:
            account_address = to_checksum_address(request_json['account_address'])

            if is_buy == True:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                #  5) 指定したアカウントアドレス以外
                orders = session.query(
                    Order.order_id, Order.amount, Order.price, \
                    Order.exchange_address, Order.account_address, \
                    func.sum(Agreement.amount)).\
                    outerjoin(
                        Agreement,
                        Order.unique_order_id == Agreement.unique_order_id).\
                    group_by(
                        Order.order_id, Order.amount,
                        Order.price, Order.exchange_address,
                        Order.account_address).\
                    filter(Order.exchange_address == exchange_address).\
                    filter(Order.token_address == token_address).\
                    filter(Order.is_buy == False).\
                    filter(Order.is_cancelled == False).\
                    filter(Order.account_address != account_address).\
                    all()
            else:  # 売注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以上
                #  5) 指定したアカウントアドレス以外
                orders = session.query(
                    Order.order_id, Order.amount, Order.price, \
                    Order.exchange_address, Order.account_address, \
                    func.sum(Agreement.amount)).\
                    outerjoin(
                        Agreement,
                        Order.unique_order_id == Agreement.unique_order_id).\
                    group_by(
                        Order.order_id, Order.amount,
                        Order.price, Order.exchange_address,
                        Order.account_address).\
                    filter(Order.exchange_address == exchange_address).\
                    filter(Order.token_address == token_address).\
                    filter(Order.is_buy == True).\
                    filter(Order.is_cancelled == False).\
                    filter(Order.account_address != account_address).\
                    all()
        else:
            if is_buy == True:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                orders = session.query(Order, func.sum(Agreement.amount)).\
                         outerjoin(
                            Agreement,
                            Order.exchange_address == Agreement.exchange_address,
                            Order.order_id == Agreement.order_id).\
                         group_by(Order.exchange_address, Order.order_id).\
                         filter(Order.exchange_address == exchange_address).\
                         filter(Order.token_address == token_address).\
                         filter(Order.is_buy == False).\
                         filter(Order.is_cancelled == False).\
                         all()

            else:  # 売注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以上
                orders = session.query(Order, func.sum(Agreement.amount)).\
                         outerjoin(
                            Agreement,
                            Order.exchange_address == Agreement.exchange_address,
                            Order.order_id == Agreement.order_id).\
                         group_by(Order.exchange_address, Order.order_id).\
                         filter(Order.exchange_address == exchange_address).\
                         filter(Order.token_address == token_address).\
                         filter(Order.is_buy == True).\
                         filter(Order.is_cancelled == False).\
                         all()

        # レスポンス用の注文一覧を構築
        order_list_tmp = []
        for (order_id, amount, price, exchange_address,
            account_address, agreement_amount) in orders:
            # 残存注文数量 = 発注数量 - 約定済み数量
            if not (agreement_amount is None):
                amount -= int(agreement_amount)

            # 残注文ありの注文のみを抽出する
            if amount <= 0:
                continue

            order_list_tmp.append({
                'order_id': order_id,
                'price': price,
                'amount': amount,
                'account_address': account_address,
            })

        # 買い注文の場合は価格で昇順に、売り注文の場合は価格で降順にソートする
        if request_json['order_type'] == 'buy':
            order_list = sorted(order_list_tmp, key=lambda x: x['price'])
        else:
            order_list = sorted(order_list_tmp, key=lambda x: -x['price'])

        self.on_success(res, order_list)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'account_address': {
                'type': 'string'
            },
            'token_address': {
                'type': 'string',
                'empty': False,
                'required': True
            },
            'order_type': {
                'type': 'string',
                'empty': False,
                'required': True,
                'allowed': ['buy', 'sell']
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(request_json['token_address']):
            raise InvalidParameterError

        if not Web3.isAddress(request_json['account_address']):
            raise InvalidParameterError

        return request_json

# ------------------------------
# [クーポン]現在値取得
# ------------------------------
class CouponLastPrice(BaseResource):
    '''
    Handle for endpoint: /v1/Coupon/LastPrice
    '''

    def on_post(self, req, res):
        LOG.info('v1.marketInformation.CouponLastPrice')

        request_json = CouponLastPrice.validate(req)

        ExchangeContract = Contract.get_contract(
            'IbetCouponExchange',
            os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS')
        )

        price_list = []
        for token_address in request_json['address_list']:
            try:
                last_price = ExchangeContract.functions.\
                    lastPrice(to_checksum_address(token_address)).call()
            except:
                last_price = 0

            price_list.append({
                'token_address': token_address,
                'last_price': last_price
            })

        self.on_success(res, price_list)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'address_list': {
                'type': 'list',
                'empty': False,
                'required': True,
                'schema': {
                    'type': 'string',
                    'required': True,
                    'empty': False,
                }
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for token_address in request_json['address_list']:
            if not Web3.isAddress(token_address):
                raise InvalidParameterError

        return request_json

# ------------------------------
# [クーポン]歩み値取得
# ------------------------------
class CouponTick(BaseResource):
    '''
    Handle for endpoint: /v1/Coupon/Tick
    '''

    def on_post(self, req, res):
        LOG.info('v1.marketInformation.CouponTick')

        request_json = Tick.validate(req)

        ExchangeContract = Contract.get_contract(
            'IbetCouponExchange',
            os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS')
        )

        tick_list = []
        # TokenごとにTickを取得
        for token_address in request_json['address_list']:
            token = to_checksum_address(token_address)
            tick = []
            try:
                event_filter = ExchangeContract.events.Agree.\
                    createFilter(
                        fromBlock='earliest',
                        argument_filters={'tokenAddress': token}
                    )
                entries = event_filter.get_all_entries()
                web3.eth.uninstallFilter(event_filter.filter_id)

                for entry in entries:
                    tick.append({
                        'block_timestamp': datetime.\
                            fromtimestamp(web3.eth.getBlock(entry['blockNumber'])['timestamp'],JST).\
                            strftime("%Y/%m/%d %H:%M:%S"),
                        'buy_address': entry['args']['buyAddress'],
                        'sell_address': entry['args']['sellAddress'],
                        'order_id': entry['args']['orderId'],
                        'agreement_id': entry['args']['agreementId'],
                        'price': entry['args']['price'],
                        'amount': entry['args']['amount'],
                    })
                tick_list.append({
                    'token_address': token_address,
                    'tick': tick
                })
            except:
                tick_list = []

        self.on_success(res, tick_list)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'address_list': {
                'type': 'list',
                'empty': False,
                'required': True,
                'schema': {
                    'type': 'string',
                    'required': True,
                    'empty': False,
                }
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for token_address in request_json['address_list']:
            if not Web3.isAddress(token_address):
                raise InvalidParameterError

        return request_json
