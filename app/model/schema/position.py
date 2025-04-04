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
from enum import StrEnum
from typing import Generic, Optional, TypeVar, Union

from pydantic import BaseModel, Field, RootModel, StrictStr

from app.model.schema.base import (
    BasePaginationQuery,
    EthereumAddress,
    ResultSet,
    SortOrder,
    TokenType,
)
from app.model.schema.token_bond import RetrieveStraightBondTokenResponse
from app.model.schema.token_coupon import RetrieveCouponTokenResponse
from app.model.schema.token_membership import RetrieveMembershipTokenResponse
from app.model.schema.token_share import RetrieveShareTokenResponse


############################
# COMMON
############################
class TokenAddress(BaseModel):
    token_address: EthereumAddress


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
    token_address: EthereumAddress = Field(
        description="set when include_token_details=false"
    )


class SharePositionWithDetail(SecurityTokenPosition):
    token: RetrieveShareTokenResponse = Field(
        description="set when include_token_details=true"
    )


class SharePositionWithAddress(SecurityTokenPosition):
    token_address: EthereumAddress = Field(
        description="set when include_token_details=false"
    )


class SecurityTokenPositionWithDetail(
    SecurityTokenPosition, Generic[SecurityTokenResponseT]
):
    token: SecurityTokenResponseT | TokenAddress = Field(
        description="set when include_token_details=false or null"
    )


class SecurityTokenPositionWithAddress(SecurityTokenPosition):
    token_address: EthereumAddress = Field(
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
    token_address: EthereumAddress = Field(
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
    token_address: EthereumAddress = Field(
        description="set when include_token_details=true"
    )


class LockEventCategory(StrEnum):
    Lock = "Lock"
    Unlock = "Unlock"


class Locked(BaseModel):
    token_address: EthereumAddress
    lock_address: EthereumAddress
    account_address: EthereumAddress
    value: int


class LockedWithTokenDetail(Locked, Generic[SecurityTokenResponseT]):
    token: SecurityTokenResponseT = Field(..., description="Token information")


class LockEvent(BaseModel):
    category: LockEventCategory = Field(description="history item category")
    is_forced: bool = Field(description="Set to `True` for force lock/unlock events")
    transaction_hash: str = Field(description="Transaction hash")
    msg_sender: Optional[EthereumAddress] = Field(..., description="Message sender")
    token_address: EthereumAddress = Field(description="Token address")
    lock_address: EthereumAddress = Field(description="Lock address")
    account_address: EthereumAddress = Field(description="Account address")
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
class ListAllTokenPositionQuery(BasePaginationQuery):
    token_type_list: Optional[list[TokenType]] = Field(
        None, description="type of token"
    )


class ListAllPositionQuery(BasePaginationQuery):
    include_token_details: Optional[bool] = Field(
        False, description="include token details"
    )
    enable_index: Optional[bool] = Field(
        None, description="enable using indexed position data"
    )


class GetPositionQuery(BaseModel):
    enable_index: Optional[bool] = Field(
        None, description="enable using indexed position data"
    )


class ListAllLockedSortItem(StrEnum):
    token_address = "token_address"
    lock_address = "lock_address"
    account_address = "account_address"
    value = "value"


class ListAllLockedPositionQuery(BasePaginationQuery):
    token_address_list: list[StrictStr] = Field(
        default_factory=list,
        description="list of token address (**this affects total number**)",
    )
    lock_address: Optional[str] = Field(None, description="lock address")
    include_token_details: Optional[bool] = Field(
        False, description="include token details"
    )

    sort_item: ListAllLockedSortItem = Field(
        ListAllLockedSortItem.token_address, description="sort item"
    )
    sort_order: SortOrder = Field(SortOrder.ASC, description=SortOrder.__doc__)


class LockEventSortItem(StrEnum):
    token_address = "token_address"
    lock_address = "lock_address"
    recipient_address = "recipient_address"
    value = "value"
    block_timestamp = "block_timestamp"


class ListAllLockEventQuery(BasePaginationQuery):
    token_address_list: list[StrictStr] = Field(
        default_factory=list,
        description="list of token address (**this affects total number**)",
    )
    msg_sender: Optional[str] = Field(None, description="message sender")
    lock_address: Optional[str] = Field(None, description="lock address")
    recipient_address: Optional[str] = Field(None, description="recipient address")
    data: Optional[str] = Field(None, description="data")
    category: Optional[LockEventCategory] = Field(
        None, description="history item category"
    )
    include_token_details: Optional[bool] = Field(
        False, description="include token details"
    )

    sort_item: LockEventSortItem = Field(
        LockEventSortItem.block_timestamp, description="sort item"
    )
    sort_order: SortOrder = Field(SortOrder.DESC, description=SortOrder.__doc__)


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
