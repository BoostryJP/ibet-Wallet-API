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

from typing import TYPE_CHECKING, Annotated, Callable, Sequence

from eth_utils.address import to_checksum_address
from fastapi import APIRouter, Path, Query
from sqlalchemy import String, and_, desc, distinct, select, type_coerce
from sqlalchemy.orm import aliased

from app import config, log
from app.contracts import AsyncContract
from app.database import DBAsyncSession
from app.errors import DataNotExistsError, InvalidParameterError
from app.model.blockchain import (
    BondToken,
    CouponToken,
    MembershipToken,
    ShareToken,
    TokenClassTypes,
    TokenInstanceTypes,
)
from app.model.db import (
    IDXBondToken,
    IDXCouponToken,
    IDXMembershipToken,
    IDXShareToken,
    Listing,
)
from app.model.schema import (
    ListAllCompaniesQuery,
    ListAllCompaniesResponse,
    ListAllCompanyTokensQuery,
    ListAllCompanyTokensResponse,
    RetrieveCompanyInfoResponse,
    RetrieveCouponTokenResponse,
    RetrieveMembershipTokenResponse,
    RetrieveShareTokenResponse,
    RetrieveStraightBondTokenResponse,
    TokenDetailDict,
)
from app.model.schema.base import (
    BondToken as BondTokenSchema,
    CouponToken as CouponTokenSchema,
    GenericSuccessResponse,
    MembershipToken as MembershipTokenSchema,
    ShareToken as ShareTokenSchema,
    Success200MetaModel,
    SuccessResponse,
    TokenType,
)
from app.model.schema.company_info import CompanyInfo
from app.model.type import EthereumAddress
from app.model.type.company_list import Trustee as CompanyListTrustee
from app.utils.company_list import Company, CompanyList
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
    operation_id="ListAllCompanies",
    response_model=GenericSuccessResponse[ListAllCompaniesResponse],
    responses=get_routers_responses(),
)
async def list_all_companies(
    async_session: DBAsyncSession,
    request_query: Annotated[ListAllCompaniesQuery, Query()],
):
    """
    Returns a list of issuer information.
    """

    # Get company list
    _company_list = await CompanyList.get()
    company_list = _company_list.all()

    # Get the token listed
    if request_query.include_private_listing:
        available_tokens: Sequence[
            tuple[Listing, str | None, str | None, str | None, str | None]
        ] = (
            (
                await async_session.execute(
                    select(
                        Listing,
                        IDXBondToken.owner_address,
                        IDXShareToken.owner_address,
                        IDXMembershipToken.owner_address,
                        IDXCouponToken.owner_address,
                    )
                    .outerjoin(
                        IDXBondToken,
                        Listing.token_address == IDXBondToken.token_address,
                    )
                    .outerjoin(
                        IDXShareToken,
                        Listing.token_address == IDXShareToken.token_address,
                    )
                    .outerjoin(
                        IDXMembershipToken,
                        Listing.token_address == IDXMembershipToken.token_address,
                    )
                    .outerjoin(
                        IDXCouponToken,
                        Listing.token_address == IDXCouponToken.token_address,
                    )
                )
            )
            .tuples()
            .all()
        )
    else:
        available_tokens: Sequence[
            tuple[Listing, str | None, str | None, str | None, str | None]
        ] = (
            (
                await async_session.execute(
                    select(
                        Listing,
                        IDXBondToken.owner_address,
                        IDXShareToken.owner_address,
                        IDXMembershipToken.owner_address,
                        IDXCouponToken.owner_address,
                    )
                    .where(Listing.is_public == True)
                    .outerjoin(
                        IDXBondToken,
                        Listing.token_address == IDXBondToken.token_address,
                    )
                    .outerjoin(
                        IDXShareToken,
                        Listing.token_address == IDXShareToken.token_address,
                    )
                    .outerjoin(
                        IDXMembershipToken,
                        Listing.token_address == IDXMembershipToken.token_address,
                    )
                    .outerjoin(
                        IDXCouponToken,
                        Listing.token_address == IDXCouponToken.token_address,
                    )
                )
            )
            .tuples()
            .all()
        )

    # Filter only issuers that issue the listed tokens
    listing_owner_set: set[str] = set()
    for token in available_tokens:
        try:
            owner_address_is_cached = [t for t in token[1:5] if t is not None]
            if owner_address_is_cached:
                listing_owner_set.add(owner_address_is_cached[0])
                continue

            # TODO: Migrate listing.token_address to NOT NULL and update ORM typing
            assert token[0].token_address is not None
            token_address = to_checksum_address(token[0].token_address)
            token_contract = AsyncContract.get_contract(
                contract_name="Ownable", address=token_address
            )
            owner_address = await AsyncContract.call_function(
                contract=token_contract,
                function_name="owner",
                args=(),
                default_returns=config.ZERO_ADDRESS,
            )
            listing_owner_set.add(owner_address)
        except Exception as e:
            LOG.notice(str(e))

    has_listing_owner_function = has_listing_owner_function_creator(listing_owner_set)
    filtered_companies = list(filter(has_listing_owner_function, company_list))

    if TYPE_CHECKING:
        type_checked_companies: list[CompanyInfo] = []
        for company in filtered_companies:
            company_trustee = company["trustee"]
            type_checked_trustee: CompanyListTrustee | None = None
            if company_trustee is not None:
                type_checked_trustee = CompanyListTrustee(
                    corporate_name=company_trustee["corporate_name"],
                    corporate_number=company_trustee["corporate_number"],
                    corporate_address=company_trustee["corporate_address"],
                )
            type_checked_companies.append(
                CompanyInfo(
                    address=company["address"],
                    corporate_name=company["corporate_name"],
                    trustee=type_checked_trustee,
                    rsa_publickey=company["rsa_publickey"],
                    homepage=company["homepage"],
                )
            )
        _ = GenericSuccessResponse[ListAllCompaniesResponse](
            meta=Success200MetaModel(code=200, message="OK"),
            data=ListAllCompaniesResponse(root=type_checked_companies),
        )
    return json_response({**SuccessResponse.default(), "data": filtered_companies})


