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
import sys
import configparser

# 基本設定
BRAND_NAME = 'ibet-Wallet-API'

APP_ENV = os.environ.get('APP_ENV') or 'local'

# コンソーシアム企業リスト設定
NETWORK = os.environ.get("NETWORK") or "IBET"  # IBET or IBETFIN
COMPANY_LIST_URL = os.environ.get("COMPANY_LIST_URL")
COMPANY_LIST_LOCAL_MODE = True if os.environ.get("COMPANY_LIST_LOCAL_MODE") == "1" else False
COMPANY_LIST_SLEEP_INTERVAL = int(os.environ.get("COMPANY_LIST_SLEEP_INTERVAL")) \
    if os.environ.get("COMPANY_LIST_SLEEP_INTERVAL") else 3600

# 環境設定読み込み
UNIT_TEST_MODE = True if os.environ.get("UNIT_TEST_MODE") == "1" else False
if APP_ENV != "live":
    INI_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), f"../conf/{APP_ENV}.ini")
else:
    if NETWORK == "IBET":  # ibet
        INI_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), f"../conf/live.ini")
    else:  # ibet for Fin
        INI_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), f"../conf/live_fin.ini")
CONFIG = configparser.ConfigParser()
CONFIG.read(INI_FILE)

# Web3設定
WEB3_HTTP_PROVIDER = os.environ.get("WEB3_HTTP_PROVIDER") or 'http://localhost:8545'
WEB3_HTTP_PROVIDER_STANDBY = [node.strip() for node in os.environ.get("WEB3_HTTP_PROVIDER_STANDBY").split(",")] \
    if os.environ.get("WEB3_HTTP_PROVIDER_STANDBY") else []
WEB3_CHAINID = os.environ.get("WEB3_CHAINID") or CONFIG['web3']['chainid']
TRANSACTION_WAIT_TIMEOUT = int(os.environ.get("TRANSACTION_WAIT_TIMEOUT")) \
    if os.environ.get("TRANSACTION_WAIT_TIMEOUT") else 120

# サーバ設定
WORKER_COUNT = int(os.environ.get("WORKER_COUNT")) if os.environ.get("WORKER_COUNT") else 8
REQUEST_TIMEOUT = (3.0, 7.5)
SLEEP_INTERVAL = int(os.environ.get("SLEEP_INTERVAL")) if os.environ.get("SLEEP_INTERVAL") else 3

# プロセッサ設定
# ブロック同期状態監視間隔 (秒)
BLOCK_SYNC_STATUS_SLEEP_INTERVAL = int(os.environ.get("BLOCK_SYNC_STATUS_SLEEP_INTERVAL", SLEEP_INTERVAL))
# ブロック同期状態の判定に使用する監視データの数
BLOCK_SYNC_STATUS_CALC_PERIOD = int(os.environ.get("BLOCK_SYNC_STATUS_CALC_PERIOD", 5))
# ブロック同期残のしきい値（block）
# NOTE: highestBlock と currentBlock の差のしきい値
BLOCK_SYNC_REMAINING_THRESHOLD = int(os.environ.get("BLOCK_SYNC_REMAINING_THRESHOLD", 1))
# ブロック同期停止と判断するブロック生成速度のしきい値 (%)
# NOTE: Quorum Validator 4台中1台がクラッシュ障害状態のとき、ブロック生成速度は 20% 〜 35% ぐらいになる
if APP_ENV == "local":
    BLOCK_GENERATION_SPEED_THRESHOLD = int(os.environ.get("BLOCK_GENERATION_SPEED_THRESHOLD")) \
        if os.environ.get("BLOCK_GENERATION_SPEED_THRESHOLD") else 0
else:
    BLOCK_GENERATION_SPEED_THRESHOLD = int(os.environ.get("BLOCK_GENERATION_SPEED_THRESHOLD")) \
        if os.environ.get("BLOCK_GENERATION_SPEED_THRESHOLD") else 10
WEB3_REQUEST_RETRY_COUNT = int(os.environ.get("WEB3_REQUEST_RETRY_COUNT")) if os.environ.get(
    "WEB3_REQUEST_RETRY_COUNT") else 3
WEB3_REQUEST_WAIT_TIME = int(os.environ.get("WEB3_REQUEST_WAIT_TIME")) \
    if os.environ.get("WEB3_REQUEST_WAIT_TIME") else BLOCK_SYNC_STATUS_SLEEP_INTERVAL  # Same batch interval

# データベース設定
if UNIT_TEST_MODE:  # 単体テスト実行時
    DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or 'postgresql://ethuser:ethpass@localhost:5432/ethcache_test'
