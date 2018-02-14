# -*- coding: utf-8 -*-
from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.model import Contract
from app.errors import AppError, InvalidParameterError, DataNotExistsError
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

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        nonce = web3.eth.getTransactionCount(to_checksum_address(eth_address))
        gasprice = web3.eth.gasPrice
        chainid = config.WEB3_CHAINID

        eth_info = {'nonce':nonce, 'gasprice':gasprice, 'chainid':chainid}

        self.on_success(res, eth_info)
