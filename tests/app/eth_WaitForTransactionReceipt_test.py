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

from unittest import mock

from eth_utils.address import to_checksum_address
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import TxParams, Wei

from app import config
from app.model.db import ExecutableContract, Listing
from tests.account_config import eth_account
from tests.helpers import IbetCouponTestHelper
from tests.types import SharedContract

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


def _tx_params(from_address: str) -> TxParams:
    return {"from": from_address, "gas": 6000000, "gasPrice": Wei(0)}


def listing_token(session: Session, token_address: str) -> None:
    listing = Listing()
    listing.token_address = token_address
    listing.is_public = True
    listing.max_holding_quantity = 1
    listing.max_sell_amount = 1000
    listing.owner_address = "0x0000000000000000000000000000000000000000"
    session.add(listing)


def executable_contract_token(session: Session, contract_address: str) -> None:
    executable_contract = ExecutableContract()
    executable_contract.contract_address = contract_address
    session.add(executable_contract)


class TestEthWaitForTransactionReceipt:
    # テスト対象API
    apiurl = "/Eth/WaitForTransactionReceipt"

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # Wait receipt for successful transaction
    def test_normal_1(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        # Issue a token
        tokenlist = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist["address"]

        issuer = eth_account["issuer"]
        coupontoken_1 = IbetCouponTestHelper.issue(
            issuer["account_address"],
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
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"], coupontoken_1.address, tokenlist["address"]
        )

        # List the issued token
        listing_token(session, coupontoken_1.address)
        executable_contract_token(session, coupontoken_1.address)

        # Send a test transaction
        user1 = eth_account["user1"]
        IbetCouponTestHelper.transfer_token(
            issuer["account_address"],
            coupontoken_1.address,
            user1["account_address"],
            10,
        )
        tx = coupontoken_1.functions.consume(10).build_transaction(
            _tx_params(to_checksum_address(user1["account_address"]))
        )
        tx_hash = web3.eth.send_transaction(tx)

        # Call API
        resp = client.get(self.apiurl, params={"transaction_hash": tx_hash.to_0x_hex()})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {"status": 1}

    # <Normal_2>
    # Wait receipt for reverted transaction
    def test_normal_2(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        # Issue a token
        tokenlist = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist["address"]

        issuer = eth_account["issuer"]
        coupontoken_1 = IbetCouponTestHelper.issue(
            issuer["account_address"],
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
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"], coupontoken_1.address, tokenlist["address"]
        )

        # List the issued token
        listing_token(session, coupontoken_1.address)
        executable_contract_token(session, coupontoken_1.address)

        # Send a test transaction
        # NOTE: Coupon consumption with no balance -> Revert
        user1 = eth_account["user1"]
        tx = coupontoken_1.functions.consume(10000).build_transaction(
            _tx_params(to_checksum_address(user1["account_address"]))
        )
        tx_hash = web3.eth.send_transaction(tx)

        # Request the target API
        with mock.patch(
            "app.api.routers.eth.inspect_tx_failure", return_value="130401"
        ):
            resp = client.get(
                self.apiurl, params={"transaction_hash": tx_hash.to_0x_hex()}
            )

            # Assertion
            assert resp.status_code == 200
            assert resp.json()["meta"] == {"code": 200, "message": "OK"}
            assert resp.json()["data"] == {
                "status": 0,
                "error_code": 130401,
                "error_msg": "Message sender balance is insufficient.",
            }

    ###################################################################
    # Error
    ###################################################################

    # Error_1
    # Data Not Exists
    # Without timeout setting
    def test_error_1(self, client: TestClient, session: Session):
        # Request the target API
        resp = client.get(
            self.apiurl,
            params={
                "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455"
            },
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {"code": 30, "message": "Data Not Exists"}

    # Error_2
    # Data Not Exists
    # With timeout setting
    def test_error_2(self, client: TestClient, session: Session):
        # Request the target API
        resp = client.get(
            self.apiurl,
            params={
                "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455",
                "timeout": 1,
            },
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {"code": 30, "message": "Data Not Exists"}

    # Error_3
    # Method Not Allowed
    def test_error_3(self, client: TestClient, session: Session):
        resp = client.post(self.apiurl)

        assert resp.status_code == 405
        assert resp.json()["meta"] == {
            "code": 1,
            "message": "Method Not Allowed",
            "description": "method: POST, url: /Eth/WaitForTransactionReceipt",
        }

    # Error_4_1
    # Invalid Parameter
    # `timeout` is greater than or equal to 1
    def test_error_4_1(self, client: TestClient, session: Session):
        # Request the target API
        request_params = {
            "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455",
            "timeout": 0,
        }
        resp = client.get(self.apiurl, params=request_params)

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"ge": 1},
                    "input": "0",
                    "loc": ["query", "timeout"],
                    "msg": "Input should be greater than or equal to 1",
                    "type": "greater_than_equal",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_4_2
    # Invalid Parameter
    # `timeout` is less than or equal to 30
    def test_error_4_2(self, client: TestClient, session: Session):
        # Request the target API
        request_params = {
            "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455",
            "timeout": 31,
        }
        resp = client.get(self.apiurl, params=request_params)

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"le": 30},
                    "input": "31",
                    "loc": ["query", "timeout"],
                    "msg": "Input should be less than or equal to 30",
                    "type": "less_than_equal",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_4_3
    # Invalid Parameter
    # type_error: timeout
    def test_error_4_3(self, client: TestClient, session: Session):
        request_params = {
            "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455",
            "timeout": "aaaa",
        }
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": "aaaa",
                    "loc": ["query", "timeout"],
                    "msg": "Input should be a valid integer, unable to parse "
                    "string as an integer",
                    "type": "int_parsing",
                }
            ],
            "message": "Invalid Parameter",
        }
