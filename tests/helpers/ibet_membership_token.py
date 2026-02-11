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

from typing import Any

from web3 import Web3
from web3.contract import Contract as Web3Contract
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from tests.helpers.contract import Contract

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class IbetMembershipTestHelper:
    @staticmethod
    def issue(tx_from: str, args: dict[str, Any]) -> Web3Contract:
        """
        Issue IbetMembership token

        :param tx_from: Transaction sender address
        :param args: IbetMembership issue arguments
        :return: IbetMembership contract instance
        """
        # issue
        arguments = [
            args["name"],
            args["symbol"],
            args["initialSupply"],
            args["tradableExchange"],
            args["details"],
            args["returnDetails"],
            args["expirationDate"],
            args["memo"],
            args["transferable"],
            args["contactInformation"],
            args["privacyPolicy"],
        ]
        contract_address, _ = Contract.deploy_contract(
            contract_name="IbetMembership", args=arguments, deployer=tx_from
        )

        coupon_contract = Contract.get_contract(
            contract_name="IbetMembership", address=contract_address
        )
        return coupon_contract

    @staticmethod
    def register_token_list(
        tx_from: str,
        token_address: str,
        token_list_contract_address: str,
        token_template_name: str = "IbetMembership",
    ) -> None:
        """
        Register IbetMembership token to TokenList contract

        :param tx_from: Transaction sender address
        :param token_address: IbetMembership token contract address
        :param token_list_contract_address: TokenList contract address
        :param token_template_name: Token template name (default: "IbetMembership")
        """
        token_list_contract = Contract.get_contract(
            contract_name="TokenList", address=token_list_contract_address
        )
        token_list_contract.functions.register(
            token_address, token_template_name
        ).transact({"from": tx_from})

    @staticmethod
    def transfer_token(tx_from: str, token_address: str, to: str, amount: int) -> None:
        """
        Transfer IbetMembership token

        :param tx_from: Transaction sender address
        :param token_address: IbetMembership contract address
        :param to: Transfer destination address
        :param amount: Transfer amount
        """
        token_contract = Contract.get_contract(
            contract_name="IbetMembership", address=token_address
        )
        token_contract.functions.transfer(to, amount).transact({"from": tx_from})

    @staticmethod
    def set_token_status(tx_from: str, token_address: str, status: int) -> None:
        """
        Set token status on IbetMembership contract

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetMembership contract address
        :param status: Token status
        """
        token_contract = Contract.get_contract(
            contract_name="IbetMembership", address=token_address
        )
        token_contract.functions.setStatus(status).transact({"from": tx_from})
