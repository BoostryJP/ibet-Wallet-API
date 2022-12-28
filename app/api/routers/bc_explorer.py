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
from pathlib import Path
from typing import Tuple, Dict, Any

from eth_utils import to_checksum_address
from fastapi import (
    APIRouter,
    Depends
)
from pydantic import NonNegativeInt
from sqlalchemy import desc
from sqlalchemy.orm import Session
from starlette.requests import Request
from web3.contract import ContractFunction

from app import log, config
from app.contracts import Contract
from app.database import db_session
from app.errors import (
    DataNotExistsError,
    NotSupportedError,
    ResponseLimitExceededError
)
from app.model.db import (
    IDXBlockData,
    IDXTxData,
    IDXTokenListItem
)
from app.model.schema import (
    GenericSuccessResponse,
    SuccessResponse,
    ListBlockDataQuery,
    ListTxDataQuery,
    BlockDataResponse,
    BlockDataListResponse,
    TxDataResponse,
    TxDataListResponse
)
from app.utils.docs_utils import get_routers_responses
from app.utils.web3_utils import Web3Wrapper

LOG = log.get_logger()
web3 = Web3Wrapper()
BLOCK_RESPONSE_LIMIT = 1000
TX_RESPONSE_LIMIT = 10000

router = APIRouter(
    prefix="/NodeInfo",
    tags=["node_info"]
)


# ------------------------------
# [BC-Explorer] List Block data
# ------------------------------
@router.get(
    "/BlockData",
    summary="[ibet Blockchain Explorer] List block data",
    operation_id="ListBlockData",
    response_model=GenericSuccessResponse[BlockDataListResponse],
    responses=get_routers_responses(NotSupportedError, ResponseLimitExceededError)
)
def list_block_data(
    req: Request,
    request_query: ListBlockDataQuery = Depends(),
    session: Session = Depends(db_session)
):
    """
    Returns a list of block data within the specified block number range.
    The maximum number of search results is 1000.
    """
    if config.BC_EXPLORER_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    offset = request_query.offset
    limit = request_query.limit
    from_block_number = request_query.from_block_number
    to_block_number = request_query.to_block_number

    query = session.query(IDXBlockData)
    total = query.count()

    # Search Filter
    if from_block_number is not None and to_block_number is not None:
        query = query.filter(IDXBlockData.number >= from_block_number, IDXBlockData.number <= to_block_number)
    elif from_block_number is not None:
        query = query.filter(IDXBlockData.number >= from_block_number)
    elif to_block_number is not None:
        query = query.filter(IDXBlockData.number <= to_block_number)

    count = query.count()

    # Sort
    query = query.order_by(IDXBlockData.number)

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    if query.count() > BLOCK_RESPONSE_LIMIT:
        raise ResponseLimitExceededError("Search results exceed the limit")

    block_data_tmp: list[IDXBlockData] = query.all()
    block_data = []
    for bd in block_data_tmp:
        block_data.append({
            "number": bd.number,
            "hash": bd.hash,
            "transactions": bd.transactions,
            "timestamp": bd.timestamp,
            "gas_limit": bd.gas_limit,
            "gas_used": bd.gas_used,
            "size": bd.size
        })

    data = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "block_data": block_data
    }

    return {
        **SuccessResponse.use().dict(),
        "data": data
    }

# ------------------------------
# [BC-Explorer] Retrieve Block data
# ------------------------------
@router.get(
    "/BlockData/{block_number}",
    summary="[ibet Blockchain Explorer] Retrieve block data",
    operation_id="GetBlockData",
    response_model=GenericSuccessResponse[BlockDataResponse],
    responses=get_routers_responses(NotSupportedError, DataNotExistsError)
)
def get_block_data(
    req: Request,
    block_number: NonNegativeInt = Path(description="Block number"),
    session: Session = Depends(db_session)
):
    """
    Returns block data in the specified block number.
    """
    if config.BC_EXPLORER_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    block_data = (
        session.query(IDXBlockData).
        filter(IDXBlockData.number == block_number).
        first()
    )
    if block_data is None:
        raise DataNotExistsError

    return {
        **SuccessResponse.use().dict(),
        "data": {
            "number": block_data.number,
            "parent_hash": block_data.parent_hash,
            "sha3_uncles": block_data.sha3_uncles,
            "miner": block_data.miner,
            "state_root": block_data.state_root,
            "transactions_root": block_data.transactions_root,
            "receipts_root": block_data.receipts_root,
            "logs_bloom": block_data.logs_bloom,
            "difficulty": block_data.difficulty,
            "gas_limit": block_data.gas_limit,
            "gas_used": block_data.gas_used,
            "timestamp": block_data.timestamp,
            "proof_of_authority_data": block_data.proof_of_authority_data,
            "mix_hash": block_data.mix_hash,
            "nonce": block_data.nonce,
            "hash": block_data.hash,
            "size": block_data.size,
            "transactions": block_data.transactions
        }
    }

