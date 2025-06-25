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
from typing import Literal, Optional

from pydantic import UUID4, BaseModel, Field, StrictStr

from app.model.schema.base import (
    BasePaginationQuery,
    EthereumAddress,
    ResultSet,
    SortOrder,
    TokenType,
    ValidatedNaiveUTCDatetime,
    ValueOperator,
)


############################
# COMMON
############################
class TransferSourceEvent(StrEnum):
    Transfer = "Transfer"
    Unlock = "Unlock"
    ForceUnlock = "ForceUnlock"


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


class ListAllTokenHoldersQuery(BasePaginationQuery):
    account_tag: Optional[str] = Field(
        None, description="account tag (**this affects total number**)"
    )
    exclude_owner: Optional[bool] = Field(False, description="exclude owner")
    amount: Optional[int] = Field(None, description="amount")
    amount_operator: Optional[ValueOperator] = Field(
        ValueOperator.EQUAL,
        description="value filter condition(0: equal, 1: greater than, 2: less than)",
    )
    pending_transfer: Optional[int] = Field(None, description="pending transfer")
    pending_transfer_operator: Optional[ValueOperator] = Field(
        ValueOperator.EQUAL,
        description="value filter condition(0: equal, 1: greater than, 2: less than)",
    )
    exchange_balance: Optional[int] = Field(None, description="exchange balance")
    exchange_balance_operator: Optional[ValueOperator] = Field(
        ValueOperator.EQUAL,
        description="value filter condition(0: equal, 1: greater than, 2: less than)",
    )
    exchange_commitment: Optional[int] = Field(None, description="exchange commitment")
    exchange_commitment_operator: Optional[ValueOperator] = Field(
        ValueOperator.EQUAL,
        description="value filter condition(0: equal, 1: greater than, 2: less than)",
    )
    locked: Optional[int] = Field(None, description="locked")
    locked_operator: Optional[ValueOperator] = Field(
        ValueOperator.EQUAL,
        description="value filter condition(0: equal, 1: greater than, 2: less than)",
    )


class SearchTokenHoldersSortItem(StrEnum):
    created = "created"
    account_address_list = "account_address_list"
    amount = "amount"
    pending_transfer = "pending_transfer"
    exchange_balance = "exchange_balance"
    exchange_commitment = "exchange_commitment"
    locked = "locked"


class SearchTokenHoldersRequest(BaseModel):
    account_address_list: list[StrictStr] = Field(
        [],
        description="list of token address (**this affects total number**)",
    )
    exclude_owner: Optional[bool] = Field(default=False, description="exclude owner")
    offset: Optional[int] = Field(default=None, description="start position", ge=0)
    limit: Optional[int] = Field(default=None, description="number of set", ge=0)

    amount: Optional[int] = Field(default=None, description="amount")
    amount_operator: Optional[ValueOperator] = Field(
        default=ValueOperator.EQUAL,
        description="value filter condition(0: equal, 1: greater than, 2: less than)",
    )
    pending_transfer: Optional[int] = Field(
        default=None, description="pending transfer"
    )
    pending_transfer_operator: Optional[ValueOperator] = Field(
        default=ValueOperator.EQUAL,
        description="value filter condition(0: equal, 1: greater than, 2: less than)",
    )
    exchange_balance: Optional[int] = Field(
        default=None, description="exchange balance"
    )
    exchange_balance_operator: Optional[ValueOperator] = Field(
        default=ValueOperator.EQUAL,
        description="value filter condition(0: equal, 1: greater than, 2: less than)",
    )
    exchange_commitment: Optional[int] = Field(
        default=None, description="exchange commitment"
    )
    exchange_commitment_operator: Optional[ValueOperator] = Field(
        default=ValueOperator.EQUAL,
        description="value filter condition(0: equal, 1: greater than, 2: less than)",
    )
    locked: Optional[int] = Field(default=None, description="locked")
    locked_operator: Optional[ValueOperator] = Field(
        default=ValueOperator.EQUAL,
        description="value filter condition(0: equal, 1: greater than, 2: less than)",
    )
    sort_item: Optional[SearchTokenHoldersSortItem] = Field(
        default=SearchTokenHoldersSortItem.created, description="sort item"
    )
    sort_order: Optional[SortOrder] = Field(
        default=SortOrder.DESC, description="sort order"
    )


class RetrieveTokenHoldersCountQuery(BaseModel):
    account_tag: Optional[str] = Field(
        None, description="account tag (**this affects total number**)"
    )
    exclude_owner: Optional[bool] = Field(False, description="exclude owner")


