# -*- coding: utf-8 -*-
import os

from cerberus import Validator, ValidationError

from app import log
from app import config
from app.api.common import BaseResource
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
        required_version_ios = config.TMRAPP_REQUIRED_VERSION_IOS
        force_ios = bool(config.TMRAPP_FORCE_UPDATE_IOS)
        update_url_scheme_ios = config.TMRAPP_UPDATE_URL_SCHEME_IOS
        update_url_ios = config.TMRAPP_UPDATE_URL_IOS
        # 環境変数の読み込み（Android）
        required_version_android = config.TMRAPP_REQUIRED_VERSION_ANDROID
        force_android = bool(config.TMRAPP_FORCE_UPDATE_ANDROID)
        update_url_scheme_android = config.TMRAPP_UPDATE_URL_SCHEME_ANDROID
        update_url_android = config.TMRAPP_UPDATE_URL_ANDROID
        
        if request_json['platform'] == "ios":
            required_version = {
                "required_version": required_version_ios, 
                "force": force_ios,
                "update_url_scheme": update_url_scheme_ios,
                "update_url": update_url_ios,
            }
        else:
            required_version = {
                "required_version": required_version_android, 
                "force": force_android,
                "update_url_scheme": update_url_scheme_android,
                "update_url": update_url_android,
            }

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
