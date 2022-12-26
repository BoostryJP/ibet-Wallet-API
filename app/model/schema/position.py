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
from fastapi import Query
from typing import Optional, TypeVar, Generic, Union
from pydantic import (
    BaseModel,
    Field,
)
from pydantic.dataclasses import dataclass
from app.model.schema.base import ResultSet
from app.model.schema.token_coupon import RetrieveCouponTokenResponse
from app.model.schema.token_membership import RetrieveMembershipTokenResponse

############################
# COMMON
############################


############################
# REQUEST
############################

@dataclass
class ListAllPositionQuery:
    offset: Optional[int] = Query(default=None, description="start position", ge=0)
    limit: Optional[int] = Query(default=None, description="number of set", ge=0)
    include_token_details: Optional[bool] = Query(default=False, description="include token details")
    enable_index: Optional[bool] = Query(default=False, description="enable using indexed position data")


@dataclass
class GetPositionQuery:
    enable_index: Optional[bool] = Query(default=False, description="enable using indexed position data")


############################
# RESPONSE
############################

class TokenAddress(BaseModel):
    token_address: str


class SecurityTokenPosition(BaseModel):
    balance: int
    pending_transfer: int
    exchange_balance: int
    exchange_commitment: int
    locked: Optional[int] = Field(default=None, description="set when enable_index=true")


T = TypeVar("T")


class SecurityTokenPositionWithDetail(SecurityTokenPosition, Generic[T]):
    token: T | TokenAddress = Field(description="set when include_token_details=false or null")


class SecurityTokenPositionWithAddress(SecurityTokenPosition):
    token_address: str = Field(description="set when include_token_details=true")


class GenericSecurityTokenPositionsResponse(BaseModel, Generic[T]):
    result_set: ResultSet
    positions: Union[list[SecurityTokenPositionWithDetail[T]], list[SecurityTokenPositionWithAddress]]


class MembershipPosition(BaseModel):
    balance: int
    exchange_balance: int
    exchange_commitment: int


class MembershipPositionWithDetail(MembershipPosition):
    token: RetrieveMembershipTokenResponse = Field(description="set when include_token_details=false or null")


class MembershipPositionWithAddress(MembershipPosition):
    token_address: str = Field(description="set when include_token_details=true")


class MembershipPositionsResponse(BaseModel):
    result_set: ResultSet
    positions: Union[list[MembershipPositionWithDetail], list[MembershipPositionWithAddress]]


class CouponPosition(BaseModel):
    balance: int
    exchange_balance: int
    exchange_commitment: int
    used: int


class CouponPositionWithDetail(CouponPosition):
    token: RetrieveCouponTokenResponse = Field(description="set when include_token_details=false or null")


class CouponPositionWithAddress(CouponPosition):
    token_address: str = Field(description="set when include_token_details=true")


class CouponPositionsResponse(BaseModel):
    result_set: ResultSet
    positions: Union[list[CouponPositionWithDetail], list[CouponPositionWithAddress]]
