# -*- coding: utf-8 -*-
from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from web3 import Web3

from app import log
from app.api.common import BaseResource
from app.model import Contract
from app.errors import AppError, InvalidParameterError, DataNotExistsError

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

        web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
        nonce = web3.eth.getTransactionCount(eth_address)
        gasprice = web3.eth.gasPrice

        transaction_count = {'nonce':nonce, 'gasprice':gasprice}

        self.on_success(res, transaction_count)
