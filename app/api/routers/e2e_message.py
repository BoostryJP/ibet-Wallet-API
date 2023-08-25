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
from typing import Annotated

from fastapi import APIRouter, Path

from app import config, log
from app.contracts import Contract
from app.errors import DataNotExistsError, InvalidParameterError
from app.model.schema import E2EMessageEncryptionKeyResponse
from app.model.schema.base import (
    GenericSuccessResponse,
    SuccessResponse,
    ValidatedEthereumAddress,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()

router = APIRouter(prefix="/E2EMessage", tags=["messaging"])


@router.get(
    "/EncryptionKey/{account_address}",
    summary="Retrieve message encryption key",
    operation_id="EncryptionKey",
    response_model=GenericSuccessResponse[E2EMessageEncryptionKeyResponse],
    responses=get_routers_responses(InvalidParameterError, DataNotExistsError),
)
def retrieve_encryption_key(
    account_address: Annotated[
        ValidatedEthereumAddress, Path(description="Account address (message receiver)")
    ]
):
    """
    Endpoint: /E2EMessage/EncryptionKey/{account_address}
    """
    # Get public key
    messaging_contract = Contract.get_contract(
        contract_name="E2EMessaging", address=str(config.E2E_MESSAGING_CONTRACT_ADDRESS)
    )
    key, key_type = Contract.call_function(
        contract=messaging_contract,
        function_name="getPublicKey",
        args=(account_address,),
        default_returns=("", ""),
    )
    if key == "":  # not registered
        raise DataNotExistsError(f"account_address: {account_address}")
    else:
        encryption_key = {"key": key, "key_type": key_type}
    return json_response({**SuccessResponse.default(), "data": encryption_key})
