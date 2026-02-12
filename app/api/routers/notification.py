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

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any, Optional, Sequence

from eth_utils.address import to_checksum_address
from fastapi import APIRouter, Path, Query
from sqlalchemy import desc, func, select, update

from app import log
from app.database import DBAsyncSession
from app.errors import DataNotExistsError
from app.model.db import Notification, NotificationType
from app.model.schema import (
    NotificationReadRequest,
    NotificationsCountQuery,
    NotificationsCountResponse,
    NotificationsQuery,
    NotificationsResponse,
    NotificationsSortItem,
    NotificationUpdateResponse,
    UpdateNotificationRequest,
)
from app.model.schema.base import (
    EmptyData,
    GenericSuccessResponse,
    ResultSet,
    Success200MetaModel,
    SuccessResponse,
)
from app.model.schema.notification import Notification as NotificationSchema
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
async def list_all_notifications(
    async_session: DBAsyncSession,
    request_query: Annotated[NotificationsQuery, Query()],
):
    """
    Returns notifications filtered by given query.
    """
    notification_category = request_query.notification_category
    address = request_query.address
    notification_type = request_query.notification_type
    priority = request_query.priority
    sort_item = request_query.sort_item
    sort_order = request_query.sort_order  # default: asc
    offset = request_query.offset
    limit = request_query.limit

    stmt = select(Notification)
    total = await async_session.scalar(
        stmt.with_only_columns(func.count()).select_from(Notification).order_by(None)
    )

    # Search Filter
    if notification_category is not None:
        stmt = stmt.where(Notification.notification_category == notification_category)
    if address is not None:
        stmt = stmt.where(Notification.address == to_checksum_address(address))
    if notification_type is not None:
        stmt = stmt.where(Notification.notification_type == notification_type)
    if priority is not None:
        stmt = stmt.where(Notification.priority == priority)
    count = await async_session.scalar(
        stmt.with_only_columns(func.count()).select_from(Notification).order_by(None)
    )

    # Sort
    if sort_item == NotificationsSortItem.notification_type:
        sort_attr = Notification.notification_type
    elif sort_item == NotificationsSortItem.priority:
        sort_attr = Notification.priority
    elif sort_item == NotificationsSortItem.block_timestamp:
        sort_attr = Notification.block_timestamp
    else:
        sort_attr = Notification.created
    if sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if sort_item != NotificationsSortItem.created:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(Notification.created)

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    sort_id = 0
    if offset is not None:
        stmt = stmt.offset(offset)
        sort_id = offset

    _notification_list: Sequence[Notification] = (
        await async_session.scalars(stmt)
    ).all()

    notifications: list[dict[str, Any]] = []
    for i, _notification in enumerate(_notification_list):
        # TODO: Migrate notification.created to NOT NULL and update ORM typing
        assert _notification.created is not None
        notification_data = {
            **_notification.json(),
            "sort_id": sort_id + i + 1,
            "created": "{}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
                _notification.created.year,
                _notification.created.month,
                _notification.created.day,
                _notification.created.hour,
                _notification.created.minute,
                _notification.created.second,
            ),
        }
        notifications.append(notification_data)
    data: dict[str, object] = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "notifications": notifications,
    }

    if TYPE_CHECKING:
        type_checked_notifications: list[NotificationSchema] = []
        for i, _notification in enumerate(_notification_list):
            assert _notification.created is not None
            notification_data = _notification.json()
            notification_type_value = notification_data["notification_type"]
            priority_value = notification_data["priority"]
            block_timestamp_value = notification_data["block_timestamp"]
            is_read_value = notification_data["is_read"]
            is_flagged_value = notification_data["is_flagged"]
            is_deleted_value = notification_data["is_deleted"]
            metainfo_value = notification_data["metainfo"]
            account_address_value = notification_data["account_address"]
            created_value = "{}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
                _notification.created.year,
                _notification.created.month,
                _notification.created.day,
                _notification.created.hour,
                _notification.created.minute,
                _notification.created.second,
            )
            # TODO: Migrate notification.notification_type, priority, block_timestamp,
            # is_read, is_flagged, is_deleted, metainfo, and address to NOT NULL and
            # update ORM typing.
            assert notification_type_value is not None
            assert priority_value is not None
            assert block_timestamp_value is not None
            assert is_read_value is not None
            assert is_flagged_value is not None
            assert is_deleted_value is not None
            assert metainfo_value is not None
            assert account_address_value is not None
            type_checked_notifications.append(
                NotificationSchema(
                    notification_category=notification_data["notification_category"],
                    id=notification_data["id"],
                    notification_type=NotificationType(notification_type_value),
                    priority=priority_value,
                    block_timestamp=block_timestamp_value,
                    is_read=is_read_value,
                    is_flagged=is_flagged_value,
                    is_deleted=is_deleted_value,
                    deleted_at=notification_data["deleted_at"],
                    args=notification_data["args"],
                    metainfo=metainfo_value,
                    account_address=account_address_value,
                    sort_id=sort_id + i + 1,
                    created=created_value,
                )
            )
        _ = GenericSuccessResponse[NotificationsResponse](
            meta=Success200MetaModel(code=200, message="OK"),
            data=NotificationsResponse(
                result_set=ResultSet(
                    count=count,
                    offset=offset,
                    limit=limit,
                    total=total,
                ),
                notifications=type_checked_notifications,
            ),
        )
    return json_response({**SuccessResponse.default(), "data": data})


