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
from uuid import UUID
from typing import List
from fastapi import (
    APIRouter,
    Depends,
    Path
)
from sqlalchemy import (
    or_,
    desc,
    asc
)
from web3 import Web3
from eth_utils import to_checksum_address
from sqlalchemy.orm import Session

from app import log
from app.database import db_session
from app.errors import (
    InvalidParameterError,
    DataNotExistsError
)
from app import config
from app.contracts import Contract
from app.model.schema import (
    CreateTokenHoldersCollectionRequest,
    RetrieveTokenHoldersCountQuery,
    ResultSetQuery,
    GenericSuccessResponse,
    TokenStatusResponse,
    SuccessResponse,
    TokenHoldersResponse,
    TokenHoldersCountResponse,
    CreateTokenHoldersCollectionResponse,
    TokenHoldersCollectionResponse,
    TransferHistoriesResponse,
    ListAllTokenHoldersQuery,
    TransferApprovalHistoriesResponse
)
from app.utils.docs_utils import get_routers_responses
from app.utils.web3_utils import Web3Wrapper
from app.model.db import (
    Listing,
    IDXPosition,
    IDXTransfer,
    IDXTransferApproval,
    TokenHoldersList,
    TokenHolderBatchStatus,
    TokenHolder
)

LOG = log.get_logger()


router = APIRouter(
    prefix="/Token",
    tags=["Token"]
)


@router.get(
    "/{token_address}/Status",
    summary="Token Status",
    operation_id="TokenStatus",
    response_model=GenericSuccessResponse[TokenStatusResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError)
)
def get_token_status(
    token_address: str = Path(description="token address"),
    session: Session = Depends(db_session)
):
    """
    Endpoint: /Token/{contract_address}/Status
    """

    # 入力アドレスフォーマットチェック
    try:
        contract_address = to_checksum_address(token_address)
        if not Web3.isAddress(contract_address):
            description = 'invalid contract_address'
            raise InvalidParameterError(description=description)
    except:
        description = 'invalid contract_address'
        raise InvalidParameterError(description=description)

    # 取扱トークンチェック
    listed_token = session.query(Listing).filter(Listing.token_address == contract_address).first()
    if listed_token is None:
        raise DataNotExistsError('contract_address: %s' % contract_address)

    # TokenList-Contractへの接続
    list_contract = Contract.get_contract('TokenList', str(config.TOKEN_LIST_CONTRACT_ADDRESS))

    # TokenList-Contractからトークンの情報を取得する
    token_address = to_checksum_address(contract_address)
    token = Contract.call_function(
        contract=list_contract,
        function_name="getTokenByAddress",
        args=(token_address,),
        default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
    )

    token_template = token[1]
    try:
        # Token-Contractへの接続
        token_contract = Contract.get_contract(token_template, token_address)
        status = Contract.call_function(
            contract=token_contract,
            function_name="status",
            args=()
        )
        transferable = Contract.call_function(
            contract=token_contract,
            function_name="transferable",
            args=()
        )
    except Exception as e:
        LOG.error(e)
        raise DataNotExistsError('contract_address: %s' % contract_address)

    response_json = {
        'token_template': token_template,
        'status': status,
        'transferable': transferable
    }
    return {
        **SuccessResponse.use().dict(),
        "data": response_json
    }


