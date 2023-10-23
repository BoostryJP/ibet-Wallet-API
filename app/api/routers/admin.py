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
from typing import Sequence

from fastapi import APIRouter, Path
from sqlalchemy import delete, select

from app import config, log
from app.contracts import Contract
from app.database import DBSession
from app.errors import (
    AppError,
    DataConflictError,
    DataNotExistsError,
    InvalidParameterError,
)
from app.model.blockchain import BondToken, CouponToken, MembershipToken, ShareToken
from app.model.db import (
    ExecutableContract,
    IDXBondToken,
    IDXCouponToken,
    IDXMembershipToken,
    IDXPosition,
    IDXShareToken,
    Listing,
)
from app.model.schema import (
    GetAdminTokenTypeResponse,
    ListAllAdminTokensResponse,
    RegisterAdminTokenRequest,
    RetrieveAdminTokenResponse,
    UpdateAdminTokenRequest,
)
from app.model.schema.base import GenericSuccessResponse, SuccessResponse, TokenType
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()

router = APIRouter(prefix="/Admin", tags=["admin"])

# ------------------------------
# [管理]取扱トークン登録/一覧取得
# ------------------------------


@router.get(
    "/Tokens",
    summary="List All Listed Tokens",
    operation_id="TokensGET",
    response_model=GenericSuccessResponse[ListAllAdminTokensResponse],
)
def list_all_admin_tokens(session: DBSession):
    """
    Endpoint: /Admin/Tokens
      - GET: 取扱トークン一覧取得
    """
    listed_tokens: Sequence[Listing] = session.scalars(select(Listing)).all()

    res_body = [token.json() for token in listed_tokens]

    # idの降順にソート
    res_body.sort(key=lambda x: x["id"], reverse=True)  # type: ignore

    return json_response({**SuccessResponse.default(), "data": res_body})


@router.post(
    "/Tokens",
    summary="List a Token",
    operation_id="TokensPOST",
    response_model=SuccessResponse,
    responses=get_routers_responses(DataConflictError, InvalidParameterError),
)
def register_admin_token(session: DBSession, data: RegisterAdminTokenRequest):
    """
    Endpoint: /Admin/Tokens
      - POST: 取扱トークン登録
    """
    contract_address = data.contract_address

    # 既存レコードの存在チェック
    _listing = session.scalars(
        select(Listing).where(Listing.token_address == contract_address).limit(1)
    ).first()

    if _listing is not None:
        raise DataConflictError(description="contract_address already exist")

    _executable_contract = session.scalars(
        select(ExecutableContract)
        .where(ExecutableContract.contract_address == contract_address)
        .limit(1)
    ).first()
    if _executable_contract is not None:
        raise DataConflictError(description="contract_address already exist")

    # token情報をTokenListコントラクトから取得
    list_contract = Contract.get_contract(
        contract_name="TokenList", address=config.TOKEN_LIST_CONTRACT_ADDRESS or ""
    )
    token = Contract.call_function(
        contract=list_contract,
        function_name="getTokenByAddress",
        args=(contract_address,),
        default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS),
    )

    # contract_addressの有効性チェック
    if token[1] is None or token[1] not in available_token_template():
        raise InvalidParameterError(
            description="contract_address is invalid token address"
        )

    owner_address = token[2]

    # 新規レコードの登録
    is_public = data.is_public
    max_holding_quantity = data.max_holding_quantity
    max_sell_amount = data.max_sell_amount

    listing = Listing(
        token_address=contract_address,
        is_public=is_public,
        max_holding_quantity=max_holding_quantity,
        max_sell_amount=max_sell_amount,
        owner_address=owner_address,
    )
    session.add(listing)

    executable_contract = ExecutableContract(contract_address=contract_address)
    session.add(executable_contract)

    token_type = token[1]
    # Fetch token detail data to store cache
    if token_type == TokenType.IbetCoupon:
        token_obj = CouponToken.get(session, contract_address)
        session.merge(token_obj.to_model())
    elif token_type == TokenType.IbetMembership:
        token_obj = MembershipToken.get(session, contract_address)
        session.merge(token_obj.to_model())
    elif token_type == TokenType.IbetStraightBond:
        token_obj = BondToken.get(session, contract_address)
        session.merge(token_obj.to_model())
    elif token_type == TokenType.IbetShare:
        token_obj = ShareToken.get(session, contract_address)
        session.merge(token_obj.to_model())

    (
        balance,
        pending_transfer,
        exchange_balance,
        exchange_commitment,
    ) = get_account_balance_all(
        token_template=token_type,
        token_address=contract_address,
        account_address=owner_address,
    )
    position = IDXPosition(
        token_address=contract_address,
        account_address=owner_address,
        balance=balance or 0,
        pending_transfer=pending_transfer or 0,
        exchange_balance=exchange_balance or 0,
        exchange_commitment=exchange_commitment or 0,
    )
    session.merge(position)
    session.commit()

    return json_response(SuccessResponse.default())


