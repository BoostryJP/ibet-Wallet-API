# -*- coding: utf-8 -*-
import json
import requests
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=+9), 'JST')

from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.model import TokenTemplate, Order, Agreement
from app.errors import AppError, InvalidParameterError, DataNotExistsError
from app import config

LOG = log.get_logger()

# ------------------------------
# 板情報取得
# ------------------------------
class OrderBook(BaseResource):
    '''
    Handle for endpoint: /v1/OrderBook
    '''
    def on_post(self, req, res):
        LOG.info('v1.marketInformation.OrderBook')

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        session = req.context['session']

        # 入力値チェック
        request_json = OrderBook.validate(req)

        # 注文を抽出
        is_buy = request_json['order_type'] == 'sell' # 相対注文が買い注文かどうか
        # 抽出条件) 1. Token Addressが指定したものと同じ
        #          2. クライアントが買い注文をしたい場合 => 売り注文を抽出
        #                         売り注文をしたい場合 => 買い注文を抽出
        #          3. 未キャンセル
        #          4. 残注文あり
        #          5. 指値以下
        orders = session.query(Order, func.sum(Agreement.amount)).\
                 outerjoin(Agreement, Order.id == Agreement.order_id).\
                 group_by(Order.id).\
                 filter(Order.token_address == request_json['token_address']).\
                 filter(Order.is_buy == is_buy).\
                 filter(Order.is_cancelled == False).\
                 filter(Order.price <= request_json['price']).\
                 all()

        # レスポンス用の注文一覧を構築
        order_list_tmp = []
        for (order, agreement_amount) in orders:
            # 残存注文数量 = 発注数量 - 約定済み数量
            amount = order.amount
            if not(agreement_amount is None):
                amount -= int(agreement_amount)

            # 残注文ありの注文のみを抽出する
            if amount <= 0:
                continue
            
            order_list_tmp.append({
                'order_id': order.id,
                'price': order.price,
                'amount': amount,
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
            'account_address': {'type': 'string'},
            'token_address': {'type': 'string', 'empty': False, 'required': True},
            'order_type':{'type': 'string', 'empty': False, 'required': True, 'allowed':['buy','sell']},
            'price':{'type': 'number', 'empty': False, 'required': True},
            'amount':{'type': 'number', 'empty': False, 'required': True},
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(request_json['token_address']):
            raise InvalidParameterError

        return request_json


# ------------------------------
# 現在値取得
# ------------------------------
class LastPrice(BaseResource):
    '''
    Handle for endpoint: /v1/LastPrice
    '''
    def on_post(self, req, res):
        LOG.info('v1.marketInformation.LastPrice')

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))

        request_json = LastPrice.validate(req)

        exchange_contract_address = config.IBET_EXCHANGE_CONTRACT_ADDRESS
        exchange_contract_abi = json.loads(config.IBET_EXCHANGE_CONTRACT_ABI)

        ExchangeContract = web3.eth.contract(
            address = to_checksum_address(exchange_contract_address),
            abi = exchange_contract_abi,
        )

        price_list = []
        for token_address in request_json['address_list']:
            try:
                last_price = ExchangeContract.functions.lastPrice(to_checksum_address(token_address)).call()
            except:
                last_price = 0
            price_list.append({'token_address':token_address, 'last_price':last_price})

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
# 歩み値取得
# ------------------------------
class Tick(BaseResource):
    '''
    Handle for endpoint: /v1/Tick
    '''
    def on_post(self, req, res):
        LOG.info('v1.marketInformation.Tick')

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        if config.WEB3_CHAINID == '4' or '2017':
            from web3.middleware import geth_poa_middleware
            web3.middleware_stack.inject(geth_poa_middleware, layer=0)

        request_json = Tick.validate(req)

        exchange_contract_address = config.IBET_EXCHANGE_CONTRACT_ADDRESS
        exchange_contract_abi = json.loads(config.IBET_EXCHANGE_CONTRACT_ABI)

        ExchangeContract = web3.eth.contract(
            address = to_checksum_address(exchange_contract_address),
            abi = exchange_contract_abi,
        )

        tick_list = []
        for token_address in request_json['address_list']:
            tick = []
            try:
                event_filter = ExchangeContract.eventFilter(
                    'Agree', {
                        'filter':{'tokenAddress':to_checksum_address(token_address)},
                        'fromBlock':'earliest'
                    }
                )
                entries = event_filter.get_all_entries()
                for entry in entries:
                    tick.append({
                        'block_timestamp':datetime.fromtimestamp(web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST).strftime("%Y/%m/%d %H:%M:%S"),
                        'buy_address':entry['args']['buyAddress'],
                        'sell_address':entry['args']['sellAddress'],
                        'order_id':entry['args']['orderId'],
                        'agreement_id':entry['args']['agreementId'],
                        'price':entry['args']['price'],
                        'amount':entry['args']['amount'],
                    })
                tick_list.append({'token_address':token_address, 'tick':tick})
            except:
                tick_list = []

        self.on_success(res,tick_list)

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
