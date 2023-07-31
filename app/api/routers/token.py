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
from typing import Optional, Sequence
from uuid import UUID

from eth_utils import to_checksum_address
from fastapi import APIRouter, Depends, Path
from sqlalchemy import String, and_, asc, cast, desc, func, or_, select
from web3 import Web3

from app import config, log
from app.contracts import Contract
from app.database import DBSession
from app.errors import DataNotExistsError, InvalidParameterError, ServiceUnavailable
from app.model.db import (
    IDXLockedPosition,
    IDXPosition,
    IDXTransfer,
    IDXTransferApproval,
    Listing,
    TokenHolder,
    TokenHolderBatchStatus,
    TokenHoldersList,
)
from app.model.schema import (  # Request; Response
    CreateTokenHoldersCollectionRequest,
    CreateTokenHoldersCollectionResponse,
    GenericSuccessResponse,
    ListAllTokenHoldersQuery,
    ListAllTransferHistoryQuery,
    ResultSetQuery,
    RetrieveTokenHoldersCountQuery,
    SuccessResponse,
    TokenHoldersCollectionResponse,
    TokenHoldersCountResponse,
    TokenHoldersResponse,
    TokenStatusResponse,
    TransferApprovalHistoriesResponse,
    TransferHistoriesResponse,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response
from app.utils.web3_utils import Web3Wrapper

LOG = log.get_logger()


router = APIRouter(prefix="/Token", tags=["token_info"])


@router.get(
    "/{token_address}/Status",
    summary="Token Status",
    operation_id="TokenStatus",
    response_model=GenericSuccessResponse[TokenStatusResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError),
)
def get_token_status(
    session: DBSession,
    token_address: str = Path(description="token address"),
):
    """
    Endpoint: /Token/{contract_address}/Status
    """

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
    listed_token = session.scalars(
        select(Listing).where(Listing.token_address == contract_address).limit(1)
    ).first()
    if listed_token is None:
        raise DataNotExistsError("contract_address: %s" % contract_address)

    # TokenList-Contractへの接続
    list_contract = Contract.get_contract(
        "TokenList", str(config.TOKEN_LIST_CONTRACT_ADDRESS)
    )

    # TokenList-Contractからトークンの情報を取得する
    token_address = to_checksum_address(contract_address)
    token = Contract.call_function(
        contract=list_contract,
        function_name="getTokenByAddress",
        args=(token_address,),
        default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS),
    )

    token_template = token[1]
    try:
        # Token-Contractへの接続
        token_contract = Contract.get_contract(token_template, token_address)
        status = Contract.call_function(
            contract=token_contract, function_name="status", args=()
        )
        transferable = Contract.call_function(
            contract=token_contract, function_name="transferable", args=()
        )
    except ServiceUnavailable as e:
        LOG.warning(e)
        raise DataNotExistsError("contract_address: %s" % contract_address)
    except Exception as e:
        LOG.error(e)
        raise DataNotExistsError("contract_address: %s" % contract_address)

    response_json = {
        "token_template": token_template,
        "status": status,
        "transferable": transferable,
    }
    return json_response({**SuccessResponse.default(), "data": response_json})


