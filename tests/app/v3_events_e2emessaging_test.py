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
from web3.middleware import geth_poa_middleware

from app import config
from app.contracts import Contract
from tests.account_config import eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestEventsE2EMessaging:

    # Test API
    apiurl = "/v3/Events/E2EMessaging"

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    # No event
    def test_normal_1(self, client, shared_contract):
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        latest_block_number = web3.eth.blockNumber

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number + 1,
                "to_block": latest_block_number + 1,
                "event": "PublicKeyUpdated"
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json["data"] == []

    # Normal_2_1
    # event = PublicKeyUpdated
    def test_normal_2_1(self, client, shared_contract):
        user1 = eth_account["user1"]["account_address"]
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # prepare data
        e2e_messaging_contract = Contract.get_contract(
            contract_name="E2EMessaging",
            address=e2e_messaging_contract.address
        )
        tx = e2e_messaging_contract.functions.setPublicKey(
            "test_key",
            "test_key_type"
        ).transact({
            "from": user1
        })
        latest_block_number = web3.eth.blockNumber

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "event": "PublicKeyUpdated"
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json["data"] == [
            {
                "event": "PublicKeyUpdated",
                "args": {
                    "key": "test_key",
                    "key_type": "test_key_type",
                    "who": user1
                },
                "transaction_hash": tx.hex(),
                "block_number": latest_block_number,
                "log_index": 0
            }
        ]

    # Normal_2_2
    # event = Message
    def test_normal_2_2(self, client, shared_contract):
        user1 = eth_account["user1"]["account_address"]
        user2 = eth_account["user2"]["account_address"]
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # prepare data
        e2e_messaging_contract = Contract.get_contract(
            contract_name="E2EMessaging",
            address=e2e_messaging_contract.address
        )
        tx = e2e_messaging_contract.functions.sendMessage(
            user2,
            "test_message"
        ).transact({
            "from": user1
        })
        latest_block_number = web3.eth.blockNumber

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "event": "Message"
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json["data"][0]["event"] == "Message"
        assert resp.json["data"][0]["args"]["sender"] == user1
        assert resp.json["data"][0]["args"]["receiver"] == user2
        assert resp.json["data"][0]["args"]["text"] == "test_message"
        assert resp.json["data"][0]["transaction_hash"] == tx.hex()
        assert resp.json["data"][0]["block_number"] == latest_block_number
        assert resp.json["data"][0]["log_index"] == 0

    # Normal_2_3
    # event = None
    def test_normal_2_3(self, client, shared_contract):
        user1 = eth_account["user1"]["account_address"]
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # prepare data
        e2e_messaging_contract = Contract.get_contract(
            contract_name="E2EMessaging",
            address=e2e_messaging_contract.address
        )
        tx = e2e_messaging_contract.functions.setPublicKey(
            "test_key",
            "test_key_type"
        ).transact({
            "from": user1
        })
        latest_block_number = web3.eth.blockNumber

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json["data"] == [
            {
                "event": "PublicKeyUpdated",
                "args": {
                    "key": "test_key",
                    "key_type": "test_key_type",
                    "who": user1
                },
                "transaction_hash": tx.hex(),
                "block_number": latest_block_number,
                "log_index": 0
            }
        ]

    # Normal_3
    # Multiple events
    def test_normal_3(self, client, shared_contract):
        user1 = eth_account["user1"]["account_address"]
        user2 = eth_account["user2"]["account_address"]
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # prepare data
        e2e_messaging_contract = Contract.get_contract(
            contract_name="E2EMessaging",
            address=e2e_messaging_contract.address
        )
        tx_1 = e2e_messaging_contract.functions.sendMessage(
            user2,
            "test_message"
        ).transact({
            "from": user1
        })

        tx_2 = e2e_messaging_contract.functions.sendMessage(
            user2,
            "test_message"
        ).transact({
            "from": user1
        })
        latest_block_number = web3.eth.blockNumber

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number - 1,
                "to_block": latest_block_number,
                "event": "Message"
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {
            "code": 200,
            "message": "OK"
        }

        assert resp.json["data"][0]["event"] == "Message"
        assert resp.json["data"][0]["args"]["sender"] == user1
        assert resp.json["data"][0]["args"]["receiver"] == user2
        assert resp.json["data"][0]["args"]["text"] == "test_message"
        assert resp.json["data"][0]["transaction_hash"] == tx_1.hex()
        assert resp.json["data"][0]["block_number"] == latest_block_number - 1
        assert resp.json["data"][0]["log_index"] == 0

        assert resp.json["data"][1]["event"] == "Message"
        assert resp.json["data"][1]["args"]["sender"] == user1
        assert resp.json["data"][1]["args"]["receiver"] == user2
        assert resp.json["data"][1]["args"]["text"] == "test_message"
        assert resp.json["data"][1]["block_number"] == latest_block_number
        assert resp.json["data"][1]["transaction_hash"] == tx_2.hex()
        assert resp.json["data"][1]["log_index"] == 0

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # InvalidParameterError
    # null value not allowed
    def test_error_1(self, client, shared_contract):
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={}
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "from_block": [
                    "null value not allowed",
                    "field 'from_block' could not be coerced",
                    "must be of integer type"
                ],
                "to_block": [
                    "null value not allowed",
                    "field 'to_block' could not be coerced",
                    "must be of integer type"
                ]
            }
        }

    # Error_2
    # InvalidParameterError
    # from_block, to_block: min value
    def test_error_2(self, client, shared_contract):
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": 0,
                "to_block": 0
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "from_block": "min value is 1",
                "to_block": "min value is 1"
            }
        }

    # Error_3
    # InvalidParameterError
    # event: unallowed value
    def test_error_3(self, client, shared_contract):
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address
        latest_block_number = web3.eth.blockNumber

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "event": "some_event"
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {"event": "unallowed value some_event"}
        }

    # Error_4
    # InvalidParameterError
    # to_block must be greater than or equal to the from_block
    def test_error_4(self, client, shared_contract):
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address
        latest_block_number = web3.eth.blockNumber

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number - 1
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "to_block must be greater than or equal to the from_block"
        }
