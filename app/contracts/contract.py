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
from typing import Type, TypeVar

from eth_utils import to_checksum_address
from web3 import contract
from web3.contract import Contract as Web3Contract
from web3.contract.async_contract import AsyncContractEvents
from web3.eth.async_eth import AsyncContract as Web3AsyncContract
from web3.exceptions import BadFunctionCallOutput, ContractLogicError

from app.utils.web3_utils import AsyncWeb3Wrapper, Web3Wrapper

web3 = Web3Wrapper()
async_web3 = AsyncWeb3Wrapper()


class Contract:
    cache = {}  # コントラクト情報のキャッシュ
    factory_map: dict[str, Type[Web3Contract]] = {}

    @classmethod
    def get_contract(cls, contract_name: str, address: str):
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
            contract_json = json.load(open(contract_file, "r"))
            Contract.cache[contract_name] = contract_json

        contract_factory = cls.factory_map.get(contract_name)
        if contract_factory is not None:
            return contract_factory(address=to_checksum_address(address))

        contract_factory = web3.eth.contract(abi=contract_json["abi"])
        cls.factory_map[contract_name] = contract_factory
        return contract_factory(address=to_checksum_address(address))

    @staticmethod
    def deploy_contract(contract_name: str, args: list, deployer: str):
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
            contract_json = json.load(open(contract_file, "r"))
            Contract.cache[contract_name] = contract_json

        contract = web3.eth.contract(
            abi=contract_json["abi"],
            bytecode=contract_json["bytecode"],
            bytecode_runtime=contract_json["deployedBytecode"],
        )

        tx_hash = contract.constructor(*args).transact(
            {"from": deployer, "gas": 6000000}
        )
        tx = web3.eth.wait_for_transaction_receipt(tx_hash)

        contract_address = ""
        if tx is not None:
            # ブロックの状態を確認して、コントラクトアドレスが登録されているかを確認する。
            if "contractAddress" in tx.keys():
                contract_address = tx["contractAddress"]

        return contract_address, contract_json["abi"]

    T = TypeVar("T")

    @staticmethod
    def call_function(
        contract: contract, function_name: str, args: tuple, default_returns: T = None
    ) -> T:
        """Call contract function

        :param contract: Contract
        :param function_name: Function name
        :param args: Function args
        :param default_returns: Default return when exception is raised
        :return: Return from function or default return
        """
        _function = getattr(contract.functions, function_name)

        try:
            result = _function(*args).call()
        except (BadFunctionCallOutput, ContractLogicError) as exc:
            if default_returns is not None:
                return default_returns
            else:
                raise exc

        return result


class AsyncContractEventsView:
    def __init__(self, address: str, contract_events: AsyncContractEvents) -> None:
        self._address = address
        self._events = contract_events

    @property
    def address(self) -> str:
        return self._address

    @property
    def events(self) -> AsyncContractEvents:
        return self._events


class AsyncContract:
    cache = {}  # コントラクト情報のキャッシュ
    factory_map: dict[str, Type[Web3AsyncContract]] = {}

    @classmethod
    def get_contract(cls, contract_name: str, address: str) -> Web3AsyncContract:
        """
        コントラクト取得

        :param contract_name: コントラクト名
        :param address: コントラクトアドレス
        :return: コントラクト
        """
        if contract_name in AsyncContract.cache:
            contract_json = AsyncContract.cache[contract_name]
        else:
            contract_file = f"app/contracts/json/{contract_name}.json"
            contract_json = json.load(open(contract_file, "r"))
            AsyncContract.cache[contract_name] = contract_json

        contract_factory = cls.factory_map.get(contract_name)
        if contract_factory is not None:
            return contract_factory(address=to_checksum_address(address))

        contract_factory = async_web3.eth.contract(abi=contract_json["abi"])
        cls.factory_map[contract_name] = contract_factory
        return contract_factory(address=to_checksum_address(address))

    @staticmethod
    async def deploy_contract(contract_name: str, args: list, deployer: str):
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
            contract_json = json.load(open(contract_file, "r"))
            Contract.cache[contract_name] = contract_json

        async_contract = async_web3.eth.contract(
            abi=contract_json["abi"],
            bytecode=contract_json["bytecode"],
            bytecode_runtime=contract_json["deployedBytecode"],
        )

        tx_hash = await async_contract.constructor(*args).transact(
            {"from": deployer, "gas": 6000000}
        )
        tx = await async_web3.eth.wait_for_transaction_receipt(tx_hash)

        contract_address = ""
        if tx is not None:
            # ブロックの状態を確認して、コントラクトアドレスが登録されているかを確認する。
            if "contractAddress" in tx.keys():
                contract_address = tx["contractAddress"]

        return contract_address, contract_json["abi"]

    T = TypeVar("T")

    @staticmethod
    async def call_function(
        contract: contract, function_name: str, args: tuple, default_returns: T = None
    ) -> T:
        """Call contract function

        :param contract: Contract
        :param function_name: Function name
        :param args: Function args
        :param default_returns: Default return when exception is raised
        :return: Return from function or default return
        """
        _function = getattr(contract.functions, function_name)

        try:
            result = await _function(*args).call()
        except (BadFunctionCallOutput, ContractLogicError) as exc:
            if default_returns is not None:
                return default_returns
            else:
                raise exc

        return result
