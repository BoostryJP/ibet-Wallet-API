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
from fastapi import (
    APIRouter,
    Depends,
    Path
)

from sqlalchemy.orm import Session

from app import log
from app import config
from app.contracts import Contract
from app.database import db_session
from app.errors import (
    InvalidParameterError,
    DataNotExistsError,
    AppError,
    DataConflictError
)
from app.model.blockchain import (
    CouponToken,
    MembershipToken,
    BondToken,
    ShareToken
)
from app.model.db import (
    Listing,
    ExecutableContract,
    IDXBondToken,
    IDXShareToken,
    IDXMembershipToken,
    IDXCouponToken,
    IDXPosition
)
from app.model.schema import (
    SuccessResponse,
    RegisterAdminTokenRequest,
    UpdateAdminTokenRequest,
    GenericSuccessResponse,
    ListAllAdminTokensResponse,
    RetrieveAdminTokenResponse,
    GetAdminTokenTypeResponse
)
from app.utils.docs_utils import get_routers_responses

LOG = log.get_logger()

router = APIRouter(
    prefix="/Admin",
    tags=["Admin"]
)

# ------------------------------
# [管理]取扱トークン登録/一覧取得
# ------------------------------


@router.get(
    "/Tokens",
    summary="List All Listed Tokens",
    operation_id="TokensGET",
    response_model=GenericSuccessResponse[ListAllAdminTokensResponse]
)
def list_all_admin_tokens(
    session: Session = Depends(db_session)
):
    """
    Endpoint: /Admin/Tokens
      - GET: 取扱トークン一覧取得
    """
    res_body = []

    listed_tokens = session.query(Listing).all()
    for token in listed_tokens:
        item = token.json()
        res_body.append(item)

    # idの降順にソート
    res_body.sort(key=lambda x: x["id"], reverse=True)  # type: ignore

    return {
        **SuccessResponse.use().dict(),
        "data": res_body
    }


@router.post(
    "/Tokens",
    summary="List a Token",
    operation_id="TokensPOST",
    response_model=SuccessResponse,
    responses=get_routers_responses(DataConflictError, InvalidParameterError),
)
def register_admin_token(
    data: RegisterAdminTokenRequest,
    session: Session = Depends(db_session)
):
    """
    Endpoint: /Admin/Tokens
      - POST: 取扱トークン登録
    """
    contract_address = data.contract_address

    # 既存レコードの存在チェック
    _listing = session.query(Listing). \
        filter(Listing.token_address == contract_address). \
        first()
    if _listing is not None:
        raise DataConflictError(description="contract_address already exist")

    _executable_contract = session.query(ExecutableContract). \
        filter(ExecutableContract.contract_address == contract_address). \
        first()
    if _executable_contract is not None:
        raise DataConflictError(description="contract_address already exist")

    # token情報をTokenListコントラクトから取得
    list_contract = Contract.get_contract(
        contract_name='TokenList',
        address=config.TOKEN_LIST_CONTRACT_ADDRESS or ""
    )
    token = Contract.call_function(
        contract=list_contract,
        function_name="getTokenByAddress",
        args=(contract_address,),
        default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
    )

    # contract_addressの有効性チェック
    if token[1] is None or token[1] not in available_token_template():
        raise InvalidParameterError(description="contract_address is invalid token address")

    owner_address = token[2]

    # 新規レコードの登録
    is_public = data.is_public
    max_holding_quantity = data.max_holding_quantity
    max_sell_amount = data.max_sell_amount

    listing = Listing()
    listing.token_address = contract_address
    listing.is_public = is_public
    listing.max_holding_quantity = max_holding_quantity
    listing.max_sell_amount = max_sell_amount
    listing.owner_address = owner_address
    session.add(listing)

    executable_contract = ExecutableContract()
    executable_contract.contract_address = contract_address
    session.add(executable_contract)

    token_type = token[1]
    # Fetch token detail data to store cache
    if token_type == "IbetCoupon":
        token_obj = CouponToken.get(session, contract_address)
        session.merge(token_obj.to_model())
    elif token_type == "IbetMembership":
        token_obj = MembershipToken.get(session, contract_address)
        session.merge(token_obj.to_model())
    elif token_type == "IbetStraightBond":
        token_obj = BondToken.get(session, contract_address)
        session.merge(token_obj.to_model())
    elif token_type == "IbetShare":
        token_obj = ShareToken.get(session, contract_address)
        session.merge(token_obj.to_model())

    balance, pending_transfer, exchange_balance, exchange_commitment = (
        get_account_balance_all(
            token_template=token_type,
            token_address=contract_address,
            account_address=owner_address
        )
    )
    position = IDXPosition()
    position.token_address = contract_address
    position.account_address = owner_address
    position.balance = balance or 0
    position.pending_transfer = pending_transfer or 0
    position.exchange_balance = exchange_balance or 0
    position.exchange_commitment = exchange_commitment or 0
    session.merge(position)
    session.commit()

    return SuccessResponse.use()


# ------------------------------
# [管理]取扱トークン種別
# ------------------------------

@router.get(
    "/Tokens/Type",
    summary="Available status by token type",
    operation_id="TokenType",
    response_model=GenericSuccessResponse[GetAdminTokenTypeResponse],
    response_model_exclude_unset=True
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
        "IbetCoupon": config.COUPON_TOKEN_ENABLED
    }
    return {
        **SuccessResponse.use().dict(),
        "data": res_body
    }


