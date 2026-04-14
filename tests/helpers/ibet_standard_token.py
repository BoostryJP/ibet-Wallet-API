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

from tests.helpers.contract import Contract, web3


class IbetStandardTokenHelper:
    @staticmethod
    def issue(tx_from: str, args: dict[str, Any]) -> Web3Contract:
        """issue token

        :param tx_from: transaction sender
        :param args: deploy args
        :return: Contract
        """
        arguments = [
            args["name"],
            args["symbol"],
            args["totalSupply"],
            args["tradableExchange"],
            args["contactInformation"],
            args["privacyPolicy"],
        ]
        contract_address, _ = Contract.deploy_contract(
            contract_name="IbetStandardToken", args=arguments, deployer=tx_from
        )
        contract = Contract.get_contract(
            contract_name="IbetStandardToken", address=contract_address
        )
        return contract

    @staticmethod
    def transfer_token(
        tx_from: str, token_address: str, to: str, amount: int
    ) -> HexBytes:
        """
        Transfer IbetStandardToken token

        :param tx_from: Transaction sender address
        :param token_address: IbetStandardToken token contract address
        :param to: Recipient address
        :param amount: Transfer amount
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStandardToken", address=token_address
        )
        tx = token_contract.functions.transfer(to, amount).transact({"from": tx_from})  # type: ignore
        web3.eth.wait_for_transaction_receipt(tx)
        return tx
