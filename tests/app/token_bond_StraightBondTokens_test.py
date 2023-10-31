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
import pytest
from eth_utils import to_checksum_address
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.contracts import Contract
from app.model.db import IDXTokenListItem, Listing
from batch import indexer_Token_Detail
from batch.indexer_Token_Detail import Processor
from tests.account_config import eth_account
from tests.contract_modules import issue_bond_token, register_bond_list

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    indexer_Token_Detail.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"][
        "address"
    ]
    return indexer_Token_Detail


@pytest.fixture(scope="function")
def processor(test_module, session):
    config.BOND_TOKEN_ENABLED = True
    processor = test_module.Processor()
    return processor


class TestTokenStraightBondTokens:
    """
    Test Case for token.StraightBondTokens
    """

    # テスト対象API
    apiurl = "/Token/StraightBond"

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
        token_list_item = IDXTokenListItem()
        token_list_item.token_address = token["address"]
        token_list_item.token_template = "IbetStraightBond"
        token_list_item.owner_address = ""
        session.add(token_list_item)
        session.commit()

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1_1>
    # List all tokens
    def test_normal_1_1(
        self,
        client: TestClient,
        session: Session,
        shared_contract,
        processor: Processor,
    ):
        config.BOND_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = self.bond_token_attribute(exchange_address, personal_info)
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, bond_token)

        # 事前準備
        processor.SEC_PER_RECORD = 0
        processor.process()

        query_string = ""
        resp = client.get(self.apiurl, params=query_string)
        tokens = [
            {
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
                "transfer_approval_required": False,
                "face_value_currency": "JPY",
                "interest_payment_currency": "JPY",
                "redemption_value_currency": "JPY",
                "base_fx_rate": 0.0,
            }
        ]

        assumed_body = {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 1},
            "tokens": tokens,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_1_2>
    # List specific tokens with query
    def test_normal_1_2(
        self,
        client: TestClient,
        session: Session,
        shared_contract,
        processor: Processor,
    ):
        config.BOND_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])

        token_address_list = []

        attribute_token1 = self.bond_token_attribute(
            exchange_address,
            personal_info,
        )
        attribute_token1["name"] = "テスト債券1"
        bond_token1 = issue_bond_token(issuer, attribute_token1)
        token_address_list.append(bond_token1["address"])
        register_bond_list(issuer, bond_token1, token_list)

        attribute_token2 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token2["name"] = "テスト債券2"
        bond_token2 = issue_bond_token(issuer, attribute_token2)
        token_address_list.append(bond_token2["address"])
        register_bond_list(issuer, bond_token2, token_list)

        attribute_token3 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token3["name"] = "テスト債券3"
        bond_token3 = issue_bond_token(issuer, attribute_token3)
        token_address_list.append(bond_token3["address"])
        register_bond_list(issuer, bond_token3, token_list)

        attribute_token4 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token4["name"] = "テスト債券4"
        bond_token4 = issue_bond_token(issuer, attribute_token4)
        token_address_list.append(bond_token4["address"])
        register_bond_list(issuer, bond_token4, token_list)

        attribute_token5 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token5["name"] = "テスト債券5"
        bond_token5 = issue_bond_token(issuer, attribute_token5)
        token_address_list.append(bond_token5["address"])
        register_bond_list(issuer, bond_token5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, bond_token1)
        self.list_token(session, bond_token2)
        self.list_token(session, bond_token3)
        self.list_token(session, bond_token4)
        self.list_token(session, bond_token5)

        # 事前準備
        processor.SEC_PER_RECORD = 1
        processor.process()

        target_token_addrss_list = token_address_list[1:4]

        resp = client.get(
            self.apiurl, params={"address_list": target_token_addrss_list}
        )

        tokens = [
            {
                "token_address": token_address_list[i],
                "token_template": "IbetStraightBond",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": f"テスト債券{i+1}",
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
                "transfer_approval_required": False,
                "face_value_currency": "JPY",
                "interest_payment_currency": "JPY",
                "redemption_value_currency": "JPY",
                "base_fx_rate": 0.0,
            }
            for i in range(1, 4)
        ]

        assumed_body = {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 3},
            "tokens": tokens,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_2>
    # Pagination
    def test_normal_2(
        self,
        client: TestClient,
        session: Session,
        shared_contract,
        processor: Processor,
    ):
        config.BOND_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])

        token_address_list = []

        attribute_token1 = self.bond_token_attribute(
            exchange_address,
            personal_info,
        )
        attribute_token1["name"] = "テスト債券1"
        bond_token1 = issue_bond_token(issuer, attribute_token1)
        token_address_list.append(bond_token1["address"])
        register_bond_list(issuer, bond_token1, token_list)

        attribute_token2 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token2["name"] = "テスト債券2"
        bond_token2 = issue_bond_token(issuer, attribute_token2)
        token_address_list.append(bond_token2["address"])
        register_bond_list(issuer, bond_token2, token_list)

        attribute_token3 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token3["name"] = "テスト債券3"
        bond_token3 = issue_bond_token(issuer, attribute_token3)
        token_address_list.append(bond_token3["address"])
        register_bond_list(issuer, bond_token3, token_list)

        attribute_token4 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token4["name"] = "テスト債券4"
        bond_token4 = issue_bond_token(issuer, attribute_token4)
        token_address_list.append(bond_token4["address"])
        register_bond_list(issuer, bond_token4, token_list)

        attribute_token5 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token5["name"] = "テスト債券5"
        bond_token5 = issue_bond_token(issuer, attribute_token5)
        token_address_list.append(bond_token5["address"])
        register_bond_list(issuer, bond_token5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, bond_token1)
        self.list_token(session, bond_token2)
        self.list_token(session, bond_token3)
        self.list_token(session, bond_token4)
        self.list_token(session, bond_token5)

        # 事前準備
        processor.SEC_PER_RECORD = 1
        processor.process()

        resp = client.get(
            self.apiurl,
            params={
                "offset": 1,
                "limit": 2,
            },
        )
        tokens = [
            {
                "token_address": token_address_list[i],
                "token_template": "IbetStraightBond",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": f"テスト債券{i+1}",
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
                "transfer_approval_required": False,
                "face_value_currency": "JPY",
                "interest_payment_currency": "JPY",
                "redemption_value_currency": "JPY",
                "base_fx_rate": 0.0,
            }
            for i in range(1, 3)
        ]

        assumed_body = {
            "result_set": {"count": 5, "offset": 1, "limit": 2, "total": 5},
            "tokens": tokens,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_3>
    # Pagination(over offset)
    def test_normal_3(
        self,
        client: TestClient,
        session: Session,
        shared_contract,
        processor: Processor,
    ):
        config.BOND_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])

        token_address_list = []

        attribute_token1 = self.bond_token_attribute(
            exchange_address,
            personal_info,
        )
        attribute_token1["name"] = "テスト債券1"
        bond_token1 = issue_bond_token(issuer, attribute_token1)
        token_address_list.append(bond_token1["address"])
        register_bond_list(issuer, bond_token1, token_list)

        attribute_token2 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token2["name"] = "テスト債券2"
        bond_token2 = issue_bond_token(issuer, attribute_token2)
        token_address_list.append(bond_token2["address"])
        register_bond_list(issuer, bond_token2, token_list)

        attribute_token3 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token3["name"] = "テスト債券3"
        bond_token3 = issue_bond_token(issuer, attribute_token3)
        token_address_list.append(bond_token3["address"])
        register_bond_list(issuer, bond_token3, token_list)

        attribute_token4 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token4["name"] = "テスト債券4"
        bond_token4 = issue_bond_token(issuer, attribute_token4)
        token_address_list.append(bond_token4["address"])
        register_bond_list(issuer, bond_token4, token_list)

        attribute_token5 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token5["name"] = "テスト債券5"
        bond_token5 = issue_bond_token(issuer, attribute_token5)
        token_address_list.append(bond_token5["address"])
        register_bond_list(issuer, bond_token5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, bond_token1)
        self.list_token(session, bond_token2)
        self.list_token(session, bond_token3)
        self.list_token(session, bond_token4)
        self.list_token(session, bond_token5)

        # 事前準備
        processor.SEC_PER_RECORD = 0
        processor.process()

        resp = client.get(self.apiurl, params={"offset": 7})
        tokens = []

        assumed_body = {
            "result_set": {"count": 5, "offset": 7, "limit": None, "total": 5},
            "tokens": tokens,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_4>
    # Search Filter
    def test_normal_4(
        self,
        client: TestClient,
        session: Session,
        shared_contract,
        processor: Processor,
    ):
        config.BOND_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])

        token_address_list = []

        attribute_token1 = self.bond_token_attribute(
            exchange_address,
            personal_info,
        )
        attribute_token1["name"] = "テスト債券1"
        bond_token1 = issue_bond_token(issuer, attribute_token1)
        token_address_list.append(bond_token1["address"])
        register_bond_list(issuer, bond_token1, token_list)

        attribute_token2 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token2["name"] = "テスト債券2"
        bond_token2 = issue_bond_token(issuer, attribute_token2)
        token_address_list.append(bond_token2["address"])
        register_bond_list(issuer, bond_token2, token_list)

        attribute_token3 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token3["name"] = "テスト債券3"
        bond_token3 = issue_bond_token(issuer, attribute_token3)
        token_address_list.append(bond_token3["address"])
        register_bond_list(issuer, bond_token3, token_list)

        attribute_token4 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token4["name"] = "テスト債券4"
        bond_token4 = issue_bond_token(issuer, attribute_token4)
        token_address_list.append(bond_token4["address"])
        register_bond_list(issuer, bond_token4, token_list)

        attribute_token5 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token5["name"] = "テスト債券5"
        bond_token5 = issue_bond_token(issuer, attribute_token5)
        token_address_list.append(bond_token5["address"])
        register_bond_list(issuer, bond_token5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, bond_token1)
        self.list_token(session, bond_token2)
        self.list_token(session, bond_token3)
        self.list_token(session, bond_token4)
        self.list_token(session, bond_token5)

        # 事前準備
        processor.SEC_PER_RECORD = 1
        processor.process()

        resp = client.get(
            self.apiurl,
            params={
                "name": "テスト債券",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "symbol": "BO",
                "is_redeemed": False,
                "is_offering": False,
                "transferable": True,
                "tradable_exchange": exchange_address,
                "status": True,
                "personal_info_address": personal_info,
                "transfer_approval_required": False,
            },
        )
        tokens = [
            {
                "token_address": token_address_list[i],
                "token_template": "IbetStraightBond",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": f"テスト債券{i+1}",
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
                "transfer_approval_required": False,
                "face_value_currency": "JPY",
                "interest_payment_currency": "JPY",
                "redemption_value_currency": "JPY",
                "base_fx_rate": 0.0,
            }
            for i in range(0, 5)
        ]

        assumed_body = {
            "result_set": {"count": 5, "offset": None, "limit": None, "total": 5},
            "tokens": tokens,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_5>
    # Search Filter(not hit)
    def test_normal_5(
        self,
        client: TestClient,
        session: Session,
        shared_contract,
        processor: Processor,
    ):
        config.BOND_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])

        token_address_list = []

        attribute_token1 = self.bond_token_attribute(
            exchange_address,
            personal_info,
        )
        attribute_token1["name"] = "テスト債券1"
        bond_token1 = issue_bond_token(issuer, attribute_token1)
        token_address_list.append(bond_token1["address"])
        register_bond_list(issuer, bond_token1, token_list)

        attribute_token2 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token2["name"] = "テスト債券2"
        bond_token2 = issue_bond_token(issuer, attribute_token2)
        token_address_list.append(bond_token2["address"])
        register_bond_list(issuer, bond_token2, token_list)

        attribute_token3 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token3["name"] = "テスト債券3"
        bond_token3 = issue_bond_token(issuer, attribute_token3)
        token_address_list.append(bond_token3["address"])
        register_bond_list(issuer, bond_token3, token_list)

        attribute_token4 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token4["name"] = "テスト債券4"
        bond_token4 = issue_bond_token(issuer, attribute_token4)
        token_address_list.append(bond_token4["address"])
        register_bond_list(issuer, bond_token4, token_list)

        attribute_token5 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token5["name"] = "テスト債券5"
        bond_token5 = issue_bond_token(issuer, attribute_token5)
        token_address_list.append(bond_token5["address"])
        register_bond_list(issuer, bond_token5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, bond_token1)
        self.list_token(session, bond_token2)
        self.list_token(session, bond_token3)
        self.list_token(session, bond_token4)
        self.list_token(session, bond_token5)

        # 事前準備
        processor.SEC_PER_RECORD = 0
        processor.process()

        not_matched_key_value = {
            "name": "not_matched_value",
            "owner_address": "0x0000000000000000000000000000000000000000",
            "company_name": "not_matched_value",
            "symbol": "not_matched_value",
            "is_redeemed": True,
            "is_offering": True,
            "transferable": False,
            "tradable_exchange": "0x0000000000000000000000000000000000000000",
            "status": False,
            "personal_info_address": "0x0000000000000000000000000000000000000000",
            "transfer_approval_required": True,
        }

        for key, value in not_matched_key_value.items():
            resp = client.get(self.apiurl, params={key: value})

            assumed_body = {
                "result_set": {"count": 0, "offset": None, "limit": None, "total": 5},
                "tokens": [],
            }

            assert resp.status_code == 200
            assert resp.json()["meta"] == {"code": 200, "message": "OK"}
            assert resp.json()["data"] == assumed_body

    # <Normal_6>
    # Sort
    def test_normal_6(
        self,
        client: TestClient,
        session: Session,
        shared_contract,
        processor: Processor,
    ):
        config.BOND_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])

        token_address_list = []

        attribute_token1 = self.bond_token_attribute(
            exchange_address,
            personal_info,
        )
        attribute_token1["name"] = "テスト債券1"
        bond_token1 = issue_bond_token(issuer, attribute_token1)
        token_address_list.append(bond_token1["address"])
        register_bond_list(issuer, bond_token1, token_list)

        attribute_token2 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token2["name"] = "テスト債券2"
        bond_token2 = issue_bond_token(issuer, attribute_token2)
        token_address_list.append(bond_token2["address"])
        register_bond_list(issuer, bond_token2, token_list)

        attribute_token3 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token3["name"] = "テスト債券3"
        bond_token3 = issue_bond_token(issuer, attribute_token3)
        token_address_list.append(bond_token3["address"])
        register_bond_list(issuer, bond_token3, token_list)

        attribute_token4 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token4["name"] = "テスト債券4"
        bond_token4 = issue_bond_token(issuer, attribute_token4)
        token_address_list.append(bond_token4["address"])
        register_bond_list(issuer, bond_token4, token_list)

        attribute_token5 = self.bond_token_attribute(exchange_address, personal_info)
        attribute_token5["name"] = "テスト債券5"
        bond_token5 = issue_bond_token(issuer, attribute_token5)
        token_address_list.append(bond_token5["address"])
        register_bond_list(issuer, bond_token5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, bond_token1)
        self.list_token(session, bond_token2)
        self.list_token(session, bond_token3)
        self.list_token(session, bond_token4)
        self.list_token(session, bond_token5)

        # 事前準備
        processor.SEC_PER_RECORD = 1
        processor.process()

        resp = client.get(
            self.apiurl,
            params={
                "name": "テスト債券",
                "is_redeemed": False,
                "sort_item": "name",
                "sort_order": 1,
            },
        )
        tokens = [
            {
                "token_address": token_address_list[i],
                "token_template": "IbetStraightBond",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": f"テスト債券{i+1}",
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
                "transfer_approval_required": False,
                "face_value_currency": "JPY",
                "interest_payment_currency": "JPY",
                "redemption_value_currency": "JPY",
                "base_fx_rate": 0.0,
            }
            for i in range(0, 5)
        ]

        assumed_body = {
            "result_set": {"count": 5, "offset": None, "limit": None, "total": 5},
            "tokens": list(reversed(tokens)),
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Error_1>
    # NotSupportedError
    def test_error_1(
        self,
        client: TestClient,
        session: Session,
        shared_contract,
        processor: Processor,
    ):
        config.BOND_TOKEN_ENABLED = False
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = self.bond_token_attribute(exchange_address, personal_info)
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, bond_token)

        # 事前準備
        processor.SEC_PER_RECORD = 0
        processor.process()

        query_string = ""
        resp = client.get(self.apiurl, params=query_string)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "description": "method: GET, url: /Token/StraightBond",
            "message": "Not Supported",
        }

    # <Error_2>
    # InvalidParameterError
    def test_error_2(
        self,
        client: TestClient,
        session: Session,
        shared_contract,
        processor: Processor,
    ):
        config.BOND_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = self.bond_token_attribute(exchange_address, personal_info)
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, bond_token)

        # 事前準備
        processor.SEC_PER_RECORD = 0
        processor.process()

        invalid_key_value_1 = {
            "is_redeemed": "invalid_param",
            "is_offering": "invalid_param",
            "transferable": "invalid_param",
            "status": "invalid_param",
            "transfer_approval_required": "invalid_param",
        }
        for key, value in invalid_key_value_1.items():
            resp = client.get(self.apiurl, params={key: value})

            assert resp.status_code == 400
            assert resp.json()["meta"] == {
                "code": 88,
                "description": [
                    {
                        "input": "invalid_param",
                        "loc": ["query", key],
                        "msg": "Input should be a valid boolean, unable to interpret "
                        "input",
                        "type": "bool_parsing",
                    }
                ],
                "message": "Invalid Parameter",
            }

        invalid_key_value_2 = {"offset": "invalid_param", "limit": "invalid_param"}
        for key, value in invalid_key_value_2.items():
            resp = client.get(self.apiurl, params={key: value})

            assert resp.status_code == 400
            assert resp.json()["meta"] == {
                "code": 88,
                "description": [
                    {
                        "input": "invalid_param",
                        "loc": ["query", key],
                        "msg": "Input should be a valid integer, unable to parse "
                        "string as an integer",
                        "type": "int_parsing",
                    }
                ],
                "message": "Invalid Parameter",
            }

        invalid_key_value_list = [
            {"address_list": ["invalid_address2", "invalid_address1"]},
            {"address_list": ["invalid_address1", "0x000000000000000000000000000000"]},
        ]
        for invalid_key_value in invalid_key_value_list:
            for key in invalid_key_value.keys():
                resp = client.get(self.apiurl, params={key: invalid_key_value[key]})

                assert resp.status_code == 400
                assert resp.json()["meta"] == {
                    "code": 88,
                    "message": "Invalid Parameter",
                    "description": [
                        {
                            "type": "value_error",
                            "loc": ["query", "address_list", 0],
                            "msg": "Value error, Invalid ethereum address",
                            "input": invalid_key_value[key][0],
                            "ctx": {"error": {}},
                        },
                        {
                            "type": "value_error",
                            "loc": ["query", "address_list", 1],
                            "msg": "Value error, Invalid ethereum address",
                            "input": invalid_key_value[key][1],
                            "ctx": {"error": {}},
                        },
                    ],
                }
