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

from enum import StrEnum
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.model.db import NotificationType
from app.model.schema.base import (
    BasePaginationQuery,
    EthereumAddress,
    ResultSet,
    SortOrder,
    TokenType,
)

############################
# COMMON
############################


############################
# REQUEST
############################
class NotificationsSortItem(StrEnum):
    notification_type = "notification_type"
    priority = "priority"
    block_timestamp = "block_timestamp"
    created = "created"


class NotificationsQuery(BasePaginationQuery):
    notification_category: Optional[Literal["event_log", "attribute_change"]] = Field(
        None
    )
    address: Optional[EthereumAddress] = Field(None, description="account address")
    notification_type: Optional[NotificationType] = Field(None)
    priority: Optional[int] = Field(None, ge=0, le=2)
    sort_item: Optional[NotificationsSortItem] = Field(
        NotificationsSortItem.created, description="sort item"
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.ASC, description=SortOrder.__doc__
    )


class NotificationReadRequest(BaseModel):
    address: EthereumAddress
    is_read: bool


class NotificationsCountQuery(BaseModel):
    address: EthereumAddress = Field()


class UpdateNotificationRequest(BaseModel):
    is_read: Optional[bool] = Field(default=None, description="Read update")
    is_flagged: Optional[bool] = Field(default=None, description="Set flag")
    is_deleted: Optional[bool] = Field(default=None, description="Logical deletion")


############################
# RESPONSE
############################
class NotificationMetainfo(BaseModel):
    company_name: str
    token_address: EthereumAddress
    token_name: str
    exchange_address: EthereumAddress
    token_type: TokenType


class Notification(BaseModel):
    notification_category: Literal["event_log", "attribute_change"]
    id: str = Field(examples=["0x00000373ca8600000000000000"])
    notification_type: NotificationType = Field(examples=[NotificationType.NEW_ORDER])
    priority: int
    block_timestamp: str = Field(description="block timestamp")
    is_read: bool
    is_flagged: bool
    is_deleted: bool
    deleted_at: Optional[str] = Field(description="datetime of deletion")
    args: object
    metainfo: NotificationMetainfo | dict
    account_address: EthereumAddress
    sort_id: int
    created: str = Field(description="datetime of create")


class NotificationsResponse(BaseModel):
    result_set: ResultSet
    notifications: list[Notification]


class NotificationsCountResponse(BaseModel):
    unread_counts: int


class NotificationUpdateResponse(BaseModel):
    notification_type: NotificationType = Field(examples=[NotificationType.NEW_ORDER])
    id: str = Field(examples=["0x00000373ca8600000000000000"])
    priority: int
    block_timestamp: str = Field(description="block timestamp")
    is_read: bool
    is_flagged: bool
    is_deleted: bool
    deleted_at: Optional[str] = Field(description="datetime of deletion")
    args: object
    metainfo: NotificationMetainfo | dict
    account_address: EthereumAddress
