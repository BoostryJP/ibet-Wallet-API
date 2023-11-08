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
from datetime import timezone
from typing import Annotated, Optional, Sequence

from fastapi import APIRouter, Depends, Path
from pydantic import UUID4
from sqlalchemy import String, and_, asc, case, cast, desc, func, or_, select

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
from app.model.schema import (
    CreateTokenHoldersCollectionRequest,
    CreateTokenHoldersCollectionResponse,
    ListAllTokenHoldersQuery,
    ListAllTransferApprovalHistoryQuery,
    ListAllTransferHistoryQuery,
    RetrieveTokenHoldersCountQuery,
    SearchTokenHoldersRequest,
    SearchTransferApprovalHistoryRequest,
    SearchTransferHistoryRequest,
    TokenHoldersCollectionResponse,
    TokenHoldersCountResponse,
    TokenHoldersResponse,
    TokenStatusResponse,
    TransferApprovalHistoriesResponse,
    TransferHistoriesResponse,
)
from app.model.schema.base import (
    GenericSuccessResponse,
    SuccessResponse,
    ValidatedEthereumAddress,
    ValueOperator,
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
    token_address: Annotated[
        ValidatedEthereumAddress, Path(description="Token address")
    ],
):
    """
    Returns status of given token.
    """
    # 取扱トークンチェック
    listed_token = session.scalars(
        select(Listing).where(Listing.token_address == token_address).limit(1)
    ).first()
    if listed_token is None:
        raise DataNotExistsError("token_address: %s" % token_address)

    # TokenList-Contractへの接続
    list_contract = Contract.get_contract(
        "TokenList", str(config.TOKEN_LIST_CONTRACT_ADDRESS)
    )

    # TokenList-Contractからトークンの情報を取得する
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
        raise DataNotExistsError("token_address: %s" % token_address)
    except Exception as e:
        LOG.error(e)
        raise DataNotExistsError("token_address: %s" % token_address)

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
    token_address: Annotated[
        ValidatedEthereumAddress, Path(description="Token address")
    ],
    request_query: ListAllTokenHoldersQuery = Depends(),
):
    """
    Returns a list of token holders for a given token.
    """
    # Check if the token exists in the list
    listed_token = session.scalars(
        select(Listing).where(Listing.token_address == token_address).limit(1)
    ).first()
    if listed_token is None:
        raise DataNotExistsError("token_address: %s" % token_address)

    limit = request_query.limit
    offset = request_query.offset
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
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))

    if request_query.exclude_owner is True:
        stmt = stmt.where(IDXPosition.account_address != listed_token.owner_address)
    count = session.scalar(select(func.count()).select_from(stmt.subquery()))

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    holders: Sequence[tuple[IDXPosition, int | None]] = session.execute(
        stmt.order_by(desc(IDXPosition.created))
    ).all()

    resp_body = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "token_holder_list": [
            {
                "token_address": holder[0].token_address,
                "account_address": holder[0].account_address,
                "amount": holder[0].balance if holder[0].balance else 0,
                "pending_transfer": holder[0].pending_transfer
                if holder[0].pending_transfer
                else 0,
                "exchange_balance": holder[0].exchange_balance
                if holder[0].exchange_balance
                else 0,
                "exchange_commitment": holder[0].exchange_commitment
                if holder[0].exchange_commitment
                else 0,
                "locked": holder[1] if holder[1] else 0,
            }
            for holder in holders
        ],
    }

    return json_response({**SuccessResponse.default(), "data": resp_body})


