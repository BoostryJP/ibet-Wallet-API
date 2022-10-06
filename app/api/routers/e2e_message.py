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
from fastapi import (
    APIRouter,
    Path
)
from web3 import Web3

from app import (
    log,
    config
)
from app.contracts import Contract
from app.errors import (
    InvalidParameterError,
    DataNotExistsError
)
from app.model.schema import (
    GenericSuccessResponse,
    E2EMessageEncryptionKeyResponse,
    SuccessResponse
)
from app.utils.docs_utils import get_routers_responses

LOG = log.get_logger()

router = APIRouter(
    prefix="/E2EMessage",
    tags=["E2EMessage"]
)


@router.get(
    "/EncryptionKey/{account_address}",
    summary="Retrieve message encryption key",
    operation_id="EncryptionKey",
    response_model=GenericSuccessResponse[E2EMessageEncryptionKeyResponse],
    responses=get_routers_responses(InvalidParameterError, DataNotExistsError)
)
def retrieve_encryption_key(
    account_address: str = Path(description="Account address (message receiver)")
):
    """
    Endpoint: /E2EMessage/EncryptionKey/{account_address}
    """
    # Validation
    try:
        account_address = to_checksum_address(account_address)
        if not Web3.isAddress(account_address):
            raise InvalidParameterError(description="invalid account_address")
    except:
        raise InvalidParameterError(description="invalid account_address")

    # Get public key
    messaging_contract = Contract.get_contract(
        contract_name="E2EMessaging",
        address=str(config.E2E_MESSAGING_CONTRACT_ADDRESS)
    )
    key, key_type = Contract.call_function(
        contract=messaging_contract,
        function_name="getPublicKey",
        args=(account_address, ),
        default_returns=("", "")
    )
    if key == "":  # not registered
        raise DataNotExistsError(f"account_address: {account_address}")
    else:
        encryption_key = {
            "key": key,
            "key_type": key_type
        }
    return {
        **SuccessResponse.use().dict(),
        "data": encryption_key
    }
