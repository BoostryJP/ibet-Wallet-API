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
from fastapi import (
    APIRouter,
    Depends
)
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import log
from app.database import db_session
from app.errors import (
    InvalidParameterError,
    DataNotExistsError
)
from app.model.schema import (
    GenericSuccessResponse,
    SuccessResponse,
    ListAllLockedQuery,
    ListLockedResponse
)
from app.utils.docs_utils import get_routers_responses
from app.model.db import IDXLockedPosition

LOG = log.get_logger()


router = APIRouter(
    prefix="/Locked",
    tags=["locked"]
)


@router.get(
    "",
    summary="Locked List",
    operation_id="ListAllLocked",
    response_model=GenericSuccessResponse[ListLockedResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError)
)
def list_all_lock(
    request_query: ListAllLockedQuery = Depends(),
    session: Session = Depends(db_session)
):
    """
    Endpoint: /Locked
    """

    token_address_list = request_query.token_address_list
    lock_address = request_query.lock_address
    account_address = request_query.account_address
    limit = request_query.limit
    offset = request_query.offset

    sort_item = request_query.sort_item
    sort_order = request_query.sort_order  # default: asc

    query = session.query(IDXLockedPosition)
    if len(token_address_list) > 0:
        query = query.filter(IDXLockedPosition.token_address.in_(token_address_list))

    total = query.count()

    if lock_address is not None:
        query = query.filter(IDXLockedPosition.lock_address == lock_address)
    if account_address is not None:
        query = query.filter(IDXLockedPosition.account_address == account_address)
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
    locked_list = []

    for _locked in _locked_list:
        locked_list.append(_locked.json())

    data = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "locked_list": locked_list
    }

    return {
        **SuccessResponse.use().dict(),
        "data": data
    }
