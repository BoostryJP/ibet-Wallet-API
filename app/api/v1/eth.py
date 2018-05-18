# -*- coding: utf-8 -*-
import time

from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import AppError, InvalidParameterError, EthValueError
from app import config

LOG = log.get_logger()

# ------------------------------
# nonce取得
# ------------------------------
class GetTransactionCount(BaseResource):
    '''
    Handle for endpoint: /v1/Eth/TransactionCount/{eth_address}
    '''
    def on_get(self, req, res, eth_address):
        LOG.info('v1.Eth.GetTransactionCount')

        try:
            eth_address = to_checksum_address(eth_address)
        except ValueError:
            raise InvalidParameterError

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        nonce = web3.eth.getTransactionCount(to_checksum_address(eth_address))
        gasprice = web3.eth.gasPrice
        chainid = config.WEB3_CHAINID

        eth_info = {'nonce':nonce, 'gasprice':gasprice, 'chainid':chainid}

        self.on_success(res, eth_info)

# ------------------------------
# sendRawTransaction
# ------------------------------
class SendRawTransaction(BaseResource):
    '''
    Handle for endpoint: /v1/Eth/SendRawTransaction
    '''
    def on_post(self, req, res):
        LOG.info('v1.Eth.SendRawTransaction')

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        if config.WEB3_CHAINID == '4' or '2017':
            from web3.middleware import geth_poa_middleware
            web3.middleware_stack.inject(geth_poa_middleware, layer=0)

        request_json = SendRawTransaction.validate(req)
        raw_tx_hex_list = request_json['raw_tx_hex_list']

        result = []

        for i, raw_tx_hex in enumerate(raw_tx_hex_list):
            try:
                tx_hash = web3.eth.sendRawTransaction(raw_tx_hex)
            except ValueError as e:
                result.append({
                    'id': i+1,
                    'status': 0,
                })
                continue

            try:
                tx = web3.eth.waitForTransactionReceipt(tx_hash, 30)
            except:
                # NOTE: eth.waitForTransactionReceiptは本来はExceptionではなくNoneを返す仕様だが、
                #       バグでExceptionを返すようになっているため対応しておく
                tx = None
                pass

            if tx is None:
                result.append({
                    'id': i+1,
                    'status': 0,
                })
            else:
                result.append({
                    'id': i+1,
                    'status': tx['status'],
                })

        self.on_success(res, result)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'raw_tx_hex_list': {
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

        return request_json
