# -*- coding: utf-8 -*-
import json
import falcon
from cerberus import Validator
import sqlalchemy
from web3 import Web3
from eth_utils import to_checksum_address
import boto3

from app import log
from app.api.common import BaseResource
from app.errors import AppError, InvalidParameterError, InvalidCardError, \
    DoubleChargeError
from app.utils.hooks import VerifySignature
from app.model import OmiseCharge, OmiseChargeStatus
from app import config

import stripe
stripe.api_key = config.STRIPE_SECRET

LOG = log.get_logger()

# ------------------------------
# [Stripe]Connected Account(ウォレット利用者)登録
# ------------------------------
class CreateAccount(BaseResource):
    '''
    Handle for endpoint: /v1/Stripe/CreateAccount/
    '''
    @falcon.before(VerifySignature())
    def on_post(self, req, res):
        LOG.info('v1.Stripe.CreateAccount')

        # 入力値チェック
        request_json = CreateAccount.validate(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context['address'])

        # 新しくConnectアカウントを作成する
        try:
            account = stripe.Account.create(
                type='custom',
                account_token=request_json['account_token'],
                requested_capabilities=['card_payments']
            )
        except stripe.Errors.api_connection_error:
            raise Exception(description='Failure to connect to Stripes API.')
        # except stripe.Errors.api_error:
        #     raise Exception(description='Stripe API Error.')
        # except stripe.Errors.authentication_error:
        #     raise Exception(description='Failure to properly authenticate yourself in the request.')
        # except stripe.Errors.invalid_request_error:
        #     raise Exception(description='Invalid request errors arise when your request has invalid parameters.')
        # except stripe.Errors.rate_limit_error:
        #     raise Exception(description='Too many requests hit the API too quickly.')
        # except stripe.Errors.validation_error:
        #     raise Exception(description="failing to validate fields")

        account_id = {'account_id': account.id}

        self.on_success(res, account_id)

        @staticmethod
        def validate(req):
            request_json = req.context['data']
            if request_json is None:
                raise InvalidParameterError

            validator = Validator({
                'account_address': {
                    'type': 'string',
                    'schema': {'type': 'string'},
                    'empty': False,
                    'required': True
                },
                'account_token': {
                    'type': 'string',
                    'schema': {'type': 'string'},
                    'empty': False,
                    'required': True
                }
            })

            if not validator.validate(request_json):
                raise InvalidParameterError(validator.errors)

            if not Web3.isAddress(req.context['address']):
                raise InvalidParameterError

            return validator.document


# ------------------------------
# [Stripe]External Account(銀行口座)登録
# ------------------------------
class CreateExternalAccount(BaseResource):
    '''
    Handle for endpoint: /v1/Stripe/CreateExternalAccount
    '''
    @falcon.before(VerifySignature())
    def on_post(self, req, res):
        LOG.info('v1.Stripe.CreateExternalAccount')

        # 入力値チェック
        request_json = CreateAccount.validate(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context['address'])

        # アカウントアドレスに紐づくConnectアカウントの有無をDBで確認

        # TODO DB select
        account_id = None

        # 紐づくConnectアカウントがない場合、Connectアカウントを作成する
        if account_id is None:
            account_id = CreateAccount()

        # Connectアカウントに銀行口座を登録する
        try:
            external_account = stripe.Account.create_external_account(
                account_id,
                external_account=request_json['bank_token']
            )
        except stripe.Errors.api_connection_error:
            raise Exception(description='Failure to connect to Stripes API.')

        self.on_success(res)

        @staticmethod
        def validate(req):
            request_json = req.context['data']
            if request_json is None:
                raise InvalidParameterError

            validator = Validator({
                'account_address': {
                    'type': 'string',
                    'schema': {'type': 'string'},
                    'empty': False,
                    'required': True
                },
                'bank_token': {
                    'type': 'string',
                    'schema': {'type': 'string'},
                    'empty': False,
                    'required': True
                }
            })

            if not validator.validate(request_json):
                raise InvalidParameterError(validator.errors)

            if not Web3.isAddress(req.context['address']):
                raise InvalidParameterError

            return validator.document


# ------------------------------
# [Stripe]Connected Accountの取得
# ------------------------------
class GetAccountInfo(BaseResource):
    '''
    Handle for endpoint: /v1/Stripe/GetAccountInfo/
    '''
    @falcon.before(VerifySignature())
    def on_post(self, req, res):
        LOG.info('v1.Stripe.GetAccountInfo')

        # 入力値チェック
        request_json = CreateAccount.validate(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context['address'])

        # Connectアカウント情報をDBから取得
        # TODO DB select
        response_json = None

        self.on_success(res, response_json)

        @staticmethod
        def validate(req):
            request_json = req.context['data']
            if request_json is None:
                raise InvalidParameterError

            validator = Validator({
                'account_address_list': {
                    'type': 'list',
                    'schema': {'type': 'string'},
                    'empty': False,
                    'required': True
                }
            })

            if not validator.validate(request_json):
                raise InvalidParameterError(validator.errors)

            if not Web3.isAddress(req.context['address']):
                raise InvalidParameterError

            return validator.document


# ------------------------------
# [Stripe]Customer(顧客)とカード情報の登録
# ------------------------------
class CreateCustomer(BaseResource):
    '''
    Handle for endpoint: /v1/Stripe/CreateCustomer/
    '''
    @falcon.before(VerifySignature())
    def on_post(self, req, res):
        LOG.info('v1.Stripe.CreateCustomer')

        # 入力値チェック
        request_json = CreateAccount.validate(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context['address'])

        # アカウントアドレスに紐づくCustomerの有無をDBで確認
        # TODO DB select
        exists_customer_id = None

        # 紐づくCustomerがない場合、クレカ情報を紐付けたCustomerを作成
        try:
            account = stripe.Account.create(
                type='custom',
                account_token=request_json['account_token'],
                requested_capabilities=['card_payments']
            )
        except stripe.Errors.api_connection_error:
            raise Exception(description='Failure to connect to Stripes API.')


        if exists_customer_id is None:
            description = "Customer for " + address
            try:
                customer = stripe.Customer.create(
                    description=description,
                    source = request_json['card_token']
                )['id']
            except stripe.Errors.api_connection_error:
                raise Exception(description='Failure to connect to Stripes API.')
        # 紐づくCustomerがある場合、クレカ情報を更新する
        else:
            customer = stripe.Customer.modify(
                exists_customer_id,
                source=request_json['card_token']
            )['id']

        stripe_customer_id = customer.id


        self.on_success(res, stripe_customer_id)

        @staticmethod
        def validate(req):
            request_json = req.context['data']
            if request_json is None:
                raise InvalidParameterError

            validator = Validator({
                'account_address': {
                    'type': 'string',
                    'schema': {'type': 'string'},
                    'empty': False,
                    'required': True
                },
                'card_token': {
                    'type': 'string',
                    'schema': {'type': 'string'},
                    'empty': False,
                    'required': True
                }
            })

            if not validator.validate(request_json):
                raise InvalidParameterError(validator.errors)

            if not Web3.isAddress(req.context['address']):
                raise InvalidParameterError

            return validator.document


# ------------------------------
# [Stripe]課金
# ------------------------------
class Charge(BaseResource):
    '''
    Handle for endpoint: /v1/Stripe/Charge/
    '''
    @falcon.before(VerifySignature())
    def on_post(self, req, res):
        LOG.info('v1.Stripe.Charge')

        # 入力値チェック
        request_json = CreateAccount.validate(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context['address'])

        #########
        # TODO
        #########

