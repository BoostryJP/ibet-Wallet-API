# -*- coding: utf-8 -*-

import os
import configparser

BRAND_NAME = 'TMR-API'

APP_ENV = os.environ.get('APP_ENV') or 'local'
INI_FILE = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '../conf/{}.ini'.format(APP_ENV))

CONFIG = configparser.ConfigParser()
CONFIG.read(INI_FILE)
POSTGRES = CONFIG['postgres']
DB_CONFIG = (POSTGRES['user'], POSTGRES['password'], POSTGRES['host'], POSTGRES['database'])
DATABASE_URL = "postgresql+psycopg2://%s:%s@%s/%s" % DB_CONFIG

DB_ECHO = True if CONFIG['database']['echo'] == 'yes' else False
DB_AUTOCOMMIT = True

LOG_LEVEL = CONFIG['logging']['level']

WEB3_HTTP_PROVIDER = CONFIG['web3']['HTTPProvider']
WEB3_CHAINID = CONFIG['web3']['chainid']

# WhiteList-Contract
WHITE_LIST_CONTRACT_ABI = '[{"constant": true,"inputs": [{"name": "","type": "address"},{"name": "","type": "address"}],"name": "payment_accounts","outputs": [{"name": "account_address","type": "address"},{"name": "agent_address","type": "address"},{"name": "encrypted_info","type": "string"},{"name": "approval_status","type": "uint8"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": false,"inputs": [{"name": "_agent_address","type": "address"},{"name": "_encrypted_info","type": "string"}],"name": "register","outputs": [{"name": "","type": "bool"}],"payable": false,"stateMutability": "nonpayable","type": "function"},{"constant": false,"inputs": [{"name": "_agent_address","type": "address"},{"name": "_encrypted_info","type": "string"}],"name": "changeInfo","outputs": [{"name": "","type": "bool"}],"payable": false,"stateMutability": "nonpayable","type": "function"},{"constant": true,"inputs": [{"name": "_account_address","type": "address"},{"name": "_agent_address","type": "address"}],"name": "isRegistered","outputs": [{"name": "","type": "bool"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": false,"inputs": [{"name": "_account_address","type": "address"}],"name": "approve","outputs": [{"name": "","type": "bool"}],"payable": false,"stateMutability": "nonpayable","type": "function"},{"constant": false,"inputs": [{"name": "_account_address","type": "address"}],"name": "warn","outputs": [{"name": "","type": "bool"}],"payable": false,"stateMutability": "nonpayable","type": "function"},{"constant": false,"inputs": [{"name": "_account_address","type": "address"}],"name": "unapprove","outputs": [{"name": "","type": "bool"}],"payable": false,"stateMutability": "nonpayable","type": "function"},{"inputs": [],"payable": false,"stateMutability": "nonpayable","type": "constructor"},{"anonymous": false,"inputs": [{"indexed": true,"name": "account_address","type": "address"},{"indexed": true,"name": "agent_address","type": "address"}],"name": "Register","type": "event"},{"anonymous": false,"inputs": [{"indexed": true,"name": "account_address","type": "address"},{"indexed": true,"name": "agent_address","type": "address"}],"name": "ChangeInfo","type": "event"},{"anonymous": false,"inputs": [{"indexed": true,"name": "account_address","type": "address"},{"indexed": true,"name": "agent_address","type": "address"}],"name": "Approve","type": "event"},{"anonymous": false,"inputs": [{"indexed": true,"name": "account_address","type": "address"},{"indexed": true,"name": "agent_address","type": "address"}],"name": "Warn","type": "event"},{"anonymous": false,"inputs": [{"indexed": true,"name": "account_address","type": "address"},{"indexed": true,"name": "agent_address","type": "address"}],"name": "Unapprove","type": "event"}]'

# PersonalInfo-Contract
PERSONAL_INFO_CONTRACT_ABI = '[{"constant": true,"inputs": [{"name": "","type": "address"},{"name": "","type": "address"}],"name": "personal_info","outputs": [{"name": "account_address","type": "address"},{"name": "issuer_address","type": "address"},{"name": "encrypted_info","type": "string"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": false,"inputs": [{"name": "_issuer_address","type": "address"},{"name": "_encrypted_info","type": "string"}],"name": "register","outputs": [{"name": "","type": "bool"}],"payable": false,"stateMutability": "nonpayable","type": "function"},{"constant": true,"inputs": [{"name": "_account_address","type": "address"},{"name": "_issuer_address","type": "address"}],"name": "isRegistered","outputs": [{"name": "","type": "bool"}],"payable": false,"stateMutability": "view","type": "function"},{"inputs": [],"payable": false,"stateMutability": "nonpayable","type": "constructor"},{"anonymous": false,"inputs": [{"indexed": true,"name": "account_address","type": "address"},{"indexed": true,"name": "issuer_address","type": "address"}],"name": "Register","type": "event"}]'

