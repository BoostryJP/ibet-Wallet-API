# -*- coding: utf-8 -*-
import json
import os

from cerberus import Validator, ValidationError

from app import log
from app.api.common import BaseResource
from app.utils.hooks import VerifySignature
from app.errors import InvalidParameterError


LOG = log.get_logger()

# ------------------------------
# 動作保証アプリバーションの取得
# ------------------------------
class RequiredVersion(BaseResource):
    '''
    Handle for endpoint: /v1/RequiredVersion
    '''
    def on_get(self, req, res):
        LOG.info('v1.Version.RequiredVersion')

        request_json = RequiredVersion.validate(req)

        # 環境変数の読み込み（iOS）
        required_version_ios = os.environ.get('TMRAPP_REQUIRED_VERSION_IOS')
        force_ios = os.environ.get('TMRAPP_FORCE_UPDATE_IOS')
        url_ios = os.environ.get('TMRAPP_UPDATE_URL_IOS')
        print(url_ios)

        # 環境変数の読み込み（Android）
        required_version_android = os.environ.get('TMRAPP_REQUIRED_VERSION_ANDROID')
        force_android = os.environ.get('TMRAPP_FORCE_UPDATE_ANDROID')
        url_android = os.environ.get('TMRAPP_UPDATE_URL_ANDROID')
        
        if request_json['platform'] == "ios":
            required_version = {
                "required_version": required_version_ios, 
                "force": force_ios, 
                "update_url": url_ios}
        else:
            required_version = {
                "required_version": required_version_android, 
                "force": force_android, 
                "update_url": url_android}

        self.on_success(res, required_version)
    
    @staticmethod
    def validate(req):
        request_json = {'platform': req.get_param('platform')}
        validator = Validator({
            'platform' : {
                'type': 'string', 
                'empty': False, 
                'required': True,
                'allowed': ['ios', 'android'],
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return request_json
