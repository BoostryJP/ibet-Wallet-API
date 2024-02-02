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

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy import desc, func, select

from app import config, log
from app.database import DBAsyncSession
from app.errors import (
    DataNotExistsError,
    InvalidParameterError,
    NotSupportedError,
    ServiceUnavailable,
)
from app.model.blockchain import BondToken
from app.model.db import IDXBondToken, Listing
from app.model.schema import (
    ListAllStraightBondTokenAddressesResponse,
    ListAllStraightBondTokensQuery,
    ListAllStraightBondTokensResponse,
    RetrieveStraightBondTokenResponse,
)
from app.model.schema.base import (
    GenericSuccessResponse,
    SuccessResponse,
    ValidatedEthereumAddress,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()

router = APIRouter(prefix="/Token/StraightBond", tags=["token_info"])


@router.get(
    "",
    summary="Token detail list of StraightBond tokens",
    operation_id="StraightBondTokens",
    response_model=GenericSuccessResponse[ListAllStraightBondTokensResponse],
    responses=get_routers_responses(NotSupportedError, InvalidParameterError),
)
async def list_all_straight_bond_tokens(
    async_session: DBAsyncSession,
    req: Request,
    address_list: Annotated[
        list[ValidatedEthereumAddress],
        Query(
            default_factory=list,
            description="list of token address (**this affects total number**)",
        ),
    ],
    request_query: ListAllStraightBondTokensQuery = Depends(),
):
    """
    [StraightBond]Returns a detail list of tokens.
    """
    if config.BOND_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    owner_address: Optional[str] = request_query.owner_address
    name: Optional[str] = request_query.name
    symbol: Optional[str] = request_query.symbol
    company_name: Optional[str] = request_query.company_name
    tradable_exchange: Optional[str] = request_query.tradable_exchange
    status: Optional[bool] = request_query.status
    personal_info_address: Optional[str] = request_query.personal_info_address
    transferable: Optional[bool] = request_query.transferable
    is_offering: Optional[bool] = request_query.is_offering
    transfer_approval_required: Optional[bool] = (
        request_query.transfer_approval_required
    )
    is_redeemed: Optional[bool] = request_query.is_redeemed

    sort_item = request_query.sort_item
    sort_order = request_query.sort_order  # default: asc
    offset = request_query.offset
    limit = request_query.limit

    # 取扱トークンリストを取得
    # 公開属性によるフィルタリングを行うためJOIN
    stmt = (
        select(IDXBondToken)
        .join(Listing, Listing.token_address == IDXBondToken.token_address)
        .where(Listing.is_public == True)
    )
    if len(address_list):
        stmt = stmt.where(IDXBondToken.token_address.in_(address_list))
    total = await async_session.scalar(
        select(func.count()).select_from(stmt.subquery())
    )

    # Search Filter
    if owner_address is not None:
        stmt = stmt.where(IDXBondToken.owner_address == owner_address)
    if name is not None:
        stmt = stmt.where(IDXBondToken.name.contains(name))
    if symbol is not None:
        stmt = stmt.where(IDXBondToken.symbol.contains(symbol))
    if company_name is not None:
        stmt = stmt.where(IDXBondToken.company_name.contains(company_name))
    if tradable_exchange is not None:
        stmt = stmt.where(IDXBondToken.tradable_exchange == tradable_exchange)
    if status is not None:
        stmt = stmt.where(IDXBondToken.status == status)
    if personal_info_address is not None:
        stmt = stmt.where(IDXBondToken.personal_info_address == personal_info_address)
    if transferable is not None:
        stmt = stmt.where(IDXBondToken.transferable == transferable)
    if is_offering is not None:
        stmt = stmt.where(IDXBondToken.is_offering == is_offering)
    if transfer_approval_required is not None:
        stmt = stmt.where(
            IDXBondToken.transfer_approval_required == transfer_approval_required
        )
    if is_redeemed is not None:
        stmt = stmt.where(IDXBondToken.is_redeemed == is_redeemed)
    count = await async_session.scalar(
        select(func.count()).select_from(stmt.subquery())
    )

    if sort_item == "created":
        sort_attr = getattr(Listing, sort_item, None)
    else:
        sort_attr = getattr(IDXBondToken, sort_item, None)

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

    _token_list: Sequence[IDXBondToken] = (await async_session.scalars(stmt)).all()

    tokens = [BondToken.from_model(_token).__dict__ for _token in _token_list]
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
    summary="List of StraightBond token address",
    operation_id="StraightBondTokenAddresses",
    response_model=GenericSuccessResponse[ListAllStraightBondTokenAddressesResponse],
    responses=get_routers_responses(NotSupportedError),
)
async def list_all_straight_bond_token_addresses(
    async_session: DBAsyncSession,
    req: Request,
    request_query: ListAllStraightBondTokensQuery = Depends(),
):
    """
    [StraightBond]Returns a list of token addresses.
    """
    if config.BOND_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    owner_address: Optional[str] = request_query.owner_address
    name: Optional[str] = request_query.name
    symbol: Optional[str] = request_query.symbol
    company_name: Optional[str] = request_query.company_name
    tradable_exchange: Optional[str] = request_query.tradable_exchange
    status: Optional[bool] = request_query.status
    personal_info_address: Optional[str] = request_query.personal_info_address
    transferable: Optional[bool] = request_query.transferable
    is_offering: Optional[bool] = request_query.is_offering
    transfer_approval_required: Optional[bool] = (
        request_query.transfer_approval_required
    )
    is_redeemed: Optional[bool] = request_query.is_redeemed

    sort_item = request_query.sort_item
    sort_order = request_query.sort_order  # default: asc
    offset = request_query.offset
    limit = request_query.limit

    # 取扱トークンリストを取得
    # 公開属性によるフィルタリングを行うためJOIN
    stmt = (
        select(IDXBondToken)
        .join(Listing, Listing.token_address == IDXBondToken.token_address)
        .where(Listing.is_public == True)
    )
    total = await async_session.scalar(
        select(func.count()).select_from(stmt.subquery())
    )

    # Search Filter
    if owner_address is not None:
        stmt = stmt.where(IDXBondToken.owner_address == owner_address)
    if name is not None:
        stmt = stmt.where(IDXBondToken.name.contains(name))
    if symbol is not None:
        stmt = stmt.where(IDXBondToken.symbol.contains(symbol))
    if company_name is not None:
        stmt = stmt.where(IDXBondToken.company_name.contains(company_name))
    if tradable_exchange is not None:
        stmt = stmt.where(IDXBondToken.tradable_exchange == tradable_exchange)
    if status is not None:
        stmt = stmt.where(IDXBondToken.status == status)
    if personal_info_address is not None:
        stmt = stmt.where(IDXBondToken.personal_info_address == personal_info_address)
    if transferable is not None:
        stmt = stmt.where(IDXBondToken.transferable == transferable)
    if is_offering is not None:
        stmt = stmt.where(IDXBondToken.is_offering == is_offering)
    if transfer_approval_required is not None:
        stmt = stmt.where(
            IDXBondToken.transfer_approval_required == transfer_approval_required
        )
    if is_redeemed is not None:
        stmt = stmt.where(IDXBondToken.is_redeemed == is_redeemed)
    count = await async_session.scalar(
        select(func.count()).select_from(stmt.subquery())
    )

    if sort_item == "created":
        sort_attr = getattr(Listing, sort_item, None)
    else:
        sort_attr = getattr(IDXBondToken, sort_item, None)

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

    _token_list: Sequence[IDXBondToken] = (await async_session.scalars(stmt)).all()

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
    summary="StraightBond token details",
    operation_id="StraightBondTokenDetails",
    response_model=GenericSuccessResponse[RetrieveStraightBondTokenResponse],
    responses=get_routers_responses(
        NotSupportedError, DataNotExistsError, InvalidParameterError
    ),
)
async def retrieve_straight_bond_token(
    async_session: DBAsyncSession,
    req: Request,
    token_address: Annotated[
        ValidatedEthereumAddress, Path(description="Token address")
    ],
):
    """
    [StraightBond]Returns the details of the token.
    """
    if config.BOND_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    # 取扱トークンチェック
    # NOTE:非公開トークンも取扱対象とする
    listed_token = (
        await async_session.scalars(
            select(Listing).where(Listing.token_address == token_address).limit(1)
        )
    ).first()
    if listed_token is None:
        raise DataNotExistsError("token_address: %s" % token_address)

    try:
        token_detail = await BondToken.get(
            async_session=async_session, token_address=token_address
        )
    except ServiceUnavailable as e:
        LOG.warning(e)
        raise DataNotExistsError("token_address: %s" % token_address) from None
    except Exception as e:
        LOG.error(e)
        raise DataNotExistsError("token_address: %s" % token_address) from None

    if token_detail is None:
        raise DataNotExistsError("token_address: %s" % token_address)

    return json_response({**SuccessResponse.default(), "data": token_detail.__dict__})
