"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""
import os
import configparser

BRAND_NAME = 'ibet-Wallet-API'

####################################################
# Basic settings
####################################################
# Unit test mode
UNIT_TEST_MODE = True if os.environ.get("UNIT_TEST_MODE") == "1" else False

# Blockchain network
NETWORK = os.environ.get("NETWORK") or "IBET"  # IBET or IBETFIN

# Environment-specific settings
APP_ENV = os.environ.get('APP_ENV') or 'local'
if APP_ENV != "live":
    INI_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), f"../conf/{APP_ENV}.ini")
else:
    if NETWORK == "IBET":  # ibet
        INI_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), f"../conf/live.ini")
    else:  # ibet for Fin
        INI_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), f"../conf/live_fin.ini")
CONFIG = configparser.ConfigParser()
CONFIG.read(INI_FILE)

# Issuing companies list
COMPANY_LIST_URL = os.environ.get("COMPANY_LIST_URL")
COMPANY_LIST_LOCAL_MODE = True if os.environ.get("COMPANY_LIST_LOCAL_MODE") == "1" else False
COMPANY_LIST_SLEEP_INTERVAL = int(os.environ.get("COMPANY_LIST_SLEEP_INTERVAL")) if os.environ.get("COMPANY_LIST_SLEEP_INTERVAL") else 3600

####################################################
# Server settings
####################################################
# Worker thread 
WORKER_COUNT = int(os.environ.get("WORKER_COUNT")) if os.environ.get("WORKER_COUNT") else 8

# HTTP request timeout
REQUEST_TIMEOUT = (3.0, 7.5)

# Batch processing interval
BATCH_PROCESS_INTERVAL = int(os.environ.get("SLEEP_INTERVAL")) if os.environ.get("SLEEP_INTERVAL") else 3
NOTIFICATION_PROCESS_INTERVAL = int(os.environ.get("NOTIFICATION_PROCESS_INTERVAL")) if os.environ.get("NOTIFICATION_PROCESS_INTERVAL") else 60

# Database
if UNIT_TEST_MODE:
    DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or 'postgresql://ethuser:ethpass@localhost:5432/ethcache_test'
else:
    DATABASE_URL = os.environ.get("DATABASE_URL") or 'postgresql://ethuser:ethpass@localhost:5432/ethcache'
DB_ECHO = True if CONFIG['database']['echo'] == 'yes' else False

# Logging
LOG_LEVEL = CONFIG['logging']['level']
INFO_LOG_FORMAT = '[%(asctime)s] [%(process)d] [%(levelname)s] {} %(message)s'
DEBUG_LOG_FORMAT = '[%(asctime)s] [%(process)d] [%(levelname)s] {} %(message)s [in %(pathname)s:%(lineno)d]'
LOG_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S %z"

APP_LOGFILE = os.environ.get('APP_LOGFILE') or '/dev/stdout'
ACCESS_LOGFILE = os.environ.get('ACCESS_LOGFILE') or '/dev/stdout'

####################################################
# Blockchain monitoring settings
####################################################
# Block synchronization monitoring interval [sec]
BLOCK_SYNC_STATUS_SLEEP_INTERVAL = int(os.environ.get("BLOCK_SYNC_STATUS_SLEEP_INTERVAL", 3))
# Number of monitoring data period
BLOCK_SYNC_STATUS_CALC_PERIOD = int(os.environ.get("BLOCK_SYNC_STATUS_CALC_PERIOD", 5))
# Threshold for remaining block synchronization
# - Threshold for difference between highestBlock and currentBlock
BLOCK_SYNC_REMAINING_THRESHOLD = int(os.environ.get("BLOCK_SYNC_REMAINING_THRESHOLD", 2))
# Threshold of block generation speed for judging synchronous stop [%]
if APP_ENV == "local":
    BLOCK_GENERATION_SPEED_THRESHOLD = int(os.environ.get("BLOCK_GENERATION_SPEED_THRESHOLD")) \
        if os.environ.get("BLOCK_GENERATION_SPEED_THRESHOLD") else 0
else:
    BLOCK_GENERATION_SPEED_THRESHOLD = int(os.environ.get("BLOCK_GENERATION_SPEED_THRESHOLD")) \
        if os.environ.get("BLOCK_GENERATION_SPEED_THRESHOLD") else 10

####################################################
# Web3 settings
####################################################
# Provider
WEB3_HTTP_PROVIDER = os.environ.get("WEB3_HTTP_PROVIDER") or 'http://localhost:8545'
WEB3_HTTP_PROVIDER_STANDBY = [node.strip() for node in os.environ.get("WEB3_HTTP_PROVIDER_STANDBY").split(",")] if os.environ.get("WEB3_HTTP_PROVIDER_STANDBY") else []

# Chain ID
WEB3_CHAINID = os.environ.get("WEB3_CHAINID") or CONFIG['web3']['chainid']

