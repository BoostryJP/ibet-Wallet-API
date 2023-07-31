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
from typing import Callable, Optional, Sequence

from eth_utils import to_checksum_address
from fastapi import APIRouter, Path, Query
from sqlalchemy import desc, select
from web3 import Web3

from app import config, log
from app.contracts import Contract
from app.database import DBSession
from app.errors import DataNotExistsError, InvalidParameterError
from app.model.blockchain import BondToken, CouponToken, MembershipToken, ShareToken
from app.model.db import (
    IDXBondToken,
    IDXCouponToken,
    IDXMembershipToken,
    IDXShareToken,
    Listing,
)
from app.model.schema import (
    GenericSuccessResponse,
    ListAllCompanyInfoResponse,
    ListAllCompanyTokensResponse,
    RetrieveCompanyInfoResponse,
    SuccessResponse,
)
from app.utils.company_list import CompanyList
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()

router = APIRouter(prefix="/Companies", tags=["company_info"])


# ------------------------------
# 発行会社一覧参照
# ------------------------------
@router.get(
    "",
    summary="Issuer Information List",
    operation_id="Companies",
    response_model=GenericSuccessResponse[ListAllCompanyInfoResponse],
    responses=get_routers_responses(),
)
def list_all_companies(
    session: DBSession,
    include_private_listing: Optional[bool] = Query(
        default=False, description="include private listing token issuers"
    ),
):
    """
    Endpoint: /Companies
    """

    # Get company list
    _company_list = CompanyList.get()
    company_list = [company.json() for company in _company_list.all()]

    # Get the token listed
    if include_private_listing:
        available_tokens: Sequence[
            tuple[Listing, str, str, str, str]
        ] = session.execute(
            select(
                Listing,
                IDXBondToken.owner_address,
                IDXShareToken.owner_address,
                IDXMembershipToken.owner_address,
                IDXCouponToken.owner_address,
            )
            .outerjoin(
                IDXBondToken, Listing.token_address == IDXBondToken.token_address
            )
            .outerjoin(
                IDXShareToken, Listing.token_address == IDXShareToken.token_address
            )
            .outerjoin(
                IDXMembershipToken,
                Listing.token_address == IDXMembershipToken.token_address,
            )
            .outerjoin(
                IDXCouponToken, Listing.token_address == IDXCouponToken.token_address
            )
        ).all()
    else:
        available_tokens: Sequence[
            tuple[Listing, str, str, str, str]
        ] = session.execute(
            select(
                Listing,
                IDXBondToken.owner_address,
                IDXShareToken.owner_address,
                IDXMembershipToken.owner_address,
                IDXCouponToken.owner_address,
            )
            .where(Listing.is_public == True)
            .outerjoin(
                IDXBondToken, Listing.token_address == IDXBondToken.token_address
            )
            .outerjoin(
                IDXShareToken, Listing.token_address == IDXShareToken.token_address
            )
            .outerjoin(
                IDXMembershipToken,
                Listing.token_address == IDXMembershipToken.token_address,
            )
            .outerjoin(
                IDXCouponToken, Listing.token_address == IDXCouponToken.token_address
            )
        ).all()

    # Filter only issuers that issue the listed tokens
    listing_owner_set = set()
    for token in available_tokens:
        try:
            owner_address_is_cached = [t for t in token[1:5] if t is not None]
            if owner_address_is_cached:
                listing_owner_set.add(owner_address_is_cached[0])
                continue

            token_address = to_checksum_address(token[0].token_address)
            token_contract = Contract.get_contract(
                contract_name="Ownable", address=token_address
            )
            owner_address = Contract.call_function(
                contract=token_contract,
                function_name="owner",
                args=(),
                default_returns=config.ZERO_ADDRESS,
            )
            listing_owner_set.add(owner_address)
        except Exception as e:
            LOG.warning(e)

    has_listing_owner_function = has_listing_owner_function_creator(listing_owner_set)
    filtered_company_list = filter(has_listing_owner_function, company_list)

    return json_response(
        {**SuccessResponse.default(), "data": list(filtered_company_list)}
    )


