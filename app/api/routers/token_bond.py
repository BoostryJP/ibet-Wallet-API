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
from sqlalchemy import desc
from sqlalchemy.orm import Session
from web3 import Web3

from app import config, log
from app.database import db_session
from app.errors import (
    DataNotExistsError,
    InvalidParameterError,
    NotSupportedError,
    ServiceUnavailable,
)
from app.model.blockchain import BondToken
from app.model.db import IDXBondToken, Listing
from app.model.schema import (
    GenericSuccessResponse,
    ListAllStraightBondTokenAddressesResponse,
    ListAllStraightBondTokensQuery,
    ListAllStraightBondTokensResponse,
    RetrieveStraightBondTokenResponse,
    SuccessResponse,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi import json_response

LOG = log.get_logger()

router = APIRouter(prefix="/Token/StraightBond", tags=["token_info"])


@router.get(
    "",
    summary="Token detail list of StraightBond tokens",
    operation_id="StraightBondTokens",
    response_model=GenericSuccessResponse[ListAllStraightBondTokensResponse],
    responses=get_routers_responses(NotSupportedError, InvalidParameterError),
)
def list_all_straight_bond_tokens(
    req: Request,
    address_list: list[str] = Query(
        default=[], description="list of token address (**this affects total number**)"
    ),
    request_query: ListAllStraightBondTokensQuery = Depends(),
    session: Session = Depends(db_session),
):
    """
    Endpoint: /Token/StraightBond
    """
    if config.BOND_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    for address in address_list:
        if address is not None:
            if not Web3.isAddress(address):
                raise InvalidParameterError(f"invalid token_address: {address}")

    owner_address: Optional[str] = request_query.owner_address
    name: Optional[str] = request_query.name
    symbol: Optional[str] = request_query.symbol
    company_name: Optional[str] = request_query.company_name
    tradable_exchange: Optional[str] = request_query.tradable_exchange
    status: Optional[bool] = request_query.status
    personal_info_address: Optional[str] = request_query.personal_info_address
    transferable: Optional[bool] = request_query.transferable
    is_offering: Optional[bool] = request_query.is_offering
    transfer_approval_required: Optional[
        bool
    ] = request_query.transfer_approval_required
    is_redeemed: Optional[bool] = request_query.is_redeemed

    sort_item = request_query.sort_item
    sort_order = request_query.sort_order  # default: asc
    offset = request_query.offset
    limit = request_query.limit

    # 取扱トークンリストを取得
    # 公開属性によるフィルタリングを行うためJOIN
    query = (
        session.query(IDXBondToken)
        .join(Listing, Listing.token_address == IDXBondToken.token_address)
        .filter(Listing.is_public == True)
    )
    if len(address_list):
        query = query.filter(IDXBondToken.token_address.in_(address_list))
    total = query.count()

    # Search Filter
    if owner_address is not None:
        query = query.filter(IDXBondToken.owner_address == owner_address)
    if name is not None:
        query = query.filter(IDXBondToken.name.contains(name))
    if symbol is not None:
        query = query.filter(IDXBondToken.symbol.contains(symbol))
    if company_name is not None:
        query = query.filter(IDXBondToken.company_name.contains(company_name))
    if tradable_exchange is not None:
        query = query.filter(IDXBondToken.tradable_exchange == tradable_exchange)
    if status is not None:
        query = query.filter(IDXBondToken.status == status)
    if personal_info_address is not None:
        query = query.filter(
            IDXBondToken.personal_info_address == personal_info_address
        )
    if transferable is not None:
        query = query.filter(IDXBondToken.transferable == transferable)
    if is_offering is not None:
        query = query.filter(IDXBondToken.is_offering == is_offering)
    if transfer_approval_required is not None:
        query = query.filter(
            IDXBondToken.transfer_approval_required == transfer_approval_required
        )
    if is_redeemed is not None:
        query = query.filter(IDXBondToken.is_redeemed == is_redeemed)
    count = query.count()

    sort_attr = getattr(IDXBondToken, sort_item, None)

    if sort_order == 0:  # ASC
        query = query.order_by(sort_attr)
    else:  # DESC
        query = query.order_by(desc(sort_attr))
    if sort_item != "created":
        # NOTE: Set secondary sort for consistent results
        query = query.order_by(IDXBondToken.created)

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    _token_list: list[IDXBondToken] = query.all()
    tokens = []

    for _token in _token_list:
        tokens.append(BondToken.from_model(_token).__dict__)

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
def list_all_straight_bond_token_addresses(
    req: Request,
    request_query: ListAllStraightBondTokensQuery = Depends(),
    session: Session = Depends(db_session),
):
    """
    Endpoint: /Token/StraightBond/Addresses
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
    transfer_approval_required: Optional[
        bool
    ] = request_query.transfer_approval_required
    is_redeemed: Optional[bool] = request_query.is_redeemed

    sort_item = request_query.sort_item
    sort_order = request_query.sort_order  # default: asc
    offset = request_query.offset
    limit = request_query.limit

    # 取扱トークンリストを取得
    # 公開属性によるフィルタリングを行うためJOIN
    query = (
        session.query(IDXBondToken)
        .join(Listing, Listing.token_address == IDXBondToken.token_address)
        .filter(Listing.is_public == True)
    )
    total = query.count()

    # Search Filter
    if owner_address is not None:
        query = query.filter(IDXBondToken.owner_address == owner_address)
    if name is not None:
        query = query.filter(IDXBondToken.name.contains(name))
    if symbol is not None:
        query = query.filter(IDXBondToken.symbol.contains(symbol))
    if company_name is not None:
        query = query.filter(IDXBondToken.company_name.contains(company_name))
    if tradable_exchange is not None:
        query = query.filter(IDXBondToken.tradable_exchange == tradable_exchange)
    if status is not None:
        query = query.filter(IDXBondToken.status == status)
    if personal_info_address is not None:
        query = query.filter(
            IDXBondToken.personal_info_address == personal_info_address
        )
    if transferable is not None:
        query = query.filter(IDXBondToken.transferable == transferable)
    if is_offering is not None:
        query = query.filter(IDXBondToken.is_offering == is_offering)
    if transfer_approval_required is not None:
        query = query.filter(
            IDXBondToken.transfer_approval_required == transfer_approval_required
        )
    if is_redeemed is not None:
        query = query.filter(IDXBondToken.is_redeemed == is_redeemed)
    count = query.count()

    sort_attr = getattr(IDXBondToken, sort_item, None)

    if sort_order == 0:  # ASC
        query = query.order_by(sort_attr)
    else:  # DESC
        query = query.order_by(desc(sort_attr))
    if sort_item != "created":
        # NOTE: Set secondary sort for consistent results
        query = query.order_by(IDXBondToken.created)

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    _token_list: list[IDXBondToken] = query.all()

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
def retrieve_straight_bond_token(
    req: Request, token_address: str, session: Session = Depends(db_session)
):
    """
    Endpoint: /Token/StraightBond/{contract_address}
    """
    if config.BOND_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    # 入力アドレスフォーマットチェック
    try:
        contract_address = to_checksum_address(token_address)
        if not Web3.isAddress(contract_address):
            description = "invalid contract_address"
            raise InvalidParameterError(description=description)
    except:
        description = "invalid contract_address"
        raise InvalidParameterError(description=description)

    # 取扱トークンチェック
    # NOTE:非公開トークンも取扱対象とする
    listed_token = (
        session.query(Listing).filter(Listing.token_address == contract_address).first()
    )
    if listed_token is None:
        raise DataNotExistsError("contract_address: %s" % contract_address)

    token_address = to_checksum_address(contract_address)
    try:
        token_detail = BondToken.get(session=session, token_address=token_address)

    except ServiceUnavailable as e:
        LOG.warning(e)
        raise DataNotExistsError("contract_address: %s" % contract_address) from None
    except Exception as e:
        LOG.error(e)
        raise DataNotExistsError("contract_address: %s" % contract_address) from None

    if token_detail is None:
        raise DataNotExistsError("contract_address: %s" % contract_address)

    return json_response({**SuccessResponse.default(), "data": token_detail.__dict__})
