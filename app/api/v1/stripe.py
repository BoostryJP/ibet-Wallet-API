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
from app.model import StripeCharge
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

        # Todo DBにインサートする処理

        self.on_success(res, account_id)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
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
        request_json = CreateExternalAccount.validate(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context['address'])
        
        # アカウントアドレスに紐づくConnectアカウントの有無をDBで確認
        # （アカウントアドレスは重複していない前提）
        session = req.context['session']
        account_id = session.query(StripeCharge).filter(StripeCharge.exchange_address == address).all()[0] \
            .account_id

        # 紐づくConnectアカウントがない場合、Connectアカウントを作成する
        if account_id is None:
            description = 'Stripe Connected Account does not exists.'
            raise InvalidParameterError(description=description)

        # Connectアカウントに銀行口座を登録する
        try:
            stripe.Account.create_external_account(
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
        request_json = GetAccountInfo.validate(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context['address'])

        # アカウント情報を取得
        session = req.context["session"]
        stripe_account_info_list = {}
        account_info = session.query(StripeCharge).filter(StripeCharge.exchange_address == address).all()[0]
        stripe_account_info_list.append(account_info)

        self.on_success(res, stripe_account_info_list)

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
        request_json = CreateCustomer.validate(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context['address'])

        # アカウントアドレスに紐づくCustomerの有無をDBで確認
        # （アカウントアドレスはテーブル内でユニークである前提）
        session = req.context['session']
        customer_id = session.query(StripeCharge).filter(StripeCharge.exchange_address == address).all[0] \
            .customer_id

        # 紐づくCustomerがない場合、クレカ情報を紐付けたCustomerを作成
        if customer_id is None:
            description = "Customer for " + address
            try:
                customer = stripe.Customer.create(
                    description=description,
                    source=request_json['card_token']
                )['id']
            except stripe.Errors.api_connection_error:
                raise Exception(description='Failure to connect to Stripes API.')

        # 紐づくCustomerがある場合、クレカ情報を更新する
        else:
            customer = stripe.Customer.modify(
                customer_id,
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

