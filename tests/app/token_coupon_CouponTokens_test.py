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
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import config
from app.model.db import IDXTokenListRegister, Listing
from batch.sub_indexers.indexer_Token_Detail import Processor
from tests.account_config import eth_account
from tests.helpers import IbetCouponTestHelper
from tests.types import SharedContract


@pytest.fixture(scope="function")
def processor(session: Session) -> Processor:
    config.COUPON_TOKEN_ENABLED = True
    processor = Processor()
    return processor


class TestTokenCouponTokens:
    """
    Test Case for token.CouponTokens
    """

    # テスト対象API
    apiurl = "/Token/Coupon"

    @staticmethod
    def token_attribute(exchange_address: str) -> dict[str, Any]:
        attribute = {
            "name": "テストクーポン",
            "symbol": "COUPON",
            "totalSupply": 10000,
            "tradableExchange": exchange_address,
            "details": "クーポン詳細",
            "returnDetails": "リターンクーポン詳細",
            "memo": "メモ欄",
            "expirationDate": "20191231",
            "transferable": True,
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
        }
        return attribute

    @staticmethod
    def list_token(session: Session, token_address: str) -> None:
        listed_token = Listing()
        listed_token.token_address = token_address
        listed_token.is_public = True
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
        listed_token.owner_address = "0x0000000000000000000000000000000000000000"
        session.add(listed_token)
        token_list_item = IDXTokenListRegister()
        token_list_item.token_address = token_address
        token_list_item.token_template = "IbetCoupon"
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
        shared_contract: SharedContract,
        processor: Processor,
    ):
        config.COUPON_TOKEN_ENABLED = True

        issuer = eth_account["issuer"]

        token_list = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # トークン発行
        exchange_address = shared_contract["IbetEscrow"]["address"]
        attribute = self.token_attribute(exchange_address)
        coupon = IbetCouponTestHelper.issue(issuer["account_address"], attribute)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon.address,
            token_list["address"],
        )

        # 取扱トークンデータ挿入
        self.list_token(session, coupon.address)

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        query_string = ""
        resp = client.get(self.apiurl, params=query_string)
        tokens = [
            {
                "token_address": coupon.address,
                "token_template": "IbetCoupon",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テストクーポン",
                "symbol": "COUPON",
                "total_supply": 10000,
                "details": "クーポン詳細",
                "return_details": "リターンクーポン詳細",
                "expiration_date": "20191231",
                "memo": "メモ欄",
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
        ]

        assumed_body: dict[str, Any] = {
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
        shared_contract: SharedContract,
        processor: Processor,
    ):
        config.COUPON_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # トークン発行
        exchange_address = shared_contract["IbetEscrow"]["address"]

        token_address_list: list[str] = []

        attribute_token1 = self.token_attribute(exchange_address)
        attribute_token1["name"] = "テストクーポン1"
        coupon1 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token1
        )
        token_address_list.append(coupon1.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon1.address,
            token_list["address"],
        )

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テストクーポン2"
        coupon2 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token2
        )
        token_address_list.append(coupon2.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon2.address,
            token_list["address"],
        )

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テストクーポン3"
        coupon3 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token3
        )
        token_address_list.append(coupon3.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon3.address,
            token_list["address"],
        )

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テストクーポン4"
        coupon4 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token4
        )
        token_address_list.append(coupon4.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon4.address,
            token_list["address"],
        )

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テストクーポン5"
        coupon5 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token5
        )
        token_address_list.append(coupon5.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon5.address,
            token_list["address"],
        )

        # 取扱トークンデータ挿入
        self.list_token(session, coupon1.address)
        self.list_token(session, coupon2.address)
        self.list_token(session, coupon3.address)
        self.list_token(session, coupon4.address)
        self.list_token(session, coupon5.address)

        # 事前準備
        processor.SEC_PER_RECORD = 1
        asyncio.run(processor.process())

        target_token_address_list = token_address_list[1:4]

        resp = client.get(
            self.apiurl, params={"address_list": target_token_address_list}
        )
        tokens = [
            {
                "token_address": token_address_list[i],
                "token_template": "IbetCoupon",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": f"テストクーポン{i + 1}",
                "symbol": "COUPON",
                "total_supply": 10000,
                "details": "クーポン詳細",
                "return_details": "リターンクーポン詳細",
                "expiration_date": "20191231",
                "memo": "メモ欄",
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
            for i in range(1, 4)
        ]

        assumed_body: dict[str, Any] = {
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
        shared_contract: SharedContract,
        processor: Processor,
    ):
        config.COUPON_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # トークン発行
        exchange_address = shared_contract["IbetEscrow"]["address"]

        token_address_list: list[str] = []

        attribute_token1 = self.token_attribute(exchange_address)
        attribute_token1["name"] = "テストクーポン1"
        coupon1 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token1
        )
        token_address_list.append(coupon1.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon1.address,
            token_list["address"],
        )

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テストクーポン2"
        coupon2 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token2
        )
        token_address_list.append(coupon2.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon2.address,
            token_list["address"],
        )

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テストクーポン3"
        coupon3 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token3
        )
        token_address_list.append(coupon3.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon3.address,
            token_list["address"],
        )

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テストクーポン4"
        coupon4 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token4
        )
        token_address_list.append(coupon4.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon4.address,
            token_list["address"],
        )

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テストクーポン5"
        coupon5 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token5
        )
        token_address_list.append(coupon5.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon5.address,
            token_list["address"],
        )

        # 取扱トークンデータ挿入
        self.list_token(session, coupon1.address)
        self.list_token(session, coupon2.address)
        self.list_token(session, coupon3.address)
        self.list_token(session, coupon4.address)
        self.list_token(session, coupon5.address)

        # 事前準備
        processor.SEC_PER_RECORD = 1
        asyncio.run(processor.process())

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
                "token_template": "IbetCoupon",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": f"テストクーポン{i + 1}",
                "symbol": "COUPON",
                "total_supply": 10000,
                "details": "クーポン詳細",
                "return_details": "リターンクーポン詳細",
                "expiration_date": "20191231",
                "memo": "メモ欄",
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
            for i in range(1, 3)
        ]

        assumed_body: dict[str, Any] = {
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
        shared_contract: SharedContract,
        processor: Processor,
    ):
        config.COUPON_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # トークン発行
        exchange_address = shared_contract["IbetEscrow"]["address"]

        token_address_list: list[str] = []

        attribute_token1 = self.token_attribute(exchange_address)
        attribute_token1["name"] = "テストクーポン1"
        coupon1 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token1
        )
        token_address_list.append(coupon1.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon1.address,
            token_list["address"],
        )

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テストクーポン2"
        coupon2 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token2
        )
        token_address_list.append(coupon2.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon2.address,
            token_list["address"],
        )

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テストクーポン3"
        coupon3 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token3
        )
        token_address_list.append(coupon3.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon3.address,
            token_list["address"],
        )

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テストクーポン4"
        coupon4 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token4
        )
        token_address_list.append(coupon4.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon4.address,
            token_list["address"],
        )

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テストクーポン5"
        coupon5 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token5
        )
        token_address_list.append(coupon5.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon5.address,
            token_list["address"],
        )

        # 取扱トークンデータ挿入
        self.list_token(session, coupon1.address)
        self.list_token(session, coupon2.address)
        self.list_token(session, coupon3.address)
        self.list_token(session, coupon4.address)
        self.list_token(session, coupon5.address)

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        resp = client.get(self.apiurl, params={"offset": 7})
        tokens = []

        assumed_body: dict[str, Any] = {
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
        shared_contract: SharedContract,
        processor: Processor,
    ):
        config.COUPON_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # トークン発行
        exchange_address = shared_contract["IbetEscrow"]["address"]

        token_address_list: list[str] = []

        attribute_token1 = self.token_attribute(exchange_address)
        attribute_token1["name"] = "テストクーポン1"
        coupon1 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token1
        )
        token_address_list.append(coupon1.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon1.address,
            token_list["address"],
        )

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テストクーポン2"
        coupon2 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token2
        )
        token_address_list.append(coupon2.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon2.address,
            token_list["address"],
        )

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テストクーポン3"
        coupon3 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token3
        )
        token_address_list.append(coupon3.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon3.address,
            token_list["address"],
        )

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テストクーポン4"
        coupon4 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token4
        )
        token_address_list.append(coupon4.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon4.address,
            token_list["address"],
        )

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テストクーポン5"
        coupon5 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token5
        )
        token_address_list.append(coupon5.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon5.address,
            token_list["address"],
        )

        # 取扱トークンデータ挿入
        self.list_token(session, coupon1.address)
        self.list_token(session, coupon2.address)
        self.list_token(session, coupon3.address)
        self.list_token(session, coupon4.address)
        self.list_token(session, coupon5.address)

        # 事前準備
        processor.SEC_PER_RECORD = 1
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
        tokens = [
            {
                "token_address": token_address_list[i],
                "token_template": "IbetCoupon",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": f"テストクーポン{i + 1}",
                "symbol": "COUPON",
                "total_supply": 10000,
                "details": "クーポン詳細",
                "return_details": "リターンクーポン詳細",
                "expiration_date": "20191231",
                "memo": "メモ欄",
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
            for i in range(0, 5)
        ]

        assumed_body: dict[str, Any] = {
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
        shared_contract: SharedContract,
        processor: Processor,
    ):
        config.COUPON_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # トークン発行
        exchange_address = shared_contract["IbetEscrow"]["address"]

        token_address_list: list[str] = []

        attribute_token1 = self.token_attribute(exchange_address)
        attribute_token1["name"] = "テストクーポン1"
        coupon1 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token1
        )
        token_address_list.append(coupon1.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon1.address,
            token_list["address"],
        )

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テストクーポン2"
        coupon2 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token2
        )
        token_address_list.append(coupon2.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon2.address,
            token_list["address"],
        )

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テストクーポン3"
        coupon3 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token3
        )
        token_address_list.append(coupon3.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon3.address,
            token_list["address"],
        )

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テストクーポン4"
        coupon4 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token4
        )
        token_address_list.append(coupon4.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon4.address,
            token_list["address"],
        )

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テストクーポン5"
        coupon5 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token5
        )
        token_address_list.append(coupon5.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon5.address,
            token_list["address"],
        )

        # 取扱トークンデータ挿入
        self.list_token(session, coupon1.address)
        self.list_token(session, coupon2.address)
        self.list_token(session, coupon3.address)
        self.list_token(session, coupon4.address)
        self.list_token(session, coupon5.address)

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

            assumed_body: dict[str, Any] = {
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
        shared_contract: SharedContract,
        processor: Processor,
    ):
        config.COUPON_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # トークン発行
        exchange_address = shared_contract["IbetEscrow"]["address"]

        token_address_list: list[str] = []

        attribute_token1 = self.token_attribute(exchange_address)
        attribute_token1["name"] = "テストクーポン1"
        coupon1 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token1
        )
        token_address_list.append(coupon1.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon1.address,
            token_list["address"],
        )

        attribute_token2 = self.token_attribute(exchange_address)
        attribute_token2["name"] = "テストクーポン2"
        coupon2 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token2
        )
        token_address_list.append(coupon2.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon2.address,
            token_list["address"],
        )

        attribute_token3 = self.token_attribute(exchange_address)
        attribute_token3["name"] = "テストクーポン3"
        coupon3 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token3
        )
        token_address_list.append(coupon3.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon3.address,
            token_list["address"],
        )

        attribute_token4 = self.token_attribute(exchange_address)
        attribute_token4["name"] = "テストクーポン4"
        coupon4 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token4
        )
        token_address_list.append(coupon4.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon4.address,
            token_list["address"],
        )

        attribute_token5 = self.token_attribute(exchange_address)
        attribute_token5["name"] = "テストクーポン5"
        coupon5 = IbetCouponTestHelper.issue(
            issuer["account_address"], attribute_token5
        )
        token_address_list.append(coupon5.address)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon5.address,
            token_list["address"],
        )

        # 取扱トークンデータ挿入
        self.list_token(session, coupon1.address)
        self.list_token(session, coupon2.address)
        self.list_token(session, coupon3.address)
        self.list_token(session, coupon4.address)
        self.list_token(session, coupon5.address)

        # 事前準備
        processor.SEC_PER_RECORD = 1
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
        tokens = [
            {
                "token_address": token_address_list[i],
                "token_template": "IbetCoupon",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": f"テストクーポン{i + 1}",
                "symbol": "COUPON",
                "total_supply": 10000,
                "details": "クーポン詳細",
                "return_details": "リターンクーポン詳細",
                "expiration_date": "20191231",
                "memo": "メモ欄",
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
            for i in range(0, 5)
        ]

        assumed_body: dict[str, Any] = {
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
        shared_contract: SharedContract,
        processor: Processor,
    ):
        config.COUPON_TOKEN_ENABLED = False
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # トークン発行
        exchange_address = shared_contract["IbetEscrow"]["address"]
        attribute = self.token_attribute(exchange_address)
        coupon = IbetCouponTestHelper.issue(issuer["account_address"], attribute)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon.address,
            token_list["address"],
        )

        # 取扱トークンデータ挿入
        self.list_token(session, coupon.address)

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        query_string = ""
        resp = client.get(self.apiurl, params=query_string)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "description": "method: GET, url: /Token/Coupon",
            "message": "Not Supported",
        }

    # <Error_2>
    # InvalidParameterError
    def test_error_2(
        self,
        client: TestClient,
        session: Session,
        shared_contract: SharedContract,
        processor: Processor,
    ):
        config.COUPON_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # トークン発行
        exchange_address = shared_contract["IbetEscrow"]["address"]
        attribute = self.token_attribute(exchange_address)
        coupon = IbetCouponTestHelper.issue(issuer["account_address"], attribute)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            coupon.address,
            token_list["address"],
        )

        # 取扱トークンデータ挿入
        self.list_token(session, coupon.address)

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        invalid_key_value_1 = {
            "transferable": "invalid_param",
            "status": "invalid_param",
            "initial_offering_status": "invalid_param",
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
