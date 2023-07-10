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
from typing import Optional

from eth_utils import to_checksum_address
from fastapi import APIRouter, Depends, Query, Request
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
from app.model.blockchain import CouponToken
from app.model.db import IDXCouponToken, Listing
from app.model.schema import (
    GenericSuccessResponse,
    ListAllCouponTokenAddressesResponse,
    ListAllCouponTokensQuery,
    ListAllCouponTokensResponse,
    RetrieveCouponTokenResponse,
    SuccessResponse,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi import json_response

LOG = log.get_logger()

router = APIRouter(prefix="/Token/Coupon", tags=["token_info"])


@router.get(
    "",
    summary="Token detail list of Coupon tokens",
    operation_id="CouponTokens",
    response_model=GenericSuccessResponse[ListAllCouponTokensResponse],
    responses=get_routers_responses(NotSupportedError, InvalidParameterError),
)
def list_all_coupon_tokens(
    session: DBSession,
    req: Request,
    address_list: list[str] = Query(
        default=[], description="list of token address (**this affects total number**)"
    ),
    request_query: ListAllCouponTokensQuery = Depends(),
):
    """
    Endpoint: /Token/Coupon
    """
    if config.COUPON_TOKEN_ENABLED is False:
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
        select(IDXCouponToken)
        .join(Listing, Listing.token_address == IDXCouponToken.token_address)
        .where(Listing.is_public == True)
    )
    if len(address_list):
        stmt = stmt.where(IDXCouponToken.token_address.in_(address_list))
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))

    # Search Filter
    if owner_address is not None:
        stmt = stmt.where(IDXCouponToken.owner_address == owner_address)
    if name is not None:
        stmt = stmt.where(IDXCouponToken.name.contains(name))
    if symbol is not None:
        stmt = stmt.where(IDXCouponToken.symbol.contains(symbol))
    if company_name is not None:
        stmt = stmt.where(IDXCouponToken.company_name.contains(company_name))
    if tradable_exchange is not None:
        stmt = stmt.where(IDXCouponToken.tradable_exchange == tradable_exchange)
    if status is not None:
        stmt = stmt.where(IDXCouponToken.status == status)
    if transferable is not None:
        stmt = stmt.where(IDXCouponToken.transferable == transferable)
    if initial_offering_status is not None:
        stmt = stmt.where(
            IDXCouponToken.initial_offering_status == initial_offering_status
        )
    count = session.scalar(select(func.count()).select_from(stmt.subquery()))

    sort_attr = getattr(IDXCouponToken, sort_item, None)

    if sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if sort_item != "created":
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(IDXCouponToken.created)

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _token_list: list[IDXCouponToken] = session.scalars(stmt).all()
    tokens = []

    for _token in _token_list:
        tokens.append(CouponToken.from_model(_token).__dict__)

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
    summary="List of Coupon token address",
    operation_id="CouponTokenAddresses",
    response_model=GenericSuccessResponse[ListAllCouponTokenAddressesResponse],
    responses=get_routers_responses(NotSupportedError),
)
def list_all_coupon_token_addresses(
    session: DBSession,
    req: Request,
    request_query: ListAllCouponTokensQuery = Depends(),
):
    """
    Endpoint: /Token/Coupon/Addresses
    """
    if config.COUPON_TOKEN_ENABLED is False:
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
    sort_order = request_query.sort_order  # default: asc
    offset = request_query.offset
    limit = request_query.limit

    # 取扱トークンリストを取得
    # 公開属性によるフィルタリングを行うためJOIN
    stmt = (
        select(IDXCouponToken)
        .join(Listing, Listing.token_address == IDXCouponToken.token_address)
        .where(Listing.is_public == True)
    )
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))

    # Search Filter
    if owner_address is not None:
        stmt = stmt.where(IDXCouponToken.owner_address == owner_address)
    if name is not None:
        stmt = stmt.where(IDXCouponToken.name.contains(name))
    if symbol is not None:
        stmt = stmt.where(IDXCouponToken.symbol.contains(symbol))
    if company_name is not None:
        stmt = stmt.where(IDXCouponToken.company_name.contains(company_name))
    if tradable_exchange is not None:
        stmt = stmt.where(IDXCouponToken.tradable_exchange == tradable_exchange)
    if status is not None:
        stmt = stmt.where(IDXCouponToken.status == status)
    if transferable is not None:
        stmt = stmt.where(IDXCouponToken.transferable == transferable)
    if initial_offering_status is not None:
        stmt = stmt.where(
            IDXCouponToken.initial_offering_status == initial_offering_status
        )
    count = session.scalar(select(func.count()).select_from(stmt.subquery()))

    sort_attr = getattr(IDXCouponToken, sort_item, None)

    if sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if sort_item != "created":
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(IDXCouponToken.created)

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _token_list: list[IDXCouponToken] = session.scalars(stmt).all()

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
    summary="Coupon token details",
    operation_id="CouponTokenDetails",
    response_model=GenericSuccessResponse[RetrieveCouponTokenResponse],
    responses=get_routers_responses(
        NotSupportedError, InvalidParameterError, DataNotExistsError
    ),
)
def retrieve_coupon_token(session: DBSession, req: Request, token_address: str):
    """
    Endpoint: /Token/Coupon/{contract_address}
    """
    if config.COUPON_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    # 入力アドレスフォーマットチェック
    try:
        contract_address = to_checksum_address(token_address)
        if not Web3.is_address(contract_address):
            description = "invalid contract_address"
            raise InvalidParameterError(description=description)
    except:
        description = "invalid contract_address"
        raise InvalidParameterError(description=description)

    # 取扱トークンチェック
    # NOTE:非公開トークンも取扱対象とする
    listed_token = session.scalars(
        select(Listing).where(Listing.token_address == contract_address).limit(1)
    ).first()
    if listed_token is None:
        raise DataNotExistsError("contract_address: %s" % contract_address)

    # TokenList-Contractからトークンの情報を取得する
    token_address = to_checksum_address(contract_address)

    try:
        token_detail = CouponToken.get(session=session, token_address=token_address)
    except ServiceUnavailable as e:
        LOG.warning(e)
        raise DataNotExistsError("contract_address: %s" % contract_address) from None
    except Exception as e:
        LOG.error(e)
        raise DataNotExistsError("contract_address: %s" % contract_address) from None

    return json_response({**SuccessResponse.default(), "data": token_detail.__dict__})
