# -*- coding: utf-8 -*-
import json

from app import log
from app.api.common import BaseResource

LOG = log.get_logger()


# ------------------------------
# 会員権ABI参照
# ------------------------------
class GetMembershipABI(BaseResource):
    """
    Handle for endpoint: /v2/ABI/Membership
    """

    def on_get(self, req, res):
        LOG.info('v2.token_abi.GetMembershipABI')
        contracts = json.load(open('data/contracts.json', 'r'))
        abi = contracts['IbetMembership']['abi']
        self.on_success(res, abi)


# ------------------------------
# クーポンABI参照
# ------------------------------
class GetCouponABI(BaseResource):
    """
    Handle for endpoint: /v2/ABI/Coupon
    """

    def on_get(self, req, res):
        LOG.info('v2.token_abi.GetCouponABI')
        contracts = json.load(open('data/contracts.json', 'r'))
        abi = contracts['IbetCoupon']['abi']
        self.on_success(res, abi)
