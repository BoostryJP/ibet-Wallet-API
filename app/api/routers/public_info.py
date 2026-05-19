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

from typing import TYPE_CHECKING, Annotated, Sequence

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
    ListAllPublicListedTokensSortItem,
)
from app.model.schema.base import (
    GenericSuccessResponse,
    ResultSet,
    Success200MetaModel,
    SuccessResponse,
)
from app.model.schema.public_info import (
    IbetBondToken,
    IbetCouponToken,
    IbetMembershipToken,
    IbetShareToken,
    PublicAccount,
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
    if request_query.sort_item == ListAllPublicListedTokensSortItem.token_address:
        sort_attr = TokenList.token_address
    else:
        sort_attr = TokenList.token_address
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

    if TYPE_CHECKING:
        type_checked_tokens: list[
            IbetBondToken | IbetShareToken | IbetMembershipToken | IbetCouponToken
        ] = []
        for token in _token_list:
            if token.token_template == "ibetBond":
                type_checked_tokens.append(
                    IbetBondToken(
                        token_address=token.token_address,
                        token_template="ibetBond",
                        contract_version=token.contract_version,
                        key_manager=token.key_manager,
                        product_type=1,
                        issuer_address=token.issuer_address,
                    )
                )
            elif token.token_template == "ibetShare":
                # TODO: Once (token_template, product_type) constraints are enforced in DB schema and ORM typing, remove this runtime guard.
                match token.product_type:
                    case 1 | 2 | 3 | 4 | 5 as share_product_type:
                        pass
                    case _:
                        continue
                type_checked_tokens.append(
                    IbetShareToken(
                        token_address=token.token_address,
                        token_template="ibetShare",
                        contract_version=token.contract_version,
                        key_manager=token.key_manager,
                        product_type=share_product_type,
                        issuer_address=token.issuer_address,
                    )
                )
            elif token.token_template == "ibetMembership":
                type_checked_tokens.append(
                    IbetMembershipToken(
                        token_address=token.token_address,
                        token_template="ibetMembership",
                        contract_version=token.contract_version,
                        key_manager=token.key_manager,
                        product_type=1,
                        issuer_address=token.issuer_address,
                    )
                )
            else:
                type_checked_tokens.append(
                    IbetCouponToken(
                        token_address=token.token_address,
                        token_template="ibetCoupon",
                        contract_version=token.contract_version,
                        key_manager=token.key_manager,
                        product_type=1,
                        issuer_address=token.issuer_address,
                    )
                )
        _ = GenericSuccessResponse[ListAllPublicListedTokensResponse](
            meta=Success200MetaModel(code=200, message="OK"),
            data=ListAllPublicListedTokensResponse(
                result_set=ResultSet(
                    count=count,
                    offset=request_query.offset,
                    limit=request_query.limit,
                    total=total,
                ),
                tokens=type_checked_tokens,
            ),
        )
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
    if request_query.sort_item == ListAllPublicAccountsSortItem.key_manager:
        sort_attr = PublicAccountList.key_manager
    elif request_query.sort_item == ListAllPublicAccountsSortItem.key_manager_name:
        sort_attr = PublicAccountList.key_manager_name
    else:
        sort_attr = PublicAccountList.account_address
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
    if TYPE_CHECKING:
        type_checked_accounts: list[PublicAccount] = []
        for account in _account_list:
            # TODO: Migrate account.modified to NOT NULL and update ORM typing.
            assert account.modified is not None
            type_checked_accounts.append(
                PublicAccount(
                    key_manager=account.key_manager,
                    key_manager_name=account.key_manager_name,
                    account_type=account.account_type,
                    account_address=account.account_address,
                    modified=account.format_timestamp(account.modified),
                )
            )
        _ = GenericSuccessResponse[ListAllPublicAccountsResponse](
            meta=Success200MetaModel(code=200, message="OK"),
            data=ListAllPublicAccountsResponse(
                result_set=ResultSet(
                    count=count,
                    offset=request_query.offset,
                    limit=request_query.limit,
                    total=total,
                ),
                accounts=type_checked_accounts,
            ),
        )
    return json_response({**SuccessResponse.default(), "data": data})
