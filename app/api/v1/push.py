# -*- coding: utf-8 -*-
import json
import falcon
from cerberus import Validator
from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError
from app.utils.hooks import VerifySignature
from app import config
from app.model import Push

LOG = log.get_logger()

# ------------------------------
# [Push]device tokenの登録・更新
# ------------------------------
class UpdateDevice(BaseResource):
    '''
    Handle for endpoint: /v1/Push/UpdateDevice
    '''
    @falcon.before(VerifySignature())
    def on_post(self, req, res):
        LOG.info('v1.Push.UpdateDevice')

        session = req.context["session"]

        # 入力値チェック
        request_json = UpdateDevice.validate(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context['address'])
        # DBに登録
        # クエリを設定
        query = session.query(Push). \
            filter(Push.device_id == request_json['device_id'])
        device_data = query.first()
        # device idがある場合
        if device_data is not None:
            update_flag = False
            if device_data.account_address != address:
                device_data.account_address = address
                update_flag = True
            if device_data.device_token != request_json['device_token']:
                device_data.device_token = request_json['device_token']
                update_flag = True
                # AWS SNSのendpointを更新
            if update_flag:
                self.db.merge(device_data)
        else:
            # insert
                        

        self.on_success(res, customer_id)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'device_id': {
                'type': 'string',
                'required': True,
                'empty': False,
            },
            'device_token': {
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