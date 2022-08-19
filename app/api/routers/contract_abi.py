"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

import json

from app import log, config
from app.api.common import BaseResource
from app.errors import NotSupportedError

LOG = log.get_logger()


# ------------------------------
# 普通社債ABI参照
# ------------------------------
class StraightBondABI(BaseResource):
    """
    Endpoint: /ABI/StraightBond
    """

    def on_get(self, req, res, **kwargs):
        if config.BOND_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        ibet_straightbond_json = json.load(open("app/contracts/json/IbetStraightBond.json", "r"))
        abi = ibet_straightbond_json['abi']
        self.on_success(res, abi)


# ------------------------------
# 株式ABI参照
# ------------------------------
class ShareABI(BaseResource):
    """
    Endpoint: /ABI/Share
    """

    def on_get(self, req, res, **kwargs):
        if config.SHARE_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        ibet_share_json = json.load(open("app/contracts/json/IbetShare.json", "r"))
        abi = ibet_share_json['abi']
        self.on_success(res, abi)


# ------------------------------
# 会員権ABI参照
# ------------------------------
class MembershipABI(BaseResource):
    """
    Endpoint: /ABI/Membership
    """

    def on_get(self, req, res, **kwargs):
        if config.MEMBERSHIP_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        ibet_membership_json = json.load(open("app/contracts/json/IbetMembership.json", "r"))
        abi = ibet_membership_json['abi']
        self.on_success(res, abi)


# ------------------------------
# クーポンABI参照
# ------------------------------
class CouponABI(BaseResource):
    """
    Endpoint: /ABI/Coupon
    """

    def on_get(self, req, res, **kwargs):
        if config.COUPON_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        ibet_coupon_json = json.load(open("app/contracts/json/IbetCoupon.json", "r"))
        abi = ibet_coupon_json['abi']
        self.on_success(res, abi)
