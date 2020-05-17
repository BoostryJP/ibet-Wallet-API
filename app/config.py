# -*- coding: utf-8 -*-

import os
import configparser

# basic setting
BRAND_NAME = 'ibet-Wallet-API'

APP_ENV = os.environ.get('APP_ENV') or 'local'
INI_FILE = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '../conf/{}.ini'.format(APP_ENV))
CONFIG = configparser.ConfigParser()
CONFIG.read(INI_FILE)
DATABASE_URL = os.environ.get("DATABASE_URL") or 'postgresql://ethuser:ethpass@localhost:5432/ethcache'

DB_ECHO = True if CONFIG['database']['echo'] == 'yes' else False
DB_AUTOCOMMIT = True

LOG_LEVEL = CONFIG['logging']['level']

WEB3_HTTP_PROVIDER = os.environ.get("WEB3_HTTP_PROVIDER") or 'http://localhost:8545'
WEB3_CHAINID = os.environ.get("WEB3_CHAINID") or CONFIG['web3']['chainid']
WORKER_COUNT = int(os.environ.get("WORKER_COUNT")) if os.environ.get("WORKER_COUNT") else 8
SLEEP_INTERVAL = int(os.environ.get("SLEEP_INTERVAL")) if os.environ.get("SLEEP_INTERVAL") else 3

BASIC_AUTH_USER = os.environ.get('BASIC_AUTH_USER')
BASIC_AUTH_PASS = os.environ.get('BASIC_AUTH_PASS')

REQUEST_TIMEOUT = (3.0, 7.5)

# enable token type
BOND_TOKEN_ENABLED = False if os.environ.get('BOND_TOKEN_ENABLED') == '0' else True
MEMBERSHIP_TOKEN_ENABLED = False if os.environ.get('MEMBERSHIP_TOKEN_ENABLED') == '0' else True
COUPON_TOKEN_ENABLED = False if os.environ.get('COUPON_TOKEN_ENABLED') == '0' else True
SHARE_TOKEN_ENABLED = False if os.environ.get('SHARE_TOKEN_ENABLED') == '0' else True

# addresses
AGENT_ADDRESS = os.environ.get('AGENT_ADDRESS')
IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS')
IBET_CP_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS')
IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS')
IBET_SB_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS')
PAYMENT_GATEWAY_CONTRACT_ADDRESS = os.environ.get('PAYMENT_GATEWAY_CONTRACT_ADDRESS')
PERSONAL_INFO_CONTRACT_ADDRESS = os.environ.get('PERSONAL_INFO_CONTRACT_ADDRESS')
TOKEN_LIST_CONTRACT_ADDRESS = os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS')

# Issuer List
if APP_ENV == 'live':
    COMPANY_LIST_URL = 'https://s3-ap-northeast-1.amazonaws.com/ibet-company-list/company_list.json'
else:
    COMPANY_LIST_URL = 'https://s3-ap-northeast-1.amazonaws.com/ibet-company-list-dev/company_list.json'

# Payment Agent List
if APP_ENV == 'live':
    PAYMENT_AGENT_LIST_URL = 'https://s3-ap-northeast-1.amazonaws.com/ibet-company-list/payment_agent_list.json'
else:
    PAYMENT_AGENT_LIST_URL = 'https://s3-ap-northeast-1.amazonaws.com/ibet-company-list-dev/payment_agent_list.json'