# ------------------------------
# [BC-Explorer] List Tx data
# ------------------------------
@router.get(
    "/TxData",
    summary="[ibet Blockchain Explorer] List tx data",
    operation_id="ListTxData",
    response_model=GenericSuccessResponse[TxDataListResponse],
    responses=get_routers_responses(NotSupportedError, ResponseLimitExceededError)
)
def list_tx_data(
    req: Request,
    request_query: ListTxDataQuery = Depends(),
    session: Session = Depends(db_session)
):
    """
    Returns a list of transactions by various search parameters.
    The maximum number of search results is 10000.
    """
    if config.BC_EXPLORER_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    offset = request_query.offset
    limit = request_query.limit
    block_number = request_query.block_number
    from_address = request_query.from_address
    to_address = request_query.to_address

    query = session.query(IDXTxData)
    total = query.count()

    # Search Filter
    if block_number is not None:
        query = query.filter(IDXTxData.block_number == block_number)
    if from_address is not None:
        query = query.filter(IDXTxData.from_address == to_checksum_address(from_address))
    if to_address is not None:
        query = query.filter(IDXTxData.to_address == to_checksum_address(to_address))

    count = query.count()

    # Sort
    query = query.order_by(desc(IDXTxData.created))

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    if query.count() > TX_RESPONSE_LIMIT:
        raise ResponseLimitExceededError("Search results exceed the limit")

    tx_data_tmp: list[IDXTxData] = query.all()
    tx_data = []
    for txd in tx_data_tmp:
        tx_data.append({
            "hash": txd.hash,
            "block_hash": txd.block_hash,
            "block_number": txd.block_number,
            "transaction_index": txd.transaction_index,
            "from_address": txd.from_address,
            "to_address": txd.to_address
        })

    data = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "tx_data": tx_data
    }
    return {
        **SuccessResponse.use().dict(),
        "data": data
    }


# ------------------------------
# [BC-Explorer] Retrieve Tx data
# ------------------------------
@router.get(
    "/TxData/{hash}",
    summary="[ibet Blockchain Explorer] Retrieve transaction data",
    operation_id="GetTxData",
    response_model=GenericSuccessResponse[TxDataResponse],
    responses=get_routers_responses(NotSupportedError, DataNotExistsError)
)
def get_tx_data(
    req: Request,
    hash: str = Path(description="Transaction hash"),
    session: Session = Depends(db_session)
):
    """
    Searching for the transaction by transaction hash
    """
    if config.BC_EXPLORER_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    # Search tx data
    tx_data = (
        session.query(IDXTxData).
        filter(IDXTxData.hash == hash).
        first()
    )
    if tx_data is None:
        raise DataNotExistsError

    # Decode contract input parameters
    contract_name: str | None = None
    contract_function: str | None = None
    contract_parameters: dict | None = None
    token_contract = (
        session.query(IDXTokenListItem).
        filter(IDXTokenListItem.token_address == tx_data.to_address).
        first()
    )
    if token_contract is not None:
        contract_name = token_contract.token_template
        try:
            contract = Contract.get_contract(
                contract_name=contract_name,
                address=tx_data.to_address
            )
            decoded_input: Tuple['ContractFunction', Dict[str, Any]] = contract.decode_function_input(tx_data.input)
            contract_function = decoded_input[0].fn_name
            contract_parameters = decoded_input[1]
        except FileNotFoundError:
            pass

    return {
        **SuccessResponse.use().dict(),
        "data": {
            "hash": tx_data.hash,
            "block_hash": tx_data.block_hash,
            "block_number": tx_data.block_number,
            "transaction_index": tx_data.transaction_index,
            "from_address": tx_data.from_address,
            "to_address": tx_data.to_address,
            "contract_name": contract_name,
            "contract_function": contract_function,
            "contract_parameters": contract_parameters,
            "gas": tx_data.gas,
            "gas_price": tx_data.gas_price,
            "value": tx_data.value,
            "nonce": tx_data.nonce
        }
    }
