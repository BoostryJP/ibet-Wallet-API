# -*- coding: utf-8 -*-
import json
import math

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
from app.model import StripeCharge, StripeAccount, Agreement
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
        address = to_checksum_address(req.context["address"])
        # DBの存在チェック
        session = req.context["session"]
        raw = session.query(StripeAccount).filter(StripeAccount.account_address == address).first()

        # すでに存在する場合はUpdate、存在しない場合はCreateしてDBインサート
        try:
            if raw is not None and raw.account_id != "":
                stripe.Account.modify(
                  raw.account_id,
                  account_token=request_json['account_token']
                )
                response_data = {'stripe_account_id': raw.account_id}
            elif raw is not None and raw.account_id == "":
                account = stripe.Account.create(
                    type='custom',
                    country='JP',
                    account_token=request_json['account_token']
                )
                # DBのaccount_idをアップデート
                raw.account_id = account.id
                session.commit()
                response_data = {'stripe_account_id': account.id}
            else:
                account = stripe.Account.create(
                    type='custom',
                    country='JP',
                    account_token=request_json['account_token']
                )
                account_id = account.id
                # DBに新規インサートする処理
                stripe_account = StripeAccount()
                stripe_account.account_address = address
                stripe_account.account_id = account.id
                stripe_account.customer_id = ""
                session.add(stripe_account)
                session.commit()
                response_data = {'stripe_account_id': account.id}

        except stripe.error.APIConnectionError as e:
            raise AppError(description='Failure to connect to Stripes API.')
        except stripe.error.AuthenticationError as e:
            raise AppError(description='Failure to properly authenticate yourself in the request.')
        except stripe.error.InvalidRequestError as e:
            raise AppError(description='Invalid request errors arise when your request has invalid parameters.')
        except stripe.error.RateLimitError as e:
            raise AppError(description='Too many requests hit the API too quickly.')

        self.on_success(res, response_data)

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
        address = to_checksum_address(req.context["address"])
        
        # アカウントアドレスに紐づくConnectアカウントの有無をDBで確認
        # （アカウントアドレスは重複していない前提）
        session = req.context['session']
        raw = session.query(StripeAccount).filter(StripeAccount.account_address == address).first()

        # 紐づくConnectアカウントがない場合、Connectアカウントを空で作成した上でexternalAccountの登録を行う
        try:
            if raw is not None and raw.account_id != "":
                stripe.Account.modify(
                  raw.account_id,
                  external_account=request_json['bank_token']
                )
                response_data = {'stripe_account_id': raw.account_id}
            elif raw is not None and raw.account_id == "":
                account = stripe.Account.create(
                    type='custom',
                    country='JP',
                    external_account=request_json['bank_token']
                )
                # DBのaccount_idをアップデート
                raw.account_id = account.id
                session.commit()
                response_data = {'stripe_account_id': account.id}
            else:
                account = stripe.Account.create(
                    type='custom',
                    country='JP',
                    external_account=request_json['bank_token']
                )
                account_id = account.id
                # DBに新規インサートする処理
                stripe_account = StripeAccount()
                stripe_account.account_address = address
                stripe_account.account_id = account.id
                stripe_account.customer_id = ""
                session.add(stripe_account)
                session.commit()
                response_data = {'stripe_account_id': account.id}
        except stripe.error.APIConnectionError as e:
            raise AppError(description='Failure to connect to Stripes API.')
        except stripe.error.AuthenticationError as e:
            raise AppError(description='Failure to properly authenticate yourself in the request.')
        except stripe.error.InvalidRequestError as e:
            raise AppError(description='Invalid request errors arise when your request has invalid parameters.')
        except stripe.error.RateLimitError as e:
            raise AppError(description='Too many requests hit the API too quickly.')

        self.on_success(res, response_data)

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
        account_info = session.query(StripeAccount).filter(StripeAccount.exchange_address == address).all()[0]
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
        address = to_checksum_address(req.context["address"])

        # アカウントアドレスに紐づくCustomerの有無をDBで確認
        # （アカウントアドレスはテーブル内でユニークである前提）
        session = req.context['session']
        raw = session.query(StripeAccount).filter(StripeAccount.account_address == address).first()

        # 紐づくCustomerがない場合、クレカ情報を紐付けたCustomerを作成
        try:
            if raw is not None and raw.customer_id != "":
                stripe.Customer.modify(
                    raw.customer_id,
                    source=request_json['card_token']
                )
                response_data = {'stripe_customer_id': raw.customer_id}
            elif raw is not None and raw.customer_id == "":
                description = "Customer for " + address
                customer_id = stripe.Customer.create(
                    description=description,
                    source=request_json['card_token']
                )['id']
                # DBのcustomer_idをアップデート
                raw.customer_id = customer_id
                session.commit()
                response_data = {'stripe_customer_id': customer_id}
            else:
                description = "Customer for " + address
                customer_id = stripe.Customer.create(
                    description=description,
                    source=request_json['card_token']
                )['id']
                # DBに新規インサート
                stripe_account = StripeAccount()
                stripe_account.account_address = address
                stripe_account.account_id = ""
                stripe_account.customer_id = customer_id
                session.add(stripe_account)
                session.commit()
                response_data = {'stripe_customer_id': customer_id}
        except stripe.error.APIConnectionError as e:
            raise AppError(description='Failure to connect to Stripes API.')
        except stripe.error.AuthenticationError as e:
            raise AppError(description='Failure to properly authenticate yourself in the request.')
        except stripe.error.InvalidRequestError as e:
            raise AppError(description='Invalid request errors arise when your request has invalid parameters.')
        except stripe.error.RateLimitError as e:
            raise AppError(description='Too many requests hit the API too quickly.')

        self.on_success(res, response_data)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'card_token': {
                'type': 'string',
                'schema': {'type': 'string'},
                'empty': False,
                'required': True
            }
        })
        session = req.context["session"]
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

        session = req.context["session"]

        # 入力値チェック
        request_json = Charge.validate(req)
        buyer_address = to_checksum_address(req.context["address"])

        # リクエストから情報を抽出
        order_id = request_json['order_id']
        agreement_id = request_json['agreement_id']

        # 手数料と収入の計算（収納代行の手数料率を百分率で環境変数に設定）
        amount = request_json['amount']
        exchange_fee = math.ceil(request_json['amount'] * config.STRIPE_FEE)
        charge_amount = amount - exchange_fee

        # 約定テーブルから情報を取得
        agreement = session.query(Agreement).\
            filter(Agreement.order_id == order_id,
                   Agreement.agreement_id == agreement_id).first()

        # Stripeテーブルから情報を取得
        stripe_row = session.query(StripeCharge).\
            filter(StripeCharge.account_address == buyer_address).first()

        # リクエストの金額が正しいか確認
        if not request_json['amount'] == agreement.amount:
            raise InvalidParameterError

        # 新しく課金オブジェクトを作成する
        try:
            charge = stripe.Charge.create(
                customer=stripe_row.customer_id,
                amount=amount,
                currency="jpy",
                destination={
                    # 子アカウントへ配分する金額
                    "amount": charge_amount,
                    # 子アカウントを指定
                    "account": stripe_row.account_id
                }
            )
        except stripe.Errors.api_connection_error:
            raise Exception(description='Failure to connect to Stripes API.')

        receipt_url = {'receipt_url': charge['receipt_url']}

        self.on_success(res, receipt_url)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'order_id': {
                'type': 'int',
                'schema': {'type': 'int'},
                'empty': False,
                'required': True
            },
            'agreement_id': {
                'type': 'int',
                'schema': {'type': 'int'},
                'empty': False,
                'required': True
            },
            'amount': {
                'type': 'int',
                'schema': {'type': 'int'},
                'empty': False,
                'required': True
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(req.context['address']):
            raise InvalidParameterError

        return validator.document
