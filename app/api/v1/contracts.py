# -*- coding: utf-8 -*-
from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from web3 import Web3

from app import log
from app.api.common import BaseResource
from app.model import Contract, TokenTemplate
from app.errors import AppError, InvalidParameterError, DataNotExistsError

LOG = log.get_logger()

# ------------------------------
# トークン発行
# ------------------------------
class ContractDeploy(BaseResource):
    '''
    Handle for endpoint: /v1/Contract
    '''
    def on_post(self, req, res):
        LOG.info('v1.contracts.ContractDeploy')
        session = req.context['session']

        request_json = ContractDeploy.validate(req)
        template_id = request_json['template_id']
        raw_tx_hex = request_json['raw_tx_hex']

        web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
        tx_hash = web3.eth.sendRawTransaction(raw_tx_hex)

        contract = Contract()
        contract.template_id = template_id
        contract.tx_hash = tx_hash
        contract.admin_address = None
        contract.contract_address = None
        session.add(contract)

        self.on_success(res)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'template_id': {'type': 'integer', 'empty': False, 'required': True},
            'raw_tx_hex': {'type': 'string', 'empty': False, 'required': True}
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return request_json


# ------------------------------
# 発行済みトークン一覧
# ------------------------------
class MyContracts(BaseResource):
    '''
    Handle for endpoint: /v1/MyContracts
    '''
    def on_post(self, req, res):
        LOG.info('v1.contracts.MyContracts')
        session = req.context['session']

        request_json = MyContracts.validate(req)
        address_tuple = tuple(request_json['address_list'])

        contract_db_list = session.query(Contract).filter(
            Contract.admin_address.in_(address_tuple)
        ).all()

        mycontracts = []
        for contract_db in contract_db_list:
            row = contract_db.to_dict()

            try:
                token_template = TokenTemplate.find_one(
                    session, row['template_id']
                ).to_dict()
            except NoResultFound:
                raise DataNotExistsError()

            web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
            token_contract = web3.eth.contract(
                address=row['contract_address'],
                abi = token_template['abi'],
                bytecode = token_template['bytecode'],
                bytecode_runtime = token_template['bytecode_runtime']
            )
            token_name = token_contract.functions.name().call()

            mycontracts.append({
                'admin_address': row['admin_address'],
                'contract_address': row['contract_address'],
                'template_name': token_template['template_name'],
                'token_name': token_name
            })

        self.on_success(res, mycontracts)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'address_list': {
                'type': 'list',
                'schema': {'type': 'string'},
                'empty': False,
                'required': True
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return request_json
