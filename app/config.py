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
DATABASE_URL = os.environ.get("DATABASE_URL") or 'postgresql://ethuser:ethpass@localhost:5432/ethcache'

DB_ECHO = True if CONFIG['database']['echo'] == 'yes' else False
DB_AUTOCOMMIT = True

LOG_LEVEL = CONFIG['logging']['level']

WEB3_HTTP_PROVIDER = os.environ.get("WEB3_HTTP_PROVIDER") or 'http://localhost:8545'
WEB3_CHAINID = os.environ.get("WEB3_CHAINID") or CONFIG['web3']['chainid']

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

OMISE_SECRET = os.environ.get('OMISE_SECRET')
OMISE_PUBLIC = os.environ.get('OMISE_PUBLIC')

STRIPE_SECRET = os.environ.get('STRIPE_SECRET')
STRIPE_FEE = os.environ.get('STRIPE_FEE')

SNS_APPLICATION_ARN_IOS = os.environ.get('SNS_APPLICATION_ARN_IOS')
SNS_APPLICATION_ARN_ANDROID = os.environ.get('SNS_APPLICATION_ARN_ANDROID')
PUSH_PRIORITY = os.environ.get('PUSH_PRIORITY') or 0

AGENT_SQS_URL = os.environ.get('AGENT_SQS_URL') or 'http://localhost:9324'
AGENT_SQS_QUEUE_NAME = os.environ.get('AGENT_SQS_QUEUE_NAME') or 'charge_message'

REQUEST_TIMEOUT = (3.0, 7.5)

# Contracts Address
IBET_SB_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS')
IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS')
IBET_CP_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS')
IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS')

# Contracts Name
IBET_SB_EXCHANGE_CONTRACT_NAME = os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS')
IBET_COUPON_EXCHANGE_CONTRACT_NAME = os.environ.get('IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS')
IBET_CP_EXCHANGE_CONTRACT_NAME = os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS')
IBET_MEMBERSHIP_EXCHANGE_CONTRACT_NAME = os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS')

IBET_SB_EXCHANGE_CONTRACT_NAME = "IbetStraightBondExchange"
IBET_COUPON_EXCHANGE_CONTRACT_NAME = "IbetMembershipExchange"
IBET_MEMBERSHIP_EXCHANGE_CONTRACT_NAME = "IbetCouponExchange"