# ------------------------------
# [管理]取扱トークン種別
# ------------------------------


@router.get(
    "/Tokens/Type",
    summary="Available status by token type",
    operation_id="TokenType",
    response_model=GenericSuccessResponse[GetAdminTokenTypeResponse],
    response_model_exclude_unset=True,
)
def get_admin_token_type():
    """
    Endpoint: /Admin/Tokens/Type
      - GET: 取扱トークン種別
    """
    res_body = {
        "IbetStraightBond": config.BOND_TOKEN_ENABLED,
        "IbetShare": config.SHARE_TOKEN_ENABLED,
        "IbetMembership": config.MEMBERSHIP_TOKEN_ENABLED,
        "IbetCoupon": config.COUPON_TOKEN_ENABLED,
    }
    return json_response({**SuccessResponse.default(), "data": res_body})


# ------------------------------
# [管理]取扱トークン情報取得/更新
# ------------------------------


@router.get(
    "/Tokens/{token_address}",
    summary="Retrieve a Listed Token",
    operation_id="TokenGET",
    response_model=GenericSuccessResponse[RetrieveAdminTokenResponse],
    response_model_exclude_unset=True,
    responses=get_routers_responses(DataNotExistsError),
)
def retrieve_admin_token(
    session: DBSession,
    token_address: str = Path(description="Token Address"),
):
    """
    Endpoint: /Admin/Tokens/{token_address}
      - GET: 取扱トークン情報取得（個別）
    """
    token = session.scalars(
        select(Listing).where(Listing.token_address == token_address).limit(1)
    ).first()

    if token is not None:
        return json_response({**SuccessResponse.default(), "data": token.json()})
    else:
        raise DataNotExistsError()


@router.post(
    "/Tokens/{token_address}",
    summary="Update a Listed Token",
    operation_id="TokenPOST",
    response_model=SuccessResponse,
    responses=get_routers_responses(InvalidParameterError, DataNotExistsError),
)
def update_token(
    session: DBSession,
    data: UpdateAdminTokenRequest,
    token_address: str = Path(description="Token Address"),
):
    """
    Endpoint: /Admin/Tokens/{contract_address}
      - POST: 取扱トークン情報更新（個別）
    """
    # 更新対象レコードを取得
    # 更新対象のレコードが存在しない場合は404エラーを返す
    token = session.scalars(
        select(Listing).where(Listing.token_address == token_address).limit(1)
    ).first()
    if token is None:
        raise DataNotExistsError()

    # レコードの更新
    is_public = data.is_public if data.is_public is not None else token.is_public
    max_holding_quantity = (
        data.max_holding_quantity
        if data.max_holding_quantity is not None
        else token.max_holding_quantity
    )
    max_sell_amount = (
        data.max_sell_amount
        if data.max_sell_amount is not None
        else token.max_sell_amount
    )
    owner_address = (
        data.owner_address if data.owner_address is not None else token.owner_address
    )

    token.is_public = is_public
    token.max_holding_quantity = max_holding_quantity
    token.max_sell_amount = max_sell_amount
    token.owner_address = owner_address
    session.merge(token)
    session.commit()
    return json_response(SuccessResponse.default())


