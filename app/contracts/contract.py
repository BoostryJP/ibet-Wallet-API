# -*- coding: utf-8 -*-
import json

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

from app import config

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)

class Contract():

    def get_contract(contract_name, address):
        contracts = json.load(open('data/contracts.json' , 'r'))
        contract = web3.eth.contract(
            address = to_checksum_address(address),
            abi = contracts[contract_name]['abi'],
        )
        return contract
