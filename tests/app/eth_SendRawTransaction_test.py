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
import logging
from unittest import mock
from unittest.mock import ANY, MagicMock

import pytest
from eth_utils import to_checksum_address
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.datastructures import AttributeDict
from web3.exceptions import TimeExhausted
from web3.middleware import geth_poa_middleware

from app import config, log
from app.api.routers import eth
from app.contracts import Contract
from app.model.db import ExecutableContract, Listing, Node
from tests.account_config import eth_account
from tests.contract_modules import coupon_register_list, issue_coupon_token

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


def insert_node_data(
    session, is_synced, endpoint_uri=config.WEB3_HTTP_PROVIDER, priority=0
):
    node = Node()
    node.is_synced = is_synced
    node.endpoint_uri = endpoint_uri
    node.priority = priority
    session.add(node)
    session.commit()


def tokenlist_contract():
    issuer = eth_account["issuer"]
    web3.eth.default_account = issuer["account_address"]
    contract_address, abi = Contract.deploy_contract(
        "TokenList", [], issuer["account_address"]
    )

    return {"address": contract_address, "abi": abi}


def listing_token(session, token):
    listing = Listing()
    listing.token_address = token["address"]
    listing.is_public = True
    listing.max_holding_quantity = 1
    listing.max_sell_amount = 1000
    session.add(listing)


def executable_contract_token(session, contract):
    executable_contract = ExecutableContract()
    executable_contract.contract_address = contract["address"]
    session.add(executable_contract)


@pytest.fixture(scope="function")
def caplog(caplog: pytest.LogCaptureFixture):
    LOG = log.get_logger()
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield caplog
    LOG.propagate = False
    LOG.setLevel(default_log_level)


