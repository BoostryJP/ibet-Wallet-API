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

from web3 import Web3
from app import config

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))

# Account Address
worker_id = os.environ.get("PYTEST_XDIST_WORKER")
if worker_id is not None:
    worker_n = 1 + int(worker_id.split("gw")[1])
    offset = 6 * worker_n
else:
    offset = 0

eth_account = {
    "deployer": web3.eth.accounts[0+offset],
    "issuer": web3.eth.accounts[1+offset],
    "agent": web3.eth.accounts[2+offset],
    "trader": web3.eth.accounts[3+offset],
    "user1": web3.eth.accounts[4+offset],
    "user2": web3.eth.accounts[5+offset]
}