class ListAllTransferHistoryQuery(BasePaginationQuery):
    account_tag: Optional[str] = Field(
        None, description="account tag (**this affects total number**)"
    )
    source_event: Optional[TransferSourceEvent] = Field(
        None, description="source event of transfer"
    )
    data: Optional[str] = Field(None, description="source event data")
    token_address: Optional[str] = Field(None, description="token address")
    transaction_hash: Optional[str] = Field(None, description="transaction hash")
    from_address: Optional[str] = Field(None, description="from address")
    to_address: Optional[str] = Field(None, description="to address")
    value: Optional[int] = Field(None, description="value")
    value_operator: Optional[ValueOperator] = Field(
        ValueOperator.EQUAL,
        description="value filter condition(0: equal, 1: greater than, 2: less than)",
    )
    created_from: Optional[ValidatedNaiveUTCDatetime] = Field(
        None, description="created datetime (From)"
    )
    created_to: Optional[ValidatedNaiveUTCDatetime] = Field(
        None, description="created datetime (To)"
    )


class ListTokenTransferHistoryQuery(BasePaginationQuery):
    account_tag: Optional[str] = Field(
        None, description="account tag (**this affects total number**)"
    )
    source_event: Optional[TransferSourceEvent] = Field(
        None, description="source event of transfer"
    )
    data: Optional[str] = Field(None, description="source event data")
    transaction_hash: Optional[str] = Field(None, description="transaction hash")
    from_address: Optional[str] = Field(None, description="from address")
    to_address: Optional[str] = Field(None, description="to address")
    value: Optional[int] = Field(None, description="value")
    value_operator: Optional[ValueOperator] = Field(
        ValueOperator.EQUAL,
        description="value filter condition(0: equal, 1: greater than, 2: less than)",
    )
    created_from: Optional[ValidatedNaiveUTCDatetime] = Field(
        None, description="created datetime (From)"
    )
    created_to: Optional[ValidatedNaiveUTCDatetime] = Field(
        None, description="created datetime (To)"
    )


class SearchTransferHistorySortItem(StrEnum):
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
        description="list of account address (**this affects total number**)",
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
    from_address: Optional[str] = Field(default=None, description="from address")
    to_address: Optional[str] = Field(default=None, description="to address")
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


class ListAllTransferApprovalHistoryQuery(BasePaginationQuery):
    account_tag: Optional[str] = Field(
        None, description="account tag (**this affects total number**)"
    )
    from_address: Optional[str] = Field(None, description="from address")
    to_address: Optional[str] = Field(None, description="to address")
    value: Optional[int] = Field(None, description="value")
    value_operator: Optional[ValueOperator] = Field(
        ValueOperator.EQUAL,
        description="value filter condition(0: equal, 1: greater than, 2: less than)",
    )


class SearchTransferApprovalHistorySortItem(StrEnum):
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
        description="list of account address (**this affects total number**)",
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
    from_address: Optional[str] = Field(default=None, description="from address")
    to_address: Optional[str] = Field(default=None, description="to address")
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
class TokenTemplateResponse(BaseModel):
    token_template: TokenType = Field(examples=["IbetStraightBond"])


class TokenStatusResponse(BaseModel):
    token_template: TokenType = Field(examples=["IbetStraightBond"])
    owner_address: EthereumAddress
    name: str
    status: bool
    transferable: bool


class TokenHolder(BaseModel):
    token_address: EthereumAddress
    account_address: EthereumAddress
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


class TokenHoldersCollectionBatchStatus(StrEnum):
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
    account_address: EthereumAddress = Field(
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
        description="Token holder list.This list is excluding token owner address."
    )


class TransferHistoryBase(BaseModel):
    transaction_hash: str = Field(description="Transaction hash")
    token_address: EthereumAddress = Field(description="Token address")
    from_address: EthereumAddress = Field(
        description="Account address of transfer source"
    )
    to_address: EthereumAddress = Field(
        description="Account address of transfer destination"
    )
    value: int = Field(description="Transfer quantity")
    data: dict | None = Field(description="Event data")
    message: (
        Literal[
            "garnishment",
            "inheritance",
            "force_unlock",
        ]
        | None
    )
    created: str = Field(
        description="block_timestamp when Transfer log was emitted (local timezone)"
    )


class TransferHistory(TransferHistoryBase):
    source_event: Literal[TransferSourceEvent.Transfer] = Field(
        description="Source Event"
    )
    data: None = Field(description="Event data")


class DataMessage(BaseModel):
    message: Literal[
        "garnishment",
        "inheritance",
        "force_unlock",
    ]


class UnlockTransferHistory(TransferHistoryBase):
    source_event: Literal[
        TransferSourceEvent.Unlock, TransferSourceEvent.ForceUnlock
    ] = Field(description="Source Event")
    data: DataMessage | dict = Field(description="Event data")


class TransferHistoriesResponse(BaseModel):
    result_set: ResultSet
    transfer_history: list[TransferHistory | UnlockTransferHistory] = Field(
        description="Transfer history"
    )


class TransferApprovalHistory(BaseModel):
    token_address: EthereumAddress = Field(description="Token address")
    exchange_address: Optional[EthereumAddress] = Field(description="Exchange address")
    application_id: int = Field(description="Application id")
    from_address: EthereumAddress = Field(
        description="Account address of transfer source"
    )
    to_address: EthereumAddress = Field(
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
