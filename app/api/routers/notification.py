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
from typing import Optional, Sequence

from eth_utils import to_checksum_address
from fastapi import APIRouter, Depends, Path
from sqlalchemy import desc, func, select, update

from app import log
from app.database import DBSession
from app.errors import DataNotExistsError
from app.model.db import Notification
from app.model.schema import (
    NotificationReadRequest,
    NotificationsCountQuery,
    NotificationsCountResponse,
    NotificationsQuery,
    NotificationsResponse,
    NotificationUpdateResponse,
    UpdateNotificationRequest,
)
from app.model.schema.base import GenericSuccessResponse, SuccessResponse
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()


router = APIRouter(prefix="/Notifications", tags=["user_notification"])


@router.get(
    "",
    summary="Notification List",
    operation_id="GetNotifications",
    response_model=GenericSuccessResponse[NotificationsResponse],
    responses=get_routers_responses(),
)
def list_all_notifications(
    session: DBSession,
    request_query: NotificationsQuery = Depends(),
):
    """
    Endpoint: /Notifications/
    """
    address = request_query.address
    notification_type = request_query.notification_type
    priority = request_query.priority
    sort_item = request_query.sort_item
    sort_order = request_query.sort_order  # default: asc
    offset = request_query.offset
    limit = request_query.limit

    stmt = select(Notification)
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))

    # Search Filter
    if address is not None:
        stmt = stmt.where(Notification.address == to_checksum_address(address))
    if notification_type is not None:
        stmt = stmt.where(Notification.notification_type == notification_type)
    if priority is not None:
        stmt = stmt.where(Notification.priority == priority)
    count = session.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    sort_attr = getattr(Notification, sort_item, None)
    if sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if sort_item != "created":
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(Notification.created)

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    sort_id = 0
    if offset is not None:
        stmt = stmt.offset(offset)
        sort_id = offset

    _notification_list: Sequence[Notification] = session.scalars(stmt).all()

    notifications = []
    for _notification in _notification_list:
        sort_id += 1
        notification = _notification.json()
        notification["sort_id"] = sort_id
        notification["created"] = _notification.created.strftime("%Y/%m/%d %H:%M:%S")
        notifications.append(notification)

    data = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "notifications": notifications,
    }

    return json_response({**SuccessResponse.default(), "data": data})


@router.post(
    "/Read",
    summary="Mark all notifications as read",
    operation_id="NotificationsRead",
    response_model=SuccessResponse,
    responses=get_routers_responses(),
)
def read_all_notifications(
    session: DBSession,
    data: NotificationReadRequest,
):
    """
    Endpoint: /Notifications/Read/
    """
    address = to_checksum_address(data.address)

    # Update Data
    session.execute(
        update(Notification)
        .where(Notification.address == address)
        .values(is_read=data.is_read)
    )
    session.commit()

    return json_response(SuccessResponse.default())


@router.get(
    "/Count",
    summary="Get the number of unread notifications",
    operation_id="NotificationsCount",
    response_model=GenericSuccessResponse[NotificationsCountResponse],
    responses=get_routers_responses(),
)
def count_notifications(
    session: DBSession,
    request_query: NotificationsCountQuery = Depends(),
):
    """
    Endpoint: /Notifications/Count/
    """
    # リクエストから情報を抽出
    address = to_checksum_address(request_query.address)

    # 未読数を取得
    count = session.scalar(
        select(func.count())
        .where(Notification.address == address)
        .where(Notification.is_read == False)
        .where(Notification.is_deleted == False)
    )

    return json_response(
        {
            **SuccessResponse.default(),
            "data": {
                "unread_counts": count,
            },
        }
    )


@router.post(
    "/{notification_id}",
    summary="Update Notification",
    operation_id="PostNotifications",
    response_model=GenericSuccessResponse[NotificationUpdateResponse],
    responses=get_routers_responses(DataNotExistsError),
)
def update_notification(
    session: DBSession,
    data: UpdateNotificationRequest,
    notification_id: str = Path(description="Notification id"),
):
    """
    Endpoint: /Notifications/{id}
    """
    # Update Notification
    notification: Optional[Notification] = session.scalars(
        select(Notification)
        .where(Notification.notification_id == notification_id)
        .limit(1)
    ).first()
    if notification is None:
        raise DataNotExistsError("notification not found")

    if data.is_read is not None:
        notification.is_read = data.is_read
    if data.is_flagged is not None:
        notification.is_flagged = data.is_flagged
    if data.is_deleted is not None:
        notification.is_deleted = data.is_deleted
        if data.is_deleted:
            notification.deleted_at = datetime.utcnow()
        else:
            notification.deleted_at = None

    session.commit()

    return json_response({**SuccessResponse.default(), "data": notification.json()})


@router.delete(
    "/{notification_id}",
    summary="Delete Notification",
    operation_id="DeleteNotification",
    response_model=SuccessResponse,
    responses=get_routers_responses(DataNotExistsError),
)
def delete_notification(
    session: DBSession,
    notification_id: str = Path(description="Notification id"),
):
    # Get Notification
    _notification = session.scalars(
        select(Notification)
        .where(Notification.notification_id == notification_id)
        .limit(1)
    ).first()
    if _notification is None:
        raise DataNotExistsError("id: %s" % notification_id)

    # Delete Notification
    session.delete(_notification)
    session.commit()

    return json_response(SuccessResponse.default())
