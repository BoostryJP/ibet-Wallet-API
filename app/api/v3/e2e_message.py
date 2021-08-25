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
from web3 import Web3

from app import (
    log,
    config
)
from app.api.common import BaseResource
from app.contracts import Contract
from app.errors import (
    InvalidParameterError,
    DataNotExistsError
)

LOG = log.get_logger()


# /E2EMessage/EncryptionKey/{account_address}
class EncryptionKey(BaseResource):
    """Message encryption key"""

    def on_get(self, req, res, account_address=None):
        """Retrieve message encryption key"""
        LOG.info("v3.e2e_message.EncryptionKey")

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
            address=config.E2E_MESSAGING_CONTRACT_ADDRESS
        )
        key, key_type = messaging_contract.functions.getPublicKey(account_address).call()

        if key == "":  # not registered
            raise DataNotExistsError(f"account_address: {account_address}")
        else:
            encryption_key = {
                "key": key,
                "key_type": key_type
            }

        self.on_success(res, encryption_key)
