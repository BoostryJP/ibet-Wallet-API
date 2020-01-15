# -*- coding: utf-8 -*-
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=+9), 'JST')

from sqlalchemy import func
from sqlalchemy import desc
from cerberus import Validator

from web3 import Web3
from web3.middleware import geth_poa_middleware

from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.model import Order, Agreement
from app.errors import InvalidParameterError
from app import config
from app.contracts import Contract

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


"""
Straight Bond
"""

# ------------------------------
# [普通社債]板情報取得
# ------------------------------
class StraightBondOrderBook(BaseResource):
    """
    Handle for endpoint: /v2/Market/OrderBook/StraightBond
    """

    def on_post(self, req, res):
        LOG.info('v2.market_information.StraightBondOrderBook')
        session = req.context['session']

        # 入力値チェック
        request_json = StraightBondOrderBook.validate(req)

        # 入力値を抽出
        token_address = to_checksum_address(request_json['token_address'])

        # 注文を抽出
        is_buy = request_json['order_type'] == 'buy'  # 相対注文が買い注文かどうか
        exchange_address = \
            to_checksum_address(
                config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS)

        # account_address（注文者のアドレス）指定時は注文者以外の注文板を取得する
        # account_address（注文者のアドレス）未指定時は全ての注文板を取得する
        if 'account_address' in request_json:
            account_address = to_checksum_address(request_json['account_address'])

            if is_buy:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                #  5) 指定したアカウントアドレス以外
                orders = session.query(
                    Order.order_id, Order.amount, Order.price,
                    Order.exchange_address, Order.account_address,
                    func.sum(Agreement.amount)). \
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
                    filter(Order.agent_address == config.AGENT_ADDRESS).\
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
                    Order.order_id, Order.amount, Order.price,
                    Order.exchange_address, Order.account_address,
                    func.sum(Agreement.amount)). \
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
                    filter(Order.agent_address == config.AGENT_ADDRESS).\
                    all()

        else:
            if is_buy:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                orders = session.query(
                    Order.order_id, Order.amount, Order.price,
                    Order.exchange_address, Order.account_address,
                    func.sum(Agreement.amount)). \
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
                    filter(Order.agent_address == config.AGENT_ADDRESS).\
                    all()

            else:  # 売注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以上
                orders = session.query(
                    Order.order_id, Order.amount, Order.price,
                    Order.exchange_address, Order.account_address,
                    func.sum(Agreement.amount)). \
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
                    filter(Order.agent_address == config.AGENT_ADDRESS).\
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

        if 'account_address' in request_json:
            if not Web3.isAddress(request_json['account_address']):
                raise InvalidParameterError

        return request_json


# ------------------------------
# [普通社債]現在値取得
# ------------------------------
class StraightBondLastPrice(BaseResource):
    """
    Handle for endpoint: /v2/Market/LastPrice/StraightBond
    """

    def on_post(self, req, res):
        LOG.info('v2.market_information.StraightBondLastPrice')

        request_json = StraightBondLastPrice.validate(req)

        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange',
            config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        )

        price_list = []
        for token_address in request_json['address_list']:
            try:
                last_price = ExchangeContract.functions.lastPrice(
                    to_checksum_address(token_address)).call()
            except Exception as e:
                LOG.error(e)
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
class StraightBondTick(BaseResource):
    """
    Handle for endpoint: /v2/Market/Tick/StraightBond
    """

    def on_post(self, req, res):
        LOG.info('v2.market_information.StraightBondTick')

        request_json = StraightBondTick.validate(req)

        session = req.context["session"]

        tick_list = []
        for token_address in request_json['address_list']:
            token = to_checksum_address(token_address)
            tick = []
            try:
                entries = session.query(Agreement, Order).\
                    join(Order, Agreement.unique_order_id == Order.unique_order_id). \
                    filter(Order.token_address == token). \
                    filter(Agreement.status == 1). \
                    filter(Order.is_cancelled == False). \
                    order_by(desc(Agreement.settlement_timestamp)). \
                    all()

                for entry in entries:
                    block_timestamp_utc = entry.Agreement.settlement_timestamp
                    tick.append({
                        'block_timestamp': block_timestamp_utc.strftime('%Y/%m/%d %H:%M:%S'),
                        'buy_address': entry.Agreement.buyer_address,
                        'sell_address': entry.Agreement.seller_address,
                        'order_id': entry.Agreement.order_id,
                        'agreement_id': entry.Agreement.agreement_id,
                        'price': entry.Order.price,
                        'amount': entry.Agreement.amount
                    })
                tick_list.append({
                    'token_address': token_address,
                    'tick': tick
                })
            except Exception as e:
                LOG.error(e)
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


"""
Membership
"""