@router.post(
    "/{token_address}/Holders/Search",
    summary="Search Token holders",
    operation_id="SearchTokenHolders",
    response_model=GenericSuccessResponse[TokenHoldersResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError),
)
def search_token_holders(
    session: DBSession,
    data: SearchTokenHoldersRequest,
    token_address: Annotated[
        ValidatedEthereumAddress, Path(description="Token address")
    ],
):
    """
    Returns a list of token holders for a given token using detailed search query.
    """
    # Check if the token exists in the list
    listed_token = session.scalars(
        select(Listing).where(Listing.token_address == token_address).limit(1)
    ).first()
    if listed_token is None:
        raise DataNotExistsError("token_address: %s" % token_address)

    limit = data.limit
    offset = data.offset
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
    if len(data.account_address_list) > 0:
        stmt = stmt.where(
            or_(
                IDXPosition.account_address.in_(data.account_address_list),
                IDXLockedPosition.account_address.in_(data.account_address_list),
            )
        )
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))

    if data.exclude_owner is True:
        stmt = stmt.where(IDXPosition.account_address != listed_token.owner_address)

    count = session.scalar(select(func.count()).select_from(stmt.subquery()))

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    holders: Sequence[tuple[IDXPosition, int | None]] = session.execute(
        stmt.order_by(desc(IDXPosition.created))
    ).all()

    resp_body = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "token_holder_list": [
            {
                "token_address": holder[0].token_address,
                "account_address": holder[0].account_address,
                "amount": holder[0].balance if holder[0].balance else 0,
                "pending_transfer": holder[0].pending_transfer
                if holder[0].pending_transfer
                else 0,
                "exchange_balance": holder[0].exchange_balance
                if holder[0].exchange_balance
                else 0,
                "exchange_commitment": holder[0].exchange_commitment
                if holder[0].exchange_commitment
                else 0,
                "locked": holder[1] if holder[1] else 0,
            }
            for holder in holders
        ],
    }

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
    token_address: Annotated[
        ValidatedEthereumAddress, Path(description="Token address")
    ],
    request_query: RetrieveTokenHoldersCountQuery = Depends(),
):
    """
    Returns count of token holders for a given token.
    """
    # Check if the token exists in the list
    listed_token = session.scalars(
        select(Listing).where(Listing.token_address == token_address).limit(1)
    ).first()
    if listed_token is None:
        raise DataNotExistsError("token_address: %s" % token_address)

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
    token_address: Annotated[
        ValidatedEthereumAddress, Path(description="Token address")
    ],
):
    """
    Enqueues task of collecting token holders for a given block number.
    """
    web3 = Web3Wrapper()

    list_id = str(data.list_id)
    block_number = data.block_number

    # ブロックナンバーのチェック
    if block_number > web3.eth.block_number or block_number < 1:
        raise InvalidParameterError("Block number must be current or past one.")

    # 取扱トークンチェック
    # NOTE:非公開トークンも取扱対象とする
    listed_token = session.scalars(
        select(Listing).where(Listing.token_address == token_address).limit(1)
    ).first()
    if listed_token is None:
        raise DataNotExistsError("token_address: %s" % token_address)

    # list_idの衝突チェック
    _same_list_id_record = session.scalars(
        select(TokenHoldersList).where(TokenHoldersList.list_id == list_id).limit(1)
    ).first()
    if _same_list_id_record is not None:
        raise InvalidParameterError("list_id must be unique.")

    _same_combi_record = session.scalars(
        select(TokenHoldersList)
        .where(TokenHoldersList.token_address == token_address)
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
            token_address=token_address,
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
    token_address: Annotated[
        ValidatedEthereumAddress, Path(description="Token address")
    ],
    list_id: UUID4 = Path(
        description="Unique id to be assigned to each token holder list."
        "This must be Version4 UUID.",
        examples=["cfd83622-34dc-4efe-a68b-2cc275d3d824"],
    ),
):
    """
    Returns a list of token holders at specific block number.
    """
    # 取扱トークンチェック
    # NOTE:非公開トークンも取扱対象とする
    listed_token = session.scalars(
        select(Listing).where(Listing.token_address == token_address).limit(1)
    ).first()
    if listed_token is None:
        raise DataNotExistsError("token_address: %s" % token_address)

    # 既存レコードの存在チェック
    _same_list_id_record: Optional[TokenHoldersList] = session.scalars(
        select(TokenHoldersList)
        .where(TokenHoldersList.list_id == str(list_id))
        .limit(1)
    ).first()

    if not _same_list_id_record:
        raise DataNotExistsError("list_id: %s" % str(list_id))
    if _same_list_id_record.token_address != token_address:
        description = "list_id: %s is not collection for token_address: %s" % (
            str(list_id),
            token_address,
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
    token_address: Annotated[
        ValidatedEthereumAddress, Path(description="Token address")
    ],
    request_query: ListAllTransferHistoryQuery = Depends(),
):
    """
    Returns a list of transfer histories for a given token.
    """
    # 取扱トークンチェック
    listed_token = session.scalars(
        select(Listing).where(Listing.token_address == token_address).limit(1)
    ).first()
    if listed_token is None:
        raise DataNotExistsError("token_address: %s" % token_address)

    # 移転履歴取得
    stmt = (
        select(IDXTransfer)
        .where(IDXTransfer.token_address == token_address)
        .order_by(IDXTransfer.id)
    )
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))

    if request_query.source_event is not None:
        stmt = stmt.where(IDXTransfer.source_event == request_query.source_event.value)
    if request_query.data is not None:
        stmt = stmt.where(
            cast(IDXTransfer.data, String).like("%" + request_query.data + "%")
        )
    if request_query.transaction_hash is not None:
        stmt = stmt.where(
            IDXTransfer.transaction_hash.like(
                "%" + request_query.transaction_hash + "%"
            )
        )
    if request_query.from_address is not None:
        stmt = stmt.where(
            IDXTransfer.from_address.like("%" + request_query.from_address + "%")
        )
    if request_query.to_address is not None:
        stmt = stmt.where(
            IDXTransfer.to_address.like("%" + request_query.to_address + "%")
        )
    if request_query.value is not None and request_query.value_operator is not None:
        match request_query.value_operator:
            case ValueOperator.EQUAL:
                stmt = stmt.where(IDXTransfer.value == request_query.value)
            case ValueOperator.GTE:
                stmt = stmt.where(IDXTransfer.value >= request_query.value)
            case ValueOperator.LTE:
                stmt = stmt.where(IDXTransfer.value <= request_query.value)

    count = session.scalar(select(func.count()).select_from(stmt.subquery()))

    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    transfer_history: Sequence[IDXTransfer] = session.scalars(stmt).all()

    resp_data = [transfer_event.json() for transfer_event in transfer_history]
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