# ------------------------------
# 発行会社情報参照
# ------------------------------
@router.get(
    "/{eth_address}",
    summary="Issuer Information",
    operation_id="RetrieveCompanyInfo",
    response_model=GenericSuccessResponse[RetrieveCompanyInfoResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError),
)
async def retrieve_company_info(
    async_session: DBAsyncSession,
    eth_address: Annotated[EthereumAddress, Path(description="Issuer address")],
):
    """
    Returns given issuer information.
    """
    # Retrieve the company information linked to the issuer.
    company = await CompanyList.get_find(to_checksum_address(eth_address))
    if company["address"] == "":
        raise DataNotExistsError("eth_address: %s" % eth_address)

    # Retrieve the personal information address linked to the issuer.
    token_all = aliased(
        (
            select(
                IDXBondToken.personal_info_address.label("personal_info_address")
            ).where(
                and_(
                    IDXBondToken.owner_address == eth_address,
                    IDXBondToken.personal_info_address != None,
                )
            )
        )
        .union_all(
            select(
                IDXShareToken.personal_info_address.label("personal_info_address")
            ).where(
                and_(
                    IDXShareToken.owner_address == eth_address,
                    IDXShareToken.personal_info_address != None,
                )
            )
        )
        .subquery()
    )

    _personal_info_list: list[str] = list(
        (
            await async_session.scalars(
                select(
                    distinct(type_coerce(token_all.c.personal_info_address, String()))
                ).where(token_all.c.personal_info_address.is_not(None))
            )
        ).all()
    )
    resp = {**company}
    resp["in_use_personal_info_addresses"] = _personal_info_list

    if TYPE_CHECKING:
        company_trustee = company["trustee"]
        type_checked_trustee: CompanyListTrustee | None = None
        if company_trustee is not None:
            type_checked_trustee = CompanyListTrustee(
                corporate_name=company_trustee["corporate_name"],
                corporate_number=company_trustee["corporate_number"],
                corporate_address=company_trustee["corporate_address"],
            )
        _ = GenericSuccessResponse[RetrieveCompanyInfoResponse](
            meta=Success200MetaModel(code=200, message="OK"),
            data=RetrieveCompanyInfoResponse(
                address=company["address"],
                corporate_name=company["corporate_name"],
                trustee=type_checked_trustee,
                rsa_publickey=company["rsa_publickey"],
                homepage=company["homepage"],
                in_use_personal_info_addresses=_personal_info_list,
            ),
        )
    return json_response({**SuccessResponse.default(), "data": resp})


