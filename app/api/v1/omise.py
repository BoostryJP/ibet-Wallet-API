# -*- coding: utf-8 -*-
import falcon
from cerberus import Validator

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
    Handle for endpoint: /v1/Omise/Customers
    '''
    @falcon.before(VerifySignature())
    def on_post(self, req, res):
        LOG.info('v1.Omise.Customers')

        session = req.context['session']

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
# [Omise]顧客情報更新
# ------------------------------

# ------------------------------
# [Omise]課金
# ------------------------------
