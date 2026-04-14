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

from tests.helpers.contract import Contract, web3


class E2EMessagingHelper:
    @staticmethod
    def set_public_key(
        tx_from: str, e2e_messaging_address: str, public_key: str, public_key_type: str
    ) -> HexBytes:
        """
        Set public key in E2EMessaging contract

        :param tx_from: Transaction sender address
        :param e2e_messaging_address: E2EMessaging contract address
        :param public_key: Public key to set
        :param public_key_type: Type of the public key
        :return: Transaction object
        """
        e2e_messaging_contract = Contract.get_contract(
            contract_name="E2EMessaging", address=e2e_messaging_address
        )
        tx = e2e_messaging_contract.functions.setPublicKey(
            public_key, public_key_type
        ).transact({"from": tx_from})  # type: ignore
        web3.eth.wait_for_transaction_receipt(tx)
        return tx

    @staticmethod
    def send_message(
        tx_from: str, e2e_messaging_address: str, recipient_address: str, message: str
    ) -> HexBytes:
        """
        Send message using E2EMessaging contract

        :param tx_from: Transaction sender address
        :param e2e_messaging_address: E2EMessaging contract address
        :param recipient_address: Recipient's address
        :param message: Message to send
        :return: Transaction object
        """
        e2e_messaging_contract = Contract.get_contract(
            contract_name="E2EMessaging", address=e2e_messaging_address
        )
        tx = e2e_messaging_contract.functions.sendMessage(
            recipient_address, message
        ).transact({"from": tx_from})  # type: ignore
        web3.eth.wait_for_transaction_receipt(tx)
        return tx
