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
        LOG.info('v1.tokenTemplates.GetABI')
        abi_str = config.STRAIGHT_BOND_ABI['abi']
        abi = json.loads(abi_str)
        self.on_success(res, abi)
