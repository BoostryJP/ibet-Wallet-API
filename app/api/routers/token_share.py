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
from app.model.blockchain import ShareToken
from app.model.db import IDXShareToken, Listing
from app.model.schema import (
    ListAllShareTokenAddressesResponse,
    ListAllShareTokensQuery,
    ListAllShareTokensResponse,
    RetrieveShareTokenResponse,
    ShareTokensQuery,
)
from app.model.schema.base import (
    EthereumAddress,
    GenericSuccessResponse,
    SuccessResponse,
    TokenType,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()

router = APIRouter(prefix="/Token/Share", tags=["token_info"])


@router.get(
    "",
    summary="Token detail list of Share tokens",
    operation_id="ShareTokens",
    response_model=GenericSuccessResponse[ListAllShareTokensResponse],
    responses=get_routers_responses(NotSupportedError, InvalidParameterError),
)
async def list_all_share_tokens(
    async_session: DBAsyncSession,
    req: Request,
    request_query: Annotated[ListAllShareTokensQuery, Query()],
):
    """
    [Share]Returns a detail list of tokens.
    """
    if config.SHARE_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    sort_item = request_query.sort_item
    sort_order = request_query.sort_order
    offset = request_query.offset
    limit = request_query.limit

    # Get list of available tokens
    # - JOIN Listing to filter public/private tokens
    stmt = (
        select(IDXShareToken)
        .join(Listing, Listing.token_address == IDXShareToken.token_address)
        .where(Listing.is_public == True)
    )
    if len(request_query.address_list):
        stmt = stmt.where(IDXShareToken.token_address.in_(request_query.address_list))
    total = await async_session.scalar(
        stmt.with_only_columns(func.count()).order_by(None)
    )

    # Search Filter
    if request_query.owner_address is not None:
        stmt = stmt.where(IDXShareToken.owner_address == request_query.owner_address)
    if request_query.name is not None:
        stmt = stmt.where(IDXShareToken.name.contains(request_query.name))
    if request_query.symbol is not None:
        stmt = stmt.where(IDXShareToken.symbol.contains(request_query.symbol))
    if request_query.company_name is not None:
        stmt = stmt.where(
            IDXShareToken.company_name.contains(request_query.company_name)
        )
    if request_query.tradable_exchange is not None:
        stmt = stmt.where(
            IDXShareToken.tradable_exchange == request_query.tradable_exchange
        )
    if request_query.status is not None:
        stmt = stmt.where(IDXShareToken.status == request_query.status)
    if request_query.personal_info_address is not None:
        stmt = stmt.where(
            IDXShareToken.personal_info_address == request_query.personal_info_address
        )
    if request_query.require_personal_info_registered is not None:
        stmt = stmt.where(
            IDXShareToken.require_personal_info_registered
            == request_query.require_personal_info_registered
        )
    if request_query.transferable is not None:
        stmt = stmt.where(IDXShareToken.transferable == request_query.transferable)
    if request_query.is_offering is not None:
        stmt = stmt.where(IDXShareToken.is_offering == request_query.is_offering)
    if request_query.transfer_approval_required is not None:
        stmt = stmt.where(
            IDXShareToken.transfer_approval_required
            == request_query.transfer_approval_required
        )
    if request_query.is_canceled is not None:
        stmt = stmt.where(IDXShareToken.is_canceled == request_query.is_canceled)
    count = await async_session.scalar(
        stmt.with_only_columns(func.count()).order_by(None)
    )

    if sort_item == "created":
        sort_attr = getattr(Listing, sort_item, None)
    else:
        sort_attr = getattr(IDXShareToken, sort_item, None)

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

    _token_list: Sequence[IDXShareToken] = (await async_session.scalars(stmt)).all()

    tokens = [ShareToken.from_model(_token).__dict__ for _token in _token_list]
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
    summary="List of Share token address",
    operation_id="ShareTokenAddresses",
    response_model=GenericSuccessResponse[ListAllShareTokenAddressesResponse],
    responses=get_routers_responses(NotSupportedError),
)
async def list_all_share_token_addresses(
    async_session: DBAsyncSession,
    req: Request,
    request_query: Annotated[ShareTokensQuery, Query()],
):
    """
    [Share]Returns a list of token addresses.
    """
    if config.SHARE_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    sort_item = request_query.sort_item
    sort_order = request_query.sort_order
    offset = request_query.offset
    limit = request_query.limit

    # Get list of available tokens
    # - JOIN Listing to filter public/private tokens
    stmt = (
        select(IDXShareToken)
        .join(Listing, Listing.token_address == IDXShareToken.token_address)
        .where(Listing.is_public == True)
    )
    total = await async_session.scalar(
        stmt.with_only_columns(func.count()).order_by(None)
    )

    # Search Filter
    if request_query.owner_address is not None:
        stmt = stmt.where(IDXShareToken.owner_address == request_query.owner_address)
    if request_query.name is not None:
        stmt = stmt.where(IDXShareToken.name.contains(request_query.name))
    if request_query.symbol is not None:
        stmt = stmt.where(IDXShareToken.symbol.contains(request_query.symbol))
    if request_query.company_name is not None:
        stmt = stmt.where(
            IDXShareToken.company_name.contains(request_query.company_name)
        )
    if request_query.tradable_exchange is not None:
        stmt = stmt.where(
            IDXShareToken.tradable_exchange == request_query.tradable_exchange
        )
    if request_query.status is not None:
        stmt = stmt.where(IDXShareToken.status == request_query.status)
    if request_query.personal_info_address is not None:
        stmt = stmt.where(
            IDXShareToken.personal_info_address == request_query.personal_info_address
        )
    if request_query.require_personal_info_registered is not None:
        stmt = stmt.where(
            IDXShareToken.require_personal_info_registered
            == request_query.require_personal_info_registered
        )
    if request_query.transferable is not None:
        stmt = stmt.where(IDXShareToken.transferable == request_query.transferable)
    if request_query.is_offering is not None:
        stmt = stmt.where(IDXShareToken.is_offering == request_query.is_offering)
    if request_query.transfer_approval_required is not None:
        stmt = stmt.where(
            IDXShareToken.transfer_approval_required
            == request_query.transfer_approval_required
        )
    if request_query.is_canceled is not None:
        stmt = stmt.where(IDXShareToken.is_canceled == request_query.is_canceled)
    count = await async_session.scalar(
        stmt.with_only_columns(func.count()).order_by(None)
    )

    if sort_item == "created":
        sort_attr = getattr(Listing, sort_item, None)
    else:
        sort_attr = getattr(IDXShareToken, sort_item, None)

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

    _token_list: Sequence[IDXShareToken] = (await async_session.scalars(stmt)).all()

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
    summary="Share token details",
    operation_id="ShareTokenDetails",
    response_model=GenericSuccessResponse[RetrieveShareTokenResponse],
    responses=get_routers_responses(NotSupportedError, InvalidParameterError),
)
async def retrieve_share_token(
    async_session: DBAsyncSession,
    req: Request,
    token_address: Annotated[EthereumAddress, Path(description="Token address")],
):
    """
    [Share]Returns the details of the token.
    """
    if config.SHARE_TOKEN_ENABLED is False:
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
    token = await AsyncContract.call_function(
        contract=list_contract,
        function_name="getTokenByAddress",
        args=(token_address,),
        default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS),
    )
    token_template = token[1]

    if token_template != TokenType.IbetShare:
        raise DataNotExistsError("token_address: %s" % token_address)

    try:
        token_detail = await ShareToken.get(
            async_session=async_session, token_address=token_address
        )
    except ServiceUnavailable as e:
        LOG.notice(e)
        raise DataNotExistsError("token_address: %s" % token_address) from None
    except Exception as e:
        LOG.error(e)
        raise DataNotExistsError("token_address: %s" % token_address) from None

    if token_detail is None:
        raise DataNotExistsError("token_address: %s" % token_address)

    return json_response({**SuccessResponse.default(), "data": token_detail.__dict__})
