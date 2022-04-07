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
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from tests.account_config import eth_account
from tests.utils import IbetStandardTokenUtils

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestEventsIbetEscrow:

    # Test API
    apiurl = "/v3/Events/IbetEscrow"

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    # No event
    def test_normal_1(self, client, session, shared_contract):
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address
        latest_block_number = web3.eth.blockNumber

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number + 1,
                "to_block": latest_block_number + 1
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
    # event = Deposited
    def test_normal_2_1(self, client, session, shared_contract):
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
                "privacyPolicy": "test_privacy_policy"
            }
        )
        tx_hash = token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
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
                "event": "Deposited",
                "args": {
                    "token": token_contract.address,
                    "account": issuer
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            }
        ]

    # Normal_2_2
    # event = Withdrawn
    def test_normal_2_2(self, client, session, shared_contract):
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
                "privacyPolicy": "test_privacy_policy"
            }
        )

        token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })  # Deposited

        tx_hash = escrow_contract.functions.withdraw(
            token_contract.address,
        ).transact({
            "from": issuer
        })  # Withdrawn

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
                "event": "Withdrawn",
                "args": {
                    "token": token_contract.address,
                    "account": issuer
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 1
            }
        ]

    # Normal_2_3
    # event = EscrowCreated
    def test_normal_2_3(self, client, session, shared_contract):
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
                "privacyPolicy": "test_privacy_policy"
            }
        )

        token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })  # Deposited

        tx_hash = escrow_contract.functions.createEscrow(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_data"
        ).transact({
            "from": issuer
        })  # EscrowCreated

        latest_block_number = web3.eth.blockNumber
        latest_block_timestamp = web3.eth.getBlock(latest_block_number)["timestamp"]
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()

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
                "event": "EscrowCreated",
                "args": {
                    "escrowId": latest_escrow_id,
                    "token": token_contract.address,
                    "sender": issuer,
                    "recipient": user1,
                    "amount": 1000,
                    "agent": agent,
                    "data": "test_data"
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            }
        ]

    # Normal_2_4
    # event = EscrowCanceled
    def test_normal_2_4(self, client, session, shared_contract):
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
                "privacyPolicy": "test_privacy_policy"
            }
        )

        token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })  # Deposited

        escrow_contract.functions.createEscrow(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_data"
        ).transact({
            "from": issuer
        })  # EscrowCreated
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()

        tx_hash = escrow_contract.functions.cancelEscrow(
            latest_escrow_id
        ).transact({
            "from": issuer
        })  # EscrowCanceled

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
                "event": "EscrowCanceled",
                "args": {
                    "escrowId": latest_escrow_id,
                    "token": token_contract.address,
                    "sender": issuer,
                    "recipient": user1,
                    "amount": 1000,
                    "agent": agent
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            }
        ]

    # Normal_2_5
    # event = EscrowFinished
    def test_normal_2_5(self, client, session, shared_contract):
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
                "privacyPolicy": "test_privacy_policy"
            }
        )

        token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })  # Deposited

        escrow_contract.functions.createEscrow(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_data"
        ).transact({
            "from": issuer
        })  # EscrowCreated
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()

        tx_hash = escrow_contract.functions.finishEscrow(
            latest_escrow_id
        ).transact({
            "from": agent
        })  # EscrowFinished

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
                "event": "EscrowFinished",
                "args": {
                    "escrowId": latest_escrow_id,
                    "token": token_contract.address,
                    "sender": issuer,
                    "recipient": user1,
                    "amount": 1000,
                    "agent": agent
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            }
        ]

    # Normal_3_1
    # event = Deposited
    # query with filter argument {"token": token_contract.address, "account": issuer}
    # results 1 record.
    def test_normal_3_1(self, client, session, shared_contract):
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
                "privacyPolicy": "test_privacy_policy"
            }
        )
        tx_hash = token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
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
                    "token": token_contract.address,
                    "account": issuer
                }),
                # "event": "Deposited"
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
                "event": "Deposited",
                "args": {
                    "token": token_contract.address,
                    "account": issuer
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            }
        ]

    # Normal_3_2
    # event = Deposited
    # query with filter argument {"token": "0x00..0", "account": "0x00..0"}
    # results no record.
    def test_normal_3_2(self, client, session, shared_contract):
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
                "privacyPolicy": "test_privacy_policy"
            }
        )
        tx_hash = token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
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
                    "token": "0x0000000000000000000000000000000000000000",
                    "account": "0x0000000000000000000000000000000000000000"
                }),
                "event": "Deposited"
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
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

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
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

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
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address
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
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address
        latest_block_number = web3.eth.blockNumber

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "argument_filters": json.dumps({
                    "escrowId": "0"
                }),
                "event": "EscrowCreated"
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {"argument_filters": [{"escrowId": ["must be of integer type"]}]}
        }

    # Error_3_3
    # InvalidParameterError
    # event: unknown field in filter argument
    def test_error_3_3(self, client, session, shared_contract):
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address
        latest_block_number = web3.eth.blockNumber

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "argument_filters": json.dumps({
                    "some key": "some value"
                }),
                "event": "EscrowCreated"
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {"argument_filters": [{"some key": ["unknown field"]}]}
        }

    # Error_4
    # InvalidParameterError
    # to_block must be greater than or equal to the from_block
    def test_error_4(self, client, session, shared_contract):
        escrow_contract = shared_contract["IbetEscrow"]
        config.IBET_ESCROW_CONTRACT_ADDRESS = escrow_contract.address
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
