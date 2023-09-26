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
from datetime import datetime
from enum import Enum
from typing import Generic, Optional, TypeVar, Union

from fastapi import Query
from pydantic import BaseModel, Field, StrictStr
from pydantic.dataclasses import dataclass

from app.model.schema.base import ResultSet, SortOrder, TokenType
from app.model.schema.token_bond import RetrieveStraightBondTokenResponse
from app.model.schema.token_coupon import RetrieveCouponTokenResponse
from app.model.schema.token_membership import RetrieveMembershipTokenResponse
from app.model.schema.token_share import RetrieveShareTokenResponse


############################
# COMMON
############################
class TokenAddress(BaseModel):
    token_address: str


class SecurityTokenPosition(BaseModel):
    balance: int
    pending_transfer: int
    exchange_balance: int
    exchange_commitment: int
    locked: Optional[int] = Field(
        default=None, description="set when enable_index=true"
    )


SecurityTokenResponseT = TypeVar(
    "SecurityTokenResponseT",
    RetrieveStraightBondTokenResponse,
    RetrieveShareTokenResponse,
)


class StraightBondPositionWithDetail(SecurityTokenPosition):
    token: RetrieveStraightBondTokenResponse = Field(
        description="set when include_token_details=true"
    )


class StraightBondPositionWithAddress(SecurityTokenPosition):
    token_address: str = Field(description="set when include_token_details=false")


class SharePositionWithDetail(SecurityTokenPosition):
    token: RetrieveShareTokenResponse = Field(
        description="set when include_token_details=true"
    )


class SharePositionWithAddress(SecurityTokenPosition):
    token_address: str = Field(description="set when include_token_details=false")


class SecurityTokenPositionWithDetail(
    SecurityTokenPosition, Generic[SecurityTokenResponseT]
):
    token: SecurityTokenResponseT | TokenAddress = Field(
        description="set when include_token_details=false or null"
    )


class SecurityTokenPositionWithAddress(SecurityTokenPosition):
    token_address: str = Field(
        description="set when include_token_details=false or null"
    )


class MembershipPosition(BaseModel):
    balance: int
    exchange_balance: int
    exchange_commitment: int


class MembershipPositionWithDetail(MembershipPosition):
    token: RetrieveMembershipTokenResponse = Field(
        description="set when include_token_details=true"
    )


class MembershipPositionWithAddress(MembershipPosition):
    token_address: str = Field(description="set when include_token_details=false")


class CouponPosition(BaseModel):
    balance: int
    exchange_balance: int
    exchange_commitment: int
    used: int


class CouponPositionWithDetail(CouponPosition):
    token: RetrieveCouponTokenResponse = Field(
        description="set when include_token_details=false or null"
    )


class CouponPositionWithAddress(CouponPosition):
    token_address: str = Field(description="set when include_token_details=true")


class LockEventCategory(str, Enum):
    Lock = "Lock"
    Unlock = "Unlock"


class Locked(BaseModel):
    token_address: str
    lock_address: str
    account_address: str
    value: int


class LockedWithTokenDetail(Locked, Generic[SecurityTokenResponseT]):
    token: SecurityTokenResponseT = Field(..., description="Token information")


class LockEvent(BaseModel):
    category: LockEventCategory = Field(description="history item category")
    transaction_hash: str = Field(description="Transaction hash")
    msg_sender: Optional[str] = Field(description="Message sender", nullable=True)
    token_address: str = Field(description="Token address")
    lock_address: str = Field(description="Lock address")
    account_address: str = Field(description="Account address")
    recipient_address: Optional[str] = Field(
        default=None, description="Recipient address"
    )
    value: int = Field(description="Transfer quantity")
    data: dict = Field(description="Data")
    block_timestamp: datetime = Field(
        description="block_timestamp when Lock log was emitted (local_timezone)"
    )


class LockEventWithTokenDetail(LockEvent, Generic[SecurityTokenResponseT]):
    token: SecurityTokenResponseT = Field(..., description="Token information")


class CouponConsumption(BaseModel):
    account_address: str = Field(description="account address")
    block_timestamp: str = Field(description="consumption datetime")
    value: int = Field(description="consumption quantity")


############################
# REQUEST
############################
@dataclass
class ListAllTokenPositionQuery:
    offset: Optional[int] = Query(default=None, description="start position", ge=0)
    limit: Optional[int] = Query(default=None, description="number of set", ge=0)
    token_type_list: Optional[list[TokenType]] = Query(
        default=None, description="type of token"
    )


