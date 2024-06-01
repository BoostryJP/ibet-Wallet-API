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
    invalidate_share_token,
    issue_share_token,
    register_share_list,
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class TestTokenShareTokenDetails:
    """
    Test Case for token.ShareTokenDetails
    """

    # Target API
    apiurl_base = "/Token/Share/"  # {contract_address}

    @staticmethod
    def share_token_attribute(exchange_address, personal_info_address):
        attribute = {
            "name": "テスト株式",
            "symbol": "SHARE",
            "tradableExchange": exchange_address,
            "personalInfoAddress": personal_info_address,
            "requirePersonalInfoRegistered": False,
            "totalSupply": 1000000,
            "issuePrice": 10000,
            "principalValue": 10000,
            "dividends": 101,
            "dividendRecordDate": "20200909",
            "dividendPaymentDate": "20201001",
            "cancellationDate": "20210101",
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
            "memo": "メモ",
            "transferable": True,
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
    @mock.patch("app.config.SHARE_TOKEN_ENABLED", True)
    def test_normal_1(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]

        # Set up TokenList contract
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # Issue token
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = self.share_token_attribute(exchange_address, personal_info)
        share_token = issue_share_token(issuer, attribute)
        register_share_list(issuer, share_token, token_list)

        # Register tokens on the list
        self.list_token(session, share_token)

        session.commit()

        # Request target API
        apiurl = self.apiurl_base + share_token["address"]
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        # Assertion
        assumed_body = {
            "token_address": share_token["address"],
            "token_template": "IbetShare",
            "owner_address": issuer["account_address"],
            "company_name": "",
            "rsa_publickey": "",
            "name": "テスト株式",
            "symbol": "SHARE",
            "total_supply": 1000000,
            "issue_price": 10000,
            "principal_value": 10000,
            "dividend_information": {
                "dividends": 0.0000000000101,
                "dividend_record_date": "20200909",
                "dividend_payment_date": "20201001",
            },
            "cancellation_date": "20210101",
            "is_offering": False,
            "memo": "メモ",
            "max_holding_quantity": 1,
            "max_sell_amount": 1000,
            "contact_information": "問い合わせ先",
            "privacy_policy": "プライバシーポリシー",
            "transferable": True,
            "status": True,
            "transfer_approval_required": False,
            "is_canceled": False,
            "tradable_exchange": exchange_address,
            "personal_info_address": personal_info,
            "require_personal_info_registered": False,
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_2
    # status = False
    @mock.patch("app.config.SHARE_TOKEN_ENABLED", True)
    def test_normal_2(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]

        # Set up TokenList contract
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # Issue token
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = self.share_token_attribute(exchange_address, personal_info)
        share_token = issue_share_token(issuer, attribute)
        register_share_list(issuer, share_token, token_list)

        # Register tokens on the list
        self.list_token(session, share_token)

        # Invalidate token
        invalidate_share_token(issuer, share_token)

        session.commit()

        # Request target API
        apiurl = self.apiurl_base + share_token["address"]
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        # Assertion
        assumed_body = {
            "token_address": share_token["address"],
            "token_template": "IbetShare",
            "owner_address": issuer["account_address"],
            "company_name": "",
            "rsa_publickey": "",
            "name": "テスト株式",
            "symbol": "SHARE",
            "total_supply": 1000000,
            "issue_price": 10000,
            "principal_value": 10000,
            "dividend_information": {
                "dividends": 0.0000000000101,
                "dividend_record_date": "20200909",
                "dividend_payment_date": "20201001",
            },
            "cancellation_date": "20210101",
            "is_offering": False,
            "memo": "メモ",
            "max_holding_quantity": 1,
            "max_sell_amount": 1000,
            "contact_information": "問い合わせ先",
            "privacy_policy": "プライバシーポリシー",
            "transferable": True,
            "status": False,
            "transfer_approval_required": False,
            "is_canceled": False,
            "tradable_exchange": exchange_address,
            "personal_info_address": personal_info,
            "require_personal_info_registered": False,
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
    @mock.patch("app.config.SHARE_TOKEN_ENABLED", True)
    def test_error_2(self, client, shared_contract, session):
        issuer = eth_account["issuer"]

        # Set up TokenList contract
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # Prepare data: issue token
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = self.share_token_attribute(exchange_address, personal_info)
        token = issue_share_token(issuer, attribute)
        register_share_list(issuer, token, token_list)

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
    @mock.patch("app.config.SHARE_TOKEN_ENABLED", False)
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
            "description": "method: GET, url: /Token/Share/0xe6A75581C7299c75392a63BCF18a3618B30ff765",
        }
