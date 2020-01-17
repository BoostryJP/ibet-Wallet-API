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
DEPOSITARY_RECEIPT_TOKEN_ENABLED = False if os.environ.get('DEPOSITARY_RECEIPT_TOKEN_ENABLED') == '0' else True

# addresses
AGENT_ADDRESS = os.environ.get('AGENT_ADDRESS')
IBET_CP_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS')
IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS')
IBET_SB_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS')
PAYMENT_GATEWAY_CONTRACT_ADDRESS = os.environ.get('PAYMENT_GATEWAY_CONTRACT_ADDRESS')
PERSONAL_INFO_CONTRACT_ADDRESS = os.environ.get('PERSONAL_INFO_CONTRACT_ADDRESS')
TOKEN_LIST_CONTRACT_ADDRESS = os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS')

# version setting
TMRAPP_REQUIRED_VERSION_IOS = os.environ.get('TMRAPP_REQUIRED_VERSION_IOS')
TMRAPP_FORCE_UPDATE_IOS = os.environ.get('TMRAPP_FORCE_UPDATE_IOS')
TMRAPP_UPDATE_URL_SCHEME_IOS = os.environ.get('TMRAPP_UPDATE_URL_SCHEME_IOS')
TMRAPP_UPDATE_URL_IOS = os.environ.get('TMRAPP_UPDATE_URL_IOS')
TMRAPP_REQUIRED_VERSION_ANDROID = os.environ.get('TMRAPP_REQUIRED_VERSION_ANDROID')
TMRAPP_FORCE_UPDATE_ANDROID = os.environ.get('TMRAPP_FORCE_UPDATE_ANDROID')
TMRAPP_UPDATE_URL_SCHEME_ANDROID = os.environ.get('TMRAPP_UPDATE_URL_SCHEME_ANDROID')
TMRAPP_UPDATE_URL_ANDROID = os.environ.get('TMRAPP_UPDATE_URL_ANDROID')

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

# stripe setting
STRIPE_SECRET = os.environ.get('STRIPE_SECRET')
STRIPE_FEE = float(os.environ.get("STRIPE_FEE")) if os.environ.get("STRIPE_FEE") else 0.1
STRIPE_MINIMUM_VALUE = int(os.environ.get("STRIPE_MINIMUM_VALUE")) if os.environ.get("STRIPE_MINIMUM_VALUE") else 50
STRIPE_MAXIMUM_VALUE = int(os.environ.get("STRIPE_MAXIMUM_VALUE")) if os.environ.get("STRIPE_MAXIMUM_VALUE") else 500000
STRIPE_PAYOUT_SCHEDULE_DELAY = int(os.environ.get("STRIPE_PAYOUT_SCHEDULE_DELAY")) if os.environ.get("STRIPE_PAYOUT_SCHEDULE_DELAY") else 18
STRIPE_PAYOUT_SCHEDULE_ANCHOR = int(os.environ.get("STRIPE_PAYOUT_SCHEDULE_ANCHOR")) if os.environ.get("STRIPE_PAYOUT_SCHEDULE_ANCHOR") else 28

# push notification setting
SNS_APPLICATION_ARN_IOS = os.environ.get('SNS_APPLICATION_ARN_IOS')
SNS_APPLICATION_ARN_ANDROID = os.environ.get('SNS_APPLICATION_ARN_ANDROID')
PUSH_PRIORITY = int(os.environ.get("PUSH_PRIORITY")) if os.environ.get("PUSH_PRIORITY") else 0

AGENT_SQS_URL = os.environ.get('AGENT_SQS_URL') or 'http://localhost:9324'
AGENT_SQS_QUEUE_NAME = os.environ.get('AGENT_SQS_QUEUE_NAME') or 'charge_message'