@dataclass
class ListAllPositionQuery:
    offset: Optional[int] = Query(default=None, description="start position", ge=0)
    limit: Optional[int] = Query(default=None, description="number of set", ge=0)
    include_token_details: Optional[bool] = Query(
        default=False, description="include token details"
    )
    enable_index: Optional[bool] = Query(
        default=False, description="enable using indexed position data"
    )


@dataclass
class GetPositionQuery:
    enable_index: Optional[bool] = Query(
        default=False, description="enable using indexed position data"
    )


class ListAllLockedSortItem(str, Enum):
    token_address = "token_address"
    lock_address = "lock_address"
    account_address = "account_address"
    value = "value"


@dataclass
class ListAllLockedPositionQuery:
    lock_address: Optional[str] = Query(default=None, description="lock address")
    offset: Optional[int] = Query(default=None, description="start position", ge=0)
    limit: Optional[int] = Query(default=None, description="number of set", ge=0)
    sort_item: ListAllLockedSortItem = Query(
        default=ListAllLockedSortItem.token_address, description="sort item"
    )
    sort_order: SortOrder = Query(
        default=SortOrder.ASC, description="sort order(0: ASC, 1: DESC)"
    )
    token_address_list: list[StrictStr] = Query(
        default=[], description="list of token address (**this affects total number**)"
    )
    include_token_details: Optional[bool] = Query(
        default=False, description="include token details"
    )


class LockEventSortItem(str, Enum):
    token_address = "token_address"
    lock_address = "lock_address"
    recipient_address = "recipient_address"
    value = "value"
    block_timestamp = "block_timestamp"


@dataclass
class ListAllLockEventQuery:
    offset: Optional[int] = Query(default=None, description="start position", ge=0)
    limit: Optional[int] = Query(default=None, description="number of set", ge=0)

    token_address_list: list[StrictStr] = Query(
        default=[], description="list of token address (**this affects total number**)"
    )
    msg_sender: Optional[str] = Query(default=None, description="message sender")
    lock_address: Optional[str] = Query(default=None, description="lock address")
    recipient_address: Optional[str] = Query(
        default=None, description="recipient address"
    )
    data: Optional[str] = Query(default=None, description="data")
    category: Optional[LockEventCategory] = Query(
        default=None, description="history item category"
    )

    sort_item: LockEventSortItem = Query(
        default=LockEventSortItem.block_timestamp, description="sort item"
    )
    sort_order: SortOrder = Query(
        default=SortOrder.DESC, description="sort order(0: ASC, 1: DESC)"
    )
    include_token_details: Optional[bool] = Query(
        default=False, description="include token details"
    )


############################
# RESPONSE
############################
class TokenPositionsResponse(BaseModel):
    result_set: ResultSet
    positions: Union[
        list[
            Union[
                StraightBondPositionWithDetail,
                SharePositionWithDetail,
                CouponPositionWithDetail,
                MembershipPositionWithDetail,
            ]
        ]
    ]


class GenericSecurityTokenPositionsResponse(BaseModel, Generic[SecurityTokenResponseT]):
    result_set: ResultSet
    positions: Union[
        list[SecurityTokenPositionWithDetail[SecurityTokenResponseT]],
        list[SecurityTokenPositionWithAddress],
    ]


class MembershipPositionsResponse(BaseModel):
    result_set: ResultSet
    positions: Union[
        list[MembershipPositionWithDetail], list[MembershipPositionWithAddress]
    ]


class CouponPositionsResponse(BaseModel):
    result_set: ResultSet
    positions: Union[list[CouponPositionWithDetail], list[CouponPositionWithAddress]]


class ListAllLockedPositionResponse(BaseModel, Generic[SecurityTokenResponseT]):
    result_set: ResultSet
    locked_positions: Union[
        list[LockedWithTokenDetail[SecurityTokenResponseT]] | list[Locked]
    ]


class ListAllLockEventsResponse(BaseModel, Generic[SecurityTokenResponseT]):
    result_set: ResultSet
    events: Union[
        list[LockEventWithTokenDetail[SecurityTokenResponseT]], list[LockEvent]
    ] = Field(description="Lock/Unlock event list")


class ListAllCouponConsumptionsResponse(BaseModel):
    __root__: list[CouponConsumption]