# ------------------------------
# [会員権]板情報取得
# ------------------------------
class MembershipOrderBook(BaseResource):
    """
    Handle for endpoint: /v2/Market/OrderBook/Membership
    """

    def on_post(self, req, res):
        LOG.info('v2.market_information.MembershipOrderBook')
        session = req.context['session']

        # 入力値チェック
        request_json = MembershipOrderBook.validate(req)

        # 入力値を抽出
        token_address = to_checksum_address(request_json['token_address'])

        # 注文を抽出
        is_buy = request_json['order_type'] == 'buy'  # 相対注文が買い注文かどうか
        exchange_address = \
            to_checksum_address(
                config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS)

        # account_address（注文者のアドレス）指定時は注文者以外の注文板を取得する
        # account_address（注文者のアドレス）未指定時は全ての注文板を取得する
        if 'account_address' in request_json:
            account_address = to_checksum_address(request_json['account_address'])

            if is_buy:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                #  5) 指定したアカウントアドレス以外
                orders = session.query(
                    Order.order_id, Order.amount, Order.price,
                    Order.exchange_address, Order.account_address,
                    func.sum(Agreement.amount)). \
                    outerjoin(
                    Agreement,
                    Order.unique_order_id == Agreement.unique_order_id). \
                    group_by(
                    Order.order_id, Order.amount,
                    Order.price, Order.exchange_address,
                    Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == False). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.account_address != account_address). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
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
                    Order.order_id, Order.amount, Order.price,
                    Order.exchange_address, Order.account_address,
                    func.sum(Agreement.amount)). \
                    outerjoin(
                    Agreement,
                    Order.unique_order_id == Agreement.unique_order_id). \
                    group_by(
                    Order.order_id, Order.amount,
                    Order.price, Order.exchange_address,
                    Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == True). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.account_address != account_address). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
                    all()

        else:
            if is_buy:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                orders = session.query(
                    Order.order_id, Order.amount, Order.price,
                    Order.exchange_address, Order.account_address,
                    func.sum(Agreement.amount)). \
                    outerjoin(
                    Agreement,
                    Order.unique_order_id == Agreement.unique_order_id). \
                    group_by(
                    Order.order_id, Order.amount,
                    Order.price, Order.exchange_address,
                    Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == False). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
                    all()

            else:  # 売注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以上
                orders = session.query(
                    Order.order_id, Order.amount, Order.price,
                    Order.exchange_address, Order.account_address,
                    func.sum(Agreement.amount)). \
                    outerjoin(
                    Agreement,
                    Order.unique_order_id == Agreement.unique_order_id). \
                    group_by(
                    Order.order_id, Order.amount,
                    Order.price, Order.exchange_address,
                    Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == True). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
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

        if 'account_address' in request_json:
            if not Web3.isAddress(request_json['account_address']):
                raise InvalidParameterError

        return request_json


# ------------------------------
# [会員権]現在値取得
# ------------------------------
class MembershipLastPrice(BaseResource):
    """
    Handle for endpoint: /v2/Market/LastPrice/Membership
    """

    def on_post(self, req, res):
        LOG.info('v2.market_information.MembershipLastPrice')

        request_json = MembershipLastPrice.validate(req)

        ExchangeContract = Contract.get_contract(
            'IbetMembershipExchange',
            config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS
        )

        price_list = []
        for token_address in request_json['address_list']:
            try:
                last_price = ExchangeContract.functions. \
                    lastPrice(to_checksum_address(token_address)).call()
            except Exception as e:
                LOG.error(e)
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
    """
    Handle for endpoint: /v2/Market/Tick/Membership
    """

    def on_post(self, req, res):
        LOG.info('v2.market_information.MembershipTick')

        request_json = MembershipTick.validate(req)

        session = req.context["session"]

        tick_list = []
        # TokenごとにTickを取得
        for token_address in request_json['address_list']:
            token = to_checksum_address(token_address)
            tick = []
            try:
                entries = session.query(Agreement, Order). \
                    join(Order, Agreement.unique_order_id == Order.unique_order_id). \
                    filter(Order.token_address == token).\
                    filter(Agreement.status == 1).\
                    filter(Order.is_cancelled == False).\
                    order_by(desc(Agreement.settlement_timestamp)).\
                    all()

                for entry in entries:
                    block_timestamp_utc = entry.Agreement.settlement_timestamp
                    tick.append({
                        'block_timestamp': block_timestamp_utc.strftime('%Y/%m/%d %H:%M:%S'),
                        'buy_address': entry.Agreement.buyer_address,
                        'sell_address': entry.Agreement.seller_address,
                        'order_id': entry.Agreement.order_id,
                        'agreement_id': entry.Agreement.agreement_id,
                        'price': entry.Order.price,
                        'amount': entry.Agreement.amount
                    })
                tick_list.append({
                    'token_address': token_address,
                    'tick': tick
                })
            except Exception as e:
                LOG.error(e)
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


"""
Coupon
"""

