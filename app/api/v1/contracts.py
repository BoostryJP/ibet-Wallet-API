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
# コントラクトデプロイ
# ------------------------------
class ContractDeploy(BaseResource):
    '''
    Handle for endpoint: /v1/Contract
    '''
    def on_post(self, req, res):
        LOG.info('v1.contracts.ContractDeploy')
        session = req.context['session']

        request_json = ContractDeploy.validate(req)
        admin_address = request_json['eth_address']
        template_id = request_json['template_id']
        raw_tx_hex = request_json['raw_tx_hex']

        contract = Contract()

        web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

        tx_hash = web3.eth.sendRawTransaction(raw_tx_hex)

        contract.admin_address = admin_address
        contract.template_id = template_id
        contract.tx_hash = tx_hash

        session.add(contract)
        self.on_success(res)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'eth_address': {'type': 'string', 'empty': False, 'required': True},
            'template_id': {'type': 'integer', 'empty': False, 'required': True},
            'raw_tx_hex': {'type': 'string', 'empty': False, 'required': True}
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return request_json
