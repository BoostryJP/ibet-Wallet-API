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

from typing import Any
from unittest import mock
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from app.errors import ServiceUnavailable
from tests.account_config import eth_account
from tests.helpers import (
    IbetCouponTestHelper,
    IbetMembershipTestHelper,
    IbetShareTestHelper,
    IbetStraightBondTestHelper,
)
from tests.types import SharedContract

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class TestTokenTokenStatus:
    """
    Test Case for token.TokenStatus
    """

    # テスト対象API
    apiurl_base = "/Token/{contract_address}/Status"

    @staticmethod
    def bond_token_attribute(
        exchange_address: str, personal_info_address: str
    ) -> dict[str, Any]:
        attribute = {
            "name": "テスト債券",
            "symbol": "BOND",
            "totalSupply": 1000000,
            "tradableExchange": exchange_address,
            "faceValue": 10000,
            "interestRate": 602,
            "interestPaymentDate1": "0101",
            "interestPaymentDate2": "0201",
            "interestPaymentDate3": "0301",
            "interestPaymentDate4": "0401",
            "interestPaymentDate5": "0501",
            "interestPaymentDate6": "0601",
            "interestPaymentDate7": "0701",
            "interestPaymentDate8": "0801",
            "interestPaymentDate9": "0901",
            "interestPaymentDate10": "1001",
            "interestPaymentDate11": "1101",
            "interestPaymentDate12": "1201",
            "redemptionDate": "20191231",
            "redemptionValue": 10000,
            "returnDate": "20191231",
            "returnAmount": "BOND商品券をプレゼント",
            "purpose": "BOND新商品の開発資金として利用。",
            "memo": "BONDメモ",
            "contactInformation": "BOND問い合わせ先",
            "privacyPolicy": "BONDプライバシーポリシー",
            "personalInfoAddress": personal_info_address,
            "faceValueCurrency": "JPY",
            "interestPaymentCurrency": "JPY",
            "redemptionValueCurrency": "JPY",
            "baseFxRate": "",
        }
        return attribute

    @staticmethod
    def share_token_attribute(
        exchange_address: str, personal_info_address: str
    ) -> dict[str, Any]:
        attribute = {
            "name": "テスト株式",
            "symbol": "SHARE",
            "tradableExchange": exchange_address,
            "personalInfoAddress": personal_info_address,
            "issuePrice": 100001,
            "principalValue": 100001,
            "totalSupply": 1000001,
            "dividends": 1000,
            "dividendRecordDate": "20201001",
            "dividendPaymentDate": "20201002",
            "cancellationDate": "20201003",
            "contactInformation": "SHARE商品の補足",
            "privacyPolicy": "SHAREプライバシーポリシー",
            "memo": "SHAREメモ",
            "transferable": True,
        }
        return attribute

    @staticmethod
    def membership_token_attribute(exchange_address: str) -> dict[str, Any]:
        attribute = {
            "name": "テスト会員権",
            "symbol": "MEMBERSHIP",
            "initialSupply": 102,
            "tradableExchange": exchange_address,
            "details": "MEMBERSHIP詳細",
            "returnDetails": "MEMBERSHIP特典詳細",
            "expirationDate": "20201101",
            "memo": "MEMBERSHIPメモ",
            "transferable": True,
            "contactInformation": "MEMBERSHIP商品の補足",
            "privacyPolicy": "MEMBERSHIPプライバシーポリシー",
        }
        return attribute

    @staticmethod
    def coupon_token_attribute(exchange_address: str) -> dict[str, Any]:
        attribute = {
            "name": "テストクーポン",
            "symbol": "COUPON",
            "totalSupply": 100003,
            "tradableExchange": exchange_address,
            "details": "COUPON詳細",
            "returnDetails": "COUPON特典詳細",
            "memo": "COUPONメモ",
            "expirationDate": "20201101",
            "transferable": True,
            "contactInformation": "COUPON商品の補足",
            "privacyPolicy": "COUPONプライバシーポリシー",
        }
        return attribute

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    # - IbetStraightBond
    def test_normal_1(self, client: TestClient, shared_contract: SharedContract):
        issuer = eth_account["issuer"]

        token_list = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # Prepare data: Issue new bond
        exchange_address = shared_contract["IbetSecurityTokenEscrow"]["address"]
        personal_info = shared_contract["PersonalInfo"]["address"]
        attribute = self.bond_token_attribute(exchange_address, personal_info)
        bond_token = IbetStraightBondTestHelper.issue(
            issuer["account_address"], attribute
        )
        IbetStraightBondTestHelper.register_token_list(
            issuer["account_address"], bond_token.address, token_list["address"]
        )

        # Call API
        apiurl = self.apiurl_base.format(contract_address=bond_token.address)
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        # Verify response
        assumed_body = {
            "name": "テスト債券",
            "token_template": "IbetStraightBond",
            "owner_address": issuer["account_address"],
            "status": True,
            "transferable": True,
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_2
    # - IbetShare
    def test_normal_2(self, client: TestClient, shared_contract: SharedContract):
        issuer = eth_account["issuer"]

        token_list = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # Prepare data: Issue new share
        exchange_address = shared_contract["IbetSecurityTokenEscrow"]["address"]
        personal_info = shared_contract["PersonalInfo"]["address"]
        attribute = self.share_token_attribute(exchange_address, personal_info)
        share_token = IbetShareTestHelper.issue(issuer["account_address"], attribute)
        IbetShareTestHelper.register_token_list(
            issuer["account_address"], share_token.address, token_list["address"]
        )

        # Call API
        apiurl = self.apiurl_base.format(contract_address=share_token.address)
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        # Verify response
        assumed_body = {
            "name": "テスト株式",
            "token_template": "IbetShare",
            "owner_address": issuer["account_address"],
            "status": True,
            "transferable": True,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_3
    # - IbetMembership
    def test_normal_3(self, client: TestClient, shared_contract: SharedContract):
        issuer = eth_account["issuer"]

        token_list = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # Prepare data: Issue new membership
        exchange_address = shared_contract["IbetSecurityTokenEscrow"]["address"]
        attribute = self.membership_token_attribute(exchange_address)
        membership_token = IbetMembershipTestHelper.issue(
            issuer["account_address"], attribute
        )
        IbetMembershipTestHelper.register_token_list(
            issuer["account_address"], membership_token.address, token_list["address"]
        )

        # Call API
        apiurl = self.apiurl_base.format(contract_address=membership_token.address)
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        # Verify response
        assumed_body = {
            "name": "テスト会員権",
            "token_template": "IbetMembership",
            "owner_address": issuer["account_address"],
            "status": True,
            "transferable": True,
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_4
    # - IbetCoupon
    def test_normal_4(self, client: TestClient, shared_contract: SharedContract):
        issuer = eth_account["issuer"]

        token_list = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # Prepare data: Issue new coupon
        exchange_address = shared_contract["IbetSecurityTokenEscrow"]["address"]
        attribute = self.coupon_token_attribute(exchange_address)
        coupon_token = IbetCouponTestHelper.issue(issuer["account_address"], attribute)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"], coupon_token.address, token_list["address"]
        )

        # Call API
        apiurl = self.apiurl_base.format(contract_address=coupon_token.address)
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        # Verify response
        assumed_body = {
            "name": "テストクーポン",
            "token_template": "IbetCoupon",
            "owner_address": issuer["account_address"],
            "status": True,
            "transferable": True,
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Invalid token address
    # -> 400
    def test_error_1(self, client: TestClient):
        apiurl = self.apiurl_base.format(contract_address="0xabcd")

        query_string = ""
        resp = client.get(apiurl, params=query_string)

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

    # <Error_2>
    # Contract not exists
    # -> 404
    def test_error_2(self, client: TestClient, shared_contract: SharedContract):
        share_exchange = shared_contract["IbetSecurityTokenEscrow"]

        apiurl = self.apiurl_base.format(contract_address=share_exchange["address"])

        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": "token_address: " + share_exchange["address"],
        }

    # <Error_3>
    # ServiceUnavailable
    def test_error_3(self, client: TestClient, shared_contract: SharedContract):
        issuer = eth_account["issuer"]

        token_list = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # Prepare data: Issue new bond
        exchange_address = shared_contract["IbetSecurityTokenEscrow"]["address"]
        personal_info = shared_contract["PersonalInfo"]["address"]
        attribute = self.bond_token_attribute(exchange_address, personal_info)
        bond_token = IbetStraightBondTestHelper.issue(
            issuer["account_address"], attribute
        )
        IbetStraightBondTestHelper.register_token_list(
            issuer["account_address"], bond_token.address, token_list["address"]
        )

        # Call API with mocking ServiceUnavailable
        with mock.patch(
            "web3.contract.async_contract.AsyncContractFunction.call",
            MagicMock(side_effect=ServiceUnavailable()),
        ):
            apiurl = self.apiurl_base.format(contract_address=bond_token.address)
            query_string = ""
            resp = client.get(apiurl, params=query_string)

        # Verify response
        assert resp.status_code == 503
        assert resp.json()["meta"] == {
            "code": 503,
            "message": "Service Unavailable",
            "description": "Service is temporarily unavailable",
        }
