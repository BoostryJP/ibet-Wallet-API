# -*- coding: utf-8 -*-
import json

from app import log
from app.api.common import BaseResource
from app import config

LOG = log.get_logger()

# ------------------------------
# 普通社債ABI参照
# ------------------------------
class GetStraightBondABI(BaseResource):
    '''
    Handle for endpoint: /v1/StraightBondABI/
    '''
    def on_get(self, req, res):
        LOG.info('v1.tokenTemplates.GetStraightBondABI')
        contracts = json.load(open('data/contracts.json' , 'r'))
        abi = contracts['IbetStraightBond']['abi']
        self.on_success(res, abi)

# ------------------------------
# クーポンABI参照
# ------------------------------
class GetCouponABI(BaseResource):
    '''
    Handle for endpoint: /v1/CouponABI/
    '''
    def on_get(self, req, res):
        LOG.info('v1.tokenTemplates.GetCouponABI')
        contracts = json.load(open('data/contracts.json' , 'r'))
        abi = contracts['IbetCoupon']['abi']
        self.on_success(res, abi)
