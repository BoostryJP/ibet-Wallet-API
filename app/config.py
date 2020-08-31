# -*- coding: utf-8 -*-
import os
import sys
import configparser

# Basic Settings
BRAND_NAME = 'ibet-Wallet-API'

APP_ENV = os.environ.get('APP_ENV') or 'local'
INI_FILE = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    '../conf/{}.ini'.format(APP_ENV)
)
CONFIG = configparser.ConfigParser()
CONFIG.read(INI_FILE)

WEB3_HTTP_PROVIDER = os.environ.get("WEB3_HTTP_PROVIDER") or 'http://localhost:8545'
WEB3_CHAINID = os.environ.get("WEB3_CHAINID") or CONFIG['web3']['chainid']

WORKER_COUNT = int(os.environ.get("WORKER_COUNT")) if os.environ.get("WORKER_COUNT") else 8
SLEEP_INTERVAL = int(os.environ.get("SLEEP_INTERVAL")) if os.environ.get("SLEEP_INTERVAL") else 3

BASIC_AUTH_USER = os.environ.get('BASIC_AUTH_USER')
BASIC_AUTH_PASS = os.environ.get('BASIC_AUTH_PASS')

REQUEST_TIMEOUT = (3.0, 7.5)

# Database Settings
if 'pytest' in sys.modules:
    # pytest実行時用DB
    DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or 'postgresql://ethuser:ethpass@localhost:5432/ethcache_test'
else:
    DATABASE_URL = os.environ.get("DATABASE_URL") or 'postgresql://ethuser:ethpass@localhost:5432/ethcache'

DB_ECHO = True if CONFIG['database']['echo'] == 'yes' else False
DB_AUTOCOMMIT = True

# Log Settings
LOG_LEVEL = CONFIG['logging']['level']

# Token Type
BOND_TOKEN_ENABLED = False if os.environ.get('BOND_TOKEN_ENABLED') == '0' else True
MEMBERSHIP_TOKEN_ENABLED = False if os.environ.get('MEMBERSHIP_TOKEN_ENABLED') == '0' else True
COUPON_TOKEN_ENABLED = False if os.environ.get('COUPON_TOKEN_ENABLED') == '0' else True
SHARE_TOKEN_ENABLED = False if os.environ.get('SHARE_TOKEN_ENABLED') == '0' else True

# Default Addresses
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
AGENT_ADDRESS = os.environ.get('AGENT_ADDRESS')
IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS')
IBET_CP_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS')
IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS')
IBET_SB_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS')
PAYMENT_GATEWAY_CONTRACT_ADDRESS = os.environ.get('PAYMENT_GATEWAY_CONTRACT_ADDRESS')
PERSONAL_INFO_CONTRACT_ADDRESS = os.environ.get('PERSONAL_INFO_CONTRACT_ADDRESS')
TOKEN_LIST_CONTRACT_ADDRESS = os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS')

# Consortium Company List
NETWORK = os.environ.get("NETWORK") or "IBET"  # IBET or IBETFIN
if NETWORK == "IBET":
    if APP_ENV == 'live':
        COMPANY_LIST_URL = 'https://s3-ap-northeast-1.amazonaws.com/ibet-company-list/company_list.json'
    else:
        COMPANY_LIST_URL = 'https://s3-ap-northeast-1.amazonaws.com/ibet-company-list-dev/company_list.json'
elif NETWORK == "IBETFIN":
    if APP_ENV == 'live':
        COMPANY_LIST_URL = 'https://s3-ap-northeast-1.amazonaws.com/ibet-fin-company-list/company_list.json'
    else:
        COMPANY_LIST_URL = 'https://s3-ap-northeast-1.amazonaws.com/ibet-fin-company-list-dev/company_list.json'
