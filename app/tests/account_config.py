# -*- coding: utf-8 -*-
from web3 import Web3
from app import config

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))

# Account Address
eth_account = {
    'deployer': {
        'account_address': web3.eth.accounts[0],
        'password': 'password'
    },
    'issuer': {
        'account_address': web3.eth.accounts[1],
        'password': 'password'
    },
    'agent': {
        'account_address': web3.eth.accounts[2],
        'password': 'password'
    },
    'trader': {
        'account_address': web3.eth.accounts[3],
        'password': 'password'
    }
}