@router.post(
    "/{token_address}/TransferHistory/Search",
    summary="Search Token Transfer History",
    operation_id="SearchTransferHistory",
    response_model=GenericSuccessResponse[TransferHistoriesResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError),
)
def search_transfer_histories(
    session: DBSession,
    data: SearchTransferHistoryRequest,
    token_address: Annotated[
        ValidatedEthereumAddress, Path(description="Token address")
    ],
):
    """
    Returns a list of transfer histories for a given token using detailed search query.
    """
    # 取扱トークンチェック
    listed_token = session.scalars(
        select(Listing).where(Listing.token_address == token_address).limit(1)
    ).first()
    if listed_token is None:
        raise DataNotExistsError("token_address: %s" % token_address)

    # 移転履歴取得
    stmt = select(IDXTransfer).where(IDXTransfer.token_address == token_address)
    if len(data.account_address_list) > 0:
        stmt = stmt.where(
            or_(
                IDXTransfer.from_address.in_(data.account_address_list),
                IDXTransfer.to_address.in_(data.account_address_list),
            )
        )
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))

    if data.source_event is not None:
        stmt = stmt.where(IDXTransfer.source_event == data.source_event.value)
    if data.data is not None:
        stmt = stmt.where(cast(IDXTransfer.data, String).like("%" + data.data + "%"))
    if data.transaction_hash is not None:
        stmt = stmt.where(
            IDXTransfer.transaction_hash.like("%" + data.transaction_hash + "%")
        )
    if data.from_address is not None:
        stmt = stmt.where(IDXTransfer.from_address.like("%" + data.from_address + "%"))
    if data.to_address is not None:
        stmt = stmt.where(IDXTransfer.to_address.like("%" + data.to_address + "%"))
    if data.created_from is not None:
        stmt = stmt.where(
            IDXTransfer.created >= data.created_from.astimezone(timezone.utc)
        )
    if data.created_to is not None:
        stmt = stmt.where(
            IDXTransfer.created <= data.created_to.astimezone(timezone.utc)
        )
    if data.value is not None and data.value_operator is not None:
        match data.value_operator:
            case ValueOperator.EQUAL:
                stmt = stmt.where(IDXTransfer.value == data.value)
            case ValueOperator.GTE:
                stmt = stmt.where(IDXTransfer.value >= data.value)
            case ValueOperator.LTE:
                stmt = stmt.where(IDXTransfer.value <= data.value)

    count = session.scalar(select(func.count()).select_from(stmt.subquery()))

    def _order(_order):
        if _order == 0:
            return asc
        else:
            return desc

    if (
        data.sort_item == "from_account_address_list"
        and len(data.account_address_list) > 0
    ):
        stmt = stmt.order_by(
            _order(data.sort_order)(
                case(
                    {
                        account_address: i
                        for i, account_address in enumerate(data.account_address_list)
                    },
                    value=IDXTransfer.from_address,
                )
            )
        )
    elif (
        data.sort_item == "to_account_address_list"
        and len(data.account_address_list) > 0
    ):
        stmt = stmt.order_by(
            _order(data.sort_order)(
                case(
                    {
                        account_address: i
                        for i, account_address in enumerate(data.account_address_list)
                    },
                    value=IDXTransfer.to_address,
                )
            )
        )
    else:
        sort_attr = getattr(IDXTransfer, data.sort_item, None)
        stmt = stmt.order_by(_order(data.sort_order)(sort_attr))

    # NOTE: Set secondary sort for consistent results
    if data.sort_item != "id":
        stmt = stmt.order_by(IDXTransfer.id)

    if data.offset is not None:
        stmt = stmt.offset(data.offset)
    if data.limit is not None:
        stmt = stmt.limit(data.limit)
    transfer_history: Sequence[IDXTransfer] = session.scalars(stmt).all()

    resp_data = [transfer_event.json() for transfer_event in transfer_history]
    data = {
        "result_set": {
            "count": count,
            "offset": data.offset,
            "limit": data.limit,
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
    token_address: Annotated[
        ValidatedEthereumAddress, Path(description="Token address")
    ],
    request_query: ListAllTransferApprovalHistoryQuery = Depends(),
):
    """
    Returns a list of transfer approval histories for a given token.
    """
    # Check that it is a listed token
    _listed_token = session.scalars(
        select(Listing).where(Listing.token_address == token_address).limit(1)
    ).first()
    if _listed_token is None:
        raise DataNotExistsError(f"token_address: {token_address}")

    # Get transfer approval data
    stmt = (
        select(IDXTransferApproval)
        .where(IDXTransferApproval.token_address == token_address)
        .order_by(
            IDXTransferApproval.exchange_address, IDXTransferApproval.application_id
        )
    )
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))

    if request_query.from_address is not None:
        stmt = stmt.where(
            IDXTransferApproval.from_address.like(
                "%" + request_query.from_address + "%"
            )
        )
    if request_query.to_address is not None:
        stmt = stmt.where(
            IDXTransferApproval.to_address.like("%" + request_query.to_address + "%")
        )
    if request_query.value is not None and request_query.value_operator is not None:
        match request_query.value_operator:
            case ValueOperator.EQUAL:
                stmt = stmt.where(IDXTransferApproval.value == request_query.value)
            case ValueOperator.GTE:
                stmt = stmt.where(IDXTransferApproval.value >= request_query.value)
            case ValueOperator.LTE:
                stmt = stmt.where(IDXTransferApproval.value <= request_query.value)

    count = session.scalar(select(func.count()).select_from(stmt.subquery()))

    # パラメータを設定
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    transfer_approval_history: Sequence[IDXTransferApproval] = session.scalars(
        stmt
    ).all()

    resp_data = [
        transfer_approval_event.json()
        for transfer_approval_event in transfer_approval_history
    ]
    data = {
        "result_set": {
            "count": count,
            "offset": request_query.offset,
            "limit": request_query.limit,
            "total": total,
        },
        "transfer_approval_history": resp_data,
    }

    return json_response({**SuccessResponse.default(), "data": data})