@router.get(
    "/{token_address}/Holders",
    summary="Token holders",
    operation_id="TokenHolders",
    response_model=GenericSuccessResponse[TokenHoldersResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError)
)
def get_token_holders(
    token_address: str = Path(description="token address"),
    request_query: ListAllTokenHoldersQuery = Depends(),
    session: Session = Depends(db_session)
):
    """
    Endpoint: /Token/{contract_address}/Holders
    """
    try:
        contract_address = to_checksum_address(token_address)
        if not Web3.isAddress(contract_address):
            description = 'invalid contract_address'
            raise InvalidParameterError(description=description)
    except:
        description = 'invalid contract_address'
        raise InvalidParameterError(description=description)

    # Check if the token exists in the list
    listed_token = session.query(Listing).\
        filter(Listing.token_address == contract_address).\
        first()
    if listed_token is None:
        raise DataNotExistsError('contract_address: %s' % contract_address)

    # Get token holders
    # add order_by id to bridge the difference between postgres and mysql
    query = session.query(IDXPosition). \
        filter(IDXPosition.token_address == contract_address). \
        filter(or_(
            IDXPosition.balance > 0,
            IDXPosition.pending_transfer > 0,
            IDXPosition.exchange_balance > 0,
            IDXPosition.exchange_commitment > 0))
    if request_query.exclude_owner is True:
        query = query.filter(IDXPosition.account_address != listed_token.owner_address)

    holders: list[IDXPosition] = query.order_by(desc(IDXPosition.id)).all()

    resp_body = []
    for holder in holders:
        resp_body.append({
            "token_address": holder.token_address,
            "account_address": holder.account_address,
            "amount": holder.balance,
            "pending_transfer": holder.pending_transfer,
            "exchange_balance": holder.exchange_balance,
            "exchange_commitment": holder.exchange_commitment
        })

    return {
        **SuccessResponse.use().dict(),
        "data": resp_body
    }


@router.get(
    "/{token_address}/Holders/Count",
    summary="Token holders count",
    operation_id="TokenHoldersCount",
    response_model=GenericSuccessResponse[TokenHoldersCountResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError)
)
def get_token_holders_count(
    token_address: str = Path(description="token address"),
    request_query: RetrieveTokenHoldersCountQuery = Depends(),
    session: Session = Depends(db_session)
):
    """
    Endpoint: /Token/{contract_address}/Holders/Count
    """
    # Validation
    try:
        contract_address = to_checksum_address(token_address)
        if not Web3.isAddress(contract_address):
            description = 'invalid contract_address'
            raise InvalidParameterError(description=description)
    except:
        description = 'invalid contract_address'
        raise InvalidParameterError(description=description)

    # Check if the token exists in the list
    listed_token = session.query(Listing).\
        filter(Listing.token_address == contract_address).\
        first()
    if listed_token is None:
        raise DataNotExistsError('contract_address: %s' % contract_address)

    # Get token holders
    # add order_by id to bridge the difference between postgres and mysql
    query = session.query(IDXPosition). \
        filter(IDXPosition.token_address == contract_address). \
        filter(or_(
            IDXPosition.balance > 0,
            IDXPosition.pending_transfer > 0,
            IDXPosition.exchange_balance > 0,
            IDXPosition.exchange_commitment > 0))
    if request_query.exclude_owner is True:
        query = query.filter(IDXPosition.account_address != listed_token.owner_address)

    _count = query.order_by(desc(IDXPosition.id)).count()

    resp_body = {
        "count": _count
    }

    return {
        **SuccessResponse.use().dict(),
        "data": resp_body
    }


