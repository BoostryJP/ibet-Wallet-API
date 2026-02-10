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

from fastapi import APIRouter, Path, Query, Request
from sqlalchemy import desc, func, select

from app import config, log
from app.contracts import AsyncContract
from app.database import DBAsyncSession
from app.errors import (
    DataNotExistsError,
    InvalidParameterError,
    NotSupportedError,
    ServiceUnavailable,
)
from app.model.blockchain import BondToken as BondTokenBlockchain
from app.model.db import IDXBondToken, Listing
from app.model.schema import (
    ListAllStraightBondTokenAddressesResponse,
    ListAllStraightBondTokensQuery,
    ListAllStraightBondTokensResponse,
    RetrieveStraightBondTokenResponse,
    StraightBondTokensQuery,
    StraightBondTokensSortItem,
)
from app.model.schema.base import (
    BondToken as BondTokenSchema,
    GenericSuccessResponse,
    ResultSet,
    SortOrder,
    Success200MetaModel,
    SuccessResponse,
    TokenType,
)
from app.model.type import EthereumAddress
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
    request_query: Annotated[ListAllStraightBondTokensQuery, Query()],
):
    """
    [StraightBond]Returns a detail list of tokens.
    """
    if config.BOND_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    sort_item = request_query.sort_item
    sort_order = request_query.sort_order  # default: asc
    offset = request_query.offset
    limit = request_query.limit

    # Get list of available tokens
    # - JOIN Listing to filter public/private tokens
    stmt = (
        select(IDXBondToken)
        .join(Listing, Listing.token_address == IDXBondToken.token_address)
        .where(Listing.is_public == True)
    )
    if len(request_query.address_list):
        stmt = stmt.where(IDXBondToken.token_address.in_(request_query.address_list))
    total = await async_session.scalar(
        stmt.with_only_columns(func.count()).order_by(None)
    )

    # Search Filter
    if request_query.owner_address is not None:
        stmt = stmt.where(IDXBondToken.owner_address == request_query.owner_address)
    if request_query.name is not None:
        stmt = stmt.where(IDXBondToken.name.contains(request_query.name))
    if request_query.symbol is not None:
        stmt = stmt.where(IDXBondToken.symbol.contains(request_query.symbol))
    if request_query.company_name is not None:
        stmt = stmt.where(
            IDXBondToken.company_name.contains(request_query.company_name)
        )
    if request_query.tradable_exchange is not None:
        stmt = stmt.where(
            IDXBondToken.tradable_exchange == request_query.tradable_exchange
        )
    if request_query.status is not None:
        stmt = stmt.where(IDXBondToken.status == request_query.status)
    if request_query.personal_info_address is not None:
        stmt = stmt.where(
            IDXBondToken.personal_info_address == request_query.personal_info_address
        )
    if request_query.require_personal_info_registered is not None:
        stmt = stmt.where(
            IDXBondToken.require_personal_info_registered
            == request_query.require_personal_info_registered
        )
    if request_query.transferable is not None:
        stmt = stmt.where(IDXBondToken.transferable == request_query.transferable)
    if request_query.is_offering is not None:
        stmt = stmt.where(IDXBondToken.is_offering == request_query.is_offering)
    if request_query.transfer_approval_required is not None:
        stmt = stmt.where(
            IDXBondToken.transfer_approval_required
            == request_query.transfer_approval_required
        )
    if request_query.is_redeemed is not None:
        stmt = stmt.where(IDXBondToken.is_redeemed == request_query.is_redeemed)
    count = await async_session.scalar(
        stmt.with_only_columns(func.count()).order_by(None)
    )

    if sort_item == StraightBondTokensSortItem.created:
        sort_attr = getattr(Listing, sort_item.value)
    else:
        sort_attr = getattr(IDXBondToken, sort_item.value)

    if sort_order == SortOrder.ASC:
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if sort_item != StraightBondTokensSortItem.created:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(Listing.created)

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _token_list: Sequence[IDXBondToken] = (await async_session.scalars(stmt)).all()
    bond_tokens = [BondTokenBlockchain.from_model(_token) for _token in _token_list]
    tokens = [token.__dict__ for token in bond_tokens]
    data = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "tokens": tokens,
    }

    if TYPE_CHECKING:
        type_checked_tokens: list[BondTokenSchema] = [
            BondTokenSchema.from_blockchain_token(token) for token in bond_tokens
        ]
        _ = GenericSuccessResponse[ListAllStraightBondTokensResponse](
            meta=Success200MetaModel(code=200, message="OK"),
            data=ListAllStraightBondTokensResponse(
                result_set=ResultSet(
                    count=count,
                    offset=offset,
                    limit=limit,
                    total=total,
                ),
                tokens=type_checked_tokens,
            ),
        )
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
    request_query: Annotated[StraightBondTokensQuery, Query()],
):
    """
    [StraightBond]Returns a list of token addresses.
    """
    if config.BOND_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    sort_item = request_query.sort_item
    sort_order = request_query.sort_order  # default: asc
    offset = request_query.offset
    limit = request_query.limit

    # Get list of available tokens
    # - JOIN Listing to filter public/private tokens
    stmt = (
        select(IDXBondToken)
        .join(Listing, Listing.token_address == IDXBondToken.token_address)
        .where(Listing.is_public == True)
    )
    total = await async_session.scalar(
        stmt.with_only_columns(func.count()).order_by(None)
    )

    # Search Filter
    if request_query.owner_address is not None:
        stmt = stmt.where(IDXBondToken.owner_address == request_query.owner_address)
    if request_query.name is not None:
        stmt = stmt.where(IDXBondToken.name.contains(request_query.name))
    if request_query.symbol is not None:
        stmt = stmt.where(IDXBondToken.symbol.contains(request_query.symbol))
    if request_query.company_name is not None:
        stmt = stmt.where(
            IDXBondToken.company_name.contains(request_query.company_name)
        )
    if request_query.tradable_exchange is not None:
        stmt = stmt.where(
            IDXBondToken.tradable_exchange == request_query.tradable_exchange
        )
    if request_query.status is not None:
        stmt = stmt.where(IDXBondToken.status == request_query.status)
    if request_query.personal_info_address is not None:
        stmt = stmt.where(
            IDXBondToken.personal_info_address == request_query.personal_info_address
        )
    if request_query.require_personal_info_registered is not None:
        stmt = stmt.where(
            IDXBondToken.require_personal_info_registered
            == request_query.require_personal_info_registered
        )
    if request_query.transferable is not None:
        stmt = stmt.where(IDXBondToken.transferable == request_query.transferable)
    if request_query.is_offering is not None:
        stmt = stmt.where(IDXBondToken.is_offering == request_query.is_offering)
    if request_query.transfer_approval_required is not None:
        stmt = stmt.where(
            IDXBondToken.transfer_approval_required
            == request_query.transfer_approval_required
        )
    if request_query.is_redeemed is not None:
        stmt = stmt.where(IDXBondToken.is_redeemed == request_query.is_redeemed)
    count = await async_session.scalar(
        stmt.with_only_columns(func.count()).order_by(None)
    )

    if sort_item == StraightBondTokensSortItem.created:
        sort_attr = getattr(Listing, sort_item.value)
    else:
        sort_attr = getattr(IDXBondToken, sort_item.value)

    if sort_order == SortOrder.ASC:
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if sort_item != StraightBondTokensSortItem.created:
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

    if TYPE_CHECKING:
        _ = GenericSuccessResponse[ListAllStraightBondTokenAddressesResponse](
            meta=Success200MetaModel(code=200, message="OK"),
            data=ListAllStraightBondTokenAddressesResponse(
                result_set=ResultSet(
                    count=count,
                    offset=offset,
                    limit=limit,
                    total=total,
                ),
                address_list=[token.token_address for token in _token_list],
            ),
        )
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
    token_address: Annotated[EthereumAddress, Path(description="Token address")],
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

    list_contract = AsyncContract.get_contract(
        contract_name="TokenList", address=config.TOKEN_LIST_CONTRACT_ADDRESS or ""
    )
    token: tuple[str, str, str] = await AsyncContract.call_function(
        contract=list_contract,
        function_name="getTokenByAddress",
        args=(token_address,),
        default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS),
    )
    token_template = str(token[1])

    if token_template != TokenType.IbetStraightBond:
        raise DataNotExistsError("token_address: %s" % token_address)

    try:
        token_detail: BondTokenBlockchain = await BondTokenBlockchain.get(
            async_session, token_address
        )
    except ServiceUnavailable as e:
        LOG.notice(str(e))
        raise DataNotExistsError("token_address: %s" % token_address) from None
    except Exception as e:
        LOG.error(e)
        raise DataNotExistsError("token_address: %s" % token_address) from None

    if TYPE_CHECKING:
        type_checked_token = BondTokenSchema.from_blockchain_token(token_detail)
        _ = GenericSuccessResponse[RetrieveStraightBondTokenResponse](
            meta=Success200MetaModel(code=200, message="OK"),
            data=RetrieveStraightBondTokenResponse(root=type_checked_token),
        )
    return json_response({**SuccessResponse.default(), "data": token_detail.__dict__})