@router.get(
    "/{token_address}/Holders",
    summary="Token holders",
    operation_id="TokenHolders",
    response_model=GenericSuccessResponse[TokenHoldersResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError),
)
def get_token_holders(
    session: DBSession,
    token_address: str = Path(description="token address"),
    request_query: ListAllTokenHoldersQuery = Depends(),
):
    """
    Endpoint: /Token/{contract_address}/Holders
    """
    try:
        contract_address = to_checksum_address(token_address)
        if not Web3.is_address(contract_address):
            description = "invalid contract_address"
            raise InvalidParameterError(description=description)
    except:
        description = "invalid contract_address"
        raise InvalidParameterError(description=description)

    # Check if the token exists in the list
    listed_token = session.scalars(
        select(Listing).where(Listing.token_address == contract_address).limit(1)
    ).first()
    if listed_token is None:
        raise DataNotExistsError("contract_address: %s" % contract_address)

    # Get token holders
    # add order_by id to bridge the difference between postgres and mysql
    stmt = (
        select(IDXPosition, func.sum(IDXLockedPosition.value))
        .outerjoin(
            IDXLockedPosition,
            and_(
                IDXLockedPosition.token_address == token_address,
                IDXLockedPosition.account_address == IDXPosition.account_address,
            ),
        )
        .where(IDXPosition.token_address == token_address)
        .where(
            or_(
                IDXPosition.balance > 0,
                IDXPosition.pending_transfer > 0,
                IDXPosition.exchange_balance > 0,
                IDXPosition.exchange_commitment > 0,
                IDXLockedPosition.value > 0,
            )
        )
        .group_by(
            IDXPosition.token_address,
            IDXPosition.account_address,
            IDXLockedPosition.account_address,
        )
    )
    if request_query.exclude_owner is True:
        stmt = stmt.where(IDXPosition.account_address != listed_token.owner_address)

    holders: Sequence[tuple[IDXPosition, int | None]] = session.execute(
        stmt.order_by(desc(IDXPosition.created))
    ).all()

    resp_body = []
    for holder in holders:
        resp_body.append(
            {
                "token_address": holder[0].token_address,
                "account_address": holder[0].account_address,
                "amount": holder[0].balance,
                "pending_transfer": holder[0].pending_transfer,
                "exchange_balance": holder[0].exchange_balance,
                "exchange_commitment": holder[0].exchange_commitment,
                "locked": holder[1] if holder[1] else 0,
            }
        )

    return json_response({**SuccessResponse.default(), "data": resp_body})


@router.get(
    "/{token_address}/Holders/Count",
    summary="Token holders count",
    operation_id="TokenHoldersCount",
    response_model=GenericSuccessResponse[TokenHoldersCountResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError),
)
def get_token_holders_count(
    session: DBSession,
    token_address: str = Path(description="token address"),
    request_query: RetrieveTokenHoldersCountQuery = Depends(),
):
    """
    Endpoint: /Token/{contract_address}/Holders/Count
    """
    # Validation
    try:
        contract_address = to_checksum_address(token_address)
        if not Web3.is_address(contract_address):
            description = "invalid contract_address"
            raise InvalidParameterError(description=description)
    except:
        description = "invalid contract_address"
        raise InvalidParameterError(description=description)

    # Check if the token exists in the list
    listed_token = session.scalars(
        select(Listing).where(Listing.token_address == contract_address).limit(1)
    ).first()
    if listed_token is None:
        raise DataNotExistsError("contract_address: %s" % contract_address)

    # Get token holders
    # add order_by id to bridge the difference between postgres and mysql
    stmt = (
        select(IDXPosition, func.sum(IDXLockedPosition.value))
        .outerjoin(
            IDXLockedPosition,
            and_(
                IDXLockedPosition.token_address == token_address,
                IDXLockedPosition.account_address == IDXPosition.account_address,
            ),
        )
        .where(IDXPosition.token_address == token_address)
        .where(
            or_(
                IDXPosition.balance > 0,
                IDXPosition.pending_transfer > 0,
                IDXPosition.exchange_balance > 0,
                IDXPosition.exchange_commitment > 0,
                IDXLockedPosition.value > 0,
            )
        )
        .group_by(
            IDXPosition.token_address,
            IDXPosition.account_address,
            IDXLockedPosition.account_address,
        )
    )
    if request_query.exclude_owner is True:
        stmt = stmt.where(IDXPosition.account_address != listed_token.owner_address)

    _count = session.scalar(select(func.count()).select_from(stmt.subquery()))

    resp_body = {"count": _count}

    return json_response({**SuccessResponse.default(), "data": resp_body})