class TestEthSendRawTransaction:
    # Test API
    apiurl = "/Eth/SendRawTransaction"

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # Input list exists (1 entry)
    # Web3 FailOver
    def test_normal_1(self, client: TestClient, session: Session):
        with mock.patch(
            "app.utils.web3_utils.FailOverHTTPProvider.fail_over_mode", True
        ):
            insert_node_data(
                session, is_synced=False, endpoint_uri="http://localhost:8546"
            )
            insert_node_data(
                session,
                is_synced=True,
                endpoint_uri=config.WEB3_HTTP_PROVIDER,
                priority=1,
            )

            # トークンリスト登録
            tokenlist = tokenlist_contract()
            config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist["address"]
            issuer = eth_account["issuer"]
            coupontoken_1 = issue_coupon_token(
                issuer,
                {
                    "name": "name_test1",
                    "symbol": "symbol_test1",
                    "totalSupply": 1000000,
                    "tradableExchange": config.ZERO_ADDRESS,
                    "details": "details_test1",
                    "returnDetails": "returnDetails_test1",
                    "memo": "memo_test1",
                    "expirationDate": "20211201",
                    "transferable": True,
                    "contactInformation": "contactInformation_test1",
                    "privacyPolicy": "privacyPolicy_test1",
                },
            )
            coupon_register_list(issuer, coupontoken_1, tokenlist)

            # Listing,実行可能コントラクト登録
            listing_token(session, coupontoken_1)
            executable_contract_token(session, coupontoken_1)

            token_contract_1 = web3.eth.contract(
                address=to_checksum_address(coupontoken_1["address"]),
                abi=coupontoken_1["abi"],
            )

            local_account_1 = web3.eth.account.create()

            # テスト用のトランザクション実行前の事前準備
            pre_tx = token_contract_1.functions.transfer(
                to_checksum_address(local_account_1.address), 10
            ).build_transaction(
                {
                    "from": to_checksum_address(issuer["account_address"]),
                    "gas": 6000000,
                    "gasPrice": 0,
                }
            )
            tx_hash = web3.eth.send_transaction(pre_tx)
            web3.eth.wait_for_transaction_receipt(tx_hash)

            tx = token_contract_1.functions.consume(10).build_transaction(
                {
                    "from": to_checksum_address(local_account_1.address),
                    "gas": 6000000,
                    "gasPrice": 0,
                }
            )
            tx["nonce"] = web3.eth.get_transaction_count(
                to_checksum_address(local_account_1.address)
            )
            signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.key)

            session.commit()

            request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
            headers = {"Content-Type": "application/json"}
            resp = client.post(self.apiurl, headers=headers, json=request_params)

            assert resp.status_code == 200
            assert resp.json()["meta"] == {"code": 200, "message": "OK"}
            assert resp.json()["data"] == [
                {"id": 1, "status": 1, "transaction_hash": ANY}
            ]

    # <Normal_2>
    # Input list exists (multiple entries)
    def test_normal_2(self, client: TestClient, session: Session):
        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist["address"]
        issuer = eth_account["issuer"]
        coupontoken_1 = issue_coupon_token(
            issuer,
            {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "totalSupply": 1000000,
                "tradableExchange": config.ZERO_ADDRESS,
                "details": "details_test1",
                "returnDetails": "returnDetails_test1",
                "memo": "memo_test1",
                "expirationDate": "20211201",
                "transferable": True,
                "contactInformation": "contactInformation_test1",
                "privacyPolicy": "privacyPolicy_test1",
            },
        )
        coupon_register_list(issuer, coupontoken_1, tokenlist)
        coupontoken_2 = issue_coupon_token(
            issuer,
            {
                "name": "name_test2",
                "symbol": "symbol_test2",
                "totalSupply": 1000000,
                "tradableExchange": config.ZERO_ADDRESS,
                "details": "details_test2",
                "returnDetails": "returnDetails_test2",
                "memo": "memo_test2",
                "expirationDate": "20211202",
                "transferable": True,
                "contactInformation": "contactInformation_test2",
                "privacyPolicy": "privacyPolicy_test2",
            },
        )
        coupon_register_list(issuer, coupontoken_2, tokenlist)

        # Listing,実行可能コントラクト登録
        listing_token(session, coupontoken_1)
        executable_contract_token(session, coupontoken_1)
        listing_token(session, coupontoken_2)
        executable_contract_token(session, coupontoken_2)

        token_contract_1 = web3.eth.contract(
            address=to_checksum_address(coupontoken_1["address"]),
            abi=coupontoken_1["abi"],
        )

        local_account_1 = web3.eth.account.create()

        # テスト用のトランザクション実行前の事前準備
        pre_tx = token_contract_1.functions.transfer(
            to_checksum_address(local_account_1.address), 10
        ).build_transaction(
            {
                "from": to_checksum_address(issuer["account_address"]),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx_hash = web3.eth.send_transaction(pre_tx)
        web3.eth.wait_for_transaction_receipt(tx_hash)

        tx = token_contract_1.functions.consume(10).build_transaction(
            {
                "from": to_checksum_address(local_account_1.address),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx["nonce"] = web3.eth.get_transaction_count(
            to_checksum_address(local_account_1.address)
        )
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.key)

        token_contract_2 = web3.eth.contract(
            address=to_checksum_address(coupontoken_2["address"]),
            abi=coupontoken_1["abi"],
        )

        local_account_2 = web3.eth.account.create()

        # テスト用のトランザクション実行前の事前準備
        pre_tx = token_contract_2.functions.transfer(
            to_checksum_address(local_account_2.address), 10
        ).build_transaction(
            {
                "from": to_checksum_address(issuer["account_address"]),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx_hash = web3.eth.send_transaction(pre_tx)
        web3.eth.wait_for_transaction_receipt(tx_hash)

        tx = token_contract_2.functions.consume(10).build_transaction(
            {
                "from": to_checksum_address(local_account_2.address),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx["nonce"] = web3.eth.get_transaction_count(
            to_checksum_address(local_account_2.address)
        )
        signed_tx_2 = web3.eth.account.sign_transaction(tx, local_account_2.key)

        session.commit()

        request_params = {
            "raw_tx_hex_list": [
                signed_tx_1.rawTransaction.hex(),
                signed_tx_2.rawTransaction.hex(),
            ]
        }
        headers = {"Content-Type": "application/json"}

        resp = client.post(self.apiurl, headers=headers, json=request_params)

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {"id": 1, "status": 1, "transaction_hash": ANY},
            {"id": 2, "status": 1, "transaction_hash": ANY},
        ]

    # <Normal_3>
    # pending transaction
    def test_normal_3(self, client: TestClient, session: Session):
        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist["address"]
        issuer = eth_account["issuer"]
        coupontoken_1 = issue_coupon_token(
            issuer,
            {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "totalSupply": 1000000,
                "tradableExchange": config.ZERO_ADDRESS,
                "details": "details_test1",
                "returnDetails": "returnDetails_test1",
                "memo": "memo_test1",
                "expirationDate": "20211201",
                "transferable": True,
                "contactInformation": "contactInformation_test1",
                "privacyPolicy": "privacyPolicy_test1",
            },
        )
        coupon_register_list(issuer, coupontoken_1, tokenlist)

        # Listing,実行可能コントラクト登録
        listing_token(session, coupontoken_1)
        executable_contract_token(session, coupontoken_1)

        token_contract_1 = web3.eth.contract(
            address=to_checksum_address(coupontoken_1["address"]),
            abi=coupontoken_1["abi"],
        )

        local_account_1 = web3.eth.account.create()

        # テスト用のトランザクション実行前の事前準備
        pre_tx = token_contract_1.functions.transfer(
            to_checksum_address(local_account_1.address), 10
        ).build_transaction(
            {
                "from": to_checksum_address(issuer["account_address"]),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx_hash = web3.eth.send_transaction(pre_tx)
        web3.eth.wait_for_transaction_receipt(tx_hash)

        tx = token_contract_1.functions.consume(10).build_transaction(
            {
                "from": to_checksum_address(local_account_1.address),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx["nonce"] = web3.eth.get_transaction_count(
            to_checksum_address(local_account_1.address)
        )
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.key)

        session.commit()

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {"Content-Type": "application/json"}

        # タイムアウト
        # NOTE: GanacheにはRPCメソッド:txpool_inspectが存在しないためMock化
        async def mock_inspect():
            return AttributeDict(
                {
                    "pending": AttributeDict(
                        {
                            to_checksum_address(local_account_1.address): AttributeDict(
                                {
                                    str(
                                        tx["nonce"]
                                    ): "0xffffffffffffffffffffffffffffffffffffffff: 0 wei + 999999 × 11111 gas"
                                }
                            )
                        }
                    ),
                    "queued": AttributeDict({}),
                }
            )

        with mock.patch(
            "web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            MagicMock(side_effect=TimeExhausted()),
        ), mock.patch(
            "web3.geth.AsyncGethTxPool.inspect",
            MagicMock(side_effect=[mock_inspect()]),
        ):
            resp = client.post(self.apiurl, headers=headers, json=request_params)

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [{"id": 1, "status": 2, "transaction_hash": ANY}]

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Unsupported HTTP method
    # -> 404 Not Supported
    def test_error_1(self, client: TestClient, session: Session):
        resp = client.get(self.apiurl)

        assert resp.status_code == 405
        assert resp.json()["meta"] == {
            "code": 1,
            "message": "Method Not Allowed",
            "description": "method: GET, url: /Eth/SendRawTransaction",
        }

    # <Error_2>
    # No headers
    # -> 400 InvalidParameterError
    def test_error_2(self, client: TestClient, session: Session):
        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": raw_tx_1}

        headers = {}
        resp = client.post(self.apiurl, headers=headers, json=request_params)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": "some_raw_tx_1",
                    "loc": ["body", "raw_tx_hex_list"],
                    "msg": "Input should be a valid list",
                    "type": "list_type",
                }
            ],
            "message": "Invalid Parameter",
        }

    # <Error_3_1>
    # Input list is empty
    # -> 400 InvalidParameterError
    def test_error_3_1(self, client: TestClient, session: Session):
        config.TOKEN_LIST_CONTRACT_ADDRESS = config.ZERO_ADDRESS
        request_params = {"raw_tx_hex_list": []}

        headers = {"Content-Type": "application/json"}
        resp = client.post(self.apiurl, headers=headers, json=request_params)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"actual_length": 0, "field_type": "List", "min_length": 1},
                    "input": [],
                    "loc": ["body", "raw_tx_hex_list"],
                    "msg": "List should have at least 1 item after validation, "
                    "not 0",
                    "type": "too_short",
                }
            ],
            "message": "Invalid Parameter",
        }

    # <Error_3_2>
    # No inputs
    # -> 400 InvalidParameterError
    def test_error_3_2(self, client: TestClient, session: Session):
        request_params = {}

        headers = {"Content-Type": "application/json"}
        resp = client.post(self.apiurl, headers=headers, json=request_params)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": {},
                    "loc": ["body", "raw_tx_hex_list"],
                    "msg": "Field required",
                    "type": "missing",
                }
            ],
            "message": "Invalid Parameter",
        }

    # <Error_4>
    # Input values are incorrect (not a list type)
    # -> 400 InvalidParameterError
    def test_error_4(self, client: TestClient, session: Session):
        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": raw_tx_1}

        headers = {"Content-Type": "application/json"}
        resp = client.post(self.apiurl, headers=headers, json=request_params)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": "some_raw_tx_1",
                    "loc": ["body", "raw_tx_hex_list"],
                    "msg": "Input should be a valid list",
                    "type": "list_type",
                }
            ],
            "message": "Invalid Parameter",
        }

    # <Error_5>
    # Input values are incorrect (not a string type)
    # -> 400 InvalidParameterError
    def test_error_5(self, client: TestClient, session: Session):
        config.TOKEN_LIST_CONTRACT_ADDRESS = config.ZERO_ADDRESS
        raw_tx_1 = 1234
        request_params = {"raw_tx_hex_list": [raw_tx_1]}

        headers = {"Content-Type": "application/json"}
        resp = client.post(self.apiurl, headers=headers, json=request_params)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": 1234,
                    "loc": ["body", "raw_tx_hex_list", 0],
                    "msg": "Input should be a valid string",
                    "type": "string_type",
                }
            ],
            "message": "Invalid Parameter",
        }

    # <Error_6>
    # Input values are incorrect (invalid transaction）
    # -> 200, status = 0
    def test_error_6(self, client: TestClient, session: Session):
        config.TOKEN_LIST_CONTRACT_ADDRESS = config.ZERO_ADDRESS

        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": [raw_tx_1]}

        headers = {"Content-Type": "application/json"}
        resp = client.post(self.apiurl, headers=headers, json=request_params)

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [{"id": 1, "status": 0, "transaction_hash": None}]

    # <Error_7>
    # block synchronization stop(Web3 FailOver Error)
    def test_error_7(self, client: TestClient, session: Session):
        config.TOKEN_LIST_CONTRACT_ADDRESS = config.ZERO_ADDRESS

        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist["address"]
        issuer = eth_account["issuer"]
        coupontoken_1 = issue_coupon_token(
            issuer,
            {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "totalSupply": 1000000,
                "tradableExchange": config.ZERO_ADDRESS,
                "details": "details_test1",
                "returnDetails": "returnDetails_test1",
                "memo": "memo_test1",
                "expirationDate": "20211201",
                "transferable": True,
                "contactInformation": "contactInformation_test1",
                "privacyPolicy": "privacyPolicy_test1",
            },
        )
        coupon_register_list(issuer, coupontoken_1, tokenlist)

        # Listing,実行可能コントラクト登録
        listing_token(session, coupontoken_1)
        executable_contract_token(session, coupontoken_1)

        token_contract_1 = web3.eth.contract(
            address=to_checksum_address(coupontoken_1["address"]),
            abi=coupontoken_1["abi"],
        )

        local_account_1 = web3.eth.account.create()

        # テスト用のトランザクション実行前の事前準備
        pre_tx = token_contract_1.functions.transfer(
            to_checksum_address(local_account_1.address), 10
        ).build_transaction(
            {
                "from": to_checksum_address(issuer["account_address"]),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx_hash = web3.eth.send_transaction(pre_tx)
        web3.eth.wait_for_transaction_receipt(tx_hash)

        tx = token_contract_1.functions.consume(10).build_transaction(
            {
                "from": to_checksum_address(local_account_1.address),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx["nonce"] = web3.eth.get_transaction_count(
            to_checksum_address(local_account_1.address)
        )
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.key)

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        with mock.patch(
            "app.utils.web3_utils.FailOverHTTPProvider.fail_over_mode", True
        ):
            insert_node_data(session, is_synced=False)
            insert_node_data(
                session,
                is_synced=False,
                endpoint_uri="http://localhost:8546",
                priority=1,
            )
            resp = client.post(self.apiurl, headers=headers, json=request_params)
        assert resp.status_code == 503
        assert resp.json()["meta"] == {
            "code": 503,
            "message": "Service Unavailable",
            "description": "Block synchronization is down",
        }

    # <Error_8>
    # Invalid token status
    def test_error_8(self, client: TestClient, session: Session):
        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist["address"]
        issuer = eth_account["issuer"]
        coupontoken_1 = issue_coupon_token(
            issuer,
            {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "totalSupply": 1000000,
                "tradableExchange": config.ZERO_ADDRESS,
                "details": "details_test1",
                "returnDetails": "returnDetails_test1",
                "memo": "memo_test1",
                "expirationDate": "20211201",
                "transferable": True,
                "contactInformation": "contactInformation_test1",
                "privacyPolicy": "privacyPolicy_test1",
            },
        )
        coupon_register_list(issuer, coupontoken_1, tokenlist)

        # Listing,実行可能コントラクト登録
        listing_token(session, coupontoken_1)
        executable_contract_token(session, coupontoken_1)

        token_contract_1 = web3.eth.contract(
            address=to_checksum_address(coupontoken_1["address"]),
            abi=coupontoken_1["abi"],
        )

        # ステータス無効化
        pre_tx = token_contract_1.functions.setStatus(False).build_transaction(
            {
                "from": to_checksum_address(issuer["account_address"]),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx_hash = web3.eth.send_transaction(pre_tx)
        web3.eth.wait_for_transaction_receipt(tx_hash)

        local_account_1 = web3.eth.account.create()

        tx = token_contract_1.functions.consume(10).build_transaction(
            {
                "from": to_checksum_address(local_account_1.address),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx["nonce"] = web3.eth.get_transaction_count(
            to_checksum_address(local_account_1.address)
        )
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.key)

        session.commit()

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {"Content-Type": "application/json"}

        resp = client.post(self.apiurl, headers=headers, json=request_params)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 20,
            "message": "Suspended Token",
            "description": "Token is currently suspended",
        }

    # <Error_9>
    # Non executable contract
    def test_error_9(self, client: TestClient, session: Session):
        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist["address"]
        issuer = eth_account["issuer"]
        coupontoken_1 = issue_coupon_token(
            issuer,
            {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "totalSupply": 1000000,
                "tradableExchange": config.ZERO_ADDRESS,
                "details": "details_test1",
                "returnDetails": "returnDetails_test1",
                "memo": "memo_test1",
                "expirationDate": "20211201",
                "transferable": True,
                "contactInformation": "contactInformation_test1",
                "privacyPolicy": "privacyPolicy_test1",
            },
        )
        coupon_register_list(issuer, coupontoken_1, tokenlist)

        # Listing登録
        listing_token(session, coupontoken_1)

        token_contract_1 = web3.eth.contract(
            address=to_checksum_address(coupontoken_1["address"]),
            abi=coupontoken_1["abi"],
        )

        local_account_1 = web3.eth.account.create()

        tx = token_contract_1.functions.consume(10).build_transaction(
            {
                "from": to_checksum_address(local_account_1.address),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx["nonce"] = web3.eth.get_transaction_count(
            to_checksum_address(local_account_1.address)
        )
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.key)

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {"Content-Type": "application/json"}

        resp = client.post(self.apiurl, headers=headers, json=request_params)

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [{"id": 1, "status": 0, "transaction_hash": None}]

    # <Error_10_1>
    # Transaction failed and revert inspection success
    def test_error_10_1(self, client: TestClient, session: Session):
        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist["address"]
        issuer = eth_account["issuer"]
        coupontoken_1 = issue_coupon_token(
            issuer,
            {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "totalSupply": 1000000,
                "tradableExchange": config.ZERO_ADDRESS,
                "details": "details_test1",
                "returnDetails": "returnDetails_test1",
                "memo": "memo_test1",
                "expirationDate": "20211201",
                "transferable": True,
                "contactInformation": "contactInformation_test1",
                "privacyPolicy": "privacyPolicy_test1",
            },
        )
        coupon_register_list(issuer, coupontoken_1, tokenlist)

        # Listing,実行可能コントラクト登録
        listing_token(session, coupontoken_1)
        executable_contract_token(session, coupontoken_1)

        token_contract_1 = web3.eth.contract(
            address=to_checksum_address(coupontoken_1["address"]),
            abi=coupontoken_1["abi"],
        )

        local_account_1 = web3.eth.account.create()

        # NOTE: 残高なしの状態でクーポン消費
        tx = token_contract_1.functions.consume(10).build_transaction(
            {
                "from": to_checksum_address(local_account_1.address),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx["nonce"] = web3.eth.get_transaction_count(
            to_checksum_address(local_account_1.address)
        )
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.key)

        session.commit()

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {"Content-Type": "application/json"}

        with mock.patch(
            "app.api.routers.eth.inspect_tx_failure", return_value="130401"
        ):
            resp = client.post(self.apiurl, headers=headers, json=request_params)

            assert resp.status_code == 200
            assert resp.json()["meta"] == {"code": 200, "message": "OK"}
            assert resp.json()["data"] == [
                {
                    "id": 1,
                    "status": 0,
                    "transaction_hash": ANY,
                    "error_code": 130401,
                    "error_msg": "Message sender balance is insufficient.",
                }
            ]

    # <Error_10_2>
    # Transaction failed and revert inspection success(no error code)
    def test_error_10_2(
        self, client: TestClient, session: Session, caplog: pytest.LogCaptureFixture
    ):
        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist["address"]
        issuer = eth_account["issuer"]
        coupontoken_1 = issue_coupon_token(
            issuer,
            {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "totalSupply": 1000000,
                "tradableExchange": config.ZERO_ADDRESS,
                "details": "details_test1",
                "returnDetails": "returnDetails_test1",
                "memo": "memo_test1",
                "expirationDate": "20211201",
                "transferable": True,
                "contactInformation": "contactInformation_test1",
                "privacyPolicy": "privacyPolicy_test1",
            },
        )
        coupon_register_list(issuer, coupontoken_1, tokenlist)

        # Listing,実行可能コントラクト登録
        listing_token(session, coupontoken_1)
        executable_contract_token(session, coupontoken_1)

        token_contract_1 = web3.eth.contract(
            address=to_checksum_address(coupontoken_1["address"]),
            abi=coupontoken_1["abi"],
        )

        local_account_1 = web3.eth.account.create()

        # NOTE: 残高なしの状態でクーポン消費
        tx = token_contract_1.functions.consume(10).build_transaction(
            {
                "from": to_checksum_address(local_account_1.address),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx["nonce"] = web3.eth.get_transaction_count(
            to_checksum_address(local_account_1.address)
        )
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.key)

        session.commit()

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {"Content-Type": "application/json"}

        with mock.patch(
            "app.api.routers.eth.inspect_tx_failure",
            return_value="Message sender balance is insufficient.",
        ):
            resp = client.post(self.apiurl, headers=headers, json=request_params)

            assert resp.status_code == 200
            assert resp.json()["meta"] == {"code": 200, "message": "OK"}
            assert resp.json()["data"] == [
                {
                    "id": 1,
                    "status": 0,
                    "transaction_hash": ANY,
                    "error_code": 0,
                    "error_msg": "Message sender balance is insufficient.",
                }
            ]
            assert (
                caplog.record_tuples.count(
                    (
                        log.LOG.name,
                        logging.WARN,
                        "Contract revert detected: code: 0 message: Message sender balance is insufficient.",
                    )
                )
                == 1
            )

    # <Error_10_3>
    # Transaction failed and revert inspection success(no revert message)
    def test_error_10_3(
        self, client: TestClient, session: Session, caplog: pytest.LogCaptureFixture
    ):
        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist["address"]
        issuer = eth_account["issuer"]
        coupontoken_1 = issue_coupon_token(
            issuer,
            {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "totalSupply": 1000000,
                "tradableExchange": config.ZERO_ADDRESS,
                "details": "details_test1",
                "returnDetails": "returnDetails_test1",
                "memo": "memo_test1",
                "expirationDate": "20211201",
                "transferable": True,
                "contactInformation": "contactInformation_test1",
                "privacyPolicy": "privacyPolicy_test1",
            },
        )
        coupon_register_list(issuer, coupontoken_1, tokenlist)

        # Listing,実行可能コントラクト登録
        listing_token(session, coupontoken_1)
        executable_contract_token(session, coupontoken_1)

        token_contract_1 = web3.eth.contract(
            address=to_checksum_address(coupontoken_1["address"]),
            abi=coupontoken_1["abi"],
        )

        local_account_1 = web3.eth.account.create()

        # NOTE: 残高なしの状態でクーポン消費
        tx = token_contract_1.functions.consume(10).build_transaction(
            {
                "from": to_checksum_address(local_account_1.address),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx["nonce"] = web3.eth.get_transaction_count(
            to_checksum_address(local_account_1.address)
        )
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.key)

        session.commit()

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {"Content-Type": "application/json"}

        with mock.patch(
            "app.api.routers.eth.inspect_tx_failure", return_value="execution reverted"
        ):
            resp = client.post(self.apiurl, headers=headers, json=request_params)

            assert resp.status_code == 200
            assert resp.json()["meta"] == {"code": 200, "message": "OK"}
            assert resp.json()["data"] == [
                {
                    "id": 1,
                    "status": 0,
                    "transaction_hash": ANY,
                    "error_code": 0,
                    "error_msg": "execution reverted",
                }
            ]
            assert (
                caplog.record_tuples.count(
                    (
                        log.LOG.name,
                        logging.WARN,
                        "Contract revert detected: code: 0 message: execution reverted",
                    )
                )
                == 1
            )

    # <Error_10_4>
    # Transaction failed and revert inspection failed
    def test_error_10_4(self, client: TestClient, session: Session):
        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist["address"]
        issuer = eth_account["issuer"]
        coupontoken_1 = issue_coupon_token(
            issuer,
            {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "totalSupply": 1000000,
                "tradableExchange": config.ZERO_ADDRESS,
                "details": "details_test1",
                "returnDetails": "returnDetails_test1",
                "memo": "memo_test1",
                "expirationDate": "20211201",
                "transferable": True,
                "contactInformation": "contactInformation_test1",
                "privacyPolicy": "privacyPolicy_test1",
            },
        )
        coupon_register_list(issuer, coupontoken_1, tokenlist)

        # Listing,実行可能コントラクト登録
        listing_token(session, coupontoken_1)
        executable_contract_token(session, coupontoken_1)

        token_contract_1 = web3.eth.contract(
            address=to_checksum_address(coupontoken_1["address"]),
            abi=coupontoken_1["abi"],
        )

        local_account_1 = web3.eth.account.create()

        # NOTE: 残高なしの状態でクーポン消費
        tx = token_contract_1.functions.consume(10).build_transaction(
            {
                "from": to_checksum_address(local_account_1.address),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx["nonce"] = web3.eth.get_transaction_count(
            to_checksum_address(local_account_1.address)
        )
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.key)

        session.commit()

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {"Content-Type": "application/json"}

        with mock.patch.object(eth.async_web3.eth, "get_transaction", ConnectionError):
            resp = client.post(self.apiurl, headers=headers, json=request_params)

            assert resp.status_code == 200
            assert resp.json()["meta"] == {"code": 200, "message": "OK"}
            assert resp.json()["data"] == [
                {"id": 1, "status": 0, "transaction_hash": ANY}
            ]

    # <Error_11>
    # waitForTransactionReceipt error
    def test_error_11(self, client: TestClient, session: Session):
        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist["address"]
        issuer = eth_account["issuer"]
        coupontoken_1 = issue_coupon_token(
            issuer,
            {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "totalSupply": 1000000,
                "tradableExchange": config.ZERO_ADDRESS,
                "details": "details_test1",
                "returnDetails": "returnDetails_test1",
                "memo": "memo_test1",
                "expirationDate": "20211201",
                "transferable": True,
                "contactInformation": "contactInformation_test1",
                "privacyPolicy": "privacyPolicy_test1",
            },
        )
        coupon_register_list(issuer, coupontoken_1, tokenlist)

        # Listing,実行可能コントラクト登録
        listing_token(session, coupontoken_1)
        executable_contract_token(session, coupontoken_1)

        token_contract_1 = web3.eth.contract(
            address=to_checksum_address(coupontoken_1["address"]),
            abi=coupontoken_1["abi"],
        )

        local_account_1 = web3.eth.account.create()

        # テスト用のトランザクション実行前の事前準備
        pre_tx = token_contract_1.functions.transfer(
            to_checksum_address(local_account_1.address), 10
        ).build_transaction(
            {
                "from": to_checksum_address(issuer["account_address"]),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx_hash = web3.eth.send_transaction(pre_tx)
        web3.eth.wait_for_transaction_receipt(tx_hash)

        tx = token_contract_1.functions.consume(10).build_transaction(
            {
                "from": to_checksum_address(local_account_1.address),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx["nonce"] = web3.eth.get_transaction_count(
            to_checksum_address(local_account_1.address)
        )
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.key)

        session.commit()

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {"Content-Type": "application/json"}

        # waitForTransactionReceiptエラー
        with mock.patch(
            "web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            MagicMock(side_effect=Exception()),
        ) as m:
            resp = client.post(self.apiurl, headers=headers, json=request_params)

        # wait_for_transaction_receipt should be called with timeout/poll_latency value from config
        m.assert_called_with(
            signed_tx_1.hash,
            timeout=config.TRANSACTION_WAIT_TIMEOUT,
            poll_latency=config.TRANSACTION_WAIT_POLL_LATENCY,
        )
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [{"id": 1, "status": 0, "transaction_hash": ANY}]

    # <Error_12>
    # recover_transaction error
    def test_error_12(self, client: TestClient, session: Session):
        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist["address"]
        issuer = eth_account["issuer"]
        coupontoken_1 = issue_coupon_token(
            issuer,
            {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "totalSupply": 1000000,
                "tradableExchange": config.ZERO_ADDRESS,
                "details": "details_test1",
                "returnDetails": "returnDetails_test1",
                "memo": "memo_test1",
                "expirationDate": "20211201",
                "transferable": True,
                "contactInformation": "contactInformation_test1",
                "privacyPolicy": "privacyPolicy_test1",
            },
        )
        coupon_register_list(issuer, coupontoken_1, tokenlist)

        # Listing,実行可能コントラクト登録
        listing_token(session, coupontoken_1)
        executable_contract_token(session, coupontoken_1)

        token_contract_1 = web3.eth.contract(
            address=to_checksum_address(coupontoken_1["address"]),
            abi=coupontoken_1["abi"],
        )

        local_account_1 = web3.eth.account.create()

        # テスト用のトランザクション実行前の事前準備
        pre_tx = token_contract_1.functions.transfer(
            to_checksum_address(local_account_1.address), 10
        ).build_transaction(
            {
                "from": to_checksum_address(issuer["account_address"]),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx_hash = web3.eth.send_transaction(pre_tx)
        web3.eth.wait_for_transaction_receipt(tx_hash)

        tx = token_contract_1.functions.consume(10).build_transaction(
            {
                "from": to_checksum_address(local_account_1.address),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx["nonce"] = web3.eth.get_transaction_count(
            to_checksum_address(local_account_1.address)
        )
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.key)

        # waitForTransactionReceiptエラー
        mock.patch.object(
            web3.eth,
            "waitForTransactionReceipt",
            MagicMock(side_effect=TimeExhausted()),
        )
        mock.patch.object(
            web3.eth.account, "recover_transaction", MagicMock(side_effect=Exception())
        )

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {"Content-Type": "application/json"}

        # タイムアウト
        # recover_transactionエラー
        with mock.patch(
            "web3.eth.Eth.wait_for_transaction_receipt",
            MagicMock(side_effect=TimeExhausted()),
        ), mock.patch(
            "eth_account.Account.recover_transaction",
            MagicMock(side_effect=Exception()),
        ):
            resp = client.post(self.apiurl, headers=headers, json=request_params)

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [{"id": 1, "status": 0, "transaction_hash": ANY}]

    # <Error_13>
    # Transaction timeout, no transition to pending
    def test_error_13(self, client: TestClient, session: Session):
        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist["address"]
        issuer = eth_account["issuer"]
        coupontoken_1 = issue_coupon_token(
            issuer,
            {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "totalSupply": 1000000,
                "tradableExchange": config.ZERO_ADDRESS,
                "details": "details_test1",
                "returnDetails": "returnDetails_test1",
                "memo": "memo_test1",
                "expirationDate": "20211201",
                "transferable": True,
                "contactInformation": "contactInformation_test1",
                "privacyPolicy": "privacyPolicy_test1",
            },
        )
        coupon_register_list(issuer, coupontoken_1, tokenlist)

        # Listing,実行可能コントラクト登録
        listing_token(session, coupontoken_1)
        executable_contract_token(session, coupontoken_1)

        token_contract_1 = web3.eth.contract(
            address=to_checksum_address(coupontoken_1["address"]),
            abi=coupontoken_1["abi"],
        )

        local_account_1 = web3.eth.account.create()

        # テスト用のトランザクション実行前の事前準備
        pre_tx = token_contract_1.functions.transfer(
            to_checksum_address(local_account_1.address), 10
        ).build_transaction(
            {
                "from": to_checksum_address(issuer["account_address"]),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx_hash = web3.eth.send_transaction(pre_tx)
        web3.eth.wait_for_transaction_receipt(tx_hash)

        tx = token_contract_1.functions.consume(10).build_transaction(
            {
                "from": to_checksum_address(local_account_1.address),
                "gas": 6000000,
                "gasPrice": 0,
            }
        )
        tx["nonce"] = web3.eth.get_transaction_count(
            to_checksum_address(local_account_1.address)
        )
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.key)

        session.commit()

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {"Content-Type": "application/json"}

        # タイムアウト
        # queuedに滞留
        # NOTE: GanacheにはRPCメソッド:txpool_inspectが存在しないためMock化
        async def mock_inspect():
            return AttributeDict(
                {
                    "pending": AttributeDict({}),
                    "queued": AttributeDict(
                        {
                            to_checksum_address(local_account_1.address): AttributeDict(
                                {
                                    str(
                                        tx["nonce"]
                                    ): "0xffffffffffffffffffffffffffffffffffffffff: 0 wei + 999999 × 11111 gas"
                                }
                            )
                        }
                    ),
                }
            )

        with mock.patch(
            "web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            MagicMock(side_effect=TimeExhausted()),
        ) as m, mock.patch(
            "web3.geth.AsyncGethTxPool.inspect",
            MagicMock(side_effect=[mock_inspect()]),
        ):
            resp = client.post(self.apiurl, headers=headers, json=request_params)

        # wait_for_transaction_receipt should be called with timeout/poll_latency value from config
        m.assert_called_with(
            signed_tx_1.hash,
            timeout=config.TRANSACTION_WAIT_TIMEOUT,
            poll_latency=config.TRANSACTION_WAIT_POLL_LATENCY,
        )

        # wait_for_transaction_receipt should be called with timeout/poll_latency value from config
        m.assert_called_with(
            signed_tx_1.hash,
            timeout=config.TRANSACTION_WAIT_TIMEOUT,
            poll_latency=config.TRANSACTION_WAIT_POLL_LATENCY,
        )

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [{"id": 1, "status": 0, "transaction_hash": ANY}]
