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
import json
from unittest.mock import ANY

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
    def test_normal_1(self, client, session, shared_contract):
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
    def test_normal_2_1(self, client, session, shared_contract):
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
        latest_block_timestamp = web3.eth.getBlock(latest_block_number)["timestamp"]

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
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            }
        ]

    # Normal_2_2
    # event = Message
    def test_normal_2_2(self, client, session, shared_contract):
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
        latest_block_timestamp = web3.eth.getBlock(latest_block_number)["timestamp"]

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
        assert resp.json["data"] == [
            {
                "event": "Message",
                "args": {
                    "sender": user1,
                    "receiver": user2,
                    "time": ANY,
                    "text": "test_message"
                },
                "transaction_hash": tx.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            }
        ]

    # Normal_2_3
    # event = None
    def test_normal_2_3(self, client, session, shared_contract):
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
        latest_block_timestamp = web3.eth.getBlock(latest_block_number)["timestamp"]

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
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            }
        ]

    # Normal_3
    # Multiple events
    def test_normal_3(self, client, session, shared_contract):
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
        block_timestamp_1 = web3.eth.getBlock(latest_block_number - 1)["timestamp"]
        block_timestamp_2 = web3.eth.getBlock(latest_block_number)["timestamp"]

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
        assert resp.json["data"] == [
            {
                "event": "Message",
                "args": {
                    "sender": user1,
                    "receiver": user2,
                    "time": ANY,
                    "text": "test_message"
                },
                "transaction_hash": tx_1.hex(),
                "block_number": latest_block_number - 1,
                "block_timestamp": block_timestamp_1,
                "log_index": 0
            },
            {
                "event": "Message",
                "args": {
                    "sender": user1,
                    "receiver": user2,
                    "time": ANY,
                    "text": "test_message"
                },
                "transaction_hash": tx_2.hex(),
                "block_number": latest_block_number,
                "block_timestamp": block_timestamp_2,
                "log_index": 0
            },
        ]

    # Normal_4_1
    # event = PublicKeyUpdated
    # query with filter argument {"who": user1}
    # results 1 record.
    def test_normal_4_1(self, client, session, shared_contract):
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
        latest_block_timestamp = web3.eth.getBlock(latest_block_number)["timestamp"]
        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "argument_filters": json.dumps({
                    "who": user1
                }),
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
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            }
        ]

    # Normal_4_2
    # event = PublicKeyUpdated
    # query with filter argument {"who": "0x0000000000000000000000000000000000000000"}
    # results no record.
    def test_normal_4_2(self, client, session, shared_contract):
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
        latest_block_timestamp = web3.eth.getBlock(latest_block_number)["timestamp"]
        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "argument_filters": json.dumps({
                    "who": "0x0000000000000000000000000000000000000000"
                }),
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

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # InvalidParameterError
    # null value not allowed
    def test_error_1(self, client, session, shared_contract):
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
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'from_block': [
                    "field 'from_block' cannot be coerced: int() argument must be a string, a bytes-like object or a number, not 'NoneType'",
                    'null value not allowed'
                ],
                'to_block': [
                    "field 'to_block' cannot be coerced: int() argument must be a string, a bytes-like object or a number, not 'NoneType'",
                    'null value not allowed'
                ]
            }
        }

    # Error_2
    # InvalidParameterError
    # from_block, to_block: min value
    def test_error_2(self, client, session, shared_contract):
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
                    "from_block": ["min value is 1"],
                "to_block": ["min value is 1"]
            }
        }

    # Error_3_1
    # InvalidParameterError
    # event: unallowed value
    def test_error_3_1(self, client, session, shared_contract):
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
            "description": {"event": ["unallowed value some_event"]}
        }

    # Error_3_2
    # InvalidParameterError
    # event: unallowed value in filter argument
    def test_error_3_2(self, client, session, shared_contract):
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address
        latest_block_number = web3.eth.blockNumber

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "argument_filters": json.dumps({
                    "who": 0
                }),
                "event": "PublicKeyUpdated"
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "argument_filters": [{"who": ["must be of string type"]}]
            }
        }

    # Error_3_3
    # InvalidParameterError
    # event: unknown field in filter argument
    def test_error_3_3(self, client, session, shared_contract):
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address
        latest_block_number = web3.eth.blockNumber

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "argument_filters": json.dumps({
                    "some_key": "some_value"
                }),
                "event": "PublicKeyUpdated"
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "argument_filters": [{"some_key": ["unknown field"]}]
            }
        }

    # Error_4
    # InvalidParameterError
    # to_block must be greater than or equal to the from_block
    def test_error_4(self, client, session, shared_contract):
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
