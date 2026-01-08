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

from eth_utils.address import to_checksum_address
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from tests.utils.contract import Contract

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class PersonalInfoUtils:
    @staticmethod
    def register(tx_from: str, personal_info_address: str, link_address: str) -> None:
        from_address = to_checksum_address(tx_from)
        web3.eth.default_account = from_address
        PersonalInfoContract = Contract.get_contract(
            contract_name="PersonalInfo", address=personal_info_address
        )
        encrypted_info = "some_encrypted_info"
        PersonalInfoContract.functions.register(link_address, encrypted_info).transact(
            {"from": from_address}
        )
