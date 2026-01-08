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

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from tests.account_config import eth_account
from tests.types import SharedContract
from tests.utils.contract import Contract

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


def _get_block_timestamp(block_number: int) -> int:
    block = web3.eth.get_block(block_number)
    timestamp = block.get("timestamp")
    assert timestamp is not None
    return timestamp


class TestEventsE2EMessaging:
    # Test API
    apiurl = "/Events/E2EMessaging"

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    # No event
    def test_normal_1(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        latest_block_number = web3.eth.block_number

        # request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": latest_block_number + 1,
                "to_block": latest_block_number + 1,
                "event": "PublicKeyUpdated",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == []

    # Normal_2_1
    # event = PublicKeyUpdated
    def test_normal_2_1(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        user1 = eth_account["user1"]["account_address"]
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # prepare data
        e2e_messaging_contract = Contract.get_contract(
            contract_name="E2EMessaging", address=e2e_messaging_contract.address
        )
        tx = e2e_messaging_contract.functions.setPublicKey(
            "test_key", "test_key_type"
        ).transact({"from": user1})
        latest_block_number = web3.eth.block_number
        latest_block_timestamp = _get_block_timestamp(latest_block_number)

        # request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "event": "PublicKeyUpdated",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "event": "PublicKeyUpdated",
                "args": {"key": "test_key", "key_type": "test_key_type", "who": user1},
                "transaction_hash": tx.to_0x_hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0,
            }
        ]

    # Normal_2_2
    # event = Message
    def test_normal_2_2(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        user1 = eth_account["user1"]["account_address"]
        user2 = eth_account["user2"]["account_address"]
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # prepare data
        e2e_messaging_contract = Contract.get_contract(
            contract_name="E2EMessaging", address=e2e_messaging_contract.address
        )
        tx = e2e_messaging_contract.functions.sendMessage(
            user2, "test_message"
        ).transact({"from": user1})
        latest_block_number = web3.eth.block_number
        latest_block_timestamp = _get_block_timestamp(latest_block_number)

        # request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "event": "Message",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "event": "Message",
                "args": {
                    "sender": user1,
                    "receiver": user2,
                    "time": ANY,
                    "text": "test_message",
                },
                "transaction_hash": tx.to_0x_hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0,
            }
        ]

    # Normal_2_3
    # event = None
    def test_normal_2_3(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        user1 = eth_account["user1"]["account_address"]
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # prepare data
        e2e_messaging_contract = Contract.get_contract(
            contract_name="E2EMessaging", address=e2e_messaging_contract.address
        )
        tx = e2e_messaging_contract.functions.setPublicKey(
            "test_key", "test_key_type"
        ).transact({"from": user1})
        latest_block_number = web3.eth.block_number
        latest_block_timestamp = _get_block_timestamp(latest_block_number)

        # request target API
        resp = client.get(
            self.apiurl,
            params={"from_block": latest_block_number, "to_block": latest_block_number},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "event": "PublicKeyUpdated",
                "args": {"key": "test_key", "key_type": "test_key_type", "who": user1},
                "transaction_hash": tx.to_0x_hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0,
            }
        ]

    # Normal_3_1
    # Multiple events
    def test_normal_3_1(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        user1 = eth_account["user1"]["account_address"]
        user2 = eth_account["user2"]["account_address"]
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # prepare data
        e2e_messaging_contract = Contract.get_contract(
            contract_name="E2EMessaging", address=e2e_messaging_contract.address
        )
        tx_1 = e2e_messaging_contract.functions.sendMessage(
            user2, "test_message"
        ).transact({"from": user1})

        tx_2 = e2e_messaging_contract.functions.sendMessage(
            user2, "test_message"
        ).transact({"from": user1})
        latest_block_number = web3.eth.block_number
        block_timestamp_1 = _get_block_timestamp(latest_block_number - 1)
        block_timestamp_2 = _get_block_timestamp(latest_block_number)

        # request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": latest_block_number - 1,
                "to_block": latest_block_number,
                "event": "Message",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "event": "Message",
                "args": {
                    "sender": user1,
                    "receiver": user2,
                    "time": ANY,
                    "text": "test_message",
                },
                "transaction_hash": tx_1.to_0x_hex(),
                "block_number": latest_block_number - 1,
                "block_timestamp": block_timestamp_1,
                "log_index": 0,
            },
            {
                "event": "Message",
                "args": {
                    "sender": user1,
                    "receiver": user2,
                    "time": ANY,
                    "text": "test_message",
                },
                "transaction_hash": tx_2.to_0x_hex(),
                "block_number": latest_block_number,
                "block_timestamp": block_timestamp_2,
                "log_index": 0,
            },
        ]

    # Normal_4_1
    # event = PublicKeyUpdated
    # query with filter argument {"who": user1}
    # results 1 record.
    def test_normal_4_1(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        user1 = eth_account["user1"]["account_address"]
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # prepare data
        e2e_messaging_contract = Contract.get_contract(
            contract_name="E2EMessaging", address=e2e_messaging_contract.address
        )
        tx = e2e_messaging_contract.functions.setPublicKey(
            "test_key", "test_key_type"
        ).transact({"from": user1})
        latest_block_number = web3.eth.block_number
        latest_block_timestamp = _get_block_timestamp(latest_block_number)
        # request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "argument_filters": json.dumps({"who": user1}),
                "event": "PublicKeyUpdated",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "event": "PublicKeyUpdated",
                "args": {"key": "test_key", "key_type": "test_key_type", "who": user1},
                "transaction_hash": tx.to_0x_hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0,
            }
        ]

    # Normal_4_2
    # event = PublicKeyUpdated
    # query with filter argument {"who": "0x0000000000000000000000000000000000000000"}
    # results no record.
    def test_normal_4_2(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        user1 = eth_account["user1"]["account_address"]
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # prepare data
        e2e_messaging_contract = Contract.get_contract(
            contract_name="E2EMessaging", address=e2e_messaging_contract.address
        )
        _tx = e2e_messaging_contract.functions.setPublicKey(
            "test_key", "test_key_type"
        ).transact({"from": user1})
        latest_block_number = web3.eth.block_number
        _latest_block_timestamp = _get_block_timestamp(latest_block_number)
        # request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "argument_filters": json.dumps(
                    {"who": "0x0000000000000000000000000000000000000000"}
                ),
                "event": "PublicKeyUpdated",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == []

    # Normal_5_1
    # event = ALL
    def test_normal_5_1(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        user1 = eth_account["user1"]["account_address"]
        user2 = eth_account["user2"]["account_address"]
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # prepare data
        e2e_messaging_contract = Contract.get_contract(
            contract_name="E2EMessaging", address=e2e_messaging_contract.address
        )

        tx_1 = e2e_messaging_contract.functions.sendMessage(
            user2, "test_message"
        ).transact({"from": user1})  # Message
        block_number_1 = web3.eth.block_number
        block_timestamp_1 = _get_block_timestamp(block_number_1)

        tx_2 = e2e_messaging_contract.functions.setPublicKey(
            "test_key", "test_key_type"
        ).transact({"from": user1})  # PublicKeyUpdated
        block_number_2 = web3.eth.block_number
        block_timestamp_2 = _get_block_timestamp(block_number_2)

        # request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": block_number_1,
                "to_block": block_number_2,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "event": "Message",
                "args": {
                    "sender": user1,
                    "receiver": user2,
                    "time": ANY,
                    "text": "test_message",
                },
                "transaction_hash": tx_1.to_0x_hex(),
                "block_number": block_number_1,
                "block_timestamp": block_timestamp_1,
                "log_index": 0,
            },
            {
                "event": "PublicKeyUpdated",
                "args": {"who": user1, "key": "test_key", "key_type": "test_key_type"},
                "transaction_hash": tx_2.to_0x_hex(),
                "block_number": block_number_2,
                "block_timestamp": block_timestamp_2,
                "log_index": 0,
            },
        ]

    # Normal_5_2
    # event = ALL
    # query with filter argument {"who": user1}
    # - Events other than "PublicKeyUpdated" are not returned because the arguments do not match.
    def test_normal_5_2(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        user1 = eth_account["user1"]["account_address"]
        user2 = eth_account["user2"]["account_address"]
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # prepare data
        e2e_messaging_contract = Contract.get_contract(
            contract_name="E2EMessaging", address=e2e_messaging_contract.address
        )

        e2e_messaging_contract.functions.sendMessage(user2, "test_message").transact(
            {"from": user1}
        )  # Message
        block_number_1 = web3.eth.block_number
        _get_block_timestamp(block_number_1)

        tx_2 = e2e_messaging_contract.functions.setPublicKey(
            "test_key", "test_key_type"
        ).transact({"from": user1})  # PublicKeyUpdated
        block_number_2 = web3.eth.block_number
        block_timestamp_2 = _get_block_timestamp(block_number_2)

        # request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": block_number_1,
                "to_block": block_number_2,
                "argument_filters": json.dumps({"who": user1}),
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "event": "PublicKeyUpdated",
                "args": {"who": user1, "key": "test_key", "key_type": "test_key_type"},
                "transaction_hash": tx_2.to_0x_hex(),
                "block_number": block_number_2,
                "block_timestamp": block_timestamp_2,
                "log_index": 0,
            },
        ]

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # InvalidParameterError
    # null value not allowed
    def test_error_1(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # request target API
        resp = client.get(self.apiurl, params={})

        # assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": {},
                    "loc": ["query", "from_block"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": {},
                    "loc": ["query", "to_block"],
                    "msg": "Field required",
                    "type": "missing",
                },
            ],
            "message": "Invalid Parameter",
        }

    # Error_2
    # InvalidParameterError
    # from_block, to_block: min value
    def test_error_2(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # request target API
        resp = client.get(self.apiurl, params={"from_block": 0, "to_block": 0})

        # assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"ge": 1},
                    "input": "0",
                    "loc": ["query", "from_block"],
                    "msg": "Input should be greater than or equal to 1",
                    "type": "greater_than_equal",
                },
                {
                    "ctx": {"ge": 1},
                    "input": "0",
                    "loc": ["query", "to_block"],
                    "msg": "Input should be greater than or equal to 1",
                    "type": "greater_than_equal",
                },
            ],
            "message": "Invalid Parameter",
        }

    # Error_3_1
    # InvalidParameterError
    # event: unallowed value
    def test_error_3_1(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address
        latest_block_number = web3.eth.block_number

        # request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "event": "some_event",
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"expected": "'PublicKeyUpdated' or 'Message'"},
                    "input": "some_event",
                    "loc": ["query", "event"],
                    "msg": "Input should be 'PublicKeyUpdated' or 'Message'",
                    "type": "enum",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_3_2
    # InvalidParameterError
    # event: unallowed value in filter argument
    def test_error_3_2(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address
        latest_block_number = web3.eth.block_number

        # request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "argument_filters": json.dumps({"who": 0}),
                "event": "PublicKeyUpdated",
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": "invalid argument_filters",
            "message": "Invalid Parameter",
        }

    # Error_4
    # InvalidParameterError
    # to_block must be greater than or equal to the from_block
    def test_error_4(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address
        latest_block_number = web3.eth.block_number

        # request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number - 1,
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"error": {}},
                    "input": {
                        "from_block": str(latest_block_number),
                        "to_block": str(latest_block_number - 1),
                    },
                    "loc": ["query"],
                    "msg": "Value error, to_block must be greater than or equal to the from_block",
                    "type": "value_error",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_5
    # RequestBlockRangeLimitExceededError
    # block range must be less than or equal to 10000
    def test_error_5(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address
        latest_block_number = web3.eth.block_number

        # request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number + 10001,
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 31,
            "description": "Search request range is over the limit",
            "message": "Request Block Range Limit Exceeded",
        }
