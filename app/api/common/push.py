# -*- coding: utf-8 -*-
import json
import falcon
import boto3
from botocore.exceptions import ClientError
from cerberus import Validator
from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError, SNSNotFoundError
from app.utils.hooks import VerifySignature
from app import config
from app.model import Push
from sqlalchemy import exc

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
        LOG.info('common.Push.UpdateDevice')

        # 入力値チェック
        request_json = UpdateDevice.validate(req)

        # DBに登録
        session = req.context["session"]
        # クエリを設定
        query = session.query(Push). \
            filter(Push.device_id == request_json['device_id'])
        device_data = query.first()
        # eth address
        address = to_checksum_address(req.context['address'])
        # device idがある場合（既存デバイス）
        if device_data is not None:
            update_flag = False
            if device_data.account_address != address:
                device_data.account_address = address
                update_flag = True
            if device_data.device_token != request_json['device_token']:
                # 古いdevice tokenを削除
                delete_endpoint(device_data.device_endpoint_arn)
                # AWS SNSのendpointを登録
                endpoint = add_endpoint(request_json['device_token'], request_json['platform'])
                # DB更新用の項目設定
                update_flag = True
                device_data.device_token = request_json['device_token']
                device_data.device_endpoint_arn = endpoint
                device_data.platform = request_json['platform']
            if update_flag:
                session.merge(device_data)
        # device idがない（新規デバイス）
        else:
            # AWS SNSのendpointを登録
            endpoint = add_endpoint(request_json['device_token'], request_json['platform'])
            # DBへinsert
            device_data = Push()
            device_data.device_id = request_json['device_id']
            device_data.account_address = address
            device_data.device_token = request_json['device_token']
            device_data.device_endpoint_arn = endpoint
            device_data.platform = request_json['platform']
            # 一意制約違反の場合でも正常応答とする（SNS登録中に別トランザクションが入る得るため）
            try:
                session.add(device_data)
                session.commit()
            except exc.IntegrityError:
                session.rollback()
                pass
        self.on_success(res, None)

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
            'platform': {
                'type': 'string',
                'required': True,
                'empty': False,
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(req.context['address']):
            raise InvalidParameterError

        return validator.document

# ------------------------------
# [Push]device tokenの削除
# ------------------------------
class DeleteDevice(BaseResource):
    '''
    Handle for endpoint: /v1/Push/DeleteDevice
    '''
    @falcon.before(VerifySignature())
    def on_post(self, req, res):
        LOG.info('common.Push.DeleteDevice')

        # 入力値チェック
        request_json = DeleteDevice.validate(req)

        # クエリを設定
        session = req.context["session"]
        address = to_checksum_address(req.context['address'])
        query = session.query(Push). \
            filter(Push.device_id == request_json['device_id']). \
            filter(Push.account_address == address)
        device_data = query.first()
        if device_data is not None:
            # SNSのendpoint ARNを削除
            delete_endpoint(device_data.device_endpoint_arn)
            # テーブルの行を削除
            session.delete(device_data)
        self.on_success(res, None)

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
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(req.context['address']):
            raise InvalidParameterError

        return validator.document

# device tokenをapplication arnに登録
def add_endpoint(device_token, platform):
    if platform == "ios":
        application_arn = config.SNS_APPLICATION_ARN_IOS
    elif platform == "android":
        application_arn = config.SNS_APPLICATION_ARN_ANDROID

    try:
        client = boto3.client('sns', 'ap-northeast-1')
        endpoint = client.create_platform_endpoint(
            PlatformApplicationArn=application_arn,
            Token=device_token
        )
    except ClientError:
        raise SNSNotFoundError
    return endpoint['EndpointArn']

# 古いdevice tokenのarnを削除
def delete_endpoint(endpoint_arn):
    try:
        client = boto3.client('sns', 'ap-northeast-1')
        client.delete_endpoint(
            EndpointArn=endpoint_arn
        )
    except ClientError:
        raise SNSNotFoundError