@router.post(
    "/{token_address}/Holders/Collection",
    summary="Execute Batch Getting Token Holders At Specific BlockNumber",
    operation_id="TokenHoldersCollection",
    response_model=GenericSuccessResponse[CreateTokenHoldersCollectionResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError)
)
def create_token_holders_collection(
    data: CreateTokenHoldersCollectionRequest,
    token_address: str = Path(description="token address"),
    session: Session = Depends(db_session)
):
    """
    Endpoint: /Token/{contract_address}/Holders/Collection
    """
    web3 = Web3Wrapper()

    list_id = str(data.list_id)
    block_number = data.block_number

    # contract_addressのフォーマットチェック
    contract_address = token_address
    try:
        if not Web3.isAddress(contract_address):
            raise InvalidParameterError("Invalid contract address")
    except Exception as err:
        LOG.debug(f"invalid contract address: {err}")
        raise InvalidParameterError("Invalid contract address")

    # ブロックナンバーのチェック
    if block_number > web3.eth.block_number or block_number < 1:
        raise InvalidParameterError("Block number must be current or past one.")

    # 取扱トークンチェック
    # NOTE:非公開トークンも取扱対象とする
    listed_token = session.query(Listing).\
        filter(Listing.token_address == contract_address).\
        first()
    if listed_token is None:
        raise DataNotExistsError('contract_address: %s' % contract_address)

    # list_idの衝突チェック
    _same_list_id_record = session.query(TokenHoldersList). \
        filter(TokenHoldersList.list_id == list_id). \
        first()
    if _same_list_id_record is not None:
        raise InvalidParameterError("list_id must be unique.")

    _same_combi_record = session.query(TokenHoldersList). \
        filter(TokenHoldersList.token_address == contract_address). \
        filter(TokenHoldersList.block_number == block_number). \
        filter(TokenHoldersList.batch_status != TokenHolderBatchStatus.FAILED.value). \
        first()

    if _same_combi_record is not None:
        # 同じブロックナンバー・トークンアドレスのコレクションが、PENDINGかDONEで既に存在する場合、
        # そのlist_idとstatusを返却する。
        return {
            **SuccessResponse.use().dict(),
            "data": {
                "list_id": _same_combi_record.list_id,
                "status": _same_combi_record.batch_status,
            }
        }
    else:
        token_holder_list = TokenHoldersList()
        token_holder_list.list_id = list_id
        token_holder_list.batch_status = TokenHolderBatchStatus.PENDING.value
        token_holder_list.block_number = block_number
        token_holder_list.token_address = contract_address
        session.add(token_holder_list)
        session.commit()

        return {
            **SuccessResponse.use().dict(),
            "data": {
                "list_id": token_holder_list.list_id,
                "status": token_holder_list.batch_status,
            }
        }


@router.get(
    "/{token_address}/Holders/Collection/{list_id}",
    summary="Token Holder At Specific BlockNumber",
    operation_id="TokenHoldersList",
    response_model=GenericSuccessResponse[TokenHoldersCollectionResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError)
)
def get_token_holders_collection(
    token_address: str = Path(description="token address"),
    list_id: UUID = Path(description="Unique id to be assigned to each token holder list."
                                          "This must be Version4 UUID.",
                              example="cfd83622-34dc-4efe-a68b-2cc275d3d824"),
    session: Session = Depends(db_session)
):
    """
    Endpoint: /Token/{contract_address}/Holders/Collection/{list_id}
    """
    """Token holders collection Id"""
    contract_address = token_address

    # 入力アドレスフォーマットチェック
    try:
        contract_address = to_checksum_address(contract_address)
        if not Web3.isAddress(contract_address):
            description = 'invalid contract_address'
            raise InvalidParameterError(description=description)
    except:
        description = 'invalid contract_address'
        raise InvalidParameterError(description=description)

    # 入力IDフォーマットチェック
    try:
        if not list_id.version == 4:
            description = "list_id must be UUIDv4."
            raise InvalidParameterError(description=description)
    except:
        description = "list_id must be UUIDv4."
        raise InvalidParameterError(description=description)

    # 取扱トークンチェック
    # NOTE:非公開トークンも取扱対象とする
    listed_token = session.query(Listing).\
        filter(Listing.token_address == contract_address).\
        first()
    if listed_token is None:
        raise DataNotExistsError('contract_address: %s' % contract_address)

    # 既存レコードの存在チェック
    _same_list_id_record: TokenHoldersList = session.query(TokenHoldersList). \
        filter(TokenHoldersList.list_id == str(list_id)). \
        first()

    if not _same_list_id_record:
        raise DataNotExistsError("list_id: %s" % str(list_id))
    if _same_list_id_record.token_address != contract_address:
        description = "list_id: %s is not collection for contract_address: %s" % (str(list_id), contract_address)
        raise InvalidParameterError(description=description)

    _token_holders: List[TokenHolder] = session.query(TokenHolder). \
        filter(TokenHolder.holder_list == _same_list_id_record.id). \
        order_by(asc(TokenHolder.account_address)).\
        all()
    token_holders = [_token_holder.json() for _token_holder in _token_holders]

    return {
        **SuccessResponse.use().dict(),
        "data": {
            "status": _same_list_id_record.batch_status,
            "holders": token_holders
        }
    }