@router.post(
    "/Read",
    summary="Mark all notifications as read",
    operation_id="NotificationsRead",
    response_model=SuccessResponse,
    responses=get_routers_responses(),
)
async def read_all_notifications(
    async_session: DBAsyncSession,
    data: NotificationReadRequest,
):
    """
    Registers all notifications as read.
    """
    address = to_checksum_address(data.address)

    # Update Data
    await async_session.execute(
        update(Notification)
        .where(Notification.address == address)
        .values(is_read=data.is_read)
    )
    await async_session.commit()

    if TYPE_CHECKING:
        _ = SuccessResponse(
            meta=Success200MetaModel(code=200, message="OK"), data=EmptyData()
        )
    return json_response(SuccessResponse.default())


@router.get(
    "/Count",
    summary="Get the number of unread notifications",
    operation_id="NotificationsCount",
    response_model=GenericSuccessResponse[NotificationsCountResponse],
    responses=get_routers_responses(),
)
async def count_notifications(
    async_session: DBAsyncSession,
    request_query: Annotated[NotificationsCountQuery, Query()],
):
    """
    Returns count of notifications filtered by given query.
    """
    # リクエストから情報を抽出
    address = to_checksum_address(request_query.address)

    # 未読数を取得
    count = (
        await async_session.scalar(
            select(func.count())
            .where(Notification.address == address)
            .where(Notification.is_read == False)
            .where(Notification.is_deleted == False)
        )
        or 0
    )

    if TYPE_CHECKING:
        _ = GenericSuccessResponse[NotificationsCountResponse](
            meta=Success200MetaModel(code=200, message="OK"),
            data=NotificationsCountResponse(unread_counts=count),
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
async def update_notification(
    async_session: DBAsyncSession,
    data: UpdateNotificationRequest,
    notification_id: Annotated[str, Path(description="Notification id")],
):
    """
    Registers given notification as read.
    """
    # Update Notification
    notification: Optional[Notification] = (
        await async_session.scalars(
            select(Notification)
            .where(Notification.notification_id == notification_id)
            .limit(1)
        )
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
            notification.deleted_at = datetime.now(UTC).replace(tzinfo=None)
        else:
            notification.deleted_at = None

    await async_session.commit()

    if TYPE_CHECKING:
        # TODO: Migrate notification.notification_type to NOT NULL and update ORM typing.
        assert notification.notification_type is not None
        # TODO: Migrate notification.priority to NOT NULL and update ORM typing.
        assert notification.priority is not None
        # TODO: Migrate notification.is_read to NOT NULL and update ORM typing.
        assert notification.is_read is not None
        # TODO: Migrate notification.is_flagged to NOT NULL and update ORM typing.
        assert notification.is_flagged is not None
        # TODO: Migrate notification.is_deleted to NOT NULL and update ORM typing.
        assert notification.is_deleted is not None
        # TODO: Migrate notification.address to NOT NULL and update ORM typing.
        assert notification.address is not None
        update_response_payload = notification.json()
        block_timestamp_value = update_response_payload["block_timestamp"]
        deleted_at_value = update_response_payload["deleted_at"]
        metainfo_value = update_response_payload["metainfo"]
        assert isinstance(block_timestamp_value, str)
        assert deleted_at_value is None or isinstance(deleted_at_value, str)
        assert isinstance(metainfo_value, dict)
        _ = GenericSuccessResponse[NotificationUpdateResponse](
            meta=Success200MetaModel(code=200, message="OK"),
            data=NotificationUpdateResponse(
                notification_type=NotificationType(notification.notification_type),
                id=notification.notification_id,
                priority=notification.priority,
                block_timestamp=block_timestamp_value,
                is_read=notification.is_read,
                is_flagged=notification.is_flagged,
                is_deleted=notification.is_deleted,
                deleted_at=deleted_at_value,
                args=update_response_payload["args"],
                metainfo=metainfo_value,
                account_address=notification.address,
            ),
        )
    return json_response({**SuccessResponse.default(), "data": notification.json()})


@router.delete(
    "/{notification_id}",
    summary="Delete Notification",
    operation_id="DeleteNotification",
    response_model=SuccessResponse,
    responses=get_routers_responses(DataNotExistsError),
)
async def delete_notification(
    async_session: DBAsyncSession,
    notification_id: Annotated[str, Path(description="Notification id")],
):
    """
    Deletes given notification.
    """
    # Get Notification
    _notification = (
        await async_session.scalars(
            select(Notification)
            .where(Notification.notification_id == notification_id)
            .limit(1)
        )
    ).first()
    if _notification is None:
        raise DataNotExistsError("id: %s" % notification_id)

    # Delete Notification
    await async_session.delete(_notification)
    await async_session.commit()

    if TYPE_CHECKING:
        _ = SuccessResponse(
            meta=Success200MetaModel(code=200, message="OK"), data=EmptyData()
        )
    return json_response(SuccessResponse.default())
