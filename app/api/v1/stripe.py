# -*- coding: utf-8 -*-
import json
import math

import falcon
from cerberus import Validator
from web3 import Web3
from eth_utils import to_checksum_address
from app.contracts import Contract
import boto3

from app import log
from app.api.common import BaseResource
from app.errors import AppError, InvalidParameterError, InvalidCardError, \
    DoubleChargeError
from app.utils.hooks import VerifySignature
from app.model import StripeCharge, StripeAccount, Agreement, StripeChargeStatus, AgreementStatus
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
        except stripe.error.RateLimitError as e:
            raise AppError(description='[stripe]Too many requests hit the API too quickly.')
        except stripe.error.InvalidRequestError as e:
            raise AppError(description='[stripe]Invalid request errors arise when your request has invalid parameters.')
        except stripe.error.AuthenticationError as e:
            raise AppError(description='[stripe]Failure to properly authenticate yourself in the request.')
        except stripe.error.APIConnectionError as e:
            raise AppError(description='[stripe]Failure to connect to Stripes API.')
        except stripe.error.StripeError as e:
            raise AppError(description='[stripe]Something happen on Stripe')

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
        except stripe.error.RateLimitError as e:
            raise AppError(description='[stripe]Too many requests hit the API too quickly.')
        except stripe.error.InvalidRequestError as e:
            raise AppError(description='[stripe]Invalid request errors arise when your request has invalid parameters.')
        except stripe.error.AuthenticationError as e:
            raise AppError(description='[stripe]Failure to properly authenticate yourself in the request.')
        except stripe.error.APIConnectionError as e:
            raise AppError(description='[stripe]Failure to connect to Stripes API.')
        except stripe.error.StripeError as e:
            raise AppError(description='[stripe]Something happen on Stripe')

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
        except stripe.error.RateLimitError as e:
            raise AppError(description='[stripe]Too many requests hit the API too quickly.')
        except stripe.error.InvalidRequestError as e:
            raise AppError(description='[stripe]Invalid request errors arise when your request has invalid parameters.')
        except stripe.error.AuthenticationError as e:
            raise AppError(description='[stripe]Failure to properly authenticate yourself in the request.')
        except stripe.error.APIConnectionError as e:
            raise AppError(description='[stripe]Failure to connect to Stripes API.')
        except stripe.error.StripeError as e:
            raise AppError(description='[stripe]Something happen on Stripe')

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
        exchange_address = to_checksum_address(request_json['exchange_address'])

        # 手数料と収入の計算（収納代行の手数料率を百分率で環境変数に設定）
        amount = request_json['amount']
        exchange_fee = math.ceil(request_json['amount'] * float(config.STRIPE_FEE))
        charge_amount = amount - exchange_fee

        # 約定テーブルから情報を取得
        agreement = session.query(Agreement).\
            filter(Agreement.order_id == order_id,
                   Agreement.agreement_id == agreement_id).first()
        # 約定テーブルに情報がない場合、入力値エラー
        if agreement is None:
            description = 'Agreement not found.'
            raise InvalidParameterError(description=description)

        # StripeAccountテーブルから買手の情報を取得
        buyer = session.query(StripeAccount).\
            filter(StripeAccount.account_address == buyer_address).first()
        # StripeAccountテーブルに情報がない場合、入力値エラー
        if buyer is None:
            description = 'Buyer not found.'
            raise InvalidParameterError(description=description)

        # StripeAccountテーブルから売手の情報を取得
        seller = session.query(StripeAccount). \
            filter(StripeAccount.account_address == agreement.seller_address).first()
        # StripeAccountテーブルに情報がない場合、入力値エラー
        if seller is None:
            description = 'Seller not found.'
            raise InvalidParameterError(description=description)

        # リクエストの金額が正しいか確認
        if not request_json['amount'] == agreement.amount:
            description = 'The amount ' + agreement.amount + ' is invalid.'
            raise InvalidParameterError(description=description)

        # Charge（課金）状態の取得
        stripe_charge = session.query(StripeCharge). \
            filter(StripeCharge.exchange_address == exchange_address). \
            filter(StripeCharge.order_id == order_id). \
            filter(StripeCharge.agreement_id == agreement_id). \
            first()

        if stripe_charge is not None:  # 既にオペレーションを1回以上実施している場合
            # 二重課金のチェック
            #  - Charge状態が[PROCESSING]、[SUCCESS]の場合はエラー
            #  - Charge状態が[ERROR]の場合は[PROCESSING]に更新（この時点でcommitする）
            if stripe_charge.status == StripeChargeStatus.PROCESSING.value or \
                    stripe_charge.status == StripeChargeStatus.SUCCESS.value:
                raise DoubleChargeError(description='double charge')
            elif stripe_charge.status == StripeChargeStatus.ERROR.value:
                stripe_charge.status = StripeChargeStatus.PROCESSING.value
                session.commit()

        else:  # オペレーション未実施の場合
            try:
                # Charge状態が[PROCESSING]のレコードを作成（この時点でcommitする）
                stripe_charge = StripeCharge()
                stripe_charge.exchange_address = exchange_address
                stripe_charge.order_id = order_id
                stripe_charge.agreement_id = agreement_id
                stripe_charge.status = StripeChargeStatus.PROCESSING.value
                session.add(stripe_charge)
                session.commit()
            except:  # 一意制約違反の場合
                session.rollback()
                raise DoubleChargeError(description='double charge')

        # 決済対象約定情報
        description_agreement = json.dumps({
            'exchange_address': exchange_address,
            'order_id': order_id,
            'agreement_id': agreement_id
        })

        # 新しく課金オブジェクトを作成する
        try:
            charge = stripe.Charge.create(
                customer=buyer.customer_id,
                amount=amount,
                currency="jpy",
                destination={
                    # 子アカウントへ配分する金額
                    "amount": charge_amount,
                    # 子アカウントを指定
                    "account": seller.account_id
                },
                description=description_agreement
            )
        except stripe.error.RateLimitError as e:
            stripe_charge.status = StripeChargeStatus.ERROR.value
            raise AppError(description='[stripe]Too many requests hit the API too quickly.')
        except stripe.error.InvalidRequestError as e:
            stripe_charge.status = StripeChargeStatus.ERROR.value
            raise AppError(description='[stripe]Invalid request errors arise when your request has invalid parameters.')
        except stripe.error.AuthenticationError as e:
            stripe_charge.status = StripeChargeStatus.ERROR.value
            raise AppError(description='[stripe]Failure to properly authenticate yourself in the request.')
        except stripe.error.APIConnectionError as e:
            stripe_charge.status = StripeChargeStatus.ERROR.value
            raise AppError(description='[stripe]Failure to connect to Stripes API.')
        except stripe.error.StripeError as e:
            stripe_charge.status = StripeChargeStatus.ERROR.value
            raise AppError(description='[stripe]Something happen on Stripe')
        except Exception as err:
            # Charge状態を[ERROR]ステータスに更新する
            stripe_charge.status = StripeChargeStatus.ERROR.value
            LOG.error('Error: %s', err)
            raise AppError

        if charge.status != 'successful':
            # Charge状態を[ERROR]ステータスに更新する
            stripe_charge.status = StripeChargeStatus.ERROR.value
            raise InvalidCardError

        sqs_msg = {
            'exchange_address': exchange_address,
            'order_id': order_id,
            'agreement_id': agreement_id,
            'amount': amount
        }

        try:
            Charge.send_sqs_msg(sqs_msg)
        except Exception as err:
            LOG.error('SQS Error: %s', err)
            raise AppError

        # 全ての処理が正常処理された場合、Charge状態を[SUCCESS]ステータスに更新する
        stripe_charge.status = StripeChargeStatus.SUCCESS.value

        receipt_url = {'receipt_url': charge['receipt_url']}
        self.on_success(res, receipt_url)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'order_id': {
                'type': 'integer',
                'empty': False,
                'required': True
            },
            'agreement_id': {
                'type': 'integer',
                'empty': False,
                'required': True
            },
            'amount': {
                'type': 'integer',
                'empty': False,
                'required': True
            },
            'exchange_address': {
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

    @staticmethod
    def send_sqs_msg(msg):
        name = config.AGENT_SQS_QUEUE_NAME
        sqs = boto3.resource(
            'sqs',
            endpoint_url=config.AGENT_SQS_URL,
            region_name='ap-northeast-1'
        )

        try:
            # キューの名前を指定してインスタンスを取得
            queue = sqs.get_queue_by_name(QueueName=name)
        except:
            # 指定したキューがない場合はキューを作成
            queue = sqs.create_queue(QueueName=name)

        # NOTE:Local開発環境では、ElasticMQに接続する
        if config.APP_ENV != 'local':
            response = queue.send_message(
                DelaySeconds=0,
                MessageBody=(
                    json.dumps(msg)
                ),
                MessageDeduplicationId='string',
                MessageGroupId='string'
            )
        else:
            response = queue.send_message(
                DelaySeconds=0,
                MessageBody=(
                    json.dumps(msg)
                )
            )

        return response
