# -*- coding: utf-8 -*-
import os
import json
import math
import falcon
import boto3

from cerberus import Validator
from web3 import Web3
from eth_utils import to_checksum_address
from app.contracts import Contract

from app import log
from app.api.common import BaseResource
from app.errors import AppError, InvalidParameterError, InvalidCardError, \
    DoubleChargeError, StripeErrorClient, StripeErrorServer
from app.utils.hooks import VerifySignature
from app.model import StripeCharge, StripeAccount, StripeAccountStatus, Agreement, StripeChargeStatus, AgreementStatus
from app import config

import stripe

stripe.api_key = config.STRIPE_SECRET

LOG = log.get_logger()


# ------------------------------
# [Stripe]Connected Account(ウォレット利用者)登録
# ------------------------------
class CreateAccount(BaseResource):
    """
    Handle for endpoint: /v1/Stripe/CreateAccount/
    """
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
                # DBに新規インサートする処理
                stripe_account = StripeAccount()
                stripe_account.account_address = address
                stripe_account.account_id = account.id
                stripe_account.customer_id = ""
                session.add(stripe_account)
                session.commit()
                response_data = {'stripe_account_id': account.id}
        except stripe.error.CardError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorClient(code=50, description='[stripe]card error caused by %s' % err.get('param'),
                                    title=err.get('message'))
        except stripe.error.RateLimitError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorClient(code=51, description='[stripe]rate limit error', title=err.get('message'))
        except stripe.error.InvalidRequestError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorClient(code=52, description='[stripe]invalid request error caused by %s' % err.get('param'),
                                    title=err.get('message'))
        except stripe.error.AuthenticationError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorServer(code=53, description='[stripe]authentication error', title=err.get('message'))
        except stripe.error.APIConnectionError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorServer(code=54, description='[stripe]api connection error', title=err.get('message'))
        except stripe.error.StripeError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorServer(code=55, description='[stripe]stripe error', title=err.get('message'))

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
    """
    Handle for endpoint: /v1/Stripe/CreateExternalAccount
    """
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
                # DBに新規インサートする処理
                stripe_account = StripeAccount()
                stripe_account.account_address = address
                stripe_account.account_id = account.id
                stripe_account.customer_id = ""
                session.add(stripe_account)
                session.commit()
                response_data = {'stripe_account_id': account.id}
        except stripe.error.CardError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorClient(code=50, description='[stripe]card error caused by %s' % err.get('param'),
                                    title=err.get('message'))
        except stripe.error.RateLimitError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorClient(code=51, description='[stripe]rate limit error', title=err.get('message'))
        except stripe.error.InvalidRequestError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorClient(code=52, description='[stripe]invalid request error caused by %s' % err.get('param'),
                                    title=err.get('message'))
        except stripe.error.AuthenticationError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorServer(code=53, description='[stripe]authentication error', title=err.get('message'))
        except stripe.error.APIConnectionError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorServer(code=54, description='[stripe]api connection error', title=err.get('message'))
        except stripe.error.StripeError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorServer(code=55, description='[stripe]stripe error', title=err.get('message'))

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
    """
    Handle for endpoint: /v1/Stripe/GetAccountInfo/
    """
    @falcon.before(VerifySignature())
    def on_post(self, req, res):
        LOG.info('v1.Stripe.GetAccountInfo')

        # 入力値チェック
        GetAccountInfo.validate(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context['address'])

        # アカウント情報を取得
        session = req.context["session"]
        stripe_account_info_list = []
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
    """
    Handle for endpoint: /v1/Stripe/CreateCustomer/
    """
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
        except stripe.error.CardError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorClient(code=50, description='[stripe]card error caused by %s' % err.get('param'),
                                    title=err.get('message'))
        except stripe.error.RateLimitError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorClient(code=51, description='[stripe]rate limit error', title=err.get('message'))
        except stripe.error.InvalidRequestError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorClient(code=52, description='[stripe]invalid request error caused by %s' % err.get('param'),
                                    title=err.get('message'))
        except stripe.error.AuthenticationError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorServer(code=53, description='[stripe]authentication error', title=err.get('message'))
        except stripe.error.APIConnectionError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorServer(code=54, description='[stripe]api connection error', title=err.get('message'))
        except stripe.error.StripeError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorServer(code=55, description='[stripe]stripe error', title=err.get('message'))

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
    """
    Handle for endpoint: /v1/Stripe/Charge/
    """
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
        #   DBにデータが存在しない場合、入力値エラーを返す
        agreement = session.query(Agreement). \
            filter(Agreement.order_id == order_id). \
            filter(Agreement.agreement_id == agreement_id). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            first()
        if agreement is None:
            raise InvalidParameterError

        # 金額チェック
        if not request_json['amount'] == agreement.amount:
            description = 'The amount ' + str(agreement.amount) + ' is invalid.'
            LOG.debug(description)
            raise InvalidParameterError

        # 約定状態のチェック
        #   Exchangeコントラクトから最新の約定キャンセル情報を取得
        #   キャンセル済みの場合、入力エラーを返す
        ExchangeContract = Charge.exchange_contracts(exchange_address)
        _, _, _, canceled, _, _ = \
            ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
        if canceled is True:
            LOG.debug('Agreement has already been canceled.')
            raise InvalidParameterError

        # StripeAccountテーブルから買手の情報を取得
        #   DBにデータが存在しない場合、入力値エラー
        buyer = session.query(StripeAccount). \
            filter(StripeAccount.account_address == buyer_address).first()
        if buyer is None:
            LOG.debug('Buyer Account not found.')
            raise InvalidParameterError

        # StripeAccountテーブルから売手の情報を取得
        #   DBにデータが存在しない場合、入力値エラー
        seller = session.query(StripeAccount). \
            filter(StripeAccount.account_address == agreement.seller_address).first()
        if seller is None:
            LOG.debug('Seller Account not found.')
            raise InvalidParameterError

        # Charge（課金）状態のチェック
        stripe_charge = session.query(StripeCharge). \
            filter(StripeCharge.exchange_address == exchange_address). \
            filter(StripeCharge.order_id == order_id). \
            filter(StripeCharge.agreement_id == agreement_id). \
            first()

        if stripe_charge is not None:  # 既にオペレーションを1回以上実施している場合
            # 二重課金のチェック
            #  - Charge状態が[PENDING]、[SUCCESS]の場合はエラー
            #  - Charge状態が[ERROR]の場合は[PENDING]に更新（この時点でcommitする）
            if stripe_charge.status == StripeChargeStatus.PENDING.value or \
                    stripe_charge.status == StripeChargeStatus.SUCCEEDED.value:
                description = "Double charge"
                raise DoubleChargeError(description=description)
            elif stripe_charge.status == StripeChargeStatus.FAILED.value:
                stripe_charge.status = StripeChargeStatus.PENDING.value
                session.commit()
        else:  # オペレーション未実施の場合
            try:
                # Charge状態が[PENDING]のレコードを作成（この時点でcommitする）
                stripe_charge = StripeCharge()
                stripe_charge.exchange_address = exchange_address
                stripe_charge.order_id = order_id
                stripe_charge.agreement_id = agreement_id
                stripe_charge.status = StripeChargeStatus.PENDING.value
                session.add(stripe_charge)
                session.commit()
            except Exception as err:  # 一意制約違反の場合
                session.rollback()
                LOG.error('Failed to Charge: %s', err)
                description = "Double charge"
                raise DoubleChargeError(description=description)

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
        except stripe.error.CardError as e:
            stripe_charge.status = StripeChargeStatus.ERROR.value
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorClient(code=50, description='[stripe]card error caused by %s' % err.get('param'),
                                    title=err.get('message'))
        except stripe.error.RateLimitError as e:
            stripe_charge.status = StripeChargeStatus.ERROR.value
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorClient(code=51, description='[stripe]rate limit error', title=err.get('message'))
        except stripe.error.InvalidRequestError as e:
            stripe_charge.status = StripeChargeStatus.ERROR.value
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorClient(code=52, description='[stripe]invalid request error caused by %s' % err.get('param'),
                                    title=err.get('message'))
        except stripe.error.AuthenticationError as e:
            stripe_charge.status = StripeChargeStatus.ERROR.value
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorServer(code=53, description='[stripe]authentication error', title=err.get('message'))
        except stripe.error.APIConnectionError as e:
            stripe_charge.status = StripeChargeStatus.ERROR.value
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorServer(code=54, description='[stripe]api connection error', title=err.get('message'))
        except stripe.error.StripeError as e:
            stripe_charge.status = StripeChargeStatus.ERROR.value
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorServer(code=55, description='[stripe]stripe error', title=err.get('message'))
        except Exception as err:
            # Charge状態を[ERROR]ステータスに更新する
            stripe_charge.status = StripeChargeStatus.FAILED.value
            LOG.error('Error: %s', err)
            raise AppError

        if charge.status != 'successful':
            # Charge状態を[ERROR]ステータスに更新する
            stripe_charge.status = StripeChargeStatus.FAILED.value
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
        stripe_charge.status = StripeChargeStatus.SUCCEEDED.value

        receipt_url = {'receipt_url': charge['receipt_url']}
        self.on_success(res, receipt_url)

    @staticmethod
    def exchange_contracts(exchange_address):
        if exchange_address == to_checksum_address(os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS')):
            ExchangeContract = Contract.get_contract(
                'IbetStraightBondExchange',
                exchange_address
            )

        elif exchange_address == to_checksum_address(os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS')):
            ExchangeContract = Contract.get_contract(
                'IbetMembershipExchange',
                exchange_address
            )

        elif exchange_address == to_checksum_address(os.environ.get('IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS')):
            ExchangeContract = Contract.get_contract(
                'IbetCouponExchange',
                exchange_address
            )
        else:
            description = 'Invalid Address.'
            raise InvalidParameterError(description=description)

        return ExchangeContract

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
        except Exception as err:
            LOG.error(err)
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


# ------------------------------
# [Stripe]Connected Accountの本人確認ステータスの取得
# ------------------------------
class AccountStatus(BaseResource):
    """
    Handle for endpoint: /v1/Stripe/AccountStatus
    """
    @falcon.before(VerifySignature())
    def on_post(self, req, res):
        LOG.info('v1.Stripe.AccountStatus')

        address = to_checksum_address(req.context["address"])
        # DBの存在チェック
        session = req.context["session"]
        raw = session.query(StripeAccount).filter(StripeAccount.account_address == address).first()

        # 存在する場合はstripeにAccount情報を聞きに行く。存在しない場合は`NONE`で返す。
        try:
            if raw is None or raw.account_id == "":
                verified_status = 'NONE'
            else:
                response = stripe.Account.retrieve(
                    raw.account_id
                )
                if response["individual"]["verification"]["status"] == StripeAccountStatus.UNVERIFIED.value:
                    verified_status = 'UNVERIFIED'
                elif response["individual"]["verification"]["status"] == StripeAccountStatus.PENDING.value:
                    verified_status = 'PENDING'
                elif response["individual"]["verification"]["status"] == StripeAccountStatus.VERIFIED.value:
                    verified_status = 'VERIFIED'
        except stripe.error.CardError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorClient(code=50, description='[stripe]card error caused by %s' % err.get('param'),
                                    title=err.get('message'))
        except stripe.error.RateLimitError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorClient(code=51, description='[stripe]rate limit error', title=err.get('message'))
        except stripe.error.InvalidRequestError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorClient(code=52, description='[stripe]invalid request error caused by %s' % err.get('param'),
                                    title=err.get('message'))
        except stripe.error.AuthenticationError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorServer(code=53, description='[stripe]authentication error', title=err.get('message'))
        except stripe.error.APIConnectionError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorServer(code=54, description='[stripe]api connection error', title=err.get('message'))
        except stripe.error.StripeError as e:
            body = e.json_body
            err = body.get('error', {})
            raise StripeErrorServer(code=55, description='[stripe]stripe error', title=err.get('message'))
        response_json = {
            'verified_status': verified_status
        }
        self.on_success(res, response_json)


# ------------------------------
# [Stripe]課金状態取得
# ------------------------------
class ChargeStatus(BaseResource):
    """
    Handle for endpoint: /v1/Stripe/ChargeStatus
    """
    def on_post(self, req, res):
        LOG.info('v1.Stripe.ChargeStatus')
        session = req.context["session"]

        # 入力値チェック
        request_json = ChargeStatus.validate(req)

        # リクエストから情報を抽出
        exchange_address = to_checksum_address(request_json['exchange_address'])
        order_id = request_json['order_id']
        agreement_id = request_json['agreement_id']

        # Charge（課金）状態の取得
        stripe_charge = session.query(StripeCharge). \
            filter(StripeCharge.exchange_address == exchange_address). \
            filter(StripeCharge.order_id == order_id). \
            filter(StripeCharge.agreement_id == agreement_id). \
            first()

        if stripe_charge is None:
            status = 'NONE'
        else:
            if stripe_charge.status == StripeChargeStatus.SUCCEEDED.value:
                status = 'SUCCEEDED'
            elif stripe_charge.status == StripeChargeStatus.PENDING.value:
                status = 'PENDING'
            elif stripe_charge.status == StripeChargeStatus.FAILED.value:
                status = 'FAILED'

        response_json = {
            'exchange_address': exchange_address,
            'order_id': order_id,
            'agreement_id': agreement_id,
            'status': status
        }

        self.on_success(res, response_json)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'exchange_address': {
                'type': 'string',
                'required': True,
                'empty': False,
            },
            'order_id': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': True,
                'nullable': False,
            },
            'agreement_id': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': True,
                'nullable': False,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(request_json['exchange_address']):
            raise InvalidParameterError(description='invalid exchange address')

        return validator.document
