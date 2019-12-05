# -*- coding: utf-8 -*-
import json

from app import log
from app.api.common import BaseResource

LOG = log.get_logger()


# ------------------------------
# 普通社債ABI参照
# ------------------------------
class StraightBondABI(BaseResource):
    """
    Handle for endpoint: /v2/ABI/StraightBond
    """

    def on_get(self, req, res):
        LOG.info('v2.token_abi.StraightBondABI')
        contracts = json.load(open('data/contracts.json', 'r'))
        abi = contracts['IbetStraightBond']['abi']
        self.on_success(res, abi)


# ------------------------------
# 会員権ABI参照
# ------------------------------
class MembershipABI(BaseResource):
    """
    Handle for endpoint: /v2/ABI/Membership
    """

    def on_get(self, req, res):
        LOG.info('v2.token_abi.MembershipABI')
        contracts = json.load(open('data/contracts.json', 'r'))
        abi = contracts['IbetMembership']['abi']
        self.on_success(res, abi)


# ------------------------------
# クーポンABI参照
# ------------------------------
class CouponABI(BaseResource):
    """
    Handle for endpoint: /v2/ABI/Coupon
    """

    def on_get(self, req, res):
        LOG.info('v2.token_abi.CouponABI')
        contracts = json.load(open('data/contracts.json', 'r'))
        abi = contracts['IbetCoupon']['abi']
        self.on_success(res, abi)
