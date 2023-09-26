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
from typing import Annotated, Optional, Sequence

from eth_utils import to_checksum_address
from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy import desc, func, select
from web3 import Web3

from app import config, log
from app.database import DBSession
from app.errors import (
    DataNotExistsError,
    InvalidParameterError,
    NotSupportedError,
    ServiceUnavailable,
)
from app.model.blockchain import MembershipToken
from app.model.db import IDXMembershipToken, Listing
from app.model.schema import (
    ListAllMembershipTokenAddressesResponse,
    ListAllMembershipTokensQuery,
    ListAllMembershipTokensResponse,
    RetrieveMembershipTokenResponse,
)
from app.model.schema.base import GenericSuccessResponse, SuccessResponse
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()

router = APIRouter(prefix="/Token/Membership", tags=["token_info"])


@router.get(
    "",
    summary="Token detail list of Membership tokens",
    operation_id="MembershipTokens",
    response_model=GenericSuccessResponse[ListAllMembershipTokensResponse],
    responses=get_routers_responses(NotSupportedError, InvalidParameterError),
)
def list_all_membership_tokens(
    session: DBSession,
    req: Request,
    address_list: list[str] = Query(
        default=[], description="list of token address (**this affects total number**)"
    ),
    request_query: ListAllMembershipTokensQuery = Depends(),
):
    """
    Get a list of membership tokens.
    """
    if config.MEMBERSHIP_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    for address in address_list:
        if address is not None:
            if not Web3.is_address(address):
                raise InvalidParameterError(f"invalid token_address: {address}")

    owner_address: Optional[str] = request_query.owner_address
    name: Optional[str] = request_query.name
    symbol: Optional[str] = request_query.symbol
    company_name: Optional[str] = request_query.company_name
    tradable_exchange: Optional[str] = request_query.tradable_exchange
    status: Optional[bool] = request_query.status
    transferable: Optional[bool] = request_query.transferable
    initial_offering_status: Optional[bool] = request_query.initial_offering_status

    sort_item = request_query.sort_item
    sort_order = request_query.sort_order  # default: asc
    offset = request_query.offset
    limit = request_query.limit

    # 取扱トークンリストを取得
    # 公開属性によるフィルタリングを行うためJOIN
    stmt = (
        select(IDXMembershipToken)
        .join(Listing, Listing.token_address == IDXMembershipToken.token_address)
        .where(Listing.is_public == True)
    )
    if len(address_list):
        stmt = stmt.where(IDXMembershipToken.token_address.in_(address_list))
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))

    # Search Filter
    if owner_address is not None:
        stmt = stmt.where(IDXMembershipToken.owner_address == owner_address)
    if name is not None:
        stmt = stmt.where(IDXMembershipToken.name.contains(name))
    if symbol is not None:
        stmt = stmt.where(IDXMembershipToken.symbol.contains(symbol))
    if company_name is not None:
        stmt = stmt.where(IDXMembershipToken.company_name.contains(company_name))
    if tradable_exchange is not None:
        stmt = stmt.where(IDXMembershipToken.tradable_exchange == tradable_exchange)
    if status is not None:
        stmt = stmt.where(IDXMembershipToken.status == status)
    if transferable is not None:
        stmt = stmt.where(IDXMembershipToken.transferable == transferable)
    if initial_offering_status is not None:
        stmt = stmt.where(
            IDXMembershipToken.initial_offering_status == initial_offering_status
        )
    count = session.scalar(select(func.count()).select_from(stmt.subquery()))

    if sort_item == "created":
        sort_attr = getattr(Listing, sort_item, None)
    else:
        sort_attr = getattr(IDXMembershipToken, sort_item, None)

    if sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if sort_item != "created":
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(Listing.created)

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _token_list: Sequence[IDXMembershipToken] = session.scalars(stmt).all()
    tokens = []

    for _token in _token_list:
        tokens.append(MembershipToken.from_model(_token).__dict__)

    data = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "tokens": tokens,
    }

    return json_response({**SuccessResponse.default(), "data": data})


