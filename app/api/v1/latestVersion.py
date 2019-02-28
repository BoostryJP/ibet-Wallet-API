# -*- coding: utf-8 -*-
import json

from cerberus import Validator, ValidationError

from app import log
from app.api.common import BaseResource
from app.utils.hooks import VerifySignature
from app.errors import InvalidParameterError


LOG = log.get_logger()

# ------------------------------
# アプリケーションの最新バージョン取得
# ------------------------------
class LatestVersion(BaseResource):
    '''
    Handle for endpoint: /v1/LatestVersion
    '''
    def on_get(self, req, res):
        LOG.info('v1.LatestVersion.Latest')

        request_json = LatestVersion.validate(req)
        
        if request_json['platform'] == "ios":
            latestVersion = {"required_version":"2.0.0","type":"force","update_url":"https://itunes.apple.com/jp/app/mdaq/id489127768?mt=8"}
        else:
            latestVersion = {"required_version":"2.0.0","type":"force","update_url":"https://play.google.com/store/apps/details?id=jp.co.nomura.nomurastock"}

        self.on_success(res, latestVersion)
    
    @staticmethod
    def validate(req):
        request_json = {'platform': req.get_param('platform')}
        validator = Validator({
            'platform' : {
                'type': 'string', 
                'empty': False, 
                'required': True,
                'allowed' : ['ios', 'android']
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return request_json
