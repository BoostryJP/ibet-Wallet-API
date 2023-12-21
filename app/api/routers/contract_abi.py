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

from fastapi import APIRouter, Request

from app import config, log
from app.errors import NotSupportedError
from app.model.schema import ABI
from app.model.schema.base import GenericSuccessResponse, SuccessResponse
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()

router = APIRouter(prefix="/ABI", tags=["abi"])


# ------------------------------
# 普通社債ABI参照
# ------------------------------
@router.get(
    "/StraightBond",
    summary="StraightBond ABI",
    operation_id="StraightBondABI",
    response_model=GenericSuccessResponse[ABI],
    responses=get_routers_responses(NotSupportedError),
)
def get_straight_bond_abi(req: Request):
    """
    Returns ABI of IbetStraightBond.
    """
    if config.BOND_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    ibet_straightbond_json = json.load(
        open("app/contracts/json/IbetStraightBond.json", "r")
    )
    abi = ibet_straightbond_json["abi"]
    return json_response({**SuccessResponse.default(), "data": abi})


# ------------------------------
# 株式ABI参照
# ------------------------------
@router.get(
    "/Share",
    summary="Share ABI",
    operation_id="ShareABI",
    response_model=GenericSuccessResponse[ABI],
    responses=get_routers_responses(NotSupportedError),
)
def get_share_abi(req: Request):
    """
    Returns ABI of IbetShare.
    """
    if config.SHARE_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    ibet_share_json = json.load(open("app/contracts/json/IbetShare.json", "r"))
    abi = ibet_share_json["abi"]
    return json_response({**SuccessResponse.default(), "data": abi})


# ------------------------------
# 会員権ABI参照
# ------------------------------
@router.get(
    "/Membership",
    summary="Membership ABI",
    operation_id="MembershipABI",
    response_model=GenericSuccessResponse[ABI],
    responses=get_routers_responses(NotSupportedError),
)
def get_membership_abi(req: Request):
    """
    Returns ABI of IbetMembership.
    """
    if config.MEMBERSHIP_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    ibet_membership_json = json.load(
        open("app/contracts/json/IbetMembership.json", "r")
    )
    abi = ibet_membership_json["abi"]
    return json_response({**SuccessResponse.default(), "data": abi})


# ------------------------------
# クーポンABI参照
# ------------------------------
@router.get(
    "/Coupon",
    summary="Coupon ABI",
    operation_id="CouponABI",
    response_model=GenericSuccessResponse[ABI],
    responses=get_routers_responses(NotSupportedError),
)
def get_coupon_abi(req: Request):
    """
    Returns ABI of IbetCoupon.
    """
    if config.COUPON_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    ibet_coupon_json = json.load(open("app/contracts/json/IbetCoupon.json", "r"))
    abi = ibet_coupon_json["abi"]
    return json_response({**SuccessResponse.default(), "data": abi})