# ------------------------------
# 発行会社情報参照
# ------------------------------
@router.get(
    "/{eth_address}",
    summary="Issuer Information",
    operation_id="Company",
    response_model=GenericSuccessResponse[RetrieveCompanyInfoResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError),
)
def retrieve_company(eth_address: str = Path(..., description="address")):
    """
    Endpoint: /Companies/{eth_address}
    """
    if not Web3.is_address(eth_address):
        description = "invalid eth_address"
        raise InvalidParameterError(description=description)

    company = CompanyList.get_find(to_checksum_address(eth_address))
    if company.address == "":
        raise DataNotExistsError("eth_address: %s" % eth_address)

    return json_response({**SuccessResponse.default(), "data": company.json()})


# ------------------------------
# 発行会社のトークン一覧
# ------------------------------
@router.get(
    "/{eth_address}/Tokens",
    summary="List of tokens issued by issuer",
    operation_id="",
    response_model=GenericSuccessResponse[ListAllCompanyTokensResponse],
    responses=get_routers_responses(),
)
def retrieve_company_tokens(
    session: DBSession,
    eth_address: str = Path(..., description="address"),
    include_private_listing: Optional[bool] = Query(
        default=False, description="include private listing token issuers"
    ),
):
    """
    Endpoint: /Companies/{eth_address}/Tokens
    """
    # Validation
    if not Web3.is_address(eth_address):
        description = "invalid eth_address"
        raise InvalidParameterError(description=description)

    # TokenList contract
    list_contract = Contract.get_contract(
        contract_name="TokenList", address=str(config.TOKEN_LIST_CONTRACT_ADDRESS)
    )

    # Get the token listed
    if include_private_listing:
        available_list: Sequence[Listing] = session.scalars(
            select(Listing)
            .where(Listing.owner_address == eth_address)
            .order_by(desc(Listing.id))
        ).all()
    else:
        available_list: Sequence[Listing] = session.scalars(
            select(Listing)
            .where(Listing.owner_address == eth_address)
            .where(Listing.is_public == True)
            .order_by(desc(Listing.id))
        ).all()

    # Get token attributes
    token_list = []
    for available_token in available_list:
        token_address = to_checksum_address(available_token.token_address)
        token_info = Contract.call_function(
            contract=list_contract,
            function_name="getTokenByAddress",
            args=(token_address,),
            default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS),
        )
        # Only those items published in TokenList will be processed
        if token_info[0] != config.ZERO_ADDRESS:
            token_template = token_info[1]
            # Filter only the token types used in the system
            if available_token_template(token_template):
                token_model = get_token_model(token_template)
                token = token_model.get(session=session, token_address=token_address)
                token_list.append(token.__dict__)
            else:
                continue

    return json_response({**SuccessResponse.default(), "data": token_list})


def available_token_template(token_template: str) -> bool:
    """Availability of token type

    :param token_template: Token type
    :return: available (True) or not available (False)
    """
    if token_template == "IbetShare":
        return config.SHARE_TOKEN_ENABLED
    elif token_template == "IbetStraightBond":
        return config.BOND_TOKEN_ENABLED
    elif token_template == "IbetMembership":
        return config.MEMBERSHIP_TOKEN_ENABLED
    elif token_template == "IbetCoupon":
        return config.COUPON_TOKEN_ENABLED
    else:
        return False


def get_token_model(token_template: str):
    """Get token model

    :param token_template: Token type
    :return: Token model
    """
    if token_template == "IbetShare":
        return ShareToken
    elif token_template == "IbetStraightBond":
        return BondToken
    elif token_template == "IbetMembership":
        return MembershipToken
    elif token_template == "IbetCoupon":
        return CouponToken
    else:
        return False


def has_listing_owner_function_creator(
    listing_owner_set: set[str],
) -> Callable[[dict], bool]:
    def has_listing_owner_function(company_info: dict):
        for address in listing_owner_set:
            if to_checksum_address(company_info["address"]) == address:
                return True
        return False

    return has_listing_owner_function
