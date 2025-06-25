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

from typing import Annotated, Sequence

from fastapi import APIRouter, Query
from sqlalchemy import desc, func, select

from app import log
from app.database import DBAsyncSession
from app.errors import InvalidParameterError
from app.model.db import PublicAccountList, TokenList
from app.model.schema import (
    ListAllPublicAccountsQuery,
    ListAllPublicAccountsResponse,
    ListAllPublicAccountsSortItem,
    ListAllPublicListedTokensQuery,
    ListAllPublicListedTokensResponse,
)
from app.model.schema.base import (
    GenericSuccessResponse,
    SuccessResponse,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()

router = APIRouter(prefix="/PublicInfo", tags=["public_info"])


@router.get(
    "/Tokens",
    summary="Information on issued tokens and associated institutions (key managers)",
    operation_id="ListAllPublicListedTokens",
    response_model=GenericSuccessResponse[ListAllPublicListedTokensResponse],
    responses=get_routers_responses(
        InvalidParameterError,
    ),
)
async def list_all_public_tokens(
    async_session: DBAsyncSession,
    request_query: Annotated[ListAllPublicListedTokensQuery, Query()],
):
    """
    List issued tokens and associated institutions (key managers)
    """
    # Base query
    stmt = select(TokenList)
    total = await async_session.scalar(
        stmt.with_only_columns(func.count()).select_from(TokenList).order_by(None)
    )

    # Filter
    if request_query.token_template is not None:
        stmt = stmt.where(TokenList.token_template == request_query.token_template)

    count = await async_session.scalar(
        stmt.with_only_columns(func.count()).select_from(TokenList).order_by(None)
    )

    # Sort
    sort_attr = getattr(TokenList, request_query.sort_item, None)
    if request_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))

    # Pagination
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)

    _token_list: Sequence[TokenList] = (await async_session.scalars(stmt)).all()

    data = {
        "result_set": {
            "count": count,
            "offset": request_query.offset,
            "limit": request_query.limit,
            "total": total,
        },
        "tokens": [_token.json() for _token in _token_list],
    }

    return json_response({**SuccessResponse.default(), "data": data})


@router.get(
    "/PublicAccounts",
    summary="Public account information of ibet consortium members",
    operation_id="ListAllPublicAccounts",
    response_model=GenericSuccessResponse[ListAllPublicAccountsResponse],
    responses=get_routers_responses(
        InvalidParameterError,
    ),
)
async def list_all_public_accounts(
    async_session: DBAsyncSession,
    request_query: Annotated[ListAllPublicAccountsQuery, Query()],
):
    """
    List public accounts of ibet consortium members
    """
    # Base query
    stmt = select(PublicAccountList)
    total = await async_session.scalar(
        stmt.with_only_columns(func.count())
        .select_from(PublicAccountList)
        .order_by(None)
    )

    # Filter
    if request_query.key_manager is not None:
        stmt = stmt.where(PublicAccountList.key_manager == request_query.key_manager)
    if request_query.key_manager_name is not None:
        stmt = stmt.where(
            PublicAccountList.key_manager_name.like(
                "%" + request_query.key_manager_name + "%"
            )
        )

    count = await async_session.scalar(
        stmt.with_only_columns(func.count())
        .select_from(PublicAccountList)
        .order_by(None)
    )

    # Sort
    sort_attr = getattr(PublicAccountList, request_query.sort_item, None)
    if request_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))

    if request_query.sort_item == ListAllPublicAccountsSortItem.key_manager:
        stmt = stmt.order_by(PublicAccountList.account_type)
    else:
        stmt = stmt.order_by(
            PublicAccountList.key_manager, PublicAccountList.account_type
        )

    # Pagination
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)

    _account_list: Sequence[PublicAccountList] = (
        await async_session.scalars(stmt)
    ).all()

    data = {
        "result_set": {
            "count": count,
            "offset": request_query.offset,
            "limit": request_query.limit,
            "total": total,
        },
        "accounts": [_account.json() for _account in _account_list],
    }
    return json_response({**SuccessResponse.default(), "data": data})
