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
from enum import Enum
from typing import Optional
from pydantic import (
    BaseModel,
    Field,
    validator
)
from web3 import Web3

from app.model.db import NotificationType
from app.model.schema.base import (
    ResultSetQuery,
    ResultSet,
    SortOrder, QueryModel
)
from app.model.schema.token import TokenType

############################
# COMMON
############################


############################
# REQUEST
############################

class NotificationsSortItem(str, Enum):
    notification_type = "notification_type"
    priority = "priority"
    block_timestamp = "block_timestamp"
    created = "created"


class NotificationsQuery(ResultSetQuery):
    address: Optional[str]
    notification_type: Optional[NotificationType]
    priority: Optional[int] = Field(ge=0, le=2)

    sort_item: Optional[NotificationsSortItem] = Field(
        default=NotificationsSortItem.created,
        description="sort item"
    )
    sort_order: Optional[SortOrder] = Field(default=SortOrder.ASC, description="sort order(0: ASC, 1: DESC)")

    @validator("address")
    def address_is_valid_address(cls, v):
        if v is not None:
            if not Web3.isAddress(v):
                raise ValueError("address is not a valid address")
        return v


class NotificationReadRequest(BaseModel):
    address: str
    is_read: bool

    @validator("address")
    def address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("address is not a valid address")
        return v


class NotificationsCountQuery(QueryModel):
    address: str

    @validator("address")
    def address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("address is not a valid address")
        return v


class UpdateNotificationRequest(BaseModel):
    is_read: Optional[bool] = Field(description="Read update")
    is_flagged: Optional[bool] = Field(description="Set flag")
    is_deleted: Optional[bool] = Field(description="Logical deletion")


############################
# RESPONSE
############################

class NotificationMetainfo(BaseModel):
    company_name: str
    token_address: str
    token_name: str
    exchange_address: str
    token_type: TokenType


class Notification(BaseModel):
    notification_type: NotificationType = Field(example=NotificationType.NEW_ORDER)
    id: str = Field(example="0x00000373ca8600000000000000")
    priority: int
    block_timestamp: str = Field(description="block timestamp")
    is_read: bool
    is_flagged: bool
    is_deleted: bool
    deleted_at: Optional[str] = Field(description="datetime of deletion")
    args: object
    metainfo: NotificationMetainfo | dict
    account_address: str
    sort_id: int
    created: str = Field(description="datetime of create")


class NotificationsResponse(BaseModel):
    result_set: ResultSet
    notifications: list[Notification]


class NotificationsCountResponse(BaseModel):
    unread_counts: int


class NotificationUpdateResponse(BaseModel):
    notification_type: NotificationType = Field(example=NotificationType.NEW_ORDER)
    id: str = Field(example="0x00000373ca8600000000000000")
    priority: int
    block_timestamp: str = Field(description="block timestamp")
    is_read: bool
    is_flagged: bool
    is_deleted: bool
    deleted_at: Optional[str] = Field(description="datetime of deletion")
    args: object
    metainfo: NotificationMetainfo | dict
    account_address: str
