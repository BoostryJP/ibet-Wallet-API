# -*- coding: utf-8 -*-
from web3 import Web3
from app import config

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))

# Account Address
eth_account = {
    'deployer': {
        'account_address': web3.eth.accounts[0],
        'password': 'password',
        'private_key': '0xe84d353a17e7ddd3b215680d9f4e138f6b6122da70d2efb04a02b4f34427b67c'
    },
    'issuer': {
        'account_address': web3.eth.accounts[1],
        'password': 'password',
        'private_key': '76b717de274a8e817fad15f0365e7ebae828093d8f0a47d61ade0577287060dc'
    },
    'agent': {
        'account_address': web3.eth.accounts[2],
        'password': 'password',
        'private_key': '0x60192eced69f75646af000d21d8ab92e056b890b1de01da04b29e77d27b23730'
    },
    'trader': {
        'account_address': web3.eth.accounts[3],
        'password': 'password',
        'private_key': '0x700e3d5daa3378e5a15ac7b86605ddd7ea34866d3415ac41c9ee4a10545feba3'
    }
}