# Transaction reception wait
TRANSACTION_WAIT_TIMEOUT = int(os.environ.get("TRANSACTION_WAIT_TIMEOUT")) if os.environ.get("TRANSACTION_WAIT_TIMEOUT") else 5
TRANSACTION_WAIT_POLL_LATENCY = float(os.environ.get("TRANSACTION_WAIT_POLL_LATENCY")) if os.environ.get("TRANSACTION_WAIT_POLL_LATENCY") else 0.5

# Fail over settings
WEB3_REQUEST_RETRY_COUNT = int(os.environ.get("WEB3_REQUEST_RETRY_COUNT")) if os.environ.get("WEB3_REQUEST_RETRY_COUNT") else 3
WEB3_REQUEST_WAIT_TIME = int(os.environ.get("WEB3_REQUEST_WAIT_TIME")) if os.environ.get("WEB3_REQUEST_WAIT_TIME") else BLOCK_SYNC_STATUS_SLEEP_INTERVAL  # Same batch interval

####################################################
# Token settings
####################################################
# Default addresses
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# Token
BOND_TOKEN_ENABLED = False if os.environ.get('BOND_TOKEN_ENABLED') == '0' else True
MEMBERSHIP_TOKEN_ENABLED = False if os.environ.get('MEMBERSHIP_TOKEN_ENABLED') == '0' else True
COUPON_TOKEN_ENABLED = False if os.environ.get('COUPON_TOKEN_ENABLED') == '0' else True
SHARE_TOKEN_ENABLED = False if os.environ.get('SHARE_TOKEN_ENABLED') == '0' else True

TOKEN_LIST_CONTRACT_ADDRESS = os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS')
PERSONAL_INFO_CONTRACT_ADDRESS = os.environ.get('PERSONAL_INFO_CONTRACT_ADDRESS')

TOKEN_NOTIFICATION_ENABLED = False if os.environ.get('TOKEN_NOTIFICATION_ENABLED') == '0' else True

# Token Escrow
IBET_ESCROW_CONTRACT_ADDRESS = os.environ.get('IBET_ESCROW_CONTRACT_ADDRESS')
IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = os.environ.get('IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS')

# On-chain Exchange
PAYMENT_GATEWAY_CONTRACT_ADDRESS = os.environ.get('PAYMENT_GATEWAY_CONTRACT_ADDRESS')
IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS')
IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS')

EXCHANGE_NOTIFICATION_ENABLED = False if os.environ.get("EXCHANGE_NOTIFICATION_ENABLED") == "0" else True

# Others
E2E_MESSAGING_CONTRACT_ADDRESS = os.environ.get('E2E_MESSAGING_CONTRACT_ADDRESS')
CONTRACT_REGISTRY_ADDRESS = os.environ.get('CONTRACT_REGISTRY_ADDRESS')

####################################################
# Token cache settings
####################################################
# Enabling token cache
TOKEN_CACHE = False if os.environ.get("TOKEN_CACHE") == "0" else True
# TTL of cache [sec]
TOKEN_CACHE_TTL = int(os.environ.get("TOKEN_CACHE_TTL")) if os.environ.get("TOKEN_CACHE_TTL") else 43200
# Refresh interval [sec]
# NOTE: Default value is 80% of TTL
TOKEN_CACHE_REFRESH_INTERVAL = int(os.environ.get("TOKEN_CACHE_REFRESH_INTERVAL"))\
    if os.environ.get("TOKEN_CACHE_REFRESH_INTERVAL") else 34560
# TTL of short-term cache [sec]
TOKEN_SHORT_TERM_CACHE_TTL = int(os.environ.get("TOKEN_SHORT_TERM_CACHE_TTL"))\
    if os.environ.get("TOKEN_SHORT_TERM_CACHE_TTL") else 40
# Refresh interval of short-term cache [sec]
# NOTE: Default value is 80% of TTL
TOKEN_SHORT_TERM_CACHE_REFRESH_INTERVAL = int(os.environ.get("TOKEN_SHORT_TERM_CACHE_REFRESH_INTERVAL"))\
    if os.environ.get("TOKEN_SHORT_TERM_CACHE_REFRESH_INTERVAL") else 32
# Fetch interval of cache [sec]
# NOTE: Interval allocated for each token information
TOKEN_FETCH_INTERVAL = int(os.environ.get("TOKEN_FETCH_INTERVAL")) \
    if os.environ.get("TOKEN_FETCH_INTERVAL") else 3
# Fetch interval of short-term cache [sec]
# NOTE: Interval allocated for each token information
TOKEN_SHORT_TERM_FETCH_INTERVAL_MSEC = int(os.environ.get("TOKEN_SHORT_TERM_FETCH_INTERVAL_MSEC")) \
    if os.environ.get("TOKEN_SHORT_TERM_FETCH_INTERVAL_MSEC") else 100

####################################################
# Blockchain explorer settings
####################################################
BC_EXPLORER_ENABLED = True if os.environ.get("BC_EXPLORER_ENABLED") == "1" else False

####################################################
# Other settings
####################################################
# Load test
BASIC_AUTH_USER = os.environ.get('BASIC_AUTH_USER')
BASIC_AUTH_PASS = os.environ.get('BASIC_AUTH_PASS')
