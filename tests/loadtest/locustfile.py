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

from __future__ import absolute_import, unicode_literals

import json
from typing import Any

from eth_utils.address import to_checksum_address
from eth_utils.conversions import to_hex
from locust import HttpLocust, TaskSet, task
from web3 import Web3
from web3.auto import w3 as auto_w3

from app import config

# テスト用のアカウント
private_key = "0000000000000000000000000000000000000000000000000000000000000001"
eth_address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

# コントラクト情報
personal_info_json = json.load(open("../../app/contracts/json/PersonalInfo.json", "r"))
personal_info_contract_address_raw = config.PERSONAL_INFO_CONTRACT_ADDRESS
assert personal_info_contract_address_raw is not None
personalinfo_contract_address = to_checksum_address(personal_info_contract_address_raw)
personalinfo_contract_abi = personal_info_json["abi"]

# Basic認証
basic_auth_user = config.BASIC_AUTH_USER
basic_auth_pass = config.BASIC_AUTH_PASS
w3: Web3 = auto_w3


class LoadTestTaskSet(TaskSet):
    def on_start(self):
        self.client.get("/", auth=(basic_auth_user, basic_auth_pass), verify=False)

    def get_tx_info(self, eth_address: str) -> tuple[int, int]:
        response = self.client.get(
            "/Eth/TransactionCount/" + eth_address,
            auth=(basic_auth_user, basic_auth_pass),
            verify=False,
        )
        response_json: dict[str, Any] = json.loads(
            response.content.decode("utf8").replace("'", '"')
        )

        nonce = int(response_json["data"]["nonce"])
        gas_price = int(response_json["data"]["gasprice"])

        return nonce, gas_price

    @task
    def eth_sendrawtransaction(self):
        contract = w3.eth.contract(
            address=personalinfo_contract_address,
            abi=personalinfo_contract_abi,
        )

        nonce, gas_price = LoadTestTaskSet.get_tx_info(self, eth_address)

        txn = contract.functions.register(eth_address, "").build_transaction(
            {
                "chainId": 2017,
                "gas": 4000000,
                "gasPrice": gas_price,
                "nonce": nonce,
            }
        )

        signed_txn = w3.eth.account.sign_transaction(txn, private_key=private_key)

        raw_tx_hex_list = [to_hex(signed_txn.raw_transaction)]

        payload = {"raw_tx_hex_list": raw_tx_hex_list}
        headers = {"content-type": "application/json"}
        response = self.client.post(
            "/Eth/SendRawTransaction",
            headers=headers,
            auth=(basic_auth_user, basic_auth_pass),
            data=json.dumps(payload),
            verify=False,
        )
        print(response.content)


class Website(HttpLocust):
    task_set = LoadTestTaskSet

    # task実行の最短待ち時間
    min_wait = 1000
    # task実行の最大待ち時間
    max_wait = 1000
