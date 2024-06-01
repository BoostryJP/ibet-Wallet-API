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
from tests.contract_modules import bond_invalidate, issue_bond_token, register_bond_list

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class TestTokenStraightBondTokenDetails:
    """
    Test Case for token.StraightBondTokenDetails
    """

    # Target API
    apiurl_base = "/Token/StraightBond/"  # {contract_address}

    @staticmethod
    def bond_token_attribute(exchange_address, personal_info_address):
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
            "returnAmount": "商品券をプレゼント",
            "purpose": "新商品の開発資金として利用。",
            "memo": "メモ",
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
            "personalInfoAddress": personal_info_address,
            "requirePersonalInfoRegistered": False,
            "faceValueCurrency": "JPY",
            "interestPaymentCurrency": "JPY",
            "redemptionValueCurrency": "JPY",
            "baseFxRate": "",
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
    @mock.patch("app.config.BOND_TOKEN_ENABLED", True)
    def test_normal_1(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]

        # Set up TokenList contract
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # Issue token
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = self.bond_token_attribute(exchange_address, personal_info)
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)

        # Register tokens on the list
        self.list_token(session, bond_token)

        session.commit()

        # Request target API
        apiurl = self.apiurl_base + bond_token["address"]
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        # Assertion
        assumed_body = {
            "token_address": bond_token["address"],
            "token_template": "IbetStraightBond",
            "owner_address": issuer["account_address"],
            "company_name": "",
            "rsa_publickey": "",
            "name": "テスト債券",
            "symbol": "BOND",
            "total_supply": 1000000,
            "face_value": 10000,
            "interest_rate": 0.0602,
            "interest_payment_date1": "0101",
            "interest_payment_date2": "0201",
            "interest_payment_date3": "0301",
            "interest_payment_date4": "0401",
            "interest_payment_date5": "0501",
            "interest_payment_date6": "0601",
            "interest_payment_date7": "0701",
            "interest_payment_date8": "0801",
            "interest_payment_date9": "0901",
            "interest_payment_date10": "1001",
            "interest_payment_date11": "1101",
            "interest_payment_date12": "1201",
            "is_redeemed": False,
            "redemption_date": "20191231",
            "redemption_value": 10000,
            "return_date": "20191231",
            "return_amount": "商品券をプレゼント",
            "purpose": "新商品の開発資金として利用。",
            "is_offering": False,
            "max_holding_quantity": 1,
            "max_sell_amount": 1000,
            "contact_information": "問い合わせ先",
            "privacy_policy": "プライバシーポリシー",
            "transferable": True,
            "tradable_exchange": exchange_address,
            "status": True,
            "memo": "メモ",
            "personal_info_address": personal_info,
            "require_personal_info_registered": False,
            "transfer_approval_required": False,
            "face_value_currency": "JPY",
            "interest_payment_currency": "JPY",
            "redemption_value_currency": "JPY",
            "base_fx_rate": 0.0,
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_2
    @mock.patch("app.config.BOND_TOKEN_ENABLED", True)
    def test_normal_2(self, client: TestClient, session: Session, shared_contract):
        issuer = eth_account["issuer"]

        # Set up TokenList contract
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # Issue token
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = self.bond_token_attribute(exchange_address, personal_info)
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)

        # Register tokens on the list
        self.list_token(session, bond_token)

        # Invalidate token
        bond_invalidate(issuer, bond_token)

        session.commit()

        # Request target API
        apiurl = self.apiurl_base + bond_token["address"]
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        # Assertion
        assumed_body = {
            "token_address": bond_token["address"],
            "token_template": "IbetStraightBond",
            "owner_address": issuer["account_address"],
            "company_name": "",
            "rsa_publickey": "",
            "name": "テスト債券",
            "symbol": "BOND",
            "total_supply": 1000000,
            "face_value": 10000,
            "interest_rate": 0.0602,
            "interest_payment_date1": "0101",
            "interest_payment_date2": "0201",
            "interest_payment_date3": "0301",
            "interest_payment_date4": "0401",
            "interest_payment_date5": "0501",
            "interest_payment_date6": "0601",
            "interest_payment_date7": "0701",
            "interest_payment_date8": "0801",
            "interest_payment_date9": "0901",
            "interest_payment_date10": "1001",
            "interest_payment_date11": "1101",
            "interest_payment_date12": "1201",
            "is_redeemed": False,
            "redemption_date": "20191231",
            "redemption_value": 10000,
            "return_date": "20191231",
            "return_amount": "商品券をプレゼント",
            "purpose": "新商品の開発資金として利用。",
            "is_offering": False,
            "max_holding_quantity": 1,
            "max_sell_amount": 1000,
            "contact_information": "問い合わせ先",
            "privacy_policy": "プライバシーポリシー",
            "transferable": True,
            "tradable_exchange": exchange_address,
            "status": False,
            "memo": "メモ",
            "personal_info_address": personal_info,
            "require_personal_info_registered": False,
            "transfer_approval_required": False,
            "face_value_currency": "JPY",
            "interest_payment_currency": "JPY",
            "redemption_value_currency": "JPY",
            "base_fx_rate": 0.0,
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
        config.BOND_TOKEN_ENABLED = True
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
    @mock.patch("app.config.BOND_TOKEN_ENABLED", True)
    def test_error_2(self, client, shared_contract, session):
        issuer = eth_account["issuer"]

        # Set up TokenList contract
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # Prepare data: issue token
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = self.bond_token_attribute(exchange_address, personal_info)
        token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, token, token_list)

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
    @mock.patch("app.config.BOND_TOKEN_ENABLED", False)
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
            "description": "method: GET, url: /Token/StraightBond/0xe6A75581C7299c75392a63BCF18a3618B30ff765",
        }
