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

from datetime import timedelta, timezone
from typing import Sequence
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select

from app import log
from app.config import TZ
from app.database import DBAsyncSession
from app.errors import InvalidParameterError
from app.model.db import IDXLockedPosition
from app.model.schema import (
    ListAllTokenLockQuery,
    ListAllTokenLockResponse,
    RetrieveTokenLockCountQuery,
    RetrieveTokenLockCountResponse,
)
from app.model.schema.base import GenericSuccessResponse, SuccessResponse
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()

UTC = timezone(timedelta(hours=0), "UTC")
local_tz = ZoneInfo(TZ)

router = APIRouter(prefix="/Token/Lock", tags=["token_info"])


@router.get(
    "",
    summary="Token Lock",
    operation_id="ListAllTokenLock",
    response_model=GenericSuccessResponse[ListAllTokenLockResponse],
    responses=get_routers_responses(InvalidParameterError),
)
async def list_all_lock(
    async_session: DBAsyncSession, request_query: ListAllTokenLockQuery = Depends()
):
    """
    Returns a list of locked positions.
    """
    token_address_list = request_query.token_address_list
    lock_address = request_query.lock_address
    account_address = request_query.account_address
    limit = request_query.limit
    offset = request_query.offset

    sort_item = request_query.sort_item
    sort_order = request_query.sort_order  # default: asc

    stmt = select(IDXLockedPosition).where(IDXLockedPosition.value > 0)
    if len(token_address_list) > 0:
        stmt = stmt.where(IDXLockedPosition.token_address.in_(token_address_list))
    total = await async_session.scalar(
        select(func.count()).select_from(stmt.subquery())
    )

    if account_address is not None:
        stmt = stmt.where(IDXLockedPosition.account_address == account_address)
    if lock_address is not None:
        stmt = stmt.where(IDXLockedPosition.lock_address == lock_address)

    count = await async_session.scalar(
        select(func.count()).select_from(stmt.subquery())
    )

    sort_attr = getattr(IDXLockedPosition, sort_item, None)

    if sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))

    # NOTE: Set secondary sort for consistent results
    if sort_item != "token_address":
        stmt = stmt.order_by(IDXLockedPosition.token_address)
    else:
        stmt = stmt.order_by(IDXLockedPosition.created)

    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _locked_list: Sequence[IDXLockedPosition] = (
        await async_session.scalars(stmt)
    ).all()

    data = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "locked_list": [lock.json() for lock in _locked_list],
    }
    return json_response({**SuccessResponse.default(), "data": data})


@router.get(
    "/Count",
    summary="Token Lock Count",
    operation_id="RetrieveTokenLockCount",
    response_model=GenericSuccessResponse[RetrieveTokenLockCountResponse],
    responses=get_routers_responses(InvalidParameterError),
)
async def retrieve_lock_count(
    async_session: DBAsyncSession,
    request_query: RetrieveTokenLockCountQuery = Depends(),
):
    """
    Returns count of locked positions.
    """
    token_address_list = request_query.token_address_list
    lock_address = request_query.lock_address
    account_address = request_query.account_address

    stmt = select(IDXLockedPosition).where(IDXLockedPosition.value > 0)
    if len(token_address_list) > 0:
        stmt = stmt.where(IDXLockedPosition.token_address.in_(token_address_list))

    if account_address is not None:
        stmt = stmt.where(IDXLockedPosition.account_address == account_address)
    if lock_address is not None:
        stmt = stmt.where(IDXLockedPosition.lock_address == lock_address)

    _count = await async_session.scalar(
        select(func.count()).select_from(stmt.subquery())
    )

    data = {"count": _count}
    return json_response({**SuccessResponse.default(), "data": data})
