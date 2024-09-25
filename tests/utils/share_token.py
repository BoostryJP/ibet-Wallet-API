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

from typing import Dict

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from app.contracts import Contract
from tests.account_config import eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class IbetShareUtils:
    @staticmethod
    def issue(tx_from: str, args: Dict):
        web3.eth.default_account = tx_from

        # issue
        arguments = [
            args["name"],
            args["symbol"],
            args["issuePrice"],
            args["totalSupply"],
            args["dividends"],
            args["dividendRecordDate"],
            args["dividendPaymentDate"],
            args["cancellationDate"],
            args["principalValue"],
        ]
        contract_address, _ = Contract.deploy_contract(
            contract_name="IbetShare", args=arguments, deployer=tx_from
        )

        # update
        share_contract = Contract.get_contract(
            contract_name="IbetShare", address=contract_address
        )
        if "tradableExchange" in args:
            share_contract.functions.setTradableExchange(
                args["tradableExchange"]
            ).transact({"from": tx_from})
        if "personalInfoAddress" in args:
            share_contract.functions.setPersonalInfoAddress(
                args["personalInfoAddress"]
            ).transact({"from": tx_from})
        if "requirePersonalInfoRegistered" in args:
            share_contract.functions.setRequirePersonalInfoRegistered(
                args["requirePersonalInfoRegistered"]
            ).transact({"from": tx_from})
        if "contactInformation" in args:
            share_contract.functions.setContactInformation(
                args["contactInformation"]
            ).transact({"from": tx_from})
        if "privacyPolicy" in args:
            share_contract.functions.setPrivacyPolicy(args["privacyPolicy"]).transact(
                {"from": tx_from}
            )
        if "memo" in args:
            share_contract.functions.setMemo(args["memo"]).transact({"from": tx_from})
        if "transferable" in args:
            share_contract.functions.setTransferable(args["transferable"]).transact(
                {"from": tx_from}
            )
        if "transferApprovalRequired" in args:
            share_contract.functions.setTransferApprovalRequired(
                args["transferApprovalRequired"]
            ).transact({"from": tx_from})

        return share_contract

    @staticmethod
    def register_token_list(tx_from: str, token_address, token_list_contract_address):
        TokenListContract = Contract.get_contract(
            contract_name="TokenList", address=token_list_contract_address
        )
        web3.eth.default_account = tx_from
        TokenListContract.functions.register(token_address, "IbetShare").transact(
            {"from": tx_from}
        )

    @staticmethod
    def sell(
        tx_from: str, exchange_address: str, token_address: str, amount: int, price: int
    ):
        IbetShareUtils.transfer_to_exchange(
            tx_from=tx_from,
            exchange_address=exchange_address,
            token_address=token_address,
            amount=amount,
        )
        IbetShareUtils.make_sell_order(
            tx_from=tx_from,
            exchange_address=exchange_address,
            token_address=token_address,
            amount=amount,
            price=price,
        )

    @staticmethod
    def transfer_to_exchange(
        tx_from: str, exchange_address: str, token_address: str, amount: int
    ):
        web3.eth.default_account = tx_from
        TokenContract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        TokenContract.functions.transfer(exchange_address, amount).transact(
            {"from": tx_from}
        )

    @staticmethod
    def make_sell_order(
        tx_from: str, exchange_address: str, token_address: str, amount: int, price: int
    ):
        web3.eth.default_account = tx_from
        agent_address = eth_account["agent"]["account_address"]
        ExchangeContract = Contract.get_contract(
            contract_name="IbetExchange", address=exchange_address
        )
        ExchangeContract.functions.createOrder(
            token_address, amount, price, False, agent_address
        ).transact({"from": tx_from})

    @staticmethod
    def set_transfer_approval_required(
        tx_from: str, token_address: str, required: bool
    ):
        TokenContract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        TokenContract.functions.setTransferApprovalRequired(required).transact(
            {"from": tx_from}
        )

    @staticmethod
    def apply_for_transfer(tx_from: str, token_address: str, to: str, value: int):
        TokenContract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        TokenContract.functions.applyForTransfer(to, value, "").transact(
            {"from": tx_from}
        )
