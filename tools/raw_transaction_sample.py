# -*- coding: utf-8 -*-
import os
import sys
path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from web3 import Web3
from web3.middleware import geth_poa_middleware
from rlp import decode
from rlp.sedes import binary
from eth_utils import to_checksum_address

from app import config

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

to_address = '0x08fed8aa9c22ca593dc0fb251e5d8329018854cc'

transaction = {
    'to': to_checksum_address(to_address),
    'value': 1000000000,
    'gas': 2000000,
    'gasPrice': 234567897654321,
    'nonce': 10000,
    'chainId': 0
}

# 秘密鍵
key = '0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318'
signed = web3.eth.account.sign_transaction(transaction, key)
print(signed)

raw_transaction = decode(signed.rawTransaction)
print(to_checksum_address("0x" + raw_transaction[3].hex()))
