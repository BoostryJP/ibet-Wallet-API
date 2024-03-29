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

from web3 import Web3

from app import config

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))

# Account Address
eth_account = {
    "deployer": {"account_address": web3.eth.accounts[0], "password": "password"},
    "issuer": {"account_address": web3.eth.accounts[1], "password": "password"},
    "agent": {"account_address": web3.eth.accounts[2], "password": "password"},
    "trader": {"account_address": web3.eth.accounts[3], "password": "password"},
    "user1": {"account_address": web3.eth.accounts[4], "password": "password"},
    "user2": {"account_address": web3.eth.accounts[5], "password": "password"},
}