# ------------------------------
# [クーポン]板情報取得
# ------------------------------
class CouponOrderBook(BaseResource):
    """
    Handle for endpoint: /v2/Market/OrderBook/Coupon
    """

    def on_post(self, req, res):
        LOG.info('v2.market_information.CouponOrderBook')
        session = req.context['session']

        # 入力値チェック
        request_json = CouponOrderBook.validate(req)

        # 入力値を抽出
        token_address = to_checksum_address(request_json['token_address'])

        # 注文を抽出
        is_buy = request_json['order_type'] == 'buy'  # 相対注文が買い注文かどうか
        exchange_address = \
            to_checksum_address(
                config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS)

        # account_address（注文者のアドレス）指定時は注文者以外の注文板を取得する
        # account_address（注文者のアドレス）未指定時は全ての注文板を取得する
        if 'account_address' in request_json:
            account_address = to_checksum_address(request_json['account_address'])

            if is_buy:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                #  5) 指定したアカウントアドレス以外
                orders = session.query(
                    Order.order_id, Order.amount, Order.price,
                    Order.exchange_address, Order.account_address,
                    func.sum(Agreement.amount)). \
                    outerjoin(
                    Agreement,
                    Order.unique_order_id == Agreement.unique_order_id). \
                    group_by(
                    Order.order_id, Order.amount,
                    Order.price, Order.exchange_address,
                    Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == False). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.account_address != account_address). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
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
                    Order.order_id, Order.amount, Order.price,
                    Order.exchange_address, Order.account_address,
                    func.sum(Agreement.amount)). \
                    outerjoin(
                    Agreement,
                    Order.unique_order_id == Agreement.unique_order_id). \
                    group_by(
                    Order.order_id, Order.amount,
                    Order.price, Order.exchange_address,
                    Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == True). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.account_address != account_address). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
                    all()

        else:
            if is_buy:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                orders = session.query(
                    Order.order_id, Order.amount, Order.price,
                    Order.exchange_address, Order.account_address,
                    func.sum(Agreement.amount)). \
                    outerjoin(
                    Agreement,
                    Order.unique_order_id == Agreement.unique_order_id). \
                    group_by(
                    Order.order_id, Order.amount,
                    Order.price, Order.exchange_address,
                    Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == False). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
                    all()

            else:  # 売注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以上
                orders = session.query(
                    Order.order_id, Order.amount, Order.price,
                    Order.exchange_address, Order.account_address,
                    func.sum(Agreement.amount)). \
                    outerjoin(
                    Agreement,
                    Order.unique_order_id == Agreement.unique_order_id). \
                    group_by(
                    Order.order_id, Order.amount,
                    Order.price, Order.exchange_address,
                    Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == True). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
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

        if 'account_address' in request_json:
            if not Web3.isAddress(request_json['account_address']):
                raise InvalidParameterError

        return request_json


# ------------------------------
# [クーポン]現在値取得
# ------------------------------
class CouponLastPrice(BaseResource):
    """
    Handle for endpoint: /v2/Market/LastPrice/Coupon
    """

    def on_post(self, req, res):
        LOG.info('v2.market_information.CouponLastPrice')

        request_json = CouponLastPrice.validate(req)

        ExchangeContract = Contract.get_contract(
            'IbetCouponExchange',
            config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS
        )

        price_list = []
        for token_address in request_json['address_list']:
            try:
                last_price = ExchangeContract.functions. \
                    lastPrice(to_checksum_address(token_address)).call()
            except Exception as e:
                LOG.error(e)
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
    """
    Handle for endpoint: /v2/Market/Tick/Coupon
    """

    def on_post(self, req, res):
        LOG.info('v2.market_information.CouponTick')

        request_json = CouponTick.validate(req)

        session = req.context["session"]

        tick_list = []
        # TokenごとにTickを取得
        for token_address in request_json['address_list']:
            token = to_checksum_address(token_address)
            tick = []
            try:
                entries = session.query(Agreement, Order). \
                    join(Order, Agreement.unique_order_id == Order.unique_order_id). \
                    filter(Order.token_address == token). \
                    filter(Agreement.status == 1). \
                    filter(Order.is_cancelled == False). \
                    order_by(desc(Agreement.settlement_timestamp)). \
                    all()

                for entry in entries:
                    block_timestamp_utc = entry.Agreement.settlement_timestamp
                    tick.append({
                        'block_timestamp': block_timestamp_utc.strftime('%Y/%m/%d %H:%M:%S'),
                        'buy_address': entry.Agreement.buyer_address,
                        'sell_address': entry.Agreement.seller_address,
                        'order_id': entry.Agreement.order_id,
                        'agreement_id': entry.Agreement.agreement_id,
                        'price': entry.Order.price,
                        'amount': entry.Agreement.amount
                    })
                tick_list.append({
                    'token_address': token_address,
                    'tick': tick
                })
            except Exception as e:
                LOG.error(e)
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