# ------------------------------
# 発行会社のトークン一覧
# ------------------------------
@router.get(
    "/{eth_address}/Tokens",
    summary="List of tokens issued by issuer",
    operation_id="ListAllCompanyTokens",
    response_model=GenericSuccessResponse[ListAllCompanyTokensResponse],
    responses=get_routers_responses(),
)
async def list_all_company_tokens(
    async_session: DBAsyncSession,
    eth_address: Annotated[EthereumAddress, Path(description="Issuer address")],
    request_query: Annotated[ListAllCompanyTokensQuery, Query()],
):
    """
    Returns a list of tokens issued by given issuer.
    """
    # TokenList contract
    list_contract = AsyncContract.get_contract(
        contract_name="TokenList", address=str(config.TOKEN_LIST_CONTRACT_ADDRESS)
    )

    # Get the token listed
    if request_query.include_private_listing:
        available_list: Sequence[Listing] = (
            await async_session.scalars(
                select(Listing)
                .where(Listing.owner_address == eth_address)
                .order_by(desc(Listing.id))
            )
        ).all()
    else:
        available_list: Sequence[Listing] = (
            await async_session.scalars(
                select(Listing)
                .where(Listing.owner_address == eth_address)
                .where(Listing.is_public == True)
                .order_by(desc(Listing.id))
            )
        ).all()

    # Get token attributes
    token_list: list[TokenDetailDict] = []
    token_instance_list: list[TokenInstanceTypes] = []
    for available_token in available_list:
        # TODO: Migrate listing.token_address to NOT NULL and update ORM typing
        assert available_token.token_address is not None
        token_address = to_checksum_address(available_token.token_address)
        token_info = await AsyncContract.call_function(
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
                if token_model is None:
                    continue
                token_model_cls: TokenClassTypes = token_model
                token_instance: TokenInstanceTypes = await token_model_cls.get(
                    async_session, token_address
                )
                token_instance_list.append(token_instance)
                token_list.append(token_instance.to_dict())
            else:
                continue

    if TYPE_CHECKING:
        type_checked_tokens: list[
            RetrieveStraightBondTokenResponse
            | RetrieveShareTokenResponse
            | RetrieveMembershipTokenResponse
            | RetrieveCouponTokenResponse
        ] = []
        for token_instance in token_instance_list:
            if isinstance(token_instance, BondToken):
                type_checked_tokens.append(
                    RetrieveStraightBondTokenResponse(
                        root=BondTokenSchema.from_blockchain_token(token_instance)
                    )
                )
            elif isinstance(token_instance, ShareToken):
                type_checked_tokens.append(
                    RetrieveShareTokenResponse(
                        root=ShareTokenSchema.from_blockchain_token(token_instance)
                    )
                )
            elif isinstance(token_instance, MembershipToken):
                type_checked_tokens.append(
                    RetrieveMembershipTokenResponse(
                        root=MembershipTokenSchema.from_blockchain_token(token_instance)
                    )
                )
            else:
                type_checked_tokens.append(
                    RetrieveCouponTokenResponse(
                        root=CouponTokenSchema.from_blockchain_token(token_instance)
                    )
                )
        _ = GenericSuccessResponse[ListAllCompanyTokensResponse](
            meta=Success200MetaModel(code=200, message="OK"),
            data=ListAllCompanyTokensResponse(root=type_checked_tokens),
        )
    return json_response({**SuccessResponse.default(), "data": token_list})


def available_token_template(token_template: str) -> bool:
    """Availability of token type

    :param token_template: Token type
    :return: available (True) or not available (False)
    """
    if token_template == TokenType.IbetShare:
        return config.SHARE_TOKEN_ENABLED
    elif token_template == TokenType.IbetStraightBond:
        return config.BOND_TOKEN_ENABLED
    elif token_template == TokenType.IbetMembership:
        return config.MEMBERSHIP_TOKEN_ENABLED
    elif token_template == TokenType.IbetCoupon:
        return config.COUPON_TOKEN_ENABLED
    else:
        return False


def get_token_model(token_template: str) -> TokenClassTypes | None:
    """Get token model

    :param token_template: Token type
    :return: Token model
    """
    if token_template == TokenType.IbetShare:
        return ShareToken
    elif token_template == TokenType.IbetStraightBond:
        return BondToken
    elif token_template == TokenType.IbetMembership:
        return MembershipToken
    elif token_template == TokenType.IbetCoupon:
        return CouponToken
    else:
        return None


def has_listing_owner_function_creator(
    listing_owner_set: set[str],
) -> Callable[[Company], bool]:
    def has_listing_owner_function(company_info: Company):
        if to_checksum_address(company_info["address"]) in listing_owner_set:
            return True
        return False

    return has_listing_owner_function
