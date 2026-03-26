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

from typing import TYPE_CHECKING, Annotated

from eth_utils.address import to_checksum_address
from fastapi import APIRouter, Query

from app import config, log
from app.contracts import AsyncContract
from app.database import DBAsyncSession
from app.errors import InvalidParameterError
from app.model.db import AccountTag
from app.model.schema import (
    RetrievePersonalInfoQuery,
    RetrievePersonalInfoRegistrationStatusResponse,
    TaggingAccountAddressRequest,
)
from app.model.schema.base import (
    GenericSuccessResponse,
    Success200MetaModel,
    SuccessResponse,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()

router = APIRouter(prefix="/User", tags=["user_info"])


@router.post(
    "/Tag",
    summary="Tagging account address",
    operation_id="TaggingAccountAddress",
    response_model=SuccessResponse,
    responses=get_routers_responses(),
)
async def tagging_account_address(
    async_session: DBAsyncSession, data: TaggingAccountAddressRequest
):
    """
    Tag any account address
    """
    account_tag = AccountTag()
    account_tag.account_address = data.account_address
    account_tag.account_tag = data.account_tag
    await async_session.merge(account_tag)
    await async_session.commit()

    if TYPE_CHECKING:
        _ = SuccessResponse(
            meta=Success200MetaModel(code=200, message="OK"),
        )
    return json_response(SuccessResponse.default())


@router.get(
    "/PersonalInfo",
    summary="Retrieve registration status for PersonalInfo contract",
    operation_id="RetrievePersonalInfoRegistrationStatus",
    response_model=GenericSuccessResponse[
        RetrievePersonalInfoRegistrationStatusResponse
    ],
    responses=get_routers_responses(),
)
async def get_personal_info_registration_status(
    query: Annotated[RetrievePersonalInfoQuery, Query()],
):
    """
    Returns personal information about given address.
    """
    # Get PersonalInfo contract
    if query.personal_info_address is not None:
        _personal_info_address = query.personal_info_address
    else:
        _personal_info_address = config.PERSONAL_INFO_CONTRACT_ADDRESS
    if _personal_info_address is None:
        raise InvalidParameterError("personal_info_address is not set")
    personal_info_contract = AsyncContract.get_contract(
        contract_name="PersonalInfo", address=_personal_info_address
    )

    # Get registration status of personal information
    info = await AsyncContract.call_function(
        contract=personal_info_contract,
        function_name="personal_info",
        args=(
            to_checksum_address(query.account_address),
            to_checksum_address(query.owner_address),
        ),
        default_returns=(
            config.ZERO_ADDRESS,
            config.ZERO_ADDRESS,
            False,
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

    if TYPE_CHECKING:
        _ = GenericSuccessResponse[RetrievePersonalInfoRegistrationStatusResponse](
            meta=Success200MetaModel(code=200, message="OK"),
            data=(
                RetrievePersonalInfoRegistrationStatusResponse(
                    account_address=query.account_address,
                    owner_address=query.owner_address,
                    registered=False,
                )
                if info[0] == config.ZERO_ADDRESS
                else RetrievePersonalInfoRegistrationStatusResponse(
                    account_address=info[0],
                    owner_address=info[1],
                    registered=True,
                )
            ),
        )
    return json_response({**SuccessResponse.default(), "data": response_json})
