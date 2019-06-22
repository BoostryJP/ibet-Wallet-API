# -*- coding: utf-8 -*-
import json

from app import log
from app.api.common import BaseResource

LOG = log.get_logger()


# ------------------------------
# 普通社債ABI参照
# ------------------------------
class GetStraightBondABI(BaseResource):
    """
    Handle for endpoint: /v1/StraightBondABI/
    """

    def on_get(self, req, res):
        LOG.info('v1.tokenTemplates.GetStraightBondABI')
        contracts = json.load(open('data/contracts.json', 'r'))
        abi = contracts['IbetStraightBond']['abi']
        self.on_success(res, abi)


# ------------------------------
# 会員権ABI参照
# ------------------------------
class GetMembershipABI(BaseResource):
    """
    Handle for endpoint: /v1/MembershipABI/
    """

    def on_get(self, req, res):
        LOG.info('v1.tokenTemplates.MembershipABI')
        contracts = json.load(open('data/contracts.json', 'r'))
        abi = contracts['IbetMembership']['abi']
        self.on_success(res, abi)


# ------------------------------
# クーポンABI参照
# ------------------------------
class GetCouponABI(BaseResource):
    """
    Handle for endpoint: /v1/CouponABI/
    """

    def on_get(self, req, res):
        LOG.info('v1.tokenTemplates.GetCouponABI')
        contracts = json.load(open('data/contracts.json', 'r'))
        abi = contracts['IbetCoupon']['abi']
        self.on_success(res, abi)


# ------------------------------
# MRF ABI参照
# ------------------------------
class GetMRFABI(BaseResource):
    """
    Handle for endpoint: /v1/MRFABI/
    """

    def on_get(self, req, res):
        LOG.info('v1.tokenTemplates.GetMRFABI')
        contracts = json.load(open('data/contracts.json', 'r'))
        abi = contracts['IbetMRF']['abi']
        self.on_success(res, abi)


# ------------------------------
# JDR ABI参照
# ------------------------------
class GetJDRABI(BaseResource):
    """
    Handle for endpoint: /v1/JDRABI/
    """

    def on_get(self, req, res):
        LOG.info('v1.tokenTemplates.GetJDRABI')
        contracts = json.load(open('data/contracts.json', 'r'))
        abi = contracts['IbetDepositaryReceipt']['abi']
        self.on_success(res, abi)
