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
from eth_utils import to_checksum_address
from fastapi import APIRouter, Depends

from app import config, log
from app.contracts import Contract
from app.model.schema import (
    GenericSuccessResponse,
    RetrievePaymentAccountQuery,
    RetrievePaymentAccountRegistrationStatusResponse,
    RetrievePersonalInfoQuery,
    RetrievePersonalInfoRegistrationStatusResponse,
    SuccessResponse,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi import json_response

LOG = log.get_logger()

router = APIRouter(prefix="/User", tags=["user_info"])


# ------------------------------
# 受領用銀行口座登録状況参照
# ------------------------------
@router.get(
    "/PaymentAccount",
    summary="Registration status to PaymentGateway Contract",
    operation_id="PaymentAccount",
    response_model=GenericSuccessResponse[
        RetrievePaymentAccountRegistrationStatusResponse
    ],
    responses=get_routers_responses(),
)
def get_payment_account_registration_status(
    query: RetrievePaymentAccountQuery = Depends(),
):
    """
    Endpoint: /User/PaymentAccount
    """
    pg_contract = Contract.get_contract(
        contract_name="PaymentGateway",
        address=str(config.PAYMENT_GATEWAY_CONTRACT_ADDRESS),
    )

    # 口座登録・承認状況を参照
    account_info = Contract.call_function(
        contract=pg_contract,
        function_name="payment_accounts",
        args=(
            to_checksum_address(query.account_address),
            to_checksum_address(query.agent_address),
        ),
    )
    if account_info[0] == "0x0000000000000000000000000000000000000000":
        response_json = {
            "account_address": query.account_address,
            "agent_address": query.agent_address,
            "approval_status": 0,
        }
    else:
        response_json = {
            "account_address": account_info[0],
            "agent_address": account_info[1],
            "approval_status": account_info[3],
        }

    return json_response({**SuccessResponse.default(), "data": response_json})


# ------------------------------
# 名簿用個人情報参照
# ------------------------------
@router.get(
    "/PersonalInfo",
    summary="Registration status to PersonalInfo Contract",
    operation_id="PersonalInfo",
    response_model=GenericSuccessResponse[
        RetrievePersonalInfoRegistrationStatusResponse
    ],
    responses=get_routers_responses(),
)
def get_personal_info_registration_status(query: RetrievePersonalInfoQuery = Depends()):
    """
    Endpoint: /User/PersonalInfo
    """
    # Get PersonalInfo contract
    if query.personal_info_address is not None:
        _personal_info_address = query.personal_info_address
    else:
        _personal_info_address = config.PERSONAL_INFO_CONTRACT_ADDRESS
    personal_info_contract = Contract.get_contract(
        contract_name="PersonalInfo", address=_personal_info_address
    )

    # Get registration status of personal information
    info = Contract.call_function(
        contract=personal_info_contract,
        function_name="personal_info",
        args=(
            to_checksum_address(query.account_address),
            to_checksum_address(query.owner_address),
        ),
    )
    if info[0] == config.ZERO_ADDRESS:
        response_json = {
            "account_address": query.account_address,
            "owner_address": query.owner_address,
            "registered": False,
        }
    else:
        response_json = {
            "account_address": info[0],
            "owner_address": info[1],
            "registered": True,
        }

    return json_response({**SuccessResponse.default(), "data": response_json})
