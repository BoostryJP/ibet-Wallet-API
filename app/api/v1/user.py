# -*- coding: utf-8 -*-
import json
import requests

from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import AppError, InvalidParameterError
from app import config

LOG = log.get_logger()

# ------------------------------
# 決済用口座登録状況参照
# ------------------------------
class PaymentAccount(BaseResource):
    '''
    Handle for endpoint: /v1/User/PaymentAccount
    '''
    def on_get(self, req, res):
        LOG.info('v1.User.PaymentAccount')

        request_json = PaymentAccount.validate(req)

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))

        # WhiteList Contract
        whitelist_contract_address = config.WHITE_LIST_CONTRACT_ADDRESS
        whitelist_contract_abi = json.loads(config.WHITE_LIST_CONTRACT_ABI)
        WhiteListContract = web3.eth.contract(
            address = whitelist_contract_address,
            abi = whitelist_contract_abi,
        )

        account_info = WhiteListContract.functions.payment_accounts(
            to_checksum_address(request_json['account_address']),
            to_checksum_address(request_json['agent_address'])
        ).call()

        if account_info[0] == '0x0000000000000000000000000000000000000000':
            response_json = {
                'account_address': request_json['account_address'],
                'agent_address': request_json['agent_address'],
                'approval_status': 0
            }
        else:
            response_json = {
                'account_address': account_info[0],
                'agent_address': account_info[1],
                'approval_status': account_info[3]
            }

        self.on_success(res, response_json)

    @staticmethod
    def validate(req):
        request_json = {'account_address': req.get_param('account_address'),
                'agent_address': req.get_param('agent_address')}

        validator = Validator({
            'account_address': {'type': 'string', 'empty': False, 'required': True},
            'agent_address': {'type': 'string', 'empty': False, 'required': True}
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(request_json['account_address']):
            raise InvalidParameterError

        if not Web3.isAddress(request_json['agent_address']):
            raise InvalidParameterError

        return request_json


# ------------------------------
# 名簿用個人情報参照
# ------------------------------
class PersonalInfo(BaseResource):
    '''
    Handle for endpoint: /v1/User/PersonalInfo
    '''
    def on_get(self, req, res):
        LOG.info('v1.User.PersonalInfo')

        request_json = PersonalInfo.validate(req)

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))

        # WhiteList Contract
        personalinfo_contract_address = config.PERSONAL_INFO_CONTRACT_ADDRESS
        personalinfo_contract_abi = json.loads(config.PERSONAL_INFO_CONTRACT_ABI)
        PersonalInfoContract = web3.eth.contract(
            address = personalinfo_contract_address,
            abi = personalinfo_contract_abi,
        )

        info = PersonalInfoContract.functions.personal_info(
            to_checksum_address(request_json['account_address']),
            to_checksum_address(request_json['owner_address'])
        ).call()

        if info[0] == '0x0000000000000000000000000000000000000000':
            response_json = {
                'account_address': request_json['account_address'],
                'owner_address': request_json['owner_address'],
                'registered': False
            }
        else:
            response_json = {
                'account_address': info[0],
                'agent_address': info[1],
                'registered': True
            }

        self.on_success(res, response_json)

    @staticmethod
    def validate(req):
        request_json = {'account_address': req.get_param('account_address'),
                'owner_address': req.get_param('owner_address')}

        validator = Validator({
            'account_address': {'type': 'string', 'empty': False, 'required': True},
            'owner_address': {'type': 'string', 'empty': False, 'required': True}
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(request_json['account_address']):
            raise InvalidParameterError

        if not Web3.isAddress(request_json['owner_address']):
            raise InvalidParameterError

        return request_json
