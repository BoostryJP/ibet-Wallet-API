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
from typing import Annotated, Optional

from fastapi import Query
from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass

from app.model.db import NotificationType
from app.model.schema.base import (
    ResultSet,
    SortOrder,
    TokenType,
    ValidatedEthereumAddress,
)

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


@dataclass
class NotificationsQuery:
    offset: Annotated[Optional[int], Query(description="start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="number of set", ge=0)] = None
    address: Annotated[
        Optional[ValidatedEthereumAddress], Query(description="account address")
    ] = None
    notification_type: Annotated[Optional[NotificationType], Query()] = None
    priority: Annotated[Optional[int], Query(ge=0, le=2)] = None
    sort_item: Annotated[
        Optional[NotificationsSortItem], Query(description="sort item")
    ] = NotificationsSortItem.created
    sort_order: Annotated[
        Optional[SortOrder], Query(description="sort order(0: ASC, 1: DESC)")
    ] = SortOrder.ASC


class NotificationReadRequest(BaseModel):
    address: ValidatedEthereumAddress
    is_read: bool


@dataclass
class NotificationsCountQuery:
    address: Annotated[ValidatedEthereumAddress, Query(default=...)]


class UpdateNotificationRequest(BaseModel):
    is_read: Optional[bool] = Field(default=None, description="Read update")
    is_flagged: Optional[bool] = Field(default=None, description="Set flag")
    is_deleted: Optional[bool] = Field(default=None, description="Logical deletion")


############################
# RESPONSE
############################
class NotificationMetainfo(BaseModel):
    company_name: str
    token_address: ValidatedEthereumAddress
    token_name: str
    exchange_address: ValidatedEthereumAddress
    token_type: TokenType


class Notification(BaseModel):
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
    account_address: ValidatedEthereumAddress
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
    account_address: ValidatedEthereumAddress
