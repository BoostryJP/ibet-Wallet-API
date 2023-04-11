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
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import desc

from app import log
from app.config import TZ
from app.database import DBSession
from app.errors import InvalidParameterError
from app.model.db import IDXLockedPosition
from app.model.schema import (
    GenericSuccessResponse,
    ListAllLockQuery,
    ListAllLockResponse,
    RetrieveLockCountQuery,
    RetrieveLockCountResponse,
    SuccessResponse,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi import json_response

LOG = log.get_logger()

UTC = timezone(timedelta(hours=0), "UTC")
local_tz = ZoneInfo(TZ)

router = APIRouter(prefix="/Lock", tags=["user_lock"])


@router.get(
    "",
    summary="Lock",
    operation_id="ListAllLock",
    response_model=GenericSuccessResponse[ListAllLockResponse],
    responses=get_routers_responses(InvalidParameterError),
)
def list_all_lock(session: DBSession, request_query: ListAllLockQuery = Depends()):
    token_address_list = request_query.token_address_list
    lock_address = request_query.lock_address
    account_address = request_query.account_address
    limit = request_query.limit
    offset = request_query.offset

    sort_item = request_query.sort_item
    sort_order = request_query.sort_order  # default: asc

    query = session.query(IDXLockedPosition).filter(IDXLockedPosition.value > 0)
    if len(token_address_list) > 0:
        query = query.filter(IDXLockedPosition.token_address.in_(token_address_list))
    total = query.count()

    if account_address is not None:
        query = query.filter(IDXLockedPosition.account_address == account_address)
    if lock_address is not None:
        query = query.filter(IDXLockedPosition.lock_address == lock_address)

    count = query.count()

    sort_attr = getattr(IDXLockedPosition, sort_item, None)

    if sort_order == 0:  # ASC
        query = query.order_by(sort_attr)
    else:  # DESC
        query = query.order_by(desc(sort_attr))

    # NOTE: Set secondary sort for consistent results
    if sort_item != "token_address":
        query = query.order_by(IDXLockedPosition.token_address)
    else:
        query = query.order_by(IDXLockedPosition.created)

    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    _locked_list: list[IDXLockedPosition] = query.all()

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
    summary="Lock Count",
    operation_id="RetrieveLockCount",
    response_model=GenericSuccessResponse[RetrieveLockCountResponse],
    responses=get_routers_responses(InvalidParameterError),
)
def retrieve_lock_count(
    session: DBSession, request_query: RetrieveLockCountQuery = Depends()
):
    token_address_list = request_query.token_address_list
    lock_address = request_query.lock_address
    account_address = request_query.account_address

    query = session.query(IDXLockedPosition).filter(IDXLockedPosition.value > 0)
    if len(token_address_list) > 0:
        query = query.filter(IDXLockedPosition.token_address.in_(token_address_list))

    if account_address is not None:
        query = query.filter(IDXLockedPosition.account_address == account_address)
    if lock_address is not None:
        query = query.filter(IDXLockedPosition.lock_address == lock_address)

    _count = query.count()

    data = {"count": _count}
    return json_response({**SuccessResponse.default(), "data": data})