@router.get(
    "/Addresses",
    summary="List of Membership token address",
    operation_id="MembershipTokenAddresses",
    response_model=GenericSuccessResponse[ListAllMembershipTokenAddressesResponse],
    responses=get_routers_responses(NotSupportedError),
)
def list_all_membership_token_addresses(
    session: DBSession,
    req: Request,
    request_query: ListAllMembershipTokensQuery = Depends(),
):
    """
    Get a list of membership token addresses.
    """
    if config.MEMBERSHIP_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    owner_address: Optional[str] = request_query.owner_address
    name: Optional[str] = request_query.name
    symbol: Optional[str] = request_query.symbol
    company_name: Optional[str] = request_query.company_name
    tradable_exchange: Optional[str] = request_query.tradable_exchange
    status: Optional[bool] = request_query.status
    transferable: Optional[bool] = request_query.transferable
    initial_offering_status: Optional[bool] = request_query.initial_offering_status

    sort_item = request_query.sort_item
    sort_order = request_query.sort_order
    offset = request_query.offset
    limit = request_query.limit

    # 取扱トークンリストを取得
    # 公開属性によるフィルタリングを行うためJOIN
    stmt = (
        select(IDXMembershipToken)
        .join(Listing, Listing.token_address == IDXMembershipToken.token_address)
        .where(Listing.is_public == True)
    )
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))

    # Search Filter
    if owner_address is not None:
        stmt = stmt.where(IDXMembershipToken.owner_address == owner_address)
    if name is not None:
        stmt = stmt.where(IDXMembershipToken.name.contains(name))
    if symbol is not None:
        stmt = stmt.where(IDXMembershipToken.symbol.contains(symbol))
    if company_name is not None:
        stmt = stmt.where(IDXMembershipToken.company_name.contains(company_name))
    if tradable_exchange is not None:
        stmt = stmt.where(IDXMembershipToken.tradable_exchange == tradable_exchange)
    if status is not None:
        stmt = stmt.where(IDXMembershipToken.status == status)
    if transferable is not None:
        stmt = stmt.where(IDXMembershipToken.transferable == transferable)
    if initial_offering_status is not None:
        stmt = stmt.where(
            IDXMembershipToken.initial_offering_status == initial_offering_status
        )
    count = session.scalar(select(func.count()).select_from(stmt.subquery()))

    if sort_item == "created":
        sort_attr = getattr(Listing, sort_item, None)
    else:
        sort_attr = getattr(IDXMembershipToken, sort_item, None)

    if sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if sort_item != "created":
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(Listing.created)

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _token_list: Sequence[IDXMembershipToken] = session.scalars(stmt).all()

    data = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "address_list": [_token.token_address for _token in _token_list],
    }

    return json_response({**SuccessResponse.default(), "data": data})


@router.get(
    "/{token_address}",
    summary="Membership token details",
    operation_id="MembershipTokenDetails",
    response_model=GenericSuccessResponse[RetrieveMembershipTokenResponse],
    responses=get_routers_responses(NotSupportedError, DataNotExistsError),
)
def retrieve_membership_token(
    session: DBSession,
    req: Request,
    token_address: Annotated[str, Path(description="Token address")],
):
    """
    Get the details of the membership token.
    """
    if config.MEMBERSHIP_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    # 入力アドレスフォーマットチェック
    try:
        token_address = to_checksum_address(token_address)
        if not Web3.is_address(token_address):
            description = "invalid token_address"
            raise InvalidParameterError(description=description)
    except:
        description = "invalid token_address"
        raise InvalidParameterError(description=description)

    # 取扱トークンチェック
    # NOTE:非公開トークンも取扱対象とする
    listed_token = session.scalars(
        select(Listing).where(Listing.token_address == token_address).limit(1)
    ).first()
    if listed_token is None:
        raise DataNotExistsError("token_address: %s" % token_address)

    token_address = to_checksum_address(token_address)

    try:
        token_detail = MembershipToken.get(session=session, token_address=token_address)
    except ServiceUnavailable as e:
        LOG.warning(e)
        raise DataNotExistsError("token_address: %s" % token_address) from None
    except Exception as e:
        LOG.error(e)
        raise DataNotExistsError("token_address: %s" % token_address) from None

    return json_response({**SuccessResponse.default(), "data": token_detail.__dict__})