# IbetExchange-Contract
IBET_EXCHANGE_CONTRACT_ABI = '[{"constant": true,"inputs": [],"name": "whiteListAddress","outputs": [{"name": "","type": "address"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [],"name": "personalInfoAddress","outputs": [{"name": "","type": "address"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [],"name": "owner","outputs": [{"name": "","type": "address"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [{"name": "","type": "uint256"}],"name": "orderBook","outputs": [{"name": "owner","type": "address"},{"name": "token","type": "address"},{"name": "amount","type": "uint256"},{"name": "price","type": "uint256"},{"name": "isBuy","type": "bool"},{"name": "agent","type": "address"},{"name": "canceled","type": "bool"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [],"name": "latestOrderId","outputs": [{"name": "","type": "uint256"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [{"name": "","type": "uint256"}],"name": "latestAgreementIds","outputs": [{"name": "","type": "uint256"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [{"name": "","type": "address"}],"name": "lastPrice","outputs": [{"name": "","type": "uint256"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [{"name": "","type": "address"},{"name": "","type": "address"}],"name": "commitments","outputs": [{"name": "","type": "uint256"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [{"name": "","type": "address"},{"name": "","type": "address"}],"name": "balances","outputs": [{"name": "","type": "uint256"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [{"name": "","type": "uint256"},{"name": "","type": "uint256"}],"name": "agreements","outputs": [{"name": "counterpart","type": "address"},{"name": "amount","type": "uint256"},{"name": "price","type": "uint256"},{"name": "canceled","type": "bool"},{"name": "paid","type": "bool"}],"payable": false,"stateMutability": "view","type": "function"},{"inputs": [{"name": "_whiteListAddress","type": "address"},{"name": "_personalInfoAddress","type": "address"}],"payable": false,"stateMutability": "nonpayable","type": "constructor"},{"anonymous": false,"inputs": [{"indexed": true,"name": "tokenAddress","type": "address"},{"indexed": false,"name": "orderId","type": "uint256"},{"indexed": false,"name": "agreementId","type": "uint256"},{"indexed": true,"name": "buyAddress","type": "address"},{"indexed": true,"name": "sellAddress","type": "address"},{"indexed": false,"name": "price","type": "uint256"},{"indexed": false,"name": "amount","type": "uint256"},{"indexed": false,"name": "agentAddress","type": "address"}],"name": "Agree","type": "event"},{"anonymous": false,"inputs": [{"indexed": true,"name": "tokenAddress","type": "address"},{"indexed": false,"name": "orderId","type": "uint256"},{"indexed": true,"name": "accountAddress","type": "address"},{"indexed": true,"name": "isBuy","type": "bool"},{"indexed": false,"name": "price","type": "uint256"},{"indexed": false,"name": "amount","type": "uint256"},{"indexed": false,"name": "agentAddress","type": "address"}],"name": "CancelOrder","type": "event"},{"anonymous": false,"inputs": [{"indexed": true,"name": "tokenAddress","type": "address"},{"indexed": false,"name": "orderId","type": "uint256"},{"indexed": true,"name": "accountAddress","type": "address"},{"indexed": true,"name": "isBuy","type": "bool"},{"indexed": false,"name": "price","type": "uint256"},{"indexed": false,"name": "amount","type": "uint256"},{"indexed": false,"name": "agentAddress","type": "address"}],"name": "NewOrder","type": "event"},{"anonymous": false,"inputs": [{"indexed": true,"name": "previousOwner","type": "address"},{"indexed": true,"name": "newOwner","type": "address"}],"name": "OwnershipTransferred","type": "event"},{"anonymous": false,"inputs": [{"indexed": true,"name": "tokenAddress","type": "address"},{"indexed": false,"name": "orderId","type": "uint256"},{"indexed": false,"name": "agreementId","type": "uint256"},{"indexed": true,"name": "buyAddress","type": "address"},{"indexed": true,"name": "sellAddress","type": "address"},{"indexed": false,"name": "price","type": "uint256"},{"indexed": false,"name": "amount","type": "uint256"},{"indexed": false,"name": "agentAddress","type": "address"}],"name": "SettlementNG","type": "event"},{"anonymous": false,"inputs": [{"indexed": true,"name": "tokenAddress","type": "address"},{"indexed": false,"name": "orderId","type": "uint256"},{"indexed": false,"name": "agreementId","type": "uint256"},{"indexed": true,"name": "buyAddress","type": "address"},{"indexed": true,"name": "sellAddress","type": "address"},{"indexed": false,"name": "price","type": "uint256"},{"indexed": false,"name": "amount","type": "uint256"},{"indexed": false,"name": "agentAddress","type": "address"}],"name": "SettlementOK","type": "event"},{"anonymous": false,"inputs": [{"indexed": true,"name": "tokenAddress","type": "address"},{"indexed": true,"name": "accountAddress","type": "address"}],"name": "Withdrawal","type": "event"},{"constant": false,"inputs": [{"name": "_orderId","type": "uint256"},{"name": "_agreementId","type": "uint256"}],"name": "cancelAgreement","outputs": [{"name": "","type": "bool"}],"payable": false,"stateMutability": "nonpayable","type": "function"},{"constant": false,"inputs": [{"name": "_orderId","type": "uint256"}],"name": "cancelOrder","outputs": [{"name": "","type": "bool"}],"payable": false,"stateMutability": "nonpayable","type": "function"},{"constant": false,"inputs": [{"name": "_orderId","type": "uint256"},{"name": "_agreementId","type": "uint256"}],"name": "confirmAgreement","outputs": [{"name": "","type": "bool"}],"payable": false,"stateMutability": "nonpayable","type": "function"},{"constant": false,"inputs": [{"name": "_token","type": "address"},{"name": "_amount","type": "uint256"},{"name": "_price","type": "uint256"},{"name": "_isBuy","type": "bool"},{"name": "_agent","type": "address"}],"name": "createOrder","outputs": [{"name": "","type": "bool"}],"payable": false,"stateMutability": "nonpayable","type": "function"},{"constant": false,"inputs": [{"name": "_orderId","type": "uint256"},{"name": "_amount","type": "uint256"},{"name": "_isBuy","type": "bool"}],"name": "executeOrder","outputs": [{"name": "","type": "bool"}],"payable": false,"stateMutability": "nonpayable","type": "function"},{"constant": false,"inputs": [{"name": "_from","type": "address"},{"name": "_value","type": "uint256"},{"name": "","type": "bytes"}],"name": "tokenFallback","outputs": [],"payable": false,"stateMutability": "nonpayable","type": "function"},{"constant": false,"inputs": [{"name": "newOwner","type": "address"}],"name": "transferOwnership","outputs": [],"payable": false,"stateMutability": "nonpayable","type": "function"},{"constant": false,"inputs": [{"name": "_token","type": "address"}],"name": "withdrawAll","outputs": [{"name": "","type": "bool"}],"payable": false,"stateMutability": "nonpayable","type": "function"}]'

