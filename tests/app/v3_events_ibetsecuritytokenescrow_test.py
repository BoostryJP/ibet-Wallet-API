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
from tests.utils import IbetShareUtils

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestEventsIbetSecurityTokenEscrow:

    # Test API
    apiurl = "/v3/Events/IbetSecurityTokenEscrow"

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    # No event
    def test_normal_1(self, client, session, shared_contract):
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address
        latest_block_number = web3.eth.block_number

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

    # Normal_2
    # event = Deposited
    def test_normal_2(self, client, session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # Issue token
        token_contract = IbetShareUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "issuePrice": 100000,
                "totalSupply": 1000,
                "dividends": 100,
                "dividendRecordDate": "20201231",
                "dividendPaymentDate": "20210101",
                "cancellationDate": "20251231",
                "principalValue": 10000,
                "tradableExchange": escrow_contract.address,
                "transferable": True
            }
        )

        # Deposit token to escrow contract
        tx_hash = token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })
        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

        # Request target API
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

    # Normal_3
    # event = Withdrawn
    def test_normal_3(self, client, session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # Issue token
        token_contract = IbetShareUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "issuePrice": 100000,
                "totalSupply": 1000,
                "dividends": 100,
                "dividendRecordDate": "20201231",
                "dividendPaymentDate": "20210101",
                "cancellationDate": "20251231",
                "principalValue": 10000,
                "tradableExchange": escrow_contract.address,
                "transferable": True
            }
        )

        # Deposit token to escrow contract
        token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })  # Deposited

        # Withdraw token from escrow contract
        tx_hash = escrow_contract.functions.withdraw(
            token_contract.address,
        ).transact({
            "from": issuer
        })  # Withdrawn

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

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

    # Normal_4_1
    # event = EscrowCreated & ApplyForTransfer
    def test_normal_4_1(self, client, session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # Issue token
        token_contract = IbetShareUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "issuePrice": 100000,
                "totalSupply": 1000,
                "dividends": 100,
                "dividendRecordDate": "20201231",
                "dividendPaymentDate": "20210101",
                "cancellationDate": "20251231",
                "principalValue": 10000,
                "tradableExchange": escrow_contract.address,
                "transferable": True,
                "transferApprovalRequired": True
            }
        )

        # Deposit token to escrow contract
        token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })  # Deposited

        # Create escrow
        tx_hash = escrow_contract.functions.createEscrow(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_application_data",
            "test_data"
        ).transact({
            "from": issuer
        })  # EscrowCreated

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()

        # Request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number
            }
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json["data"] == [
            {
                "event": "ApplyForTransfer",
                "args": {
                    "escrowId": latest_escrow_id,
                    "token": token_contract.address,
                    "from": issuer,
                    "to": user1,
                    "value": 1000,
                    "data": "test_application_data"
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            },
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
                "log_index": 1
            }
        ]

    # Normal_4_2
    # event = EscrowCreated (filter)
    def test_normal_4_2(self, client, session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # Issue token
        token_contract = IbetShareUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "issuePrice": 100000,
                "totalSupply": 1000,
                "dividends": 100,
                "dividendRecordDate": "20201231",
                "dividendPaymentDate": "20210101",
                "cancellationDate": "20251231",
                "principalValue": 10000,
                "tradableExchange": escrow_contract.address,
                "transferable": True,
                "transferApprovalRequired": True
            }
        )

        # Deposit token to escrow contract
        token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })  # Deposited

        # Create escrow
        tx_hash = escrow_contract.functions.createEscrow(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_application_data",
            "test_data"
        ).transact({
            "from": issuer
        })  # EscrowCreated

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()

        # Request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "event": "EscrowCreated"
            }
        )

        # Assertion
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
                "log_index": 1
            }
        ]

    # Normal_4_3
    # event = ApplyForTransfer (filter)
    def test_normal_4_3(self, client, session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # Issue token
        token_contract = IbetShareUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "issuePrice": 100000,
                "totalSupply": 1000,
                "dividends": 100,
                "dividendRecordDate": "20201231",
                "dividendPaymentDate": "20210101",
                "cancellationDate": "20251231",
                "principalValue": 10000,
                "tradableExchange": escrow_contract.address,
                "transferable": True,
                "transferApprovalRequired": True
            }
        )

        # Deposit token to escrow contract
        token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })  # Deposited

        # Create escrow
        tx_hash = escrow_contract.functions.createEscrow(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_application_data",
            "test_data"
        ).transact({
            "from": issuer
        })  # EscrowCreated

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()

        # Request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "event": "ApplyForTransfer"
            }
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json["data"] == [
            {
                "event": "ApplyForTransfer",
                "args": {
                    "escrowId": latest_escrow_id,
                    "token": token_contract.address,
                    "from": issuer,
                    "to": user1,
                    "value": 1000,
                    "data": "test_application_data"
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            }
        ]

    # Normal_5_1
    # event = EscrowCanceled & CancelTransfer
    def test_normal_5_1(self, client, session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # Issue token
        token_contract = IbetShareUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "issuePrice": 100000,
                "totalSupply": 1000,
                "dividends": 100,
                "dividendRecordDate": "20201231",
                "dividendPaymentDate": "20210101",
                "cancellationDate": "20251231",
                "principalValue": 10000,
                "tradableExchange": escrow_contract.address,
                "transferable": True,
                "transferApprovalRequired": True
            }
        )

        # Deposit token to escrow contract
        token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })  # Deposited

        # Create escrow
        escrow_contract.functions.createEscrow(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_application_data",
            "test_data"
        ).transact({
            "from": issuer
        })  # EscrowCreated

        # Cancel escrow
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()
        tx_hash = escrow_contract.functions.cancelEscrow(
            latest_escrow_id
        ).transact({
            "from": issuer
        })  # EscrowCanceled

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

        # Request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number
            }
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json["data"] == [
            {
                "event": "CancelTransfer",
                "args": {
                    "escrowId": latest_escrow_id,
                    "token": token_contract.address,
                    "from": issuer,
                    "to": user1
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            },
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
                "log_index": 1
            }
        ]

    # Normal_5_2
    # event = EscrowCanceled (filter)
    def test_normal_5_2(self, client, session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # Issue token
        token_contract = IbetShareUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "issuePrice": 100000,
                "totalSupply": 1000,
                "dividends": 100,
                "dividendRecordDate": "20201231",
                "dividendPaymentDate": "20210101",
                "cancellationDate": "20251231",
                "principalValue": 10000,
                "tradableExchange": escrow_contract.address,
                "transferable": True,
                "transferApprovalRequired": True
            }
        )

        # Deposit token to escrow contract
        token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })  # Deposited

        # Create escrow
        escrow_contract.functions.createEscrow(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_application_data",
            "test_data"
        ).transact({
            "from": issuer
        })  # EscrowCreated

        # Cancel escrow
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()
        tx_hash = escrow_contract.functions.cancelEscrow(
            latest_escrow_id
        ).transact({
            "from": issuer
        })  # EscrowCanceled

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

        # Request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "event": "EscrowCanceled"
            }
        )

        # Assertion
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
                "log_index": 1
            }
        ]

    # Normal_5_3
    # event = CancelTransfer (filter)
    def test_normal_5_3(self, client, session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # Issue token
        token_contract = IbetShareUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "issuePrice": 100000,
                "totalSupply": 1000,
                "dividends": 100,
                "dividendRecordDate": "20201231",
                "dividendPaymentDate": "20210101",
                "cancellationDate": "20251231",
                "principalValue": 10000,
                "tradableExchange": escrow_contract.address,
                "transferable": True,
                "transferApprovalRequired": True
            }
        )

        # Deposit token to escrow contract
        token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })  # Deposited

        # Create escrow
        escrow_contract.functions.createEscrow(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_application_data",
            "test_data"
        ).transact({
            "from": issuer
        })  # EscrowCreated

        # Cancel escrow
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()
        tx_hash = escrow_contract.functions.cancelEscrow(
            latest_escrow_id
        ).transact({
            "from": issuer
        })  # EscrowCanceled

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

        # Request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "event": "CancelTransfer"
            }
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json["data"] == [
            {
                "event": "CancelTransfer",
                "args": {
                    "escrowId": latest_escrow_id,
                    "token": token_contract.address,
                    "from": issuer,
                    "to": user1
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            }
        ]

    # Normal_6_1
    # event = EscrowFinished
    def test_normal_6_1(self, client, session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # Issue token
        token_contract = IbetShareUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "issuePrice": 100000,
                "totalSupply": 1000,
                "dividends": 100,
                "dividendRecordDate": "20201231",
                "dividendPaymentDate": "20210101",
                "cancellationDate": "20251231",
                "principalValue": 10000,
                "tradableExchange": escrow_contract.address,
                "transferable": True,
                "transferApprovalRequired": True
            }
        )

        # Deposit token to escrow contract
        token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })  # Deposited

        # Create escrow
        escrow_contract.functions.createEscrow(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_application_data",
            "test_data"
        ).transact({
            "from": issuer
        })  # EscrowCreated
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()

        # Finish escrow
        tx_hash = escrow_contract.functions.finishEscrow(
            latest_escrow_id
        ).transact({
            "from": agent
        })  # EscrowFinished

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

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
                    "agent": agent,
                    "transferApprovalRequired": True
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            }
        ]

    # Normal_6_2
    # event = EscrowFinished (filter)
    def test_normal_6_2(self, client, session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # Issue token
        token_contract = IbetShareUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "issuePrice": 100000,
                "totalSupply": 1000,
                "dividends": 100,
                "dividendRecordDate": "20201231",
                "dividendPaymentDate": "20210101",
                "cancellationDate": "20251231",
                "principalValue": 10000,
                "tradableExchange": escrow_contract.address,
                "transferable": True,
                "transferApprovalRequired": True
            }
        )

        # Deposit token to escrow contract
        token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })  # Deposited

        # Create escrow
        escrow_contract.functions.createEscrow(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_application_data",
            "test_data"
        ).transact({
            "from": issuer
        })  # EscrowCreated
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()

        # Finish escrow
        tx_hash = escrow_contract.functions.finishEscrow(
            latest_escrow_id
        ).transact({
            "from": agent
        })  # EscrowFinished

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "event": "EscrowFinished"
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
                    "agent": agent,
                    "transferApprovalRequired": True
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            }
        ]

    # Normal_7_1
    # event = ApproveTransfer
    def test_normal_7_1(self, client, session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # Issue token
        token_contract = IbetShareUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "issuePrice": 100000,
                "totalSupply": 1000,
                "dividends": 100,
                "dividendRecordDate": "20201231",
                "dividendPaymentDate": "20210101",
                "cancellationDate": "20251231",
                "principalValue": 10000,
                "tradableExchange": escrow_contract.address,
                "transferable": True,
                "transferApprovalRequired": True
            }
        )

        # Deposit token to escrow contract
        token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })  # Deposited

        # Create escrow
        escrow_contract.functions.createEscrow(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_application_data",
            "test_data"
        ).transact({
            "from": issuer
        })  # EscrowCreated
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()

        # Finish escrow
        escrow_contract.functions.finishEscrow(
            latest_escrow_id
        ).transact({
            "from": agent
        })  # EscrowFinished

        # Approve transfer
        tx_hash = escrow_contract.functions.approveTransfer(
            latest_escrow_id,
            "test_approval_data"
        ).transact({
            "from": issuer
        })

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

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
                "event": "ApproveTransfer",
                "args": {
                    "escrowId": latest_escrow_id,
                    "token": token_contract.address,
                    "data": "test_approval_data"
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            }
        ]

    # Normal_7_2
    # event = ApproveTransfer (filter)
    def test_normal_7_2(self, client, session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # Issue token
        token_contract = IbetShareUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "issuePrice": 100000,
                "totalSupply": 1000,
                "dividends": 100,
                "dividendRecordDate": "20201231",
                "dividendPaymentDate": "20210101",
                "cancellationDate": "20251231",
                "principalValue": 10000,
                "tradableExchange": escrow_contract.address,
                "transferable": True,
                "transferApprovalRequired": True
            }
        )

        # Deposit token to escrow contract
        token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })  # Deposited

        # Create escrow
        escrow_contract.functions.createEscrow(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_application_data",
            "test_data"
        ).transact({
            "from": issuer
        })  # EscrowCreated
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()

        # Finish escrow
        escrow_contract.functions.finishEscrow(
            latest_escrow_id
        ).transact({
            "from": agent
        })  # EscrowFinished

        # Approve transfer
        tx_hash = escrow_contract.functions.approveTransfer(
            latest_escrow_id,
            "test_approval_data"
        ).transact({
            "from": issuer
        })

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "event": "ApproveTransfer"
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
                "event": "ApproveTransfer",
                "args": {
                    "escrowId": latest_escrow_id,
                    "token": token_contract.address,
                    "data": "test_approval_data"
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0
            }
        ]

    # Normal_8_1
    # event = Deposited
    # query with filter argument {"token": token_contract.address, "account": issuer}
    # results 1 record.
    def test_normal_8_1(self, client, session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # Issue token
        token_contract = IbetShareUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "issuePrice": 100000,
                "totalSupply": 1000,
                "dividends": 100,
                "dividendRecordDate": "20201231",
                "dividendPaymentDate": "20210101",
                "cancellationDate": "20251231",
                "principalValue": 10000,
                "tradableExchange": escrow_contract.address,
                "transferable": True
            }
        )

        # Deposit token to escrow contract
        tx_hash = token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })
        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

        # Request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "argument_filters": json.dumps({
                    "token": token_contract.address,
                    "account": issuer
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

    # Normal_8_2
    # event = Deposited
    # query with filter argument {"token": "0x00..0", "account": "0x00..0"}
    # results no record.
    def test_normal_8_2(self, client, session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

        # Issue token
        token_contract = IbetShareUtils.issue(
            tx_from=issuer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "issuePrice": 100000,
                "totalSupply": 1000,
                "dividends": 100,
                "dividendRecordDate": "20201231",
                "dividendPaymentDate": "20210101",
                "cancellationDate": "20251231",
                "principalValue": 10000,
                "tradableExchange": escrow_contract.address,
                "transferable": True
            }
        )

        # Deposit token to escrow contract
        _tx_hash = token_contract.functions.transfer(
            escrow_contract.address,
            1000
        ).transact({
            "from": issuer
        })
        latest_block_number = web3.eth.block_number
        _latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

        # Request target API
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
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

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
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address

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
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address
        latest_block_number = web3.eth.block_number

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
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address
        latest_block_number = web3.eth.block_number

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
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address
        latest_block_number = web3.eth.block_number

        # request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "argument_filters": json.dumps({
                    "some key": "some field"
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
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS = escrow_contract.address
        latest_block_number = web3.eth.block_number

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