@router.post(
    "/{token_address}/Holders/Collection",
    summary="Execute Batch Getting Token Holders At Specific BlockNumber",
    operation_id="TokenHoldersCollection",
    response_model=GenericSuccessResponse[CreateTokenHoldersCollectionResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError),
)
def create_token_holders_collection(
    session: DBSession,
    data: CreateTokenHoldersCollectionRequest,
    token_address: str = Path(description="token address"),
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
        if not Web3.is_address(contract_address):
            raise InvalidParameterError("Invalid contract address")
    except Exception as err:
        LOG.debug(f"invalid contract address: {err}")
        raise InvalidParameterError("Invalid contract address")

    # ブロックナンバーのチェック
    if block_number > web3.eth.block_number or block_number < 1:
        raise InvalidParameterError("Block number must be current or past one.")

    # 取扱トークンチェック
    # NOTE:非公開トークンも取扱対象とする
    listed_token = session.scalars(
        select(Listing).where(Listing.token_address == contract_address).limit(1)
    ).first()
    if listed_token is None:
        raise DataNotExistsError("contract_address: %s" % contract_address)

    # list_idの衝突チェック
    _same_list_id_record = session.scalars(
        select(TokenHoldersList).where(TokenHoldersList.list_id == list_id).limit(1)
    ).first()
    if _same_list_id_record is not None:
        raise InvalidParameterError("list_id must be unique.")

    _same_combi_record = session.scalars(
        select(TokenHoldersList)
        .where(TokenHoldersList.token_address == contract_address)
        .where(TokenHoldersList.block_number == block_number)
        .where(TokenHoldersList.batch_status != TokenHolderBatchStatus.FAILED)
        .limit(1)
    ).first()

    if _same_combi_record is not None:
        # 同じブロックナンバー・トークンアドレスのコレクションが、PENDINGかDONEで既に存在する場合、
        # そのlist_idとstatusを返却する。
        return json_response(
            {
                **SuccessResponse.default(),
                "data": {
                    "list_id": _same_combi_record.list_id,
                    "status": _same_combi_record.batch_status,
                },
            }
        )
    else:
        token_holder_list = TokenHoldersList(
            list_id=list_id,
            batch_status=TokenHolderBatchStatus.PENDING.value,
            block_number=block_number,
            token_address=contract_address,
        )
        session.add(token_holder_list)
        session.commit()

        return json_response(
            {
                **SuccessResponse.default(),
                "data": {
                    "list_id": token_holder_list.list_id,
                    "status": token_holder_list.batch_status,
                },
            }
        )


@router.get(
    "/{token_address}/Holders/Collection/{list_id}",
    summary="Token Holder At Specific BlockNumber",
    operation_id="TokenHoldersList",
    response_model=GenericSuccessResponse[TokenHoldersCollectionResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError),
)
def get_token_holders_collection(
    session: DBSession,
    token_address: str = Path(description="token address"),
    list_id: UUID = Path(
        description="Unique id to be assigned to each token holder list."
        "This must be Version4 UUID.",
        example="cfd83622-34dc-4efe-a68b-2cc275d3d824",
    ),
):
    """
    Endpoint: /Token/{contract_address}/Holders/Collection/{list_id}
    """
    contract_address = token_address

    # 入力アドレスフォーマットチェック
    try:
        contract_address = to_checksum_address(contract_address)
        if not Web3.is_address(contract_address):
            description = "invalid contract_address"
            raise InvalidParameterError(description=description)
    except:
        description = "invalid contract_address"
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
    listed_token = session.scalars(
        select(Listing).where(Listing.token_address == contract_address).limit(1)
    ).first()
    if listed_token is None:
        raise DataNotExistsError("contract_address: %s" % contract_address)

    # 既存レコードの存在チェック
    _same_list_id_record: Optional[TokenHoldersList] = session.scalars(
        select(TokenHoldersList)
        .where(TokenHoldersList.list_id == str(list_id))
        .limit(1)
    ).first()

    if not _same_list_id_record:
        raise DataNotExistsError("list_id: %s" % str(list_id))
    if _same_list_id_record.token_address != contract_address:
        description = "list_id: %s is not collection for contract_address: %s" % (
            str(list_id),
            contract_address,
        )
        raise InvalidParameterError(description=description)

    _token_holders: Sequence[TokenHolder] = session.scalars(
        select(TokenHolder)
        .where(TokenHolder.holder_list == _same_list_id_record.id)
        .order_by(asc(TokenHolder.account_address))
    ).all()
    token_holders = [_token_holder.json() for _token_holder in _token_holders]

    return json_response(
        {
            **SuccessResponse.default(),
            "data": {
                "status": _same_list_id_record.batch_status,
                "holders": token_holders,
            },
        }
    )


@router.get(
    "/{token_address}/TransferHistory",
    summary="Token Transfer History",
    operation_id="TransferHistory",
    response_model=GenericSuccessResponse[TransferHistoriesResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError),
)
def list_all_transfer_histories(
    session: DBSession,
    request_query: ListAllTransferHistoryQuery = Depends(),
    token_address: str = Path(description="token address"),
):
    """
    Endpoint: /Token/{contract_address}/TransferHistory
    """
    # 入力値チェック
    try:
        contract_address = to_checksum_address(token_address)
        if not Web3.is_address(contract_address):
            description = "invalid contract_address"
            raise InvalidParameterError(description=description)
    except:
        description = "invalid contract_address"
        raise InvalidParameterError(description=description)

    # 取扱トークンチェック
    listed_token = session.scalars(
        select(Listing).where(Listing.token_address == contract_address).limit(1)
    ).first()
    if listed_token is None:
        raise DataNotExistsError("contract_address: %s" % contract_address)

    # 移転履歴取得
    stmt = (
        select(IDXTransfer)
        .where(IDXTransfer.token_address == contract_address)
        .order_by(IDXTransfer.id)
    )
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))

    if request_query.source_event is not None:
        stmt = stmt.where(IDXTransfer.source_event == request_query.source_event.value)
    if request_query.data is not None:
        stmt = stmt.where(
            cast(IDXTransfer.data, String).like("%" + request_query.data + "%")
        )

    count = session.scalar(select(func.count()).select_from(stmt.subquery()))

    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    transfer_history: Sequence[IDXTransfer] = session.scalars(stmt).all()

    resp_data = []
    for transfer_event in transfer_history:
        resp_data.append(transfer_event.json())

    data = {
        "result_set": {
            "count": count,
            "offset": request_query.offset,
            "limit": request_query.limit,
            "total": total,
        },
        "transfer_history": resp_data,
    }

    return json_response({**SuccessResponse.default(), "data": data})


