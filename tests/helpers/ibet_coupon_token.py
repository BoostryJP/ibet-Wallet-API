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

from hexbytes import HexBytes
from web3.contract import Contract as Web3Contract

from tests.helpers.contract import Contract


class IbetCouponTestHelper:
    @staticmethod
    def issue(tx_from: str, args: dict[str, Any]) -> Web3Contract:
        """
        Issue IbetCoupon token

        :param tx_from: Transaction sender address
        :param args: IbetCoupon issue arguments
        :return: IbetCoupon contract instance
        """
        # issue
        arguments = [
            args["name"],
            args["symbol"],
            args["totalSupply"],
            args["tradableExchange"],
            args["details"],
            args["returnDetails"],
            args["memo"],
            args["expirationDate"],
            args["transferable"],
            args["contactInformation"],
            args["privacyPolicy"],
        ]
        contract_address, _ = Contract.deploy_contract(
            contract_name="IbetCoupon", args=arguments, deployer=tx_from
        )

        coupon_contract = Contract.get_contract(
            contract_name="IbetCoupon", address=contract_address
        )
        return coupon_contract

    @staticmethod
    def register_token_list(
        tx_from: str,
        token_address: str,
        token_list_contract_address: str,
        token_template_name: str = "IbetCoupon",
    ) -> HexBytes:
        """
        Register IbetCoupon token to TokenList contract

        :param tx_from: Transaction sender address
        :param token_address: IbetCoupon token contract address
        :param token_list_contract_address: TokenList contract address
        :param token_template_name: Token template name (default: "IbetCoupon")
        :return: Transaction object
        """
        token_list_contract = Contract.get_contract(
            contract_name="TokenList", address=token_list_contract_address
        )
        tx = token_list_contract.functions.register(
            token_address, token_template_name
        ).transact({"from": tx_from})  # type: ignore
        return tx

    @staticmethod
    def transfer_token(
        tx_from: str, token_address: str, to: str, amount: int
    ) -> HexBytes:
        """
        Transfer IbetCoupon token

        :param tx_from: Transaction sender address
        :param token_address: IbetCoupon contract address
        :param to: Transfer destination address
        :param amount: Transfer amount
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetCoupon", address=token_address
        )
        tx = token_contract.functions.transfer(to, amount).transact({"from": tx_from})  # type: ignore
        return tx

    @staticmethod
    def consume_token(tx_from: str, token_address: str, amount: int) -> HexBytes:
        """
        Consume IbetCoupon token

        :param tx_from: Transaction sender address
        :param token_address: IbetCoupon contract address
        :param amount: Consume amount
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetCoupon", address=token_address
        )
        tx = token_contract.functions.consume(amount).transact(
            {"from": tx_from}  # type: ignore
        )
        return tx

    @staticmethod
    def set_token_status(tx_from: str, token_address: str, status: int) -> HexBytes:
        """
        Set token status on IbetCoupon contract

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetCoupon contract address
        :param status: Token status
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetCoupon", address=token_address
        )
        tx = token_contract.functions.setStatus(status).transact({"from": tx_from})  # type: ignore
        return tx