@router.get(
    "/{token_address}/TransferHistory",
    summary="Token Transfer History",
    operation_id="TransferHistory",
    response_model=GenericSuccessResponse[TransferHistoriesResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError)
)
def list_all_transfer_histories(
    request_query: ResultSetQuery = Depends(),
    token_address: str = Path(description="token address"),
    session: Session = Depends(db_session)
):

    """
    Endpoint: /Token/{contract_address}/TransferHistory
    """
    # 入力値チェック
    try:
        contract_address = to_checksum_address(token_address)
        if not Web3.isAddress(contract_address):
            description = 'invalid contract_address'
            raise InvalidParameterError(description=description)
    except:
        description = 'invalid contract_address'
        raise InvalidParameterError(description=description)

    # 取扱トークンチェック
    listed_token = session.query(Listing). \
        filter(Listing.token_address == contract_address). \
        first()
    if listed_token is None:
        raise DataNotExistsError('contract_address: %s' % contract_address)

    # 移転履歴取得
    query = session.query(IDXTransfer). \
        filter(IDXTransfer.token_address == contract_address). \
        order_by(IDXTransfer.id)
    list_length = query.count()

    if request_query.offset is not None:
        query = query.offset(request_query.offset)
    if request_query.limit is not None:
        query = query.limit(request_query.limit)
    transfer_history = query.all()

    resp_data = []
    for transfer_event in transfer_history:
        resp_data.append(transfer_event.json())

    data = {
        "result_set": {
            "count": list_length,
            "offset": request_query.offset,
            "limit": request_query.limit,
            "total": list_length
        },
        "transfer_history": resp_data
    }

    return {
        **SuccessResponse.use().dict(),
        "data": data
    }


@router.get(
    "/{token_address}/TransferApprovalHistory",
    summary="Token Transfer Approval History",
    operation_id="TransferApprovalHistory",
    response_model=GenericSuccessResponse[TransferApprovalHistoriesResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError)
)
def list_all_transfer_approval_histories(
    request_query: ResultSetQuery = Depends(),
    token_address: str = Path(description="token address"),
    session: Session = Depends(db_session)
):
    """
    Endpoint: /Token/{contract_address}/TransferApprovalHistory
    """
    # Validation
    try:
        contract_address = to_checksum_address(token_address)
        if not Web3.isAddress(contract_address):
            raise InvalidParameterError("invalid contract_address")
    except:
        raise InvalidParameterError("invalid contract_address")

    # Check that it is a listed token
    _listed_token = session.query(Listing). \
        filter(Listing.token_address == contract_address). \
        first()
    if _listed_token is None:
        raise DataNotExistsError(f"contract_address: {contract_address}")

    # Get transfer approval data
    query = session.query(IDXTransferApproval). \
        filter(IDXTransferApproval.token_address == contract_address). \
        order_by(
            IDXTransferApproval.exchange_address,
            IDXTransferApproval.application_id
        )
    list_length = query.count()

    # パラメータを設定
    if request_query.offset is not None:
        query = query.offset(request_query.offset)
    if request_query.limit is not None:
        query = query.limit(request_query.limit)
    transfer_approval_history = query.all()

    resp_data = []
    for transfer_approval_event in transfer_approval_history:
        resp_data.append(transfer_approval_event.json())
    data = {
        "result_set": {
            "count": list_length,
            "offset": request_query.offset,
            "limit": request_query.limit,
            "total": list_length
        },
        "transfer_approval_history": resp_data
    }

    return {
        **SuccessResponse.use().dict(),
        "data": data
    }

