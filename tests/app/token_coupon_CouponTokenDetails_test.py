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

from eth_utils import to_checksum_address
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from app.contracts import Contract
from app.model.db import Listing
from tests.account_config import eth_account
from tests.contract_modules import (
    coupon_register_list,
    invalidate_coupon_token,
    issue_coupon_token,
    membership_issue,
    membership_register_list,
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class TestTokenCouponTokenDetails:
    """
    Test Case for token.CouponTokenDetails
    """

    # Target API
    apiurl_base = "/Token/Coupon/"  # {contract_address}

    @staticmethod
    def coupon_token_attribute(exchange_address):
        attribute = {
            "name": "テストクーポン",
            "symbol": "COUPON",
            "totalSupply": 10000,
            "tradableExchange": exchange_address,
            "details": "クーポン詳細",
            "returnDetails": "リターン詳細",
            "memo": "クーポンメモ欄",
            "expirationDate": "20191231",
            "transferable": True,
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
        }
        return attribute

    @staticmethod
    def membership_token_attribute(exchange_address):
        attribute = {
            "name": "テスト会員権",
            "symbol": "MEMBERSHIP",
            "initialSupply": 1000000,
            "tradableExchange": exchange_address,
            "details": "詳細",
            "returnDetails": "リターン詳細",
            "expirationDate": "20191231",
            "memo": "メモ",
            "transferable": True,
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
        }
        return attribute

    @staticmethod
    def tokenlist_contract():
        deployer = eth_account["deployer"]
        web3.eth.default_account = deployer["account_address"]
        contract_address, abi = Contract.deploy_contract(
            "TokenList", [], deployer["account_address"]
        )
        return {"address": contract_address, "abi": abi}

    @staticmethod
    def list_token(session, token):
        listed_token = Listing()
        listed_token.token_address = token["address"]
        listed_token.is_public = True
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
        session.add(listed_token)

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    @mock.patch("app.config.COUPON_TOKEN_ENABLED", True)
    def test_normal_1(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]

        # Set up TokenList contract
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # Prepare data: issue token
        exchange_address = to_checksum_address(
            shared_contract["IbetCouponExchange"]["address"]
        )
        attribute = self.coupon_token_attribute(exchange_address)
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # Register tokens on the list
        self.list_token(session, token)

        session.commit()

        # Request target API
        apiurl = self.apiurl_base + token["address"]
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        # Assertion
        assumed_body = {
            "token_address": token["address"],
            "token_template": "IbetCoupon",
            "owner_address": issuer["account_address"],
            "company_name": "",
            "rsa_publickey": "",
            "name": "テストクーポン",
            "symbol": "COUPON",
            "total_supply": 10000,
            "details": "クーポン詳細",
            "return_details": "リターン詳細",
            "memo": "クーポンメモ欄",
            "expiration_date": "20191231",
            "transferable": True,
            "status": True,
            "initial_offering_status": False,
            "image_url": [
                {"id": 1, "url": ""},
                {"id": 2, "url": ""},
                {"id": 3, "url": ""},
            ],
            "max_holding_quantity": 1,
            "max_sell_amount": 1000,
            "contact_information": "問い合わせ先",
            "privacy_policy": "プライバシーポリシー",
            "tradable_exchange": exchange_address,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_2
    # status = False
    @mock.patch("app.config.COUPON_TOKEN_ENABLED", True)
    def test_normal_2(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]

        # Set up TokenList contract
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # Prepare data: issue token
        exchange_address = to_checksum_address(
            shared_contract["IbetCouponExchange"]["address"]
        )
        attribute = self.coupon_token_attribute(exchange_address)
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # Register tokens on the list
        self.list_token(session, token)

        # Invalidate token
        invalidate_coupon_token(issuer, token)

        session.commit()

        # Request target API
        apiurl = self.apiurl_base + token["address"]
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        # Assertion
        assumed_body = {
            "token_address": token["address"],
            "token_template": "IbetCoupon",
            "owner_address": issuer["account_address"],
            "company_name": "",
            "rsa_publickey": "",
            "name": "テストクーポン",
            "symbol": "COUPON",
            "total_supply": 10000,
            "details": "クーポン詳細",
            "return_details": "リターン詳細",
            "memo": "クーポンメモ欄",
            "expiration_date": "20191231",
            "transferable": True,
            "status": False,
            "initial_offering_status": False,
            "image_url": [
                {"id": 1, "url": ""},
                {"id": 2, "url": ""},
                {"id": 3, "url": ""},
            ],
            "max_holding_quantity": 1,
            "max_sell_amount": 1000,
            "contact_information": "問い合わせ先",
            "privacy_policy": "プライバシーポリシー",
            "tradable_exchange": exchange_address,
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # Invalid Parameter: invalid contract_address
    # -> 400
    @mock.patch("app.config.COUPON_TOKEN_ENABLED", True)
    def test_error_1(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base + "0xabcd"

        # Request target API
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["path", "token_address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": "0xabcd",
                    "ctx": {"error": {}},
                }
            ],
        }

    # Error_2
    # Not registered on the list
    # -> 404
    @mock.patch("app.config.COUPON_TOKEN_ENABLED", True)
    def test_error_2(self, client, shared_contract, session):
        issuer = eth_account["issuer"]

        # Set up TokenList contract
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # Prepare data: issue token
        exchange_address = to_checksum_address(
            shared_contract["IbetCouponExchange"]["address"]
        )
        attribute = self.coupon_token_attribute(exchange_address)
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        session.commit()

        # Request target API
        apiurl = self.apiurl_base + token["address"]
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        # Assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": "token_address: " + token["address"],
        }

    # Error_3
    # Not Supported
    # -> 404
    @mock.patch("app.config.COUPON_TOKEN_ENABLED", False)
    def test_error_3(self, client: TestClient, session: Session):
        # Request target API
        resp = client.get(
            self.apiurl_base + "0xe6A75581C7299c75392a63BCF18a3618B30ff765"
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /Token/Coupon/0xe6A75581C7299c75392a63BCF18a3618B30ff765",
        }

    # Error_4
    # Retrieve the token address of other token type
    # -> 404
    @mock.patch("app.config.COUPON_TOKEN_ENABLED", True)
    def test_error_4(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]

        # Set up TokenList contract
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # Prepare data: issue token
        exchange_address = to_checksum_address(
            shared_contract["IbetCouponExchange"]["address"]
        )
        attribute = self.membership_token_attribute(exchange_address)
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)

        # Register tokens on the list
        self.list_token(session, token)

        session.commit()

        # Request target API
        apiurl = self.apiurl_base + token["address"]
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        # Assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "description": f"token_address: {token['address']}",
            "message": "Data Not Exists",
        }
