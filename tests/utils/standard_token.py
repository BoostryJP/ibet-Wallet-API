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

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class IbetStandardTokenUtils:
    @staticmethod
    def issue(tx_from: str, args: Dict):
        """issue token

        :param tx_from: transaction sender
        :param args: deploy args
        :return: Contract
        """
        web3.eth.default_account = tx_from
        arguments = [
            args["name"],
            args["symbol"],
            args["totalSupply"],
            args["tradableExchange"],
            args["contactInformation"],
            args["privacyPolicy"],
        ]
        contract_address, abi = Contract.deploy_contract(
            contract_name="IbetStandardToken", args=arguments, deployer=tx_from
        )
        contract = Contract.get_contract(
            contract_name="IbetStandardToken", address=contract_address
        )
        return contract
