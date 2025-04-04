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

import asyncio

import pytest
from eth_utils import to_checksum_address
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from app.contracts import Contract
from app.model.db import IDXTokenListRegister, Listing
from batch import indexer_Token_Detail
from batch.indexer_Token_Detail import Processor
from tests.account_config import eth_account
from tests.contract_modules import coupon_register_list, issue_coupon_token

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    indexer_Token_Detail.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"][
        "address"
    ]
    return indexer_Token_Detail


@pytest.fixture(scope="function")
def processor(test_module, session):
    config.COUPON_TOKEN_ENABLED = True
    processor = test_module.Processor()
    return processor


class TestTokenCouponTokenAddresses:
    """
    Test Case for token.CouponTokenAddresses
    """

    # テスト対象API
    apiurl = "/Token/Coupon/Addresses"

    @staticmethod
    def token_attribute(exchange_address):
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
        token_list_item = IDXTokenListRegister()
        token_list_item.token_address = token["address"]
        token_list_item.token_template = "IbetCoupon"
        token_list_item.owner_address = ""
        session.add(token_list_item)

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # List all tokens
    def test_normal_1(
        self,
        client: TestClient,
        session: Session,
        shared_contract,
        processor: Processor,
    ):
        config.COUPON_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetCouponExchange"]["address"]
        )
        attribute = self.token_attribute(exchange_address)
        coupon = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, coupon, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, coupon)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        query_string = ""
        resp = client.get(self.apiurl, params=query_string)
        tokens = [coupon["address"]]

        assumed_body = {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 1},
            "address_list": tokens,
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
        config.COUPON_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetCouponExchange"]["address"]
        )

        token_address_list = []

        attribute_token1 = self.token_attribute(exchange_address)
        attribute_token1["name"] = "テストクーポン1"
        coupon1 = issue_coupon_token(issuer, attribute_token1)
        token_address_list.append(coupon1["address"])
        coupon_register_list(issuer, coupon1, token_list)

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テストクーポン2"
        coupon2 = issue_coupon_token(issuer, attribute_token2)
        token_address_list.append(coupon2["address"])
        coupon_register_list(issuer, coupon2, token_list)

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テストクーポン3"
        coupon3 = issue_coupon_token(issuer, attribute_token3)
        token_address_list.append(coupon3["address"])
        coupon_register_list(issuer, coupon3, token_list)

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テストクーポン4"
        coupon4 = issue_coupon_token(issuer, attribute_token4)
        token_address_list.append(coupon4["address"])
        coupon_register_list(issuer, coupon4, token_list)

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テストクーポン5"
        coupon5 = issue_coupon_token(issuer, attribute_token5)
        token_address_list.append(coupon5["address"])
        coupon_register_list(issuer, coupon5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, coupon1)
        self.list_token(session, coupon2)
        self.list_token(session, coupon3)
        self.list_token(session, coupon4)
        self.list_token(session, coupon5)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        resp = client.get(
            self.apiurl,
            params={
                "offset": 1,
                "limit": 2,
            },
        )
        tokens = [token_address_list[i] for i in range(1, 3)]

        assumed_body = {
            "result_set": {"count": 5, "offset": 1, "limit": 2, "total": 5},
            "address_list": tokens,
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
        config.COUPON_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetCouponExchange"]["address"]
        )

        token_address_list = []

        attribute_token1 = self.token_attribute(
            exchange_address,
        )
        attribute_token1["name"] = "テストクーポン1"
        coupon1 = issue_coupon_token(issuer, attribute_token1)
        token_address_list.append(coupon1["address"])
        coupon_register_list(issuer, coupon1, token_list)

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テストクーポン2"
        coupon2 = issue_coupon_token(issuer, attribute_token2)
        token_address_list.append(coupon2["address"])
        coupon_register_list(issuer, coupon2, token_list)

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テストクーポン3"
        coupon3 = issue_coupon_token(issuer, attribute_token3)
        token_address_list.append(coupon3["address"])
        coupon_register_list(issuer, coupon3, token_list)

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テストクーポン4"
        coupon4 = issue_coupon_token(issuer, attribute_token4)
        token_address_list.append(coupon4["address"])
        coupon_register_list(issuer, coupon4, token_list)

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テストクーポン5"
        coupon5 = issue_coupon_token(issuer, attribute_token5)
        token_address_list.append(coupon5["address"])
        coupon_register_list(issuer, coupon5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, coupon1)
        self.list_token(session, coupon2)
        self.list_token(session, coupon3)
        self.list_token(session, coupon4)
        self.list_token(session, coupon5)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        resp = client.get(self.apiurl, params={"offset": 7})
        tokens = []

        assumed_body = {
            "result_set": {"count": 5, "offset": 7, "limit": None, "total": 5},
            "address_list": tokens,
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
        config.COUPON_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetCouponExchange"]["address"]
        )

        token_address_list = []

        attribute_token1 = self.token_attribute(
            exchange_address,
        )
        attribute_token1["name"] = "テストクーポン1"
        coupon1 = issue_coupon_token(issuer, attribute_token1)
        token_address_list.append(coupon1["address"])
        coupon_register_list(issuer, coupon1, token_list)

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テストクーポン2"
        coupon2 = issue_coupon_token(issuer, attribute_token2)
        token_address_list.append(coupon2["address"])
        coupon_register_list(issuer, coupon2, token_list)

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テストクーポン3"
        coupon3 = issue_coupon_token(issuer, attribute_token3)
        token_address_list.append(coupon3["address"])
        coupon_register_list(issuer, coupon3, token_list)

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テストクーポン4"
        coupon4 = issue_coupon_token(issuer, attribute_token4)
        token_address_list.append(coupon4["address"])
        coupon_register_list(issuer, coupon4, token_list)

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テストクーポン5"
        coupon5 = issue_coupon_token(issuer, attribute_token5)
        token_address_list.append(coupon5["address"])
        coupon_register_list(issuer, coupon5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, coupon1)
        self.list_token(session, coupon2)
        self.list_token(session, coupon3)
        self.list_token(session, coupon4)
        self.list_token(session, coupon5)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        resp = client.get(
            self.apiurl,
            params={
                "name": "テストクーポン",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "symbol": "COU",
                "transferable": True,
                "status": True,
                "initial_offering_status": False,
                "tradable_exchange": exchange_address,
            },
        )
        tokens = [token_address_list[i] for i in range(0, 5)]

        assumed_body = {
            "result_set": {"count": 5, "offset": None, "limit": None, "total": 5},
            "address_list": tokens,
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
        config.COUPON_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetCouponExchange"]["address"]
        )

        token_address_list = []

        attribute_token1 = self.token_attribute(
            exchange_address,
        )
        attribute_token1["name"] = "テストクーポン1"
        coupon1 = issue_coupon_token(issuer, attribute_token1)
        token_address_list.append(coupon1["address"])
        coupon_register_list(issuer, coupon1, token_list)

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テストクーポン2"
        coupon2 = issue_coupon_token(issuer, attribute_token2)
        token_address_list.append(coupon2["address"])
        coupon_register_list(issuer, coupon2, token_list)

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テストクーポン3"
        coupon3 = issue_coupon_token(issuer, attribute_token3)
        token_address_list.append(coupon3["address"])
        coupon_register_list(issuer, coupon3, token_list)

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テストクーポン4"
        coupon4 = issue_coupon_token(issuer, attribute_token4)
        token_address_list.append(coupon4["address"])
        coupon_register_list(issuer, coupon4, token_list)

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テストクーポン5"
        coupon5 = issue_coupon_token(issuer, attribute_token5)
        token_address_list.append(coupon5["address"])
        coupon_register_list(issuer, coupon5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, coupon1)
        self.list_token(session, coupon2)
        self.list_token(session, coupon3)
        self.list_token(session, coupon4)
        self.list_token(session, coupon5)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        not_matched_key_value = {
            "name": "not_matched_value",
            "owner_address": "0x0000000000000000000000000000000000000000",
            "company_name": "not_matched_value",
            "symbol": "not_matched_value",
            "transferable": False,
            "status": False,
            "initial_offering_status": True,
            "tradable_exchange": "0x0000000000000000000000000000000000000000",
        }

        for key, value in not_matched_key_value.items():
            resp = client.get(self.apiurl, params={key: value})

            assumed_body = {
                "result_set": {"count": 0, "offset": None, "limit": None, "total": 5},
                "address_list": [],
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
        config.COUPON_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetCouponExchange"]["address"]
        )

        token_address_list = []

        attribute_token1 = self.token_attribute(
            exchange_address,
        )
        attribute_token1["name"] = "テストクーポン1"
        coupon1 = issue_coupon_token(issuer, attribute_token1)
        token_address_list.append(coupon1["address"])
        coupon_register_list(issuer, coupon1, token_list)

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テストクーポン2"
        coupon2 = issue_coupon_token(issuer, attribute_token2)
        token_address_list.append(coupon2["address"])
        coupon_register_list(issuer, coupon2, token_list)

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テストクーポン3"
        coupon3 = issue_coupon_token(issuer, attribute_token3)
        token_address_list.append(coupon3["address"])
        coupon_register_list(issuer, coupon3, token_list)

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テストクーポン4"
        coupon4 = issue_coupon_token(issuer, attribute_token4)
        token_address_list.append(coupon4["address"])
        coupon_register_list(issuer, coupon4, token_list)

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テストクーポン5"
        coupon5 = issue_coupon_token(issuer, attribute_token5)
        token_address_list.append(coupon5["address"])
        coupon_register_list(issuer, coupon5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, coupon1)
        self.list_token(session, coupon2)
        self.list_token(session, coupon3)
        self.list_token(session, coupon4)
        self.list_token(session, coupon5)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        resp = client.get(
            self.apiurl,
            params={
                "name": "テストクーポン",
                "initial_offering_status": False,
                "sort_item": "name",
                "sort_order": 1,
            },
        )
        tokens = [token_address_list[i] for i in range(0, 5)]

        assumed_body = {
            "result_set": {"count": 5, "offset": None, "limit": None, "total": 5},
            "address_list": list(reversed(tokens)),
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
        config.COUPON_TOKEN_ENABLED = False
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetCouponExchange"]["address"]
        )
        attribute = self.token_attribute(exchange_address)
        coupon = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, coupon, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, coupon)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        query_string = ""
        resp = client.get(self.apiurl, params=query_string)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "description": "method: GET, url: /Token/Coupon/Addresses",
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
        config.COUPON_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetCouponExchange"]["address"]
        )
        attribute = self.token_attribute(exchange_address)
        coupon = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, coupon, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, coupon)
        session.commit()

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        invalid_key_value = {
            "transferable": "invalid_param",
            "status": "invalid_param",
            "initial_offering_status": "invalid_param",
        }
        for key, value in invalid_key_value.items():
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

        invalid_key_value = {"offset": "invalid_param", "limit": "invalid_param"}
        for key, value in invalid_key_value.items():
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
