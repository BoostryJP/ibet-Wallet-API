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
from enum import Enum
from typing import Optional
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, Field, NonNegativeInt

from app.model.schema.base import ResultSet

############################
# COMMON
############################


class TokenType(str, Enum):
    IbetStraightBond = "IbetStraightBond"
    IbetShare = "IbetShare"
    IbetMembership = "IbetMembership"
    IbetCoupon = "IbetCoupon"


class TransferSourceEvent(str, Enum):
    Transfer = "Transfer"
    Unlock = "Unlock"


############################
# REQUEST
############################


class CreateTokenHoldersCollectionRequest(BaseModel):
    list_id: UUID = Field(
        description="Unique id to be assigned to each token holder list."
        "This must be Version4 UUID.",
        example="cfd83622-34dc-4efe-a68b-2cc275d3d824",
    )
    block_number: int = Field(description="block number")


@dataclass
class ListAllTokenHoldersQuery:
    exclude_owner: Optional[bool] = Query(default=False, description="exclude owner")


@dataclass
class RetrieveTokenHoldersCountQuery:
    exclude_owner: Optional[bool] = Query(default=False, description="exclude owner")


@dataclass
class ListAllTransferHistoryQuery:
    offset: Optional[NonNegativeInt] = Query(default=None, description="start position")
    limit: Optional[NonNegativeInt] = Query(default=None, description="number of set")
    source_event: Optional[TransferSourceEvent] = Query(
        default=None, description="source event of transfer"
    )
    data: Optional[str] = Query(default=None, description="source event data")


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
    locked: Optional[int] = Field(default=0)


class TokenHoldersResponse(BaseModel):
    __root__: list[TokenHolder]


class TokenHoldersCountResponse(BaseModel):
    count: int


class TokenHoldersCollectionBatchStatus(str, Enum):
    pending = "pending"
    done = "done"
    failed = "failed"


class CreateTokenHoldersCollectionResponse(BaseModel):
    list_id: UUID = Field(
        description="Unique id to be assigned to each token holder list."
        "This must be Version4 UUID.",
        example="cfd83622-34dc-4efe-a68b-2cc275d3d824",
    )
    status: TokenHoldersCollectionBatchStatus = Field(
        description="status code of batch job"
    )


class TokenHoldersCollectionHolder(BaseModel):
    account_address: str = Field(description="Account address of token holder.")
    hold_balance: int = Field(
        description="Amount of balance."
        "This includes balance/pending_transfer/exchange_balance/exchange_commitment/locked."
    )
    locked_balance: int = Field(description="Amount of locked balance.")


class TokenHoldersCollectionResponse(BaseModel):
    status: TokenHoldersCollectionBatchStatus
    holders: list[TokenHoldersCollectionHolder] = Field(
        description="Token holder list." "This list is excluding token owner address."
    )


class TransferHistory(BaseModel):
    transaction_hash: str = Field(description="Transaction hash")
    token_address: str = Field(description="Token address")
    from_address: str = Field(description="Account address of transfer source")
    to_address: str = Field(description="Account address of transfer destination")
    value: int = Field(description="Transfer quantity")
    source_event: TransferSourceEvent = Field(description="Source Event")
    data: dict | None = Field(description="Event data")
    created: str = Field(
        description="block_timestamp when Transfer log was emitted (local timezone)"
    )


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
    application_datetime: str = Field(
        description="application datetime (local timezone)"
    )
    application_blocktimestamp: str = Field(
        description="application blocktimestamp (local timezone)"
    )
    approval_datetime: Optional[str] = Field(
        description="approval datetime (local timezone)"
    )
    approval_blocktimestamp: Optional[str] = Field(
        description="approval blocktimestamp (local timezone)"
    )
    cancelled: Optional[bool] = Field(description="Cancellation status")
    transfer_approved: Optional[bool] = Field(description="transfer approval status")


class TransferApprovalHistoriesResponse(BaseModel):
    result_set: ResultSet
    transfer_approval_history: list[TransferApprovalHistory] = Field(
        description="Transfer approval history"
    )
