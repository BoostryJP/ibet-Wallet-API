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

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from tests.account_config import eth_account
from tests.utils import IbetStandardTokenUtils

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestEventsIbetEscrow:
    # Test API
    apiurl = "/Events/IbetEscrow"

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    # No event
    def test_normal_1(self, client: TestClient, session: Session, shared_contract):
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address
        latest_block_number = web3.eth.block_number

        # request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": latest_block_number + 1,
                "to_block": latest_block_number + 1,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == []

    # Normal_2_1
    # event = Deposited
    def test_normal_2_1(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # prepare data
        token_contract = IbetStandardTokenUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "totalSupply": 1000,
                "tradableExchange": escrow_contract.address,
                "contactInformation": "test_contact_info",
                "privacyPolicy": "test_privacy_policy",
            },
        )
        tx_hash = token_contract.functions.transfer(
            escrow_contract.address, 1000
        ).transact({"from": issuer})
        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

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
                "event": "Deposited",
                "args": {"token": token_contract.address, "account": issuer},
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0,
            }
        ]

    # Normal_2_2
    # event = Withdrawn
    def test_normal_2_2(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # prepare data
        token_contract = IbetStandardTokenUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "totalSupply": 1000,
                "tradableExchange": escrow_contract.address,
                "contactInformation": "test_contact_info",
                "privacyPolicy": "test_privacy_policy",
            },
        )

        token_contract.functions.transfer(escrow_contract.address, 1000).transact(
            {"from": issuer}
        )  # Deposited

        tx_hash = escrow_contract.functions.withdraw(
            token_contract.address,
        ).transact(
            {"from": issuer}
        )  # Withdrawn

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

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
                "event": "Withdrawn",
                "args": {"token": token_contract.address, "account": issuer},
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 1,
            }
        ]

    # Normal_2_3
    # event = EscrowCreated
    def test_normal_2_3(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # prepare data
        token_contract = IbetStandardTokenUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "totalSupply": 1000,
                "tradableExchange": escrow_contract.address,
                "contactInformation": "test_contact_info",
                "privacyPolicy": "test_privacy_policy",
            },
        )

        token_contract.functions.transfer(escrow_contract.address, 1000).transact(
            {"from": issuer}
        )  # Deposited

        tx_hash = escrow_contract.functions.createEscrow(
            token_contract.address, user1, 1000, agent, "test_data"
        ).transact(
            {"from": issuer}
        )  # EscrowCreated

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()

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
                "event": "EscrowCreated",
                "args": {
                    "escrowId": latest_escrow_id,
                    "token": token_contract.address,
                    "sender": issuer,
                    "recipient": user1,
                    "amount": 1000,
                    "agent": agent,
                    "data": "test_data",
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0,
            }
        ]

    # Normal_2_4
    # event = EscrowCanceled
    def test_normal_2_4(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # prepare data
        token_contract = IbetStandardTokenUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "totalSupply": 1000,
                "tradableExchange": escrow_contract.address,
                "contactInformation": "test_contact_info",
                "privacyPolicy": "test_privacy_policy",
            },
        )

        token_contract.functions.transfer(escrow_contract.address, 1000).transact(
            {"from": issuer}
        )  # Deposited

        escrow_contract.functions.createEscrow(
            token_contract.address, user1, 1000, agent, "test_data"
        ).transact(
            {"from": issuer}
        )  # EscrowCreated
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()

        tx_hash = escrow_contract.functions.cancelEscrow(latest_escrow_id).transact(
            {"from": issuer}
        )  # EscrowCanceled

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

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
                "event": "EscrowCanceled",
                "args": {
                    "escrowId": latest_escrow_id,
                    "token": token_contract.address,
                    "sender": issuer,
                    "recipient": user1,
                    "amount": 1000,
                    "agent": agent,
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0,
            }
        ]

    # Normal_2_5
    # event = EscrowFinished
    def test_normal_2_5(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # prepare data
        token_contract = IbetStandardTokenUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "totalSupply": 1000,
                "tradableExchange": escrow_contract.address,
                "contactInformation": "test_contact_info",
                "privacyPolicy": "test_privacy_policy",
            },
        )

        token_contract.functions.transfer(escrow_contract.address, 1000).transact(
            {"from": issuer}
        )  # Deposited

        escrow_contract.functions.createEscrow(
            token_contract.address, user1, 1000, agent, "test_data"
        ).transact(
            {"from": issuer}
        )  # EscrowCreated
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()

        tx_hash = escrow_contract.functions.finishEscrow(latest_escrow_id).transact(
            {"from": agent}
        )  # EscrowFinished

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

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
                "event": "EscrowFinished",
                "args": {
                    "escrowId": latest_escrow_id,
                    "token": token_contract.address,
                    "sender": issuer,
                    "recipient": user1,
                    "amount": 1000,
                    "agent": agent,
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0,
            }
        ]

    # Normal_3_1
    # event = Deposited
    # query with filter argument {"token": token_contract.address, "account": issuer}
    # results 1 record.
    def test_normal_3_1(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # prepare data
        token_contract = IbetStandardTokenUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "totalSupply": 1000,
                "tradableExchange": escrow_contract.address,
                "contactInformation": "test_contact_info",
                "privacyPolicy": "test_privacy_policy",
            },
        )
        tx_hash = token_contract.functions.transfer(
            escrow_contract.address, 1000
        ).transact({"from": issuer})
        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

        # request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "argument_filters": json.dumps(
                    {"token": token_contract.address, "account": issuer}
                ),
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "event": "Deposited",
                "args": {"token": token_contract.address, "account": issuer},
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0,
            }
        ]

    # Normal_3_2
    # event = Deposited
    # query with filter argument {"token": "0x00..0", "account": "0x00..0"}
    # results no record.
    def test_normal_3_2(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # prepare data
        token_contract = IbetStandardTokenUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "totalSupply": 1000,
                "tradableExchange": escrow_contract.address,
                "contactInformation": "test_contact_info",
                "privacyPolicy": "test_privacy_policy",
            },
        )
        _tx_hash = token_contract.functions.transfer(
            escrow_contract.address, 1000
        ).transact({"from": issuer})
        latest_block_number = web3.eth.block_number
        _latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

        # request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "argument_filters": json.dumps(
                    {
                        "token": "0x0000000000000000000000000000000000000000",
                        "account": "0x0000000000000000000000000000000000000000",
                    }
                ),
                "event": "Deposited",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == []

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # InvalidParameterError
    # null value not allowed
    def test_error_1(self, client: TestClient, session: Session, shared_contract):
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # request target API
        resp = client.get(self.apiurl, params={})

        # assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": None,
                    "loc": ["query", "from_block"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": None,
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
    def test_error_2(self, client: TestClient, session: Session, shared_contract):
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

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

    # Error_3
    # InvalidParameterError
    # event: unallowed value
    def test_error_3(self, client: TestClient, session: Session, shared_contract):
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address
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
                    "ctx": {
                        "expected": "'Deposited', 'Withdrawn', 'EscrowCreated', 'EscrowCanceled' "
                        "or 'EscrowFinished'"
                    },
                    "input": "some_event",
                    "loc": ["query", "event"],
                    "msg": "Input should be "
                    "'Deposited', 'Withdrawn', 'EscrowCreated', 'EscrowCanceled' "
                    "or 'EscrowFinished'",
                    "type": "enum",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_4
    # InvalidParameterError
    # to_block must be greater than or equal to the from_block
    def test_error_4(self, client: TestClient, session: Session, shared_contract):
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address
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
                        "argument_filters": None,
                        "event": None,
                        "from_block": latest_block_number,
                        "to_block": latest_block_number - 1,
                    },
                    "loc": [],
                    "msg": "Value error, to_block must be greater than or equal "
                    "to the from_block",
                    "type": "value_error",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_5
    # RequestBlockRangeLimitExceededError
    # block range must be less than or equal to 10000
    def test_error_5(self, client: TestClient, session: Session, shared_contract):
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address
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
