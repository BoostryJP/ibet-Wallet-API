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

import omise
omise.api_secret = config.OMISE_SECRET
omise.api_public = config.OMISE_PUBLIC

LOG = log.get_logger()

# ------------------------------
# [Omise]顧客情報作成
# ------------------------------
class CreateCustomer(BaseResource):
    '''
    Handle for endpoint: /v1/Omise/CreateCustomer
    '''
    @falcon.before(VerifySignature())
    def on_post(self, req, res):
        LOG.info('v1.Omise.CreateCustomer')

        # 入力値チェック
        request_json = CreateCustomer.validate(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context['address'])

        # 新しい顧客を作成し、Cardオブジェクトを紐付ける
        try:
            customer = omise.Customer.create(
              description = address,
              card = request_json['token_id']
            )
        except omise.errors.UsedTokenError:
            raise InvalidParameterError(description='token was already used')
        except omise.errors.NotFoundError:
            raise InvalidParameterError(description='token was not found')
        except:
            raise AppError

        customer_id = {'customer_id': customer.id}

        self.on_success(res, customer_id)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'token_id': {
                'type': 'string',
                'required': True,
                'empty': False,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(req.context['address']):
            raise InvalidParameterError

        return validator.document

# ------------------------------
# [Omise]カード情報更新
# ------------------------------
class UpdateCustomer(BaseResource):
    '''
    Handle for endpoint: /v1/Omise/UpdateCustomer
    '''
    @falcon.before(VerifySignature())
    def on_post(self, req, res):
        LOG.info('v1.Omise.UpdateCustomer')

        # 入力値チェック
        request_json = UpdateCustomer.validate(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context['address'])

        # Card情報を取得
        try:
            customer = omise.Customer.retrieve(request_json['customer_id'])
        except omise.errors.NotFoundError:
            raise InvalidParameterError(description='customer was not found')

        # 更新権限のチェック
        if address != customer.description:
            raise InvalidParameterError(description='update is not allowed')

        # 顧客にCard情報を紐付ける
        try:
            # 登録されているCard情報を削除する
            for card in customer.cards:
                card = customer.cards.retrieve(card.id)
                card.destroy()
            # 新しいCard情報を紐づける
            customer.update(
                card = request_json['token_id']
            )
        except omise.errors.UsedTokenError:
            raise InvalidParameterError(description='token was already used')
        except omise.errors.NotFoundError:
            raise InvalidParameterError(description='token was not found')
        except:
            raise AppError

        self.on_success(res)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'token_id': {
                'type': 'string',
                'required': True,
                'empty': False,
            },
            'customer_id': {
                'type': 'string',
                'required': True,
                'empty': False,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(req.context['address']):
            raise InvalidParameterError

        return validator.document

# ------------------------------
# [Omise]課金
# ------------------------------
class Charge(BaseResource):
    '''
    Handle for endpoint: /v1/Omise/Charge
    '''
    @falcon.before(VerifySignature())
    def on_post(self, req, res):
        LOG.info('v1.Omise.Charge')
        session = req.context["session"]

        # 入力値チェック
        request_json = Charge.validate(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context['address'])
        exchange_address = to_checksum_address(request_json['exchange_address'])
        order_id = request_json['order_id']
        agreement_id = request_json['agreement_id']
        customer_id = request_json['customer_id']
        amount = request_json['amount']

        # Card情報を取得
        try:
            customer = omise.Customer.retrieve(customer_id)
        except omise.errors.NotFoundError:
            raise InvalidParameterError(description='customer was not found')

        # 更新権限のチェック
        if address != customer.description:
            raise InvalidParameterError(description='update is not allowed')

        # Charge（課金）状態の取得
        omise_charge = session.query(OmiseCharge).\
            filter(OmiseCharge.exchange_address == exchange_address).\
            filter(OmiseCharge.order_id == order_id).\
            filter(OmiseCharge.agreement_id == agreement_id).\
            first()

        if omise_charge is not None: # 既にオペレーションを1回以上実施している場合
            # 二重課金のチェック
            #  - Charge状態が[PROCESSING]、[SUCCESS]の場合はエラー
            #  - Charge状態が[ERROR]の場合は[PROCESSING]に更新（この時点でcommitする）
            if omise_charge.status == OmiseChargeStatus.PROCESSING.value or \
                omise_charge.status == OmiseChargeStatus.SUCCESS.value:
                raise DoubleChargeError(description='double charge')
            elif omise_charge.status == OmiseChargeStatus.ERROR.value:
                omise_charge.status = OmiseChargeStatus.PROCESSING.value
                session.commit()
        else: # オペレーション未実施の場合
            try:
                # Charge状態が[PROCESSING]のレコードを作成（この時点でcommitする）
                omise_charge = OmiseCharge()
                omise_charge.exchange_address = exchange_address
                omise_charge.order_id = order_id
                omise_charge.agreement_id = agreement_id
                omise_charge.status = OmiseChargeStatus.PROCESSING.value
                session.add(omise_charge)
                session.commit()
            except: # 一意制約違反の場合
                session.rollback()
                raise DoubleChargeError(description='double charge')

        # 決済対象約定情報
        description_agreement = json.dumps({
            'exchange_address': exchange_address,
            'order_id': order_id,
            'agreement_id': agreement_id
        })

        # 課金
        try:
            charge = omise.Charge.create(
                amount = amount,
                currency = 'jpy',
                customer = customer_id,
                description = description_agreement
            )
        except omise.errors.InvalidChargeError as e:
            # Charge状態を[ERROR]ステータスに更新する
            omise_charge.status = OmiseChargeStatus.ERROR.value
            raise InvalidParameterError(description=str(e))
        except:
            # Charge状態を[ERROR]ステータスに更新する
            omise_charge.status = OmiseChargeStatus.ERROR.value
            raise AppError

        if charge.status != 'successful':
            # Charge状態を[ERROR]ステータスに更新する
            omise_charge.status = OmiseChargeStatus.ERROR.value
            raise InvalidCardError

        sqs_msg = {
            'exchange_address': exchange_address,
            'order_id': order_id,
            'agreement_id': agreement_id,
            'amount': amount
        }

        Charge.send_sqs_msg(sqs_msg)

        # 全ての処理が正常処理された場合、Charge状態を[SUCCESS]ステータスに更新する
        omise_charge.status = OmiseChargeStatus.SUCCESS.value

        self.on_success(res)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'customer_id': {
                'type': 'string',
                'required': True,
                'empty': False,
            },
            'amount': {
                'type': 'integer',
                'coerce': int,
                'min':100,
                'max':6000000,
                'required': True,
                'nullable': False,
            },
            'exchange_address': {
                'type': 'string',
                'required': True,
                'empty': False,
            },
            'order_id': {
                'type': 'integer',
                'coerce': int,
                'min':0,
                'required': True,
                'nullable': False,
            },
            'agreement_id': {
                'type': 'integer',
                'coerce': int,
                'min':0,
                'required': True,
                'nullable': False,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(req.context['address']):
            raise InvalidParameterError

        if not Web3.isAddress(request_json['exchange_address']):
            raise InvalidParameterError

        return validator.document

    @staticmethod
    def send_sqs_msg(msg):
        name = config.AGENT_SQS_QUEUE_NAME
        sqs = boto3.resource(
            'sqs',
            endpoint_url = config.AGENT_SQS_URL,
            region_name='ap-northeast-1'
        )

        try:
            # キューの名前を指定してインスタンスを取得
            queue = sqs.get_queue_by_name(QueueName=name)
        except:
            # 指定したキューがない場合はキューを作成
            queue = sqs.create_queue(QueueName=name)

        response = queue.send_message(
            DelaySeconds=0,
            MessageBody=(
                json.dumps(msg)
            )
        )

        return response

# ------------------------------
# [Omise]課金状態取得
# ------------------------------
class ChargeStatus(BaseResource):
    '''
    Handle for endpoint: /v1/Omise/ChargeStatus
    '''
    def on_post(self, req, res):
        LOG.info('v1.Omise.ChargeStatus')
        session = req.context["session"]

        # 入力値チェック
        request_json = ChargeStatus.validate(req)

        # リクエストから情報を抽出
        exchange_address = to_checksum_address(request_json['exchange_address'])
        order_id = request_json['order_id']
        agreement_id = request_json['agreement_id']

        # Charge（課金）状態の取得
        omise_charge = session.query(OmiseCharge).\
            filter(OmiseCharge.exchange_address == exchange_address).\
            filter(OmiseCharge.order_id == order_id).\
            filter(OmiseCharge.agreement_id == agreement_id).\
            first()

        if omise_charge is None:
            status = 'NONE'
        else:
            if omise_charge.status == OmiseChargeStatus.PROCESSING.value:
                status = 'PROCESSING'
            elif omise_charge.status == OmiseChargeStatus.SUCCESS.value:
                status = 'SUCCESS'
            elif omise_charge.status == OmiseChargeStatus.ERROR.value:
                status = 'ERROR'

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
                'min':0,
                'required': True,
                'nullable': False,
            },
            'agreement_id': {
                'type': 'integer',
                'coerce': int,
                'min':0,
                'required': True,
                'nullable': False,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(request_json['exchange_address']):
            raise InvalidParameterError(description='invalid exchange address')

        return validator.document
