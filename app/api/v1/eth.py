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

        request_json = SendRawTransaction.validate(req)
        raw_tx_hex_list = request_json['raw_tx_hex_list']

        for raw_tx_hex in raw_tx_hex_list:
            try:
                tx_hash = web3.eth.sendRawTransaction(raw_tx_hex)
            except ValueError as e:
                reason = e.args[0]
                raise EthValueError(reason['code'],reason['message'])

            count = 0
            tx = None
            while True:
                try:
                    tx = web3.eth.getTransactionReceipt(tx_hash)
                except:
                    time.sleep(1)

                count += 1
                if tx is not None or count > 30:
                    break

        self.on_success(res)

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
