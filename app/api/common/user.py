# -*- coding: utf-8 -*-
import json
import os

from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from web3 import Web3
from web3.middleware import geth_poa_middleware

from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError, DataNotExistsError
from app import config
from app.contracts import Contract

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)

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

        PaymentGatewayContract = Contract.get_contract(
            'PaymentGateway', config.PAYMENT_GATEWAY_CONTRACT_ADDRESS)

        # 口座登録・承認状況を参照
        account_info = PaymentGatewayContract.functions.payment_accounts(
            to_checksum_address(request_json['account_address']),
            to_checksum_address(request_json['agent_address'])
        ).call()

        # 最新版の利用規約の同意ステータスを参照
        agreement_status = PaymentGatewayContract.functions.termAgreementStatus(
            to_checksum_address(request_json['account_address']),
            to_checksum_address(request_json['agent_address'])
        ).call()

        if account_info[0] == '0x0000000000000000000000000000000000000000':
            response_json = {
                'account_address': request_json['account_address'],
                'agent_address': request_json['agent_address'],
                'approval_status': 0,
                'agreement_status': agreement_status
            }
        else:
            response_json = {
                'account_address': account_info[0],
                'agent_address': account_info[1],
                'approval_status': account_info[3],
                'agreement_status': agreement_status
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

        # PersonalInfo Contract
        PersonalInfoContract = Contract.get_contract(
            'PersonalInfo', config.PERSONAL_INFO_CONTRACT_ADDRESS)

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
                'owner_address': info[1],
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

 # ------------------------------
# 住所検索（郵便番号）
# ------------------------------
class StreetAddress(BaseResource):
    '''
    Handle for endpoint: /v1/User/StreetAddress/{postal_code}
    '''
    def on_get(self, req, res, postal_code):
        LOG.info('v1.User.StreetAddress')

        postal_code = StreetAddress.validate(postal_code)
        try:
            street_address_list = json.load(open('data/zip_code/%s/%s.json' % (postal_code[0:3], postal_code), 'r'))
        except Exception as err:
            raise DataNotExistsError('postal_code: %s' % postal_code)

        self.on_success(res, street_address_list)

    @staticmethod
    def validate(postal_code):
        request = {'postal_code': postal_code}

        validator = Validator({
            'postal_code': {'type': 'string', 'regex': '^[0-9]{7}$'}
        })

        if not validator.validate(request):
            raise InvalidParameterError('postal_code: %s' % postal_code)

        return postal_code