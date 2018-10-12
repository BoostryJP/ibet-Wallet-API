# -*- coding: utf-8 -*-
import falcon
from cerberus import Validator
from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError
from app.utils.hooks import VerifySignature
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
            customer.update(
                card = request_json['token_id']
            )
        except omise.errors.UsedTokenError:
            raise InvalidParameterError(description='token was already used')
        except omise.errors.NotFoundError:
            raise InvalidParameterError(description='token was not found')

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
