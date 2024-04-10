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

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from tests.account_config import eth_account
from tests.utils import IbetShareUtils

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestEventsIbetSecurityTokenDVP:
    # Test API
    apiurl = "/Events/IbetSecurityTokenDVP"

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    # No event
    def test_normal_1(self, client: TestClient, session: Session, shared_contract):
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address
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

    # Normal_2
    # event = Deposited
    def test_normal_2(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address

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
                "tradableExchange": dvp_contract.address,
                "transferable": True,
            },
        )

        # Deposit token to DVP contract
        tx_hash = token_contract.functions.transfer(
            dvp_contract.address, 1000
        ).transact({"from": issuer})
        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

        # Request target API
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

    # Normal_3
    # event = Withdrawn
    @pytest.mark.parametrize(
        "enable_filter",
        [
            True,
            False,
        ],
    )
    def test_normal_3(
        self, enable_filter, client: TestClient, session: Session, shared_contract
    ):
        issuer = eth_account["issuer"]["account_address"]
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address

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
                "tradableExchange": dvp_contract.address,
                "transferable": True,
            },
        )

        # Deposit token to DVP contract
        token_contract.functions.transfer(dvp_contract.address, 1000).transact(
            {"from": issuer}
        )  # Deposited

        # Withdraw token from DVP contract
        tx_hash = dvp_contract.functions.withdraw(
            token_contract.address,
        ).transact(
            {"from": issuer}
        )  # Withdrawn

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

        # request target API
        params = {
            "from_block": latest_block_number,
            "to_block": latest_block_number,
        }
        if enable_filter:
            params["event"] = "Withdrawn"
        resp = client.get(
            self.apiurl,
            params=params,
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

    # Normal_4
    # event = DeliveryCreated
    @pytest.mark.parametrize(
        "enable_filter",
        [
            True,
            False,
        ],
    )
    def test_normal_4(
        self, enable_filter, client: TestClient, session: Session, shared_contract
    ):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address

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
                "tradableExchange": dvp_contract.address,
                "transferable": True,
                "transferApprovalRequired": False,
            },
        )

        # Deposit token to DVP contract
        token_contract.functions.transfer(dvp_contract.address, 1000).transact(
            {"from": issuer}
        )  # Deposited

        # Create delivery
        tx_hash = dvp_contract.functions.createDelivery(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_data",
        ).transact(
            {"from": issuer}
        )  # DeliveryCreated

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]
        latest_delivery_id = dvp_contract.functions.latestDeliveryId().call()

        # Request target API
        params = {
            "from_block": latest_block_number,
            "to_block": latest_block_number,
        }
        if enable_filter:
            params["event"] = "DeliveryCreated"
        resp = client.get(
            self.apiurl,
            params=params,
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "event": "DeliveryCreated",
                "args": {
                    "deliveryId": latest_delivery_id,
                    "token": token_contract.address,
                    "seller": issuer,
                    "buyer": user1,
                    "amount": 1000,
                    "agent": agent,
                    "data": "test_data",
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0,
            },
        ]

    # Normal_5
    # event = DeliveryCanceled
    @pytest.mark.parametrize(
        "enable_filter",
        [
            True,
            False,
        ],
    )
    def test_normal_5(
        self, enable_filter, client: TestClient, session: Session, shared_contract
    ):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address

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
                "tradableExchange": dvp_contract.address,
                "transferable": True,
                "transferApprovalRequired": False,
            },
        )

        # Deposit token to DVP contract
        token_contract.functions.transfer(dvp_contract.address, 1000).transact(
            {"from": issuer}
        )  # Deposited

        # Create delivery
        dvp_contract.functions.createDelivery(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_data",
        ).transact(
            {"from": issuer}
        )  # DeliveryCanceled

        # Cancel delivery
        tx_hash = dvp_contract.functions.cancelDelivery(
            dvp_contract.functions.latestDeliveryId().call()
        ).transact(
            {"from": issuer}
        )  # DeliveryCreated

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]
        latest_delivery_id = dvp_contract.functions.latestDeliveryId().call()

        # Request target API
        params = {
            "from_block": latest_block_number,
            "to_block": latest_block_number,
        }
        if enable_filter:
            params["event"] = "DeliveryCanceled"
        resp = client.get(
            self.apiurl,
            params=params,
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "event": "DeliveryCanceled",
                "args": {
                    "deliveryId": latest_delivery_id,
                    "token": token_contract.address,
                    "seller": issuer,
                    "buyer": user1,
                    "amount": 1000,
                    "agent": agent,
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0,
            }
        ]

    # Normal_6
    # event = DeliveryConfirmed
    @pytest.mark.parametrize(
        "enable_filter",
        [
            True,
            False,
        ],
    )
    def test_normal_6(
        self, enable_filter, client: TestClient, session: Session, shared_contract
    ):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address

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
                "tradableExchange": dvp_contract.address,
                "transferable": True,
                "transferApprovalRequired": False,
            },
        )

        # Deposit token to DVP contract
        token_contract.functions.transfer(dvp_contract.address, 1000).transact(
            {"from": issuer}
        )  # Deposited

        # Create delivery
        dvp_contract.functions.createDelivery(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_data",
        ).transact(
            {"from": issuer}
        )  # DeliveryCreated

        # Confirm delivery
        tx_hash = dvp_contract.functions.confirmDelivery(
            dvp_contract.functions.latestDeliveryId().call()
        ).transact(
            {"from": user1}
        )  # DeliveryConfirmed

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]
        latest_delivery_id = dvp_contract.functions.latestDeliveryId().call()

        # request target API
        params = {
            "from_block": latest_block_number,
            "to_block": latest_block_number,
        }
        if enable_filter:
            params["event"] = "DeliveryConfirmed"
        resp = client.get(
            self.apiurl,
            params={"from_block": latest_block_number, "to_block": latest_block_number},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "event": "DeliveryConfirmed",
                "args": {
                    "deliveryId": latest_delivery_id,
                    "token": token_contract.address,
                    "seller": issuer,
                    "buyer": user1,
                    "amount": 1000,
                    "agent": agent,
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0,
            }
        ]

    # Normal_7
    # event = DeliveryFinished
    @pytest.mark.parametrize(
        "enable_filter",
        [
            True,
            False,
        ],
    )
    def test_normal_7(
        self, enable_filter, client: TestClient, session: Session, shared_contract
    ):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address

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
                "tradableExchange": dvp_contract.address,
                "transferable": True,
                "transferApprovalRequired": False,
            },
        )

        # Deposit token to DVP contract
        token_contract.functions.transfer(dvp_contract.address, 1000).transact(
            {"from": issuer}
        )  # Deposited

        # Create delivery
        dvp_contract.functions.createDelivery(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_data",
        ).transact(
            {"from": issuer}
        )  # DeliveryCreated

        # Confirm delivery
        dvp_contract.functions.confirmDelivery(
            dvp_contract.functions.latestDeliveryId().call()
        ).transact(
            {"from": user1}
        )  # DeliveryConfirmed

        # Finish delivery
        tx_hash = dvp_contract.functions.finishDelivery(
            dvp_contract.functions.latestDeliveryId().call()
        ).transact(
            {"from": agent}
        )  # DeliveryFinished

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]
        latest_delivery_id = dvp_contract.functions.latestDeliveryId().call()

        # request target API
        params = {
            "from_block": latest_block_number,
            "to_block": latest_block_number,
        }
        if enable_filter:
            params["event"] = "DeliveryFinished"
        resp = client.get(
            self.apiurl,
            params={"from_block": latest_block_number, "to_block": latest_block_number},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "event": "DeliveryFinished",
                "args": {
                    "deliveryId": latest_delivery_id,
                    "token": token_contract.address,
                    "seller": issuer,
                    "buyer": user1,
                    "amount": 1000,
                    "agent": agent,
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0,
            }
        ]

    # Normal_8
    # event = DeliveryAborted
    @pytest.mark.parametrize(
        "enable_filter",
        [
            True,
            False,
        ],
    )
    def test_normal_8(
        self, enable_filter, client: TestClient, session: Session, shared_contract
    ):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address

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
                "tradableExchange": dvp_contract.address,
                "transferable": True,
                "transferApprovalRequired": False,
            },
        )

        # Deposit token to DVP contract
        token_contract.functions.transfer(dvp_contract.address, 1000).transact(
            {"from": issuer}
        )  # Deposited

        # Create delivery
        dvp_contract.functions.createDelivery(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_data",
        ).transact(
            {"from": issuer}
        )  # DeliveryCreated

        # Confirm delivery
        dvp_contract.functions.confirmDelivery(
            dvp_contract.functions.latestDeliveryId().call()
        ).transact(
            {"from": user1}
        )  # DeliveryConfirmed

        # Finish delivery
        tx_hash = dvp_contract.functions.abortDelivery(
            dvp_contract.functions.latestDeliveryId().call()
        ).transact(
            {"from": agent}
        )  # DeliveryFinished

        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]
        latest_delivery_id = dvp_contract.functions.latestDeliveryId().call()

        # request target API
        params = {
            "from_block": latest_block_number,
            "to_block": latest_block_number,
        }
        if enable_filter:
            params["event"] = "DeliveryAborted"
        resp = client.get(
            self.apiurl,
            params={"from_block": latest_block_number, "to_block": latest_block_number},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "event": "DeliveryAborted",
                "args": {
                    "deliveryId": latest_delivery_id,
                    "token": token_contract.address,
                    "seller": issuer,
                    "buyer": user1,
                    "amount": 1000,
                    "agent": agent,
                },
                "transaction_hash": tx_hash.hex(),
                "block_number": latest_block_number,
                "block_timestamp": latest_block_timestamp,
                "log_index": 0,
            }
        ]

    # Normal_9_1
    # event = Deposited
    # query with filter argument {"token": token_contract.address, "account": issuer}
    # results 1 record.
    def test_normal_9_1(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address

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
                "tradableExchange": dvp_contract.address,
                "transferable": True,
            },
        )

        # Deposit token to DVP contract
        tx_hash = token_contract.functions.transfer(
            dvp_contract.address, 1000
        ).transact({"from": issuer})
        latest_block_number = web3.eth.block_number
        latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

        # Request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": latest_block_number,
                "to_block": latest_block_number,
                "argument_filters": json.dumps(
                    {"token": token_contract.address, "account": issuer}
                ),
                "event": "Deposited",
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

    # Normal_9_2
    # event = Deposited
    # query with filter argument {"token": "0x00..0", "account": "0x00..0"}
    # results no record.
    def test_normal_9_2(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address

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
                "tradableExchange": dvp_contract.address,
                "transferable": True,
            },
        )

        # Deposit token to DVP contract
        _tx_hash = token_contract.functions.transfer(
            dvp_contract.address, 1000
        ).transact({"from": issuer})
        latest_block_number = web3.eth.block_number
        _latest_block_timestamp = web3.eth.get_block(latest_block_number)["timestamp"]

        # Request target API
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

    # Normal_10_1
    # event = ALL
    def test_normal_10_1(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address

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
                "tradableExchange": dvp_contract.address,
                "transferable": True,
                "transferApprovalRequired": False,
            },
        )

        # Deposit token to DVP contract
        tx_hash_1 = token_contract.functions.transfer(
            dvp_contract.address, 1000
        ).transact(
            {"from": issuer}
        )  # Deposited
        block_number_1 = web3.eth.block_number
        block_timestamp_1 = web3.eth.get_block(block_number_1)["timestamp"]

        # Create delivery
        tx_hash_2 = dvp_contract.functions.createDelivery(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_data",
        ).transact(
            {"from": issuer}
        )  # DeliveryCreated
        block_number_2 = web3.eth.block_number
        block_timestamp_2 = web3.eth.get_block(block_number_2)["timestamp"]

        latest_delivery_id = dvp_contract.functions.latestDeliveryId().call()

        # Request target API
        resp = client.get(
            self.apiurl,
            params={"from_block": block_number_1, "to_block": block_number_2},
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "event": "Deposited",
                "args": {"token": token_contract.address, "account": issuer},
                "transaction_hash": tx_hash_1.hex(),
                "block_number": block_number_1,
                "block_timestamp": block_timestamp_1,
                "log_index": 0,
            },
            {
                "event": "DeliveryCreated",
                "args": {
                    "deliveryId": latest_delivery_id,
                    "token": token_contract.address,
                    "seller": issuer,
                    "buyer": user1,
                    "amount": 1000,
                    "agent": agent,
                    "data": "test_data",
                },
                "transaction_hash": tx_hash_2.hex(),
                "block_number": block_number_2,
                "block_timestamp": block_timestamp_2,
                "log_index": 0,
            },
        ]

    # Normal_10_2
    # event = ALL
    # query with filter argument {"token": token_contract.address, "account": issuer}
    # - Events other than "Deposited" are not returned because the arguments do not match.
    def test_normal_10_2(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]["account_address"]
        user1 = eth_account["user1"]["account_address"]
        agent = eth_account["agent"]["account_address"]
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address

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
                "tradableExchange": dvp_contract.address,
                "transferable": True,
                "transferApprovalRequired": False,
            },
        )

        # Deposit token to DVP contract
        tx_hash_1 = token_contract.functions.transfer(
            dvp_contract.address, 1000
        ).transact(
            {"from": issuer}
        )  # Deposited
        block_number_1 = web3.eth.block_number
        block_timestamp_1 = web3.eth.get_block(block_number_1)["timestamp"]

        # Create delivery
        dvp_contract.functions.createDelivery(
            token_contract.address,
            user1,
            1000,
            agent,
            "test_data",
        ).transact(
            {"from": issuer}
        )  # DeliveryCreated
        block_number_2 = web3.eth.block_number

        # Request target API
        resp = client.get(
            self.apiurl,
            params={
                "from_block": block_number_1,
                "to_block": block_number_2,
                "argument_filters": json.dumps(
                    {"token": token_contract.address, "account": issuer}
                ),
            },
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "event": "Deposited",
                "args": {"token": token_contract.address, "account": issuer},
                "transaction_hash": tx_hash_1.hex(),
                "block_number": block_number_1,
                "block_timestamp": block_timestamp_1,
                "log_index": 0,
            },
        ]

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # InvalidParameterError
    # null value not allowed
    def test_error_1(self, client: TestClient, session: Session, shared_contract):
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address

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
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address

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
    # event: un-allowed value
    def test_error_3(self, client: TestClient, session: Session, shared_contract):
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address
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
            "message": "Invalid Parameter",
            "description": [
                {
                    "ctx": {
                        "expected": "'Deposited', 'Withdrawn', "
                        "'DeliveryCreated', 'DeliveryCanceled', "
                        "'DeliveryConfirmed', 'DeliveryFinished' "
                        "or 'DeliveryAborted'"
                    },
                    "input": "some_event",
                    "loc": ["query", "event"],
                    "msg": "Input should be 'Deposited', 'Withdrawn', "
                    "'DeliveryCreated', 'DeliveryCanceled', "
                    "'DeliveryConfirmed', 'DeliveryFinished' or "
                    "'DeliveryAborted'",
                    "type": "enum",
                }
            ],
        }

    # Error_4
    # InvalidParameterError
    # to_block must be greater than or equal to the from_block
    def test_error_4(self, client: TestClient, session: Session, shared_contract):
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address
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
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS = dvp_contract.address
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