@router.get(
    "/{token_address}/TransferApprovalHistory",
    summary="Token Transfer Approval History",
    operation_id="TransferApprovalHistory",
    response_model=GenericSuccessResponse[TransferApprovalHistoriesResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError),
)
def list_all_transfer_approval_histories(
    session: DBSession,
    request_query: ResultSetQuery = Depends(),
    token_address: str = Path(description="token address"),
):
    """
    Endpoint: /Token/{contract_address}/TransferApprovalHistory
    """
    # Validation
    try:
        contract_address = to_checksum_address(token_address)
        if not Web3.is_address(contract_address):
            raise InvalidParameterError("invalid contract_address")
    except:
        raise InvalidParameterError("invalid contract_address")

    # Check that it is a listed token
    _listed_token = session.scalars(
        select(Listing).where(Listing.token_address == contract_address).limit(1)
    ).first()
    if _listed_token is None:
        raise DataNotExistsError(f"contract_address: {contract_address}")

    # Get transfer approval data
    stmt = (
        select(IDXTransferApproval)
        .where(IDXTransferApproval.token_address == contract_address)
        .order_by(
            IDXTransferApproval.exchange_address, IDXTransferApproval.application_id
        )
    )
    list_length = session.scalar(select(func.count()).select_from(stmt.subquery()))

    # パラメータを設定
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    transfer_approval_history: Sequence[IDXTransferApproval] = session.scalars(
        stmt
    ).all()

    resp_data = []
    for transfer_approval_event in transfer_approval_history:
        resp_data.append(transfer_approval_event.json())
    data = {
        "result_set": {
            "count": list_length,
            "offset": request_query.offset,
            "limit": request_query.limit,
            "total": list_length,
        },
        "transfer_approval_history": resp_data,
    }

    return json_response({**SuccessResponse.default(), "data": data})
