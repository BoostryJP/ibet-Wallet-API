# -*- coding: utf-8 -*-
import json
import requests

from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.model import Contract, TokenTemplate
from app.errors import AppError, InvalidParameterError, DataNotExistsError
from app import config

LOG = log.get_logger()

# ------------------------------
# 板情報取得
# ------------------------------
class OrderList(BaseResource):
    '''
    Handle for endpoint: /v1/OrderList
    '''
    def on_post(self, req, res):
        LOG.info('v1.marketInformation.OrderList')
        session = req.context['session']

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        request_json = OrderList.validate(req)

        exchange_contract_address = config.IBET_EXCHANGE_CONTRACT_ADDRESS
        exchange_contract_abi = json.loads(config.IBET_EXCHANGE_CONTRACT_ABI)

        ExchangeContract = web3.eth.contract(
            address = exchange_contract_address,
            abi = exchange_contract_abi,
        )

        latest_orderid = ExchangeContract.functions.latestOrderId().call()

        order_list_tmp = []
        for num in range(latest_orderid):
            orderbook = ExchangeContract.functions.orderBook(num).call()

            if request_json['order_type'] == 'buy': #買注文の場合、指値以下の売注文を検索
                if orderbook[1] == request_json['token_address'] and \
                    orderbook[4] == False and \
                    orderbook[3] <= request_json['price']:
                    order_list_tmp.append({
                        'order_id':num,
                        'price':orderbook[3],
                        'amount':orderbook[2]
                    })
            else: #売注文の場合、指値以上の買注文を検索
                if orderbook[1] == request_json['token_address'] and \
                    orderbook[4] == True and \
                    orderbook[3] >= request_json['price']:
                    order_list_tmp.append({
                        'order_id':num,
                        'price':orderbook[3],
                        'amount':orderbook[2]
                    })

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
            'token_address': {'type': 'string', 'empty': False, 'required': True},
            'token_template':{'type': 'string', 'empty': False, 'required': True},
            'order_type':{'type': 'string', 'empty': False, 'required': True, 'allowed':['buy','sell']},
            'price':{'type': 'number', 'empty': False, 'required': True},
            'amount':{'type': 'number', 'empty': False, 'required': True},
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return request_json