@router.delete(
    "/Tokens/{token_address}",
    summary="Delete a Listed Token",
    operation_id="TokenDELETE",
    response_model=SuccessResponse,
    responses=get_routers_responses(AppError),
)
def delete_token(
    session: DBSession,
    token_address: str = Path(description="Token Address"),
):
    """
    Endpoint: /Admin/Tokens/{contract_address}
      - DELETE: 取扱トークン情報削除（個別）
    """
    try:
        session.execute(delete(Listing).where(Listing.token_address == token_address))
        session.execute(
            delete(ExecutableContract).where(
                ExecutableContract.contract_address == token_address
            )
        )
        session.execute(
            delete(IDXBondToken).where(IDXBondToken.token_address == token_address)
        )
        session.execute(
            delete(IDXShareToken).where(IDXShareToken.token_address == token_address)
        )
        session.execute(
            delete(IDXMembershipToken).where(
                IDXMembershipToken.token_address == token_address
            )
        )
        session.execute(
            delete(IDXCouponToken).where(IDXCouponToken.token_address == token_address)
        )
    except Exception as err:
        LOG.exception(f"Failed to delete the data: {err}")
        raise AppError()
    session.commit()
    return json_response(SuccessResponse.default())


def available_token_template():
    """
    利用可能なtoken_templateをlistで返却

    :return: 利用可能なtoken_templateリスト
    """
    available_token_template_list = []
    if config.BOND_TOKEN_ENABLED:
        available_token_template_list.append(TokenType.IbetStraightBond)
    if config.SHARE_TOKEN_ENABLED:
        available_token_template_list.append(TokenType.IbetShare)
    if config.MEMBERSHIP_TOKEN_ENABLED:
        available_token_template_list.append(TokenType.IbetMembership)
    if config.COUPON_TOKEN_ENABLED:
        available_token_template_list.append(TokenType.IbetCoupon)
    return available_token_template_list


def get_account_balance_all(
    token_template: str, token_address: str, account_address: str
) -> tuple[int, int, int, int]:
    """Get balance"""
    token_contract = Contract.get_contract(
        contract_name=token_template, address=token_address
    )
    balance = Contract.call_function(
        contract=token_contract,
        function_name="balanceOf",
        args=(account_address,),
        default_returns=0,
    )
    pending_transfer = 0
    if token_template in [TokenType.IbetStraightBond, TokenType.IbetShare]:
        # if security token, amount of pending transfer is needed
        pending_transfer = Contract.call_function(
            contract=token_contract,
            function_name="pendingTransfer",
            args=(account_address,),
            default_returns=0,
        )
    exchange_balance = 0
    exchange_commitment = 0
    tradable_exchange_address = Contract.call_function(
        contract=token_contract,
        function_name="tradableExchange",
        args=(),
        default_returns=config.ZERO_ADDRESS,
    )
    if tradable_exchange_address != config.ZERO_ADDRESS:
        exchange_contract = Contract.get_contract(
            "IbetExchangeInterface", tradable_exchange_address
        )
        exchange_balance = Contract.call_function(
            contract=exchange_contract,
            function_name="balanceOf",
            args=(
                account_address,
                token_contract.address,
            ),
            default_returns=0,
        )
        exchange_commitment = Contract.call_function(
            contract=exchange_contract,
            function_name="commitmentOf",
            args=(
                account_address,
                token_contract.address,
            ),
            default_returns=0,
        )
    return balance, pending_transfer, exchange_balance, exchange_commitment
