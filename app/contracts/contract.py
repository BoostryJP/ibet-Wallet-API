# -*- coding: utf-8 -*-
import json

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

from app import config

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


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
            contract_json = json.load(open(contract_file, 'r'))
            Contract.cache[contract_name] = contract_json

        contract = web3.eth.contract(
            abi=contract_json['abi'],
            bytecode=contract_json['bytecode'],
            bytecode_runtime=contract_json['deployedBytecode'],
        )

        tx_hash = contract.deploy(
            transaction={'from': deployer, 'gas': 6000000},
            args=args
        ).hex()

        tx = web3.eth.waitForTransactionReceipt(tx_hash)

        contract_address = ''
        if tx is not None:
            # ブロックの状態を確認して、コントラクトアドレスが登録されているかを確認する。
            if 'contractAddress' in tx.keys():
                contract_address = tx['contractAddress']

        return contract_address, contract_json['abi']
