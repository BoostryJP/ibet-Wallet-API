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

import json

import requests
from fastapi import APIRouter
from sqlalchemy import select

from app import config, log
from app.database import DBAsyncSession
from app.errors import ServiceUnavailable
from app.model.db import Node
from app.model.schema import GetBlockSyncStatusResponse, GetNodeInfoResponse
from app.model.schema.base import GenericSuccessResponse, SuccessResponse
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response
from app.utils.web3_utils import AsyncWeb3Wrapper

LOG = log.get_logger()


router = APIRouter(prefix="/NodeInfo", tags=["node_info"])


# ------------------------------
# ノード情報
# ------------------------------
@router.get(
    "",
    summary="Blockchain node information",
    operation_id="NodeInfo",
    response_model=GenericSuccessResponse[GetNodeInfoResponse],
)
async def get_node_info():
    """
    Returns node information.
    """
    payment_gateway_json = json.load(
        open("app/contracts/json/PaymentGateway.json", "r")
    )
    personal_info_json = json.load(open("app/contracts/json/PersonalInfo.json", "r"))
    ibet_exchange_json = json.load(open("app/contracts/json/IbetExchange.json", "r"))
    ibet_escrow_json = json.load(open("app/contracts/json/IbetEscrow.json", "r"))
    ibet_security_token_escrow_json = json.load(
        open("app/contracts/json/IbetSecurityTokenEscrow.json", "r")
    )
    ibet_security_token_dvp_json = json.load(
        open("app/contracts/json/IbetSecurityTokenDVP.json", "r")
    )
    e2e_messaging_json = json.load(open("app/contracts/json/E2EMessaging.json", "r"))

    nodeInfo = {
        "payment_gateway_address": config.PAYMENT_GATEWAY_CONTRACT_ADDRESS,
        "payment_gateway_abi": payment_gateway_json["abi"],
        "personal_info_address": config.PERSONAL_INFO_CONTRACT_ADDRESS,
        "personal_info_abi": personal_info_json["abi"],
        "ibet_membership_exchange_address": config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
        "ibet_membership_exchange_abi": ibet_exchange_json["abi"],
        "ibet_coupon_exchange_address": config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
        "ibet_coupon_exchange_abi": ibet_exchange_json["abi"],
        "ibet_escrow_address": config.IBET_ESCROW_CONTRACT_ADDRESS,
        "ibet_escrow_abi": ibet_escrow_json["abi"],
        "ibet_security_token_escrow_address": config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS,
        "ibet_security_token_escrow_abi": ibet_security_token_escrow_json["abi"],
        "ibet_security_token_dvp_address": config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS,
        "ibet_security_token_dvp_abi": ibet_security_token_dvp_json["abi"],
        "e2e_messaging_address": config.E2E_MESSAGING_CONTRACT_ADDRESS,
        "e2e_messaging_abi": e2e_messaging_json["abi"],
    }
    return json_response({**SuccessResponse.default(), "data": nodeInfo})


# ------------------------------
# ブロック同期情報
# ------------------------------
@router.get(
    "/BlockSyncStatus",
    summary="Block synchronization status of the connected blockchain node",
    operation_id="NodeInfoBlockSyncStatus",
    response_model=GenericSuccessResponse[GetBlockSyncStatusResponse],
    responses=get_routers_responses(ServiceUnavailable),
)
async def get_block_sync_status(async_session: DBAsyncSession):
    """
    Returns block sync status of node.
    """
    # Get block sync status
    node: Node = (
        await async_session.scalars(
            select(Node).where(Node.is_synced == True).order_by(Node.priority).limit(1)
        )
    ).first()

    # Get the latest block number
    is_synced = False
    latest_block_number = None
    if node is not None:
        is_synced = True
        try:
            async_web3 = AsyncWeb3Wrapper(request_timeout=1)
            latest_block_number = await async_web3.eth.block_number
        except requests.exceptions.ReadTimeout:
            raise ServiceUnavailable("Temporarily unable to connect to web3 provider")

    return json_response(
        {
            **SuccessResponse.default(),
            "data": {
                "is_synced": is_synced,
                "latest_block_number": latest_block_number,
            },
        }
    )
