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
from typing import Annotated, Optional

from fastapi import Query
from pydantic import UUID4, BaseModel, Field, StrictStr

from app.model.schema.base import (
    ResultSet,
    SortOrder,
    TokenType,
    ValidatedEthereumAddress,
    ValueOperator,
)


############################
# COMMON
############################
class TransferSourceEvent(str, Enum):
    Transfer = "Transfer"
    Unlock = "Unlock"


############################
# REQUEST
############################
class CreateTokenHoldersCollectionRequest(BaseModel):
    list_id: UUID4 = Field(
        description="Unique id to be assigned to each token holder list."
        "This must be Version4 UUID.",
        examples=["cfd83622-34dc-4efe-a68b-2cc275d3d824"],
    )
    block_number: int = Field(description="block number")


@dataclass
class ListAllTokenHoldersQuery:
    exclude_owner: Annotated[Optional[bool], Query(description="exclude owner")] = False
    offset: Annotated[Optional[int], Query(description="start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="number of set", ge=0)] = None


class SearchTokenHoldersRequest(BaseModel):
    account_address_list: list[StrictStr] = Field(
        [],
        description="list of token address (**this affects total number**)",
    )
    exclude_owner: Optional[bool] = Field(default=False, description="exclude owner")
    offset: Optional[int] = Field(default=None, description="start position", ge=0)
    limit: Optional[int] = Field(default=None, description="number of set", ge=0)


@dataclass
class RetrieveTokenHoldersCountQuery:
    exclude_owner: Annotated[Optional[bool], Query(description="exclude owner")] = False


@dataclass
class ListAllTransferHistoryQuery:
    offset: Annotated[Optional[int], Query(description="start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="number of set", ge=0)] = None
    source_event: Annotated[
        Optional[TransferSourceEvent], Query(description="source event of transfer")
    ] = None
    data: Annotated[Optional[str], Query(description="source event data")] = None
    transaction_hash: Annotated[
        Optional[str], Query(description="transaction hash")
    ] = None
    value: Annotated[Optional[int], Query(description="value")] = None
    value_operator: Annotated[
        Optional[ValueOperator],
        Query(
            description="value filter condition(0: equal, 1: greater than, 2: less than)"
        ),
    ] = ValueOperator.EQUAL


class SearchTransferHistorySortItem(str, Enum):
    from_account_address_list = "from_account_address_list"
    to_account_address_list = "to_account_address_list"
    id = "id"
    created = "created"
    transaction_hash = "transaction_hash"
    from_address = "from_address"
    to_address = "to_address"
    value = "value"


class SearchTransferHistoryRequest(BaseModel):
    account_address_list: list[StrictStr] = Field(
        [],
        description="list of token address (**this affects total number**)",
    )
    offset: Optional[int] = Field(default=None, description="start position", ge=0)
    limit: Optional[int] = Field(default=None, description="number of set", ge=0)
    source_event: Optional[TransferSourceEvent] = Field(
        default=None, description="source event of transfer"
    )
    data: Optional[str] = Field(default=None, description="source event data")
    transaction_hash: Optional[str] = Field(
        default=None, description="transaction hash"
    )
    created_from: Optional[datetime] = Field(
        default=None, description="created from datetime"
    )
    created_to: Optional[datetime] = Field(
        default=None, description="created to datetime"
    )
    value: Optional[int] = Field(default=None, description="value")
    value_operator: Optional[ValueOperator] = Field(
        default=ValueOperator.EQUAL,
        description="value filter condition(0: equal, 1: greater than, 2: less than)",
    )
    sort_item: Optional[SearchTransferHistorySortItem] = Field(
        default=SearchTransferHistorySortItem.id, description="sort item"
    )
    sort_order: Optional[SortOrder] = Field(
        default=SortOrder.ASC, description="sort order"
    )


@dataclass
class ListAllTransferApprovalHistoryQuery:
    offset: Annotated[Optional[int], Query(description="start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="number of set", ge=0)] = None
    value: Annotated[Optional[int], Query(description="value")] = None
    value_operator: Annotated[
        Optional[ValueOperator],
        Query(
            description="value filter condition(0: equal, 1: greater than, 2: less than)"
        ),
    ] = ValueOperator.EQUAL


class SearchTransferApprovalHistorySortItem(str, Enum):
    from_account_address_list = "from_account_address_list"
    to_account_address_list = "to_account_address_list"
    application_id = "application_id"
    created = "created"
    from_address = "from_address"
    to_address = "to_address"
    value = "value"
    application_datetime = "application_datetime"
    application_blocktimestamp = "application_blocktimestamp"
    approval_datetime = "approval_datetime"
    approval_blocktimestamp = "approval_blocktimestamp"
    cancelled = "cancelled"


class SearchTransferApprovalHistoryRequest(BaseModel):
    account_address_list: list[StrictStr] = Field(
        [],
        description="list of token address (**this affects total number**)",
    )
    offset: Optional[int] = Field(default=None, description="start position", ge=0)
    limit: Optional[int] = Field(default=None, description="number of set", ge=0)
    application_datetime_from: Optional[datetime] = Field(
        default=None, description="application from datetime"
    )
    application_datetime_to: Optional[datetime] = Field(
        default=None, description="application to datetime"
    )
    application_blocktimestamp_from: Optional[datetime] = Field(
        default=None, description="application from block timestamp"
    )
    application_blocktimestamp_to: Optional[datetime] = Field(
        default=None, description="application to block timestamp"
    )
    approval_datetime_from: Optional[datetime] = Field(
        default=None, description="approval from datetime"
    )
    approval_datetime_to: Optional[datetime] = Field(
        default=None, description="approval to datetime"
    )
    approval_blocktimestamp_from: Optional[datetime] = Field(
        default=None, description="approval from block timestamp"
    )
    approval_blocktimestamp_to: Optional[datetime] = Field(
        default=None, description="approval to block timestamp"
    )
    value: Optional[int] = Field(default=None, description="value")
    value_operator: Optional[ValueOperator] = Field(
        default=ValueOperator.EQUAL,
        description="value filter condition(0: equal, 1: greater than, 2: less than)",
    )
    sort_item: Optional[SearchTransferApprovalHistorySortItem] = Field(
        default=SearchTransferApprovalHistorySortItem.application_id,
        description="sort item",
    )
    sort_order: Optional[SortOrder] = Field(
        default=SortOrder.ASC, description="sort order"
    )


############################
# RESPONSE
############################
class TokenStatusResponse(BaseModel):
    token_template: TokenType = Field(examples=["IbetStraightBond"])
    status: bool
    transferable: bool


class TokenHolder(BaseModel):
    token_address: ValidatedEthereumAddress
    account_address: ValidatedEthereumAddress
    amount: int = Field(default=0)
    pending_transfer: int = Field(default=0)
    exchange_balance: int = Field(default=0)
    exchange_commitment: int = Field(default=0)
    locked: int = Field(default=0)


class TokenHoldersResponse(BaseModel):
    result_set: ResultSet
    token_holder_list: list[TokenHolder]


class TokenHoldersCountResponse(BaseModel):
    count: int


class TokenHoldersCollectionBatchStatus(str, Enum):
    pending = "pending"
    done = "done"
    failed = "failed"


class CreateTokenHoldersCollectionResponse(BaseModel):
    list_id: UUID4 = Field(
        description="Unique id to be assigned to each token holder list."
        "This must be Version4 UUID.",
        examples=["cfd83622-34dc-4efe-a68b-2cc275d3d824"],
    )
    status: TokenHoldersCollectionBatchStatus = Field(
        description="status code of batch job"
    )


class TokenHoldersCollectionHolder(BaseModel):
    account_address: ValidatedEthereumAddress = Field(
        description="Account address of token holder."
    )
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
    token_address: ValidatedEthereumAddress = Field(description="Token address")
    from_address: ValidatedEthereumAddress = Field(
        description="Account address of transfer source"
    )
    to_address: ValidatedEthereumAddress = Field(
        description="Account address of transfer destination"
    )
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
    token_address: ValidatedEthereumAddress = Field(description="Token address")
    exchange_address: Optional[ValidatedEthereumAddress] = Field(
        description="Exchange address"
    )
    application_id: int = Field(description="Application id")
    from_address: ValidatedEthereumAddress = Field(
        description="Account address of transfer source"
    )
    to_address: ValidatedEthereumAddress = Field(
        description="Account address of transfer destination"
    )
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