# ------------------------------
# [管理]取扱トークン情報取得/更新
# ------------------------------

@router.get(
    "/Tokens/{token_address}",
    summary="Retrieve a Listed Token",
    operation_id="TokenGET",
    response_model=GenericSuccessResponse[RetrieveAdminTokenResponse],
    response_model_exclude_unset=True,
    responses=get_routers_responses(DataNotExistsError)
)
def retrieve_admin_token(
    token_address: str = Path(description="Token Address"),
    session: Session = Depends(db_session)
):
    """
    Endpoint: /Admin/Tokens/{token_address}
      - GET: 取扱トークン情報取得（個別）
    """
    token = session.query(Listing).\
        filter(Listing.token_address == token_address).\
        first()

    if token is not None:
        return {
            **SuccessResponse.use().dict(),
            "data": token.json()
        }
    else:
        raise DataNotExistsError()


@router.post(
    "/Tokens/{token_address}",
    summary="Update a Listed Token",
    operation_id="TokenPOST",
    response_model=SuccessResponse,
    responses=get_routers_responses(InvalidParameterError, DataNotExistsError)
)
def update_token(
    data: UpdateAdminTokenRequest,
    token_address: str = Path(description="Token Address"),
    session: Session = Depends(db_session)
):
    """
    Endpoint: /Admin/Tokens/{contract_address}
      - POST: 取扱トークン情報更新（個別）
    """
    # 更新対象レコードを取得
    # 更新対象のレコードが存在しない場合は404エラーを返す
    token = session.query(Listing).filter(Listing.token_address == token_address).first()
    if token is None:
        raise DataNotExistsError()

    # レコードの更新
    is_public = data.is_public if data.is_public is not None else token.is_public
    max_holding_quantity = data.max_holding_quantity if data.max_holding_quantity is not None else token.max_holding_quantity
    max_sell_amount = data.max_sell_amount if data.max_sell_amount is not None else token.max_sell_amount
    owner_address = data.owner_address if data.owner_address is not None else token.owner_address

    token.is_public = is_public
    token.max_holding_quantity = max_holding_quantity
    token.max_sell_amount = max_sell_amount
    token.owner_address = owner_address
    session.merge(token)
    session.commit()
    return SuccessResponse.use()


@router.delete(
    "/Tokens/{token_address}",
    summary="Delete a Listed Token",
    operation_id="TokenDELETE",
    response_model=SuccessResponse,
    responses=get_routers_responses(AppError)
)
def delete_token(
    token_address: str = Path(description="Token Address"),
    session: Session = Depends(db_session)
):
    """
    Endpoint: /Admin/Tokens/{contract_address}
      - DELETE: 取扱トークン情報削除（個別）
    """
    try:
        session.query(Listing).filter(Listing.token_address == token_address).delete()
        session.query(ExecutableContract).filter(ExecutableContract.contract_address == token_address).delete()
        session.query(IDXBondToken).filter(IDXBondToken.token_address == token_address).delete()
        session.query(IDXShareToken).filter(IDXShareToken.token_address == token_address).delete()
        session.query(IDXMembershipToken).filter(IDXMembershipToken.token_address == token_address).delete()
        session.query(IDXCouponToken).filter(IDXCouponToken.token_address == token_address).delete()
    except Exception as err:
        LOG.exception(f"Failed to delete the data: {err}")
        raise AppError()
    return SuccessResponse.use()


def available_token_template():
    """
    利用可能なtoken_templateをlistで返却

    :return: 利用可能なtoken_templateリスト
    """
    available_token_template_list = []
    if config.BOND_TOKEN_ENABLED:
        available_token_template_list.append("IbetStraightBond")
    if config.SHARE_TOKEN_ENABLED:
        available_token_template_list.append("IbetShare")
    if config.MEMBERSHIP_TOKEN_ENABLED:
        available_token_template_list.append("IbetMembership")
    if config.COUPON_TOKEN_ENABLED:
        available_token_template_list.append("IbetCoupon")
    return available_token_template_list


def get_account_balance_all(token_template: str, token_address: str, account_address: str) -> tuple[int, int, int, int]:
    """Get balance"""
    token_contract = Contract.get_contract(
        contract_name=token_template,
        address=token_address
    )
    balance = Contract.call_function(
        contract=token_contract,
        function_name="balanceOf",
        args=(account_address,),
        default_returns=0
    )
    pending_transfer = 0
    if token_template in ["IbetStraightBond", "IbetShare"]:
        # if security token, amount of pending transfer is needed
        pending_transfer = Contract.call_function(
            contract=token_contract,
            function_name="pendingTransfer",
            args=(account_address,),
            default_returns=0
        )
    exchange_balance = 0
    exchange_commitment = 0
    tradable_exchange_address = Contract.call_function(
        contract=token_contract,
        function_name="tradableExchange",
        args=(),
        default_returns=config.ZERO_ADDRESS
    )
    if tradable_exchange_address != config.ZERO_ADDRESS:
        exchange_contract = Contract.get_contract(
            "IbetExchangeInterface", tradable_exchange_address)
        exchange_balance = Contract.call_function(
            contract=exchange_contract,
            function_name="balanceOf",
            args=(account_address, token_contract.address,),
            default_returns=0
        )
        exchange_commitment = Contract.call_function(
            contract=exchange_contract,
            function_name="commitmentOf",
            args=(account_address, token_contract.address,),
            default_returns=0
        )
    return balance, pending_transfer, exchange_balance, exchange_commitment