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

from hexbytes import HexBytes

from tests.helpers.contract import Contract


class PersonalInfoHelper:
    @staticmethod
    def register(
        tx_from: str,
        personal_info_address: str,
        link_address: str,
        encrypted_info: str = "",
    ) -> HexBytes:
        """
        Register personal information in PersonalInfo contract

        :param tx_from: Transaction sender address
        :param personal_info_address: PersonalInfo contract address
        :param link_address: Link address for the personal information
        :param encrypted_info: Encrypted personal information (default: "")
        :return: Transaction object
        """
        personal_info_contract = Contract.get_contract(
            contract_name="PersonalInfo", address=personal_info_address
        )
        tx = personal_info_contract.functions.register(
            link_address, encrypted_info
        ).transact({"from": tx_from})  # type: ignore
        return tx
