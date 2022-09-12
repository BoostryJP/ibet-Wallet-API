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

from app.model.db import Listing, IDXTokenListItem
from app import config
from app.contracts import Contract
from batch import indexer_Token_Detail
from batch.indexer_Token_Detail import Processor

from tests.account_config import eth_account
from tests.contract_modules import (
    membership_issue,
    membership_register_list
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    indexer_Token_Detail.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    return indexer_Token_Detail


@pytest.fixture(scope="function")
def processor(test_module, session):
    processor = test_module.Processor()
    return processor


class TestTokenMembershipTokens:
    """
    Test Case for token.MembershipTokens
    """

    # テスト対象API
    apiurl = "/Token/Membership"

    @staticmethod
    def token_attribute(exchange_address):
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
            "privacyPolicy": "プライバシーポリシー"
        }
        return attribute

    @staticmethod
    def tokenlist_contract():
        deployer = eth_account["deployer"]
        web3.eth.default_account = deployer["account_address"]
        contract_address, abi = Contract.deploy_contract("TokenList", [], deployer["account_address"])
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
        token_list_item.token_template = "IbetMembership"
        token_list_item.owner_address = ""
        session.add(token_list_item)

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1_1>
    # List all tokens
    def test_normal_1_1(self, client: TestClient, session: Session, shared_contract, processor: Processor):
        config.MEMBERSHIP_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(shared_contract["IbetMembershipExchange"]["address"])
        attribute = self.token_attribute(exchange_address)
        membership = membership_issue(issuer, attribute)
        membership_register_list(issuer, membership, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, membership)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        processor.process()

        query_string = ""
        resp = client.get(self.apiurl, params=query_string)
        tokens = [{
            "token_address": membership["address"],
            "token_template": "IbetMembership",
            "owner_address": issuer["account_address"],
            "company_name": "",
            "rsa_publickey": "",
            "name": "テスト会員権",
            "symbol": "MEMBERSHIP",
            "total_supply": 1000000,
            "details": "詳細",
            "return_details": "リターン詳細",
            "expiration_date": "20191231",
            "memo": "メモ",
            "transferable": True,
            "status": True,
            "initial_offering_status": False,
            "image_url": [
                {"id": 1, "url": ""},
                {"id": 2, "url": ""},
                {"id": 3, "url": ""}
            ],
            "max_holding_quantity": 1,
            "max_sell_amount": 1000,
            "contact_information": "問い合わせ先",
            "privacy_policy": "プライバシーポリシー",
            "tradable_exchange": exchange_address
        }]

        assumed_body = {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 1
            },
            "tokens": tokens
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_1_2>
    # List specific tokens with query
    def test_normal_1_2(self, client: TestClient, session: Session, shared_contract, processor: Processor):
        config.MEMBERSHIP_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(shared_contract["IbetMembershipExchange"]["address"])

        token_address_list = []

        attribute_token1 = self.token_attribute(exchange_address, )
        attribute_token1["name"] = "テスト会員権1"
        membership1 = membership_issue(issuer, attribute_token1)
        token_address_list.append(membership1["address"])
        membership_register_list(issuer, membership1, token_list)

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テスト会員権2"
        membership2 = membership_issue(issuer, attribute_token2)
        token_address_list.append(membership2["address"])
        membership_register_list(issuer, membership2, token_list)

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テスト会員権3"
        membership3 = membership_issue(issuer, attribute_token3)
        token_address_list.append(membership3["address"])
        membership_register_list(issuer, membership3, token_list)

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テスト会員権4"
        membership4 = membership_issue(issuer, attribute_token4)
        token_address_list.append(membership4["address"])
        membership_register_list(issuer, membership4, token_list)

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テスト会員権5"
        membership5 = membership_issue(issuer, attribute_token5)
        token_address_list.append(membership5["address"])
        membership_register_list(issuer, membership5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, membership1)
        self.list_token(session, membership2)
        self.list_token(session, membership3)
        self.list_token(session, membership4)
        self.list_token(session, membership5)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        processor.process()

        target_token_addrss_list = token_address_list[1:4]

        resp = client.get(self.apiurl, params={
            "address_list": target_token_addrss_list
        })
        tokens = [{
            "token_address": token_address_list[i],
            "token_template": "IbetMembership",
            "owner_address": issuer["account_address"],
            "company_name": "",
            "rsa_publickey": "",
            "name": f"テスト会員権{i+1}",
            "symbol": "MEMBERSHIP",
            "total_supply": 1000000,
            "details": "詳細",
            "return_details": "リターン詳細",
            "expiration_date": "20191231",
            "memo": "メモ",
            "transferable": True,
            "status": True,
            "initial_offering_status": False,
            "image_url": [
                {"id": 1, "url": ""},
                {"id": 2, "url": ""},
                {"id": 3, "url": ""}
            ],
            "max_holding_quantity": 1,
            "max_sell_amount": 1000,
            "contact_information": "問い合わせ先",
            "privacy_policy": "プライバシーポリシー",
            "tradable_exchange": exchange_address
        } for i in range(1, 4)]

        assumed_body = {
            "result_set": {
                "count": 3,
                "offset": None,
                "limit": None,
                "total": 3
            },
            "tokens": tokens
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_2>
    # Pagination
    def test_normal_2(self, client: TestClient, session: Session, shared_contract, processor: Processor):
        config.MEMBERSHIP_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(shared_contract["IbetMembershipExchange"]["address"])

        token_address_list = []

        attribute_token1 = self.token_attribute(exchange_address)
        attribute_token1["name"] = "テスト会員権1"
        membership1 = membership_issue(issuer, attribute_token1)
        token_address_list.append(membership1["address"])
        membership_register_list(issuer, membership1, token_list)

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テスト会員権2"
        membership2 = membership_issue(issuer, attribute_token2)
        token_address_list.append(membership2["address"])
        membership_register_list(issuer, membership2, token_list)

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テスト会員権3"
        membership3 = membership_issue(issuer, attribute_token3)
        token_address_list.append(membership3["address"])
        membership_register_list(issuer, membership3, token_list)

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テスト会員権4"
        membership4 = membership_issue(issuer, attribute_token4)
        token_address_list.append(membership4["address"])
        membership_register_list(issuer, membership4, token_list)

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テスト会員権5"
        membership5 = membership_issue(issuer, attribute_token5)
        token_address_list.append(membership5["address"])
        membership_register_list(issuer, membership5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, membership1)
        self.list_token(session, membership2)
        self.list_token(session, membership3)
        self.list_token(session, membership4)
        self.list_token(session, membership5)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        processor.process()

        resp = client.get(self.apiurl, params={
            "offset": 1,
            "limit": 2,
        })
        tokens = [{
            "token_address": token_address_list[i],
            "token_template": "IbetMembership",
            "owner_address": issuer["account_address"],
            "company_name": "",
            "rsa_publickey": "",
            "name": f"テスト会員権{i+1}",
            "symbol": "MEMBERSHIP",
            "total_supply": 1000000,
            "details": "詳細",
            "return_details": "リターン詳細",
            "expiration_date": "20191231",
            "memo": "メモ",
            "transferable": True,
            "status": True,
            "initial_offering_status": False,
            "image_url": [
                {"id": 1, "url": ""},
                {"id": 2, "url": ""},
                {"id": 3, "url": ""}
            ],
            "max_holding_quantity": 1,
            "max_sell_amount": 1000,
            "contact_information": "問い合わせ先",
            "privacy_policy": "プライバシーポリシー",
            "tradable_exchange": exchange_address
        } for i in range(1, 3)]

        assumed_body = {
            "result_set": {
                "count": 5,
                "offset": 1,
                "limit": 2,
                "total": 5
            },
            "tokens": tokens
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_3>
    # Pagination(over offset)
    def test_normal_3(self, client: TestClient, session: Session, shared_contract, processor: Processor):
        config.MEMBERSHIP_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(shared_contract["IbetMembershipExchange"]["address"])

        token_address_list = []

        attribute_token1 = self.token_attribute(exchange_address, )
        attribute_token1["name"] = "テスト会員権1"
        membership1 = membership_issue(issuer, attribute_token1)
        token_address_list.append(membership1["address"])
        membership_register_list(issuer, membership1, token_list)

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テスト会員権2"
        membership2 = membership_issue(issuer, attribute_token2)
        token_address_list.append(membership2["address"])
        membership_register_list(issuer, membership2, token_list)

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テスト会員権3"
        membership3 = membership_issue(issuer, attribute_token3)
        token_address_list.append(membership3["address"])
        membership_register_list(issuer, membership3, token_list)

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テスト会員権4"
        membership4 = membership_issue(issuer, attribute_token4)
        token_address_list.append(membership4["address"])
        membership_register_list(issuer, membership4, token_list)

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テスト会員権5"
        membership5 = membership_issue(issuer, attribute_token5)
        token_address_list.append(membership5["address"])
        membership_register_list(issuer, membership5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, membership1)
        self.list_token(session, membership2)
        self.list_token(session, membership3)
        self.list_token(session, membership4)
        self.list_token(session, membership5)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        processor.process()

        resp = client.get(self.apiurl, params={
            "offset": 7
        })
        tokens = []

        assumed_body = {
            "result_set": {
                "count": 5,
                "offset": 7,
                "limit": None,
                "total": 5
            },
            "tokens": tokens
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_4>
    # Search Filter
    def test_normal_4(self, client: TestClient, session: Session, shared_contract, processor: Processor):
        config.MEMBERSHIP_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(shared_contract["IbetMembershipExchange"]["address"])

        token_address_list = []

        attribute_token1 = self.token_attribute(exchange_address, )
        attribute_token1["name"] = "テスト会員権1"
        membership1 = membership_issue(issuer, attribute_token1)
        token_address_list.append(membership1["address"])
        membership_register_list(issuer, membership1, token_list)

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テスト会員権2"
        membership2 = membership_issue(issuer, attribute_token2)
        token_address_list.append(membership2["address"])
        membership_register_list(issuer, membership2, token_list)

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テスト会員権3"
        membership3 = membership_issue(issuer, attribute_token3)
        token_address_list.append(membership3["address"])
        membership_register_list(issuer, membership3, token_list)

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テスト会員権4"
        membership4 = membership_issue(issuer, attribute_token4)
        token_address_list.append(membership4["address"])
        membership_register_list(issuer, membership4, token_list)

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テスト会員権5"
        membership5 = membership_issue(issuer, attribute_token5)
        token_address_list.append(membership5["address"])
        membership_register_list(issuer, membership5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, membership1)
        self.list_token(session, membership2)
        self.list_token(session, membership3)
        self.list_token(session, membership4)
        self.list_token(session, membership5)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        processor.process()

        resp = client.get(self.apiurl, params={
            "name": "テスト会員権",
            "owner_address": issuer["account_address"],
            "company_name": "",
            "symbol": "MEM",
            "transferable": True,
            "status": True,
            "initial_offering_status": False,
            "tradable_exchange": exchange_address
        })
        tokens = [{
            "token_address": token_address_list[i],
            "token_template": "IbetMembership",
            "owner_address": issuer["account_address"],
            "company_name": "",
            "rsa_publickey": "",
            "name": f"テスト会員権{i+1}",
            "symbol": "MEMBERSHIP",
            "total_supply": 1000000,
            "details": "詳細",
            "return_details": "リターン詳細",
            "expiration_date": "20191231",
            "memo": "メモ",
            "transferable": True,
            "status": True,
            "initial_offering_status": False,
            "image_url": [
                {"id": 1, "url": ""},
                {"id": 2, "url": ""},
                {"id": 3, "url": ""}
            ],
            "max_holding_quantity": 1,
            "max_sell_amount": 1000,
            "contact_information": "問い合わせ先",
            "privacy_policy": "プライバシーポリシー",
            "tradable_exchange": exchange_address
        } for i in range(0, 5)]

        assumed_body = {
            "result_set": {
                "count": 5,
                "offset": None,
                "limit": None,
                "total": 5
            },
            "tokens": tokens
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_5>
    # Search Filter(not hit)
    def test_normal_5(self, client: TestClient, session: Session, shared_contract, processor: Processor):
        config.MEMBERSHIP_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(shared_contract["IbetMembershipExchange"]["address"])

        token_address_list = []

        attribute_token1 = self.token_attribute(exchange_address, )
        attribute_token1["name"] = "テスト会員権1"
        membership1 = membership_issue(issuer, attribute_token1)
        token_address_list.append(membership1["address"])
        membership_register_list(issuer, membership1, token_list)

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テスト会員権2"
        membership2 = membership_issue(issuer, attribute_token2)
        token_address_list.append(membership2["address"])
        membership_register_list(issuer, membership2, token_list)

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テスト会員権3"
        membership3 = membership_issue(issuer, attribute_token3)
        token_address_list.append(membership3["address"])
        membership_register_list(issuer, membership3, token_list)

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テスト会員権4"
        membership4 = membership_issue(issuer, attribute_token4)
        token_address_list.append(membership4["address"])
        membership_register_list(issuer, membership4, token_list)

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テスト会員権5"
        membership5 = membership_issue(issuer, attribute_token5)
        token_address_list.append(membership5["address"])
        membership_register_list(issuer, membership5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, membership1)
        self.list_token(session, membership2)
        self.list_token(session, membership3)
        self.list_token(session, membership4)
        self.list_token(session, membership5)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        processor.process()

        not_matched_key_value = {
            "name": "not_matched_value",
            "owner_address": "not_matched_value",
            "company_name": "not_matched_value",
            "symbol": "not_matched_value",
            "transferable": False,
            "status": False,
            "initial_offering_status": True,
            "tradable_exchange": "not_matched_value",
        }

        for key, value in not_matched_key_value.items():
            resp = client.get(self.apiurl, params={
                key: value
            })

            assumed_body = {
                "result_set": {
                    "count": 0,
                    "offset": None,
                    "limit": None,
                    "total": 5
                },
                "tokens": []
            }

            assert resp.status_code == 200
            assert resp.json()["meta"] == {"code": 200, "message": "OK"}
            assert resp.json()["data"] == assumed_body

    # <Normal_6>
    # Sort
    def test_normal_6(self, client: TestClient, session: Session, shared_contract, processor: Processor):
        config.MEMBERSHIP_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(shared_contract["IbetMembershipExchange"]["address"])

        token_address_list = []

        attribute_token1 = self.token_attribute(exchange_address, )
        attribute_token1["name"] = "テスト会員権1"
        membership1 = membership_issue(issuer, attribute_token1)
        token_address_list.append(membership1["address"])
        membership_register_list(issuer, membership1, token_list)

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テスト会員権2"
        membership2 = membership_issue(issuer, attribute_token2)
        token_address_list.append(membership2["address"])
        membership_register_list(issuer, membership2, token_list)

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テスト会員権3"
        membership3 = membership_issue(issuer, attribute_token3)
        token_address_list.append(membership3["address"])
        membership_register_list(issuer, membership3, token_list)

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テスト会員権4"
        membership4 = membership_issue(issuer, attribute_token4)
        token_address_list.append(membership4["address"])
        membership_register_list(issuer, membership4, token_list)

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テスト会員権5"
        membership5 = membership_issue(issuer, attribute_token5)
        token_address_list.append(membership5["address"])
        membership_register_list(issuer, membership5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, membership1)
        self.list_token(session, membership2)
        self.list_token(session, membership3)
        self.list_token(session, membership4)
        self.list_token(session, membership5)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        processor.process()

        resp = client.get(self.apiurl, params={
            "name": "テスト会員権",
            "initial_offering_status": False,
            "sort_item": "name",
            "sort_order": 1
        })
        tokens = [{
            "token_address": token_address_list[i],
            "token_template": "IbetMembership",
            "owner_address": issuer["account_address"],
            "company_name": "",
            "rsa_publickey": "",
            "name": f"テスト会員権{i+1}",
            "symbol": "MEMBERSHIP",
            "total_supply": 1000000,
            "details": "詳細",
            "return_details": "リターン詳細",
            "expiration_date": "20191231",
            "memo": "メモ",
            "transferable": True,
            "status": True,
            "initial_offering_status": False,
            "image_url": [
                {"id": 1, "url": ""},
                {"id": 2, "url": ""},
                {"id": 3, "url": ""}
            ],
            "max_holding_quantity": 1,
            "max_sell_amount": 1000,
            "contact_information": "問い合わせ先",
            "privacy_policy": "プライバシーポリシー",
            "tradable_exchange": exchange_address
        } for i in range(0, 5)]

        assumed_body = {
            "result_set": {
                "count": 5,
                "offset": None,
                "limit": None,
                "total": 5
            },
            "tokens": list(reversed(tokens))
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Error_1>
    # NotSupportedError
    def test_error_1(self, client: TestClient, session: Session, shared_contract, processor: Processor):
        config.MEMBERSHIP_TOKEN_ENABLED = False
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(shared_contract["IbetMembershipExchange"]["address"])
        attribute = self.token_attribute(exchange_address)
        membership = membership_issue(issuer, attribute)
        membership_register_list(issuer, membership, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, membership)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        processor.process()

        query_string = ""
        resp = client.get(self.apiurl, params=query_string)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "description": "method: GET, url: /Token/Membership",
            "message": "Not Supported"
        }

    # <Error_2>
    # InvalidParameterError
    def test_error_2(self, client: TestClient, session: Session, shared_contract, processor: Processor):
        config.MEMBERSHIP_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(shared_contract["IbetMembershipExchange"]["address"])
        attribute = self.token_attribute(exchange_address)
        membership = membership_issue(issuer, attribute)
        membership_register_list(issuer, membership, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, membership)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        processor.process()

        invalid_key_value_1 = {
            "transferable": "invalid_param",
            "status": "invalid_param",
            "initial_offering_status": "invalid_param",
        }
        for key, value in invalid_key_value_1.items():
            resp = client.get(self.apiurl, params={
                key: value
            })

            assert resp.status_code == 400
            assert resp.json()["meta"] == {
                "code": 88,
                "description": [
                    {
                        "loc": ["query", key],
                        "msg": "value could not be parsed to a boolean",
                        "type": "type_error.bool"
                    }
                ],
                "message": "Invalid Parameter"
            }

        invalid_key_value_2 = {
            "offset": "invalid_param",
            "limit": "invalid_param"
        }
        for key, value in invalid_key_value_2.items():
            resp = client.get(self.apiurl, params={
                key: value
            })

            assert resp.status_code == 400
            assert resp.json()["meta"] == {
                "code": 88,
                "description": [
                    {
                        "loc": ["query", key],
                        "msg": "value is not a valid integer",
                        "type": "type_error.integer"
                    }
                ],
                "message": "Invalid Parameter"
            }

        invalid_key_value_list = [
            {"address_list": ["invalid_address2", "invalid_address1"]},
            {"address_list": ["invalid_address1", "0x000000000000000000000000000000"]}
        ]
        for invalid_key_value in invalid_key_value_list:
            for key in invalid_key_value.keys():
                resp = client.get(self.apiurl, params={
                    key: invalid_key_value[key]
                })

                assert resp.status_code == 400
                assert resp.json()["meta"] == {
                    "code": 88,
                    "message": "Invalid Parameter",
                    "description": f"invalid token_address: {invalid_key_value[key][0]}"
                }