# TokenList-Contract
TOKEN_LIST_CONTRACT_ABI = '[{"constant": false,"inputs": [{"name": "_token_address","type": "address"},{"name": "_token_template","type": "string"}],"name": "register","outputs": [],"payable": false,"stateMutability": "nonpayable","type": "function"},{"constant": true,"inputs": [{"name": "_num","type": "uint256"}],"name": "getTokenByNum","outputs": [{"name": "token_address","type": "address"},{"name": "token_template","type": "string"},{"name": "owner_address","type": "address"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [{"name": "_token_address","type": "address"}],"name": "getOwnerAddress","outputs": [{"name": "issuer_address","type": "address"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [{"name": "_token_address","type": "address"}],"name": "getTokenByAddress","outputs": [{"name": "token_address","type": "address"},{"name": "token_template","type": "string"},{"name": "owner_address","type": "address"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [],"name": "getListLength","outputs": [{"name": "length","type": "uint256"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": false,"inputs": [{"name": "_token_address","type": "address"},{"name": "_new_owner_address","type": "address"}],"name": "changeOwner","outputs": [],"payable": false,"stateMutability": "nonpayable","type": "function"}]'

# Company List
COMPANY_LIST_URL = 'https://s3-ap-northeast-1.amazonaws.com/ibet-company-list-dev/company_list.json'
