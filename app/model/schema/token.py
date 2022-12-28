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
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from fastapi import Query
from typing import Optional
from uuid import UUID
from pydantic import (
    BaseModel,
    Field,
)

from app.model.schema.base import (
    ResultSet,
    SortOrder,
)


############################
# COMMON
############################

class TokenType(str, Enum):
    IbetStraightBond = "IbetStraightBond"
    IbetShare = "IbetShare"
    IbetMembership = "IbetMembership"
    IbetCoupon = "IbetCoupon"


############################
# REQUEST
############################

class CreateTokenHoldersCollectionRequest(BaseModel):
    list_id: UUID = Field(description="Unique id to be assigned to each token holder list."
                                      "This must be Version4 UUID.",
                          example="cfd83622-34dc-4efe-a68b-2cc275d3d824")
    block_number: int = Field(description="block number")


@dataclass
class ListAllTokenHoldersQuery:
    exclude_owner: Optional[bool] = Query(default=False, description="exclude owner")


@dataclass
class RetrieveTokenHoldersCountQuery:
    exclude_owner: Optional[bool] = Query(default=False, description="exclude owner")


class LockEventsSortItem(str, Enum):
    lock_address = "lock_address"
    account_address = "account_address"
    value = "value"
    block_number = "block_number"
    block_timestamp = "block_timestamp"


@dataclass
class ListAllLockEventsQuery:
    offset: Optional[int] = Query(default=None, description="start position", ge=0)
    limit: Optional[int] = Query(default=None, description="number of set", ge=0)

    account_address: Optional[str] = Query(default=None, description="account address")
    lock_address: Optional[str] = Query(default=None, description="lock address")
    data: Optional[str] = Query(default=None, description="data")

    sort_item: LockEventsSortItem = Query(
        default=LockEventsSortItem.block_timestamp,
        description="sort item"
    )
    sort_order: SortOrder = Query(default=SortOrder.DESC, description="sort order(0: ASC, 1: DESC)")


class UnlockEventsSortItem(str, Enum):
    lock_address = "lock_address"
    account_address = "account_address"
    recipient_address = "recipient_address"
    value = "value"
    block_number = "block_number"
    block_timestamp = "block_timestamp"


@dataclass
class ListAllUnlockEventsQuery:
    offset: Optional[int] = Query(default=None, description="start position", ge=0)
    limit: Optional[int] = Query(default=None, description="number of set", ge=0)

    account_address: Optional[str] = Query(default=None, description="account address")
    lock_address: Optional[str] = Query(default=None, description="lock address")
    recipient_address: Optional[str] = Query(default=None, description="recipient address")
    data: Optional[str] = Query(default=None, description="data")

    sort_item: UnlockEventsSortItem = Query(
        default=UnlockEventsSortItem.block_timestamp,
        description="sort item"
    )
    sort_order: SortOrder = Query(default=SortOrder.DESC, description="sort order(0: ASC, 1: DESC)")


############################
# RESPONSE
############################

class TokenStatusResponse(BaseModel):
    token_template: str = Field(example="IbetStraightBond")
    status: bool
    transferable: bool


class TokenHolder(BaseModel):
    token_address: str
    account_address: str
    amount: Optional[int] = Field(default=0)
    pending_transfer: Optional[int] = Field(default=0)
    exchange_balance: Optional[int] = Field(default=0)
    exchange_commitment: Optional[int] = Field(default=0)


class TokenHoldersResponse(BaseModel):
    __root__: list[TokenHolder]


class TokenHoldersCountResponse(BaseModel):
    count: int


class TokenHoldersCollectionBatchStatus(str, Enum):
    pending = "pending"
    done = "done"
    failed = "failed"


class CreateTokenHoldersCollectionResponse(BaseModel):
    list_id: UUID = Field(description="Unique id to be assigned to each token holder list."
                                      "This must be Version4 UUID.",
                          example="cfd83622-34dc-4efe-a68b-2cc275d3d824")
    status: TokenHoldersCollectionBatchStatus = Field(description="status code of batch job")


class TokenHoldersCollectionHolder(BaseModel):
    account_address: str = Field(description="Account address of token holder.")
    hold_balance: int = Field(description="Amount of balance."
                                          "This includes balance/pending_transfer/exchange_balance/exchange_commitment.")


class TokenHoldersCollectionResponse(BaseModel):
    status: TokenHoldersCollectionBatchStatus
    holders: list[TokenHoldersCollectionHolder] = Field(description="Token holder list."
                                                                    "This list is excluding token owner address.")


class TransferHistory(BaseModel):
    transaction_hash: str = Field(description="Transaction hash")
    token_address: str = Field(description="Token address")
    from_address: str = Field(description="Account address of transfer source")
    to_address: str = Field(description="Account address of transfer destination")
    value: int = Field(description="Transfer quantity")
    created: str = Field(description="block_timestamp when Transfer log was emitted (JST)")


class TransferHistoriesResponse(BaseModel):
    result_set: ResultSet
    transfer_history: list[TransferHistory] = Field(description="Transfer history")


class TransferApprovalHistory(BaseModel):
    token_address: str = Field(description="Token address")
    exchange_address: Optional[str] = Field(description="Exchange address")
    application_id: int = Field(description="Application id")
    from_address: str = Field(description="Account address of transfer source")
    to_address: str = Field(description="Account address of transfer destination")
    value: int = Field(description="Transfer quantity")
    application_datetime: str = Field(description="application datetime (JST)")
    application_blocktimestamp: str = Field(description="application blocktimestamp (JST)")
    approval_datetime: Optional[str] = Field(description="approval datetime (JST)")
    approval_blocktimestamp: Optional[str] = Field(description="approval blocktimestamp (JST)")
    cancelled: Optional[bool] = Field(description="Cancellation status")
    transfer_approved: Optional[bool] = Field(description="transfer approval status")


class TransferApprovalHistoriesResponse(BaseModel):
    result_set: ResultSet
    transfer_approval_history: list[TransferApprovalHistory] = Field(description="Transfer approval history")


class LockEvent(BaseModel):
    transaction_hash: str = Field(description="Transaction hash")
    token_address: str = Field(description="Token address")
    lock_address: str = Field(description="Lock address")
    account_address: str = Field(description="Account address")
    value: int = Field(description="Transfer quantity")
    data: dict = Field(description="Data")
    block_timestamp: datetime = Field(description="block_timestamp when Lock log was emitted (JST)")


class LockEventsResponse(BaseModel):
    result_set: ResultSet
    lock_events: list[LockEvent] = Field(description="Lock event list")


class UnlockEvent(BaseModel):
    transaction_hash: str = Field(description="Transaction hash")
    token_address: str = Field(description="Token address")
    lock_address: str = Field(description="Lock address")
    account_address: str = Field(description="Account address")
    recipient_address: str = Field(description="Recipient address")
    value: int = Field(description="Transfer quantity")
    data: dict = Field(description="Data")
    block_timestamp: datetime = Field(description="block_timestamp when Lock log was emitted (JST)")


class UnlockEventsResponse(BaseModel):
    result_set: ResultSet
    unlock_events: list[UnlockEvent] = Field(description="Unlock event list")