@router.post(
    "/{token_address}/TransferApprovalHistory/Search",
    summary="Search Token Transfer Approval History",
    operation_id="SearchTransferApprovalHistory",
    response_model=GenericSuccessResponse[TransferApprovalHistoriesResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError),
)
def search_transfer_approval_histories(
    session: DBSession,
    data: SearchTransferApprovalHistoryRequest,
    token_address: Annotated[
        ValidatedEthereumAddress, Path(description="Token address")
    ],
):
    """
    Returns a list of transfer approval histories for a given token using detailed search query.
    """
    # Check that it is a listed token
    _listed_token = session.scalars(
        select(Listing).where(Listing.token_address == token_address).limit(1)
    ).first()
    if _listed_token is None:
        raise DataNotExistsError(f"token_address: {token_address}")

    # Get transfer approval data
    stmt = (
        select(IDXTransferApproval)
        .where(IDXTransferApproval.token_address == token_address)
        .order_by(
            IDXTransferApproval.exchange_address, IDXTransferApproval.application_id
        )
    )
    if len(data.account_address_list) > 0:
        stmt = stmt.where(
            or_(
                IDXTransferApproval.from_address.in_(data.account_address_list),
                IDXTransferApproval.to_address.in_(data.account_address_list),
            )
        )
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))

    if data.application_datetime_from is not None:
        stmt = stmt.where(
            IDXTransferApproval.application_datetime
            >= data.application_datetime_from.astimezone(timezone.utc)
        )
    if data.application_datetime_to is not None:
        stmt = stmt.where(
            IDXTransferApproval.application_datetime
            <= data.application_datetime_to.astimezone(timezone.utc)
        )
    if data.application_blocktimestamp_from is not None:
        stmt = stmt.where(
            IDXTransferApproval.application_blocktimestamp
            >= data.application_blocktimestamp_from.astimezone(timezone.utc)
        )
    if data.application_blocktimestamp_to is not None:
        stmt = stmt.where(
            IDXTransferApproval.application_blocktimestamp
            <= data.application_blocktimestamp_to.astimezone(timezone.utc)
        )
    if data.approval_datetime_from is not None:
        stmt = stmt.where(
            IDXTransferApproval.approval_datetime
            >= data.approval_datetime_from.astimezone(timezone.utc)
        )
    if data.approval_datetime_to is not None:
        stmt = stmt.where(
            IDXTransferApproval.approval_datetime
            <= data.approval_datetime_to.astimezone(timezone.utc)
        )
    if data.approval_blocktimestamp_from is not None:
        stmt = stmt.where(
            IDXTransferApproval.approval_blocktimestamp
            >= data.approval_blocktimestamp_from.astimezone(timezone.utc)
        )
    if data.approval_blocktimestamp_to is not None:
        stmt = stmt.where(
            IDXTransferApproval.approval_blocktimestamp
            <= data.approval_blocktimestamp_to.astimezone(timezone.utc)
        )
    if data.from_address is not None:
        stmt = stmt.where(
            IDXTransferApproval.from_address.like("%" + data.from_address + "%")
        )
    if data.to_address is not None:
        stmt = stmt.where(
            IDXTransferApproval.to_address.like("%" + data.to_address + "%")
        )
    if data.value is not None and data.value_operator is not None:
        match data.value_operator:
            case ValueOperator.EQUAL:
                stmt = stmt.where(IDXTransferApproval.value == data.value)
            case ValueOperator.GTE:
                stmt = stmt.where(IDXTransferApproval.value >= data.value)
            case ValueOperator.LTE:
                stmt = stmt.where(IDXTransferApproval.value <= data.value)

    count = session.scalar(select(func.count()).select_from(stmt.subquery()))

    def _order(_order):
        if _order == 0:
            return asc
        else:
            return desc

    if (
        data.sort_item == "from_account_address_list"
        and len(data.account_address_list) > 0
    ):
        stmt = stmt.order_by(
            _order(data.sort_order)(
                case(
                    {
                        account_address: i
                        for i, account_address in enumerate(data.account_address_list)
                    },
                    value=IDXTransferApproval.from_address,
                )
            )
        )
    elif (
        data.sort_item == "to_account_address_list"
        and len(data.account_address_list) > 0
    ):
        stmt = stmt.order_by(
            _order(data.sort_order)(
                case(
                    {
                        account_address: i
                        for i, account_address in enumerate(data.account_address_list)
                    },
                    value=IDXTransferApproval.to_address,
                )
            )
        )
    else:
        sort_attr = getattr(IDXTransferApproval, data.sort_item, None)
        stmt = stmt.order_by(_order(data.sort_order)(sort_attr))

    # NOTE: Set secondary sort for consistent results
    if data.sort_item != "application_id":
        stmt = stmt.order_by(IDXTransferApproval.application_id)

    # パラメータを設定
    if data.offset is not None:
        stmt = stmt.offset(data.offset)
    if data.limit is not None:
        stmt = stmt.limit(data.limit)
    transfer_approval_history: Sequence[IDXTransferApproval] = session.scalars(
        stmt
    ).all()

    resp_data = [
        transfer_approval_event.json()
        for transfer_approval_event in transfer_approval_history
    ]
    data = {
        "result_set": {
            "count": count,
            "offset": data.offset,
            "limit": data.limit,
            "total": total,
        },
        "transfer_approval_history": resp_data,
    }

    return json_response({**SuccessResponse.default(), "data": data})
