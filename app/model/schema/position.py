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
from typing import Annotated, Generic, Optional, TypeVar, Union

from fastapi import Query
from pydantic import BaseModel, Field, RootModel, StrictStr
from pydantic.dataclasses import dataclass

from app.model.schema.base import (
    ResultSet,
    SortOrder,
    TokenType,
    ValidatedEthereumAddress,
)
from app.model.schema.token_bond import RetrieveStraightBondTokenResponse
from app.model.schema.token_coupon import RetrieveCouponTokenResponse
from app.model.schema.token_membership import RetrieveMembershipTokenResponse
from app.model.schema.token_share import RetrieveShareTokenResponse


############################
# COMMON
############################
class TokenAddress(BaseModel):
    token_address: ValidatedEthereumAddress


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
    token_address: ValidatedEthereumAddress = Field(
        description="set when include_token_details=false"
    )


class SharePositionWithDetail(SecurityTokenPosition):
    token: RetrieveShareTokenResponse = Field(
        description="set when include_token_details=true"
    )


class SharePositionWithAddress(SecurityTokenPosition):
    token_address: ValidatedEthereumAddress = Field(
        description="set when include_token_details=false"
    )


class SecurityTokenPositionWithDetail(
    SecurityTokenPosition, Generic[SecurityTokenResponseT]
):
    token: SecurityTokenResponseT | TokenAddress = Field(
        description="set when include_token_details=false or null"
    )


class SecurityTokenPositionWithAddress(SecurityTokenPosition):
    token_address: ValidatedEthereumAddress = Field(
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
    token_address: ValidatedEthereumAddress = Field(
        description="set when include_token_details=false"
    )


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
    token_address: ValidatedEthereumAddress = Field(
        description="set when include_token_details=true"
    )


class LockEventCategory(str, Enum):
    Lock = "Lock"
    Unlock = "Unlock"


class Locked(BaseModel):
    token_address: ValidatedEthereumAddress
    lock_address: ValidatedEthereumAddress
    account_address: ValidatedEthereumAddress
    value: int


class LockedWithTokenDetail(Locked, Generic[SecurityTokenResponseT]):
    token: SecurityTokenResponseT = Field(..., description="Token information")


class LockEvent(BaseModel):
    category: LockEventCategory = Field(description="history item category")
    transaction_hash: str = Field(description="Transaction hash")
    msg_sender: Optional[ValidatedEthereumAddress] = Field(
        description="Message sender", nullable=True
    )
    token_address: ValidatedEthereumAddress = Field(description="Token address")
    lock_address: ValidatedEthereumAddress = Field(description="Lock address")
    account_address: ValidatedEthereumAddress = Field(description="Account address")
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
    offset: Annotated[Optional[int], Query(description="start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="number of set", ge=0)] = None
    token_type_list: Annotated[
        Optional[list[TokenType]], Query(description="type of token")
    ] = None


@dataclass
class ListAllPositionQuery:
    offset: Annotated[Optional[int], Query(description="start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="number of set", ge=0)] = None
    include_token_details: Annotated[
        Optional[bool], Query(description="include token details")
    ] = False
    enable_index: Annotated[
        Optional[bool], Query(description="enable using indexed position data")
    ] = None


@dataclass
class GetPositionQuery:
    enable_index: Annotated[
        Optional[bool], Query(description="enable using indexed position data")
    ] = None


class ListAllLockedSortItem(str, Enum):
    token_address = "token_address"
    lock_address = "lock_address"
    account_address = "account_address"
    value = "value"


@dataclass
class ListAllLockedPositionQuery:
    token_address_list: Annotated[
        list[StrictStr],
        Query(
            default_factory=list,
            description="list of token address (**this affects total number**)",
        ),
    ]

    lock_address: Annotated[Optional[str], Query(description="lock address")] = None
    offset: Annotated[Optional[int], Query(description="start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="number of set", ge=0)] = None
    sort_item: Annotated[ListAllLockedSortItem, Query(description="sort item")] = (
        ListAllLockedSortItem.token_address
    )
    sort_order: Annotated[
        SortOrder, Query(description="sort order(0: ASC, 1: DESC)")
    ] = SortOrder.ASC
    include_token_details: Annotated[
        Optional[bool], Query(description="include token details")
    ] = False


class LockEventSortItem(str, Enum):
    token_address = "token_address"
    lock_address = "lock_address"
    recipient_address = "recipient_address"
    value = "value"
    block_timestamp = "block_timestamp"


@dataclass
class ListAllLockEventQuery:
    token_address_list: Annotated[
        list[StrictStr],
        Query(
            default_factory=list,
            description="list of token address (**this affects total number**)",
        ),
    ]

    offset: Annotated[Optional[int], Query(description="start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="number of set", ge=0)] = None

    msg_sender: Annotated[Optional[str], Query(description="message sender")] = None
    lock_address: Annotated[Optional[str], Query(description="lock address")] = None
    recipient_address: Annotated[
        Optional[str], Query(description="recipient address")
    ] = None
    data: Annotated[Optional[str], Query(description="data")] = None
    category: Annotated[
        Optional[LockEventCategory], Query(description="history item category")
    ] = None

    sort_item: Annotated[LockEventSortItem, Query(description="sort item")] = (
        LockEventSortItem.block_timestamp
    )
    sort_order: Annotated[
        SortOrder, Query(description="sort order(0: ASC, 1: DESC)")
    ] = SortOrder.DESC
    include_token_details: Annotated[
        Optional[bool], Query(description="include token details")
    ] = False


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


class ListAllCouponConsumptionsResponse(RootModel[list[CouponConsumption]]):
    pass
