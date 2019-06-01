# -*- coding: utf-8 -*-
import json
import time

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

from app import config

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)

class Contract:

    def get_contract(contract_name, address):
        contracts = json.load(open('data/contracts.json', 'r'))
        contract = web3.eth.contract(
            address=to_checksum_address(address),
            abi=contracts[contract_name]['abi'],
        )
        return contract

    def deploy_contract(contract_name, args, deployer):
        contracts = json.load(open('data/contracts.json', 'r'))
        contract = web3.eth.contract(
            abi=contracts[contract_name]['abi'],
            bytecode=contracts[contract_name]['bytecode'],
            bytecode_runtime=contracts[contract_name]['bytecode_runtime'],
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

        return contract_address, contracts[contract_name]['abi']
