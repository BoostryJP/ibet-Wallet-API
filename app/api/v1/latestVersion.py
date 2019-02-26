# -*- coding: utf-8 -*-
import json
import falcon

from app import log
from app.api.common import BaseResource
from app.utils.hooks import VerifySignature

LOG = log.get_logger()

# ------------------------------
# アプリケーションの最新バージョン取得
# ------------------------------
class Latest(BaseResource):
    '''
    Handle for endpoint: /v1/Latest
    '''
    @falcon.before(VerifySignature())
    def on_post(self, req, res):
        LOG.info('v1.LatestVersion.Latest')
        
        # postパラメーターを取得
        body = req.stream.read()
        data = json.loads(body)
        
        # パラメーターの取得
        os = data['os']
        
        if os == "iOS":
            res.body = json.load(open('data/iOS_latest_version.json', 'r'))
        else:
            res.body = json.load(open('data/Android_latest_version.json', 'r'))
