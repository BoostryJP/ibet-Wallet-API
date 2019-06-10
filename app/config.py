# -*- coding: utf-8 -*-

import os
import configparser

# basic setting
BRAND_NAME = 'TMR-API'

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
WORKER_COUNT = os.environ.get("WORKER_COUNT") or 8
SLEEP_INTERVAL = os.environ.get("SLEEP_INTERVAL") or 3

BASIC_AUTH_USER = os.environ.get('BASIC_AUTH_USER')
BASIC_AUTH_PASS = os.environ.get('BASIC_AUTH_PASS')

REQUEST_TIMEOUT = (3.0, 7.5)

# addresses
AGENT_ADDRESS = os.environ.get('AGENT_ADDRESS')
IBET_CP_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS')
IBET_JDR_SWAP_CONTRACT_ADDRESS = os.environ.get('IBET_JDR_SWAP_CONTRACT_ADDRESS')
IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS')
IBET_MRF_TOKEN_ADDRESS = os.environ.get('IBET_MRF_TOKEN_ADDRESS')
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

# omise setting
OMISE_SECRET = os.environ.get('OMISE_SECRET')
OMISE_PUBLIC = os.environ.get('OMISE_PUBLIC')

# stripe setting
STRIPE_SECRET = os.environ.get('STRIPE_SECRET')
STRIPE_FEE = os.environ.get('STRIPE_FEE')

# push notification setting
SNS_APPLICATION_ARN_IOS = os.environ.get('SNS_APPLICATION_ARN_IOS')
SNS_APPLICATION_ARN_ANDROID = os.environ.get('SNS_APPLICATION_ARN_ANDROID')
PUSH_PRIORITY = os.environ.get('PUSH_PRIORITY') or 0

AGENT_SQS_URL = os.environ.get('AGENT_SQS_URL') or 'http://localhost:9324'
AGENT_SQS_QUEUE_NAME = os.environ.get('AGENT_SQS_QUEUE_NAME') or 'charge_message'


