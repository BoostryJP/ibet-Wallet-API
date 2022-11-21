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
import json

from eth_utils import to_checksum_address
from web3 import contract
from web3.exceptions import (
    BadFunctionCallOutput,
    ABIFunctionNotFound,
    ContractLogicError
)

from app.utils.web3_utils import Web3Wrapper

web3 = Web3Wrapper()


class Contract:
    cache = {}  # コントラクト情報のキャッシュ

    @staticmethod
    def get_contract(contract_name: str, address: str):
        """
        コントラクト取得

        :param contract_name: コントラクト名
        :param address: コントラクトアドレス
        :return: コントラクト
        """
        if contract_name in Contract.cache:
            contract_json = Contract.cache[contract_name]
        else:
            contract_file = f"app/contracts/json/{contract_name}.json"
            contract_json = json.load(open(contract_file, 'r'))
            Contract.cache[contract_name] = contract_json

        contract = web3.eth.contract(
            address=to_checksum_address(address),
            abi=contract_json['abi'],
        )
        return contract

    @staticmethod
    def deploy_contract(contract_name: str,
                        args: list,
                        deployer: str):
        """
        コントラクトデプロイ

        :param contract_name: コントラクト名
        :param args: デプロイ時の引数
        :param deployer: デプロイ実行者のアドレス
        :return: コントラクト情報
        """
        if contract_name in Contract.cache:
            contract_json = Contract.cache[contract_name]
        else:
            contract_file = f"app/contracts/json/{contract_name}.json"
            contract_json = json.load(open(contract_file, 'r'))
            Contract.cache[contract_name] = contract_json

        contract = web3.eth.contract(
            abi=contract_json['abi'],
            bytecode=contract_json['bytecode'],
            bytecode_runtime=contract_json['deployedBytecode'],
        )

        tx_hash = contract.constructor(*args).transact({
            'from': deployer,
            'gas': 6000000
        })
        tx = web3.eth.waitForTransactionReceipt(tx_hash)

        contract_address = ''
        if tx is not None:
            # ブロックの状態を確認して、コントラクトアドレスが登録されているかを確認する。
            if 'contractAddress' in tx.keys():
                contract_address = tx['contractAddress']

        return contract_address, contract_json['abi']

    @staticmethod
    def call_function(contract: contract,
                      function_name: str,
                      args: tuple,
                      default_returns=None):
        """Call contract function

        :param contract: Contract
        :param function_name: Function name
        :param args: Function args
        :param default_returns: Default return when BadFunctionCallOutput is raised
        :return: Return from function or default return
        """

        try:
            _function = getattr(contract.functions, function_name)
            result = _function(*args).call()
        except (BadFunctionCallOutput, ABIFunctionNotFound, ContractLogicError) as web3_exception:
            if default_returns is not None:
                return default_returns
            else:
                raise web3_exception

        return result