else:
    DATABASE_URL = os.environ.get("DATABASE_URL") or 'postgresql://ethuser:ethpass@localhost:5432/ethcache'
DB_ECHO = True if CONFIG['database']['echo'] == 'yes' else False

# ログ設定
LOG_LEVEL = CONFIG['logging']['level']

# 取扱トークン種別
BOND_TOKEN_ENABLED = False if os.environ.get('BOND_TOKEN_ENABLED') == '0' else True
MEMBERSHIP_TOKEN_ENABLED = False if os.environ.get('MEMBERSHIP_TOKEN_ENABLED') == '0' else True
COUPON_TOKEN_ENABLED = False if os.environ.get('COUPON_TOKEN_ENABLED') == '0' else True
SHARE_TOKEN_ENABLED = False if os.environ.get('SHARE_TOKEN_ENABLED') == '0' else True

# 各種デフォルトアドレス設定
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
AGENT_ADDRESS = os.environ.get('AGENT_ADDRESS')
IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS')
IBET_CP_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS')
IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS')
IBET_SB_EXCHANGE_CONTRACT_ADDRESS = os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS')
PAYMENT_GATEWAY_CONTRACT_ADDRESS = os.environ.get('PAYMENT_GATEWAY_CONTRACT_ADDRESS')
PERSONAL_INFO_CONTRACT_ADDRESS = os.environ.get('PERSONAL_INFO_CONTRACT_ADDRESS')
TOKEN_LIST_CONTRACT_ADDRESS = os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS')
IBET_ESCROW_CONTRACT_ADDRESS = os.environ.get('IBET_ESCROW_CONTRACT_ADDRESS')
IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = os.environ.get('IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS')
E2E_MESSAGING_CONTRACT_ADDRESS = os.environ.get('E2E_MESSAGING_CONTRACT_ADDRESS')
CONTRACT_REGISTRY_ADDRESS = os.environ.get('CONTRACT_REGISTRY_ADDRESS')

# トークン情報キャッシュの設定
TOKEN_CACHE = False if os.environ.get("TOKEN_CACHE") == "0" else True

# トークン情報キャッシュの有効期限 (秒)
TOKEN_CACHE_TTL = int(os.environ.get("TOKEN_CACHE_TTL")) if os.environ.get("TOKEN_CACHE_TTL") else 43200
# トークン情報キャッシュの更新間隔 (秒)
# NOTE: デフォルト値はTTLの80%
TOKEN_CACHE_REFRESH_INTERVAL = int(os.environ.get("TOKEN_CACHE_REFRESH_INTERVAL"))\
    if os.environ.get("TOKEN_CACHE_REFRESH_INTERVAL") else 34560

# トークン情報短時間キャッシュの有効期限 (秒)
TOKEN_SHORT_TERM_CACHE_TTL = int(os.environ.get("TOKEN_SHORT_TERM_CACHE_TTL"))\
    if os.environ.get("TOKEN_SHORT_TERM_CACHE_TTL") else 40
# トークン情報短時間キャッシュの更新間隔 (秒)
# NOTE: デフォルト値はTTLの80%
TOKEN_SHORT_TERM_CACHE_REFRESH_INTERVAL = int(os.environ.get("TOKEN_SHORT_TERM_CACHE_REFRESH_INTERVAL"))\
    if os.environ.get("TOKEN_SHORT_TERM_CACHE_REFRESH_INTERVAL") else 32

# トークン情報キャッシュの取得間隔 (秒)
# NOTE: トークン情報1件あたりに割り当てる間隔
TOKEN_FETCH_INTERVAL = int(os.environ.get("TOKEN_FETCH_INTERVAL")) \
    if os.environ.get("TOKEN_FETCH_INTERVAL") else 3
# トークン情報短時間キャッシュの取得間隔 (ミリ秒)
# NOTE: トークン情報1件あたりに割り当てる間隔
TOKEN_SHORT_TERM_FETCH_INTERVAL_MSEC = int(os.environ.get("TOKEN_SHORT_TERM_FETCH_INTERVAL_MSEC")) \
    if os.environ.get("TOKEN_SHORT_TERM_FETCH_INTERVAL_MSEC") else 100


# テスト用設定：Locust
BASIC_AUTH_USER = os.environ.get('BASIC_AUTH_USER')
BASIC_AUTH_PASS = os.environ.get('BASIC_AUTH_PASS')

# トークン関連通知
TOKEN_NOTIFICATION_ENABLED = False if os.environ.get('TOKEN_NOTIFICATION_ENABLED') == '0' else True
