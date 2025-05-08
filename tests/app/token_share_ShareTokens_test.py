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
from app.model.db import IDXTokenListRegister, Listing
from batch import indexer_Token_Detail
from batch.indexer_Token_Detail import Processor
from tests.account_config import eth_account
from tests.contract_modules import issue_share_token, register_share_list
from tests.utils.contract import Contract

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
    config.SHARE_TOKEN_ENABLED = True
    processor = test_module.Processor()
    return processor


class TestTokenShareTokens:
    """
    Test Case for token.ShareTokens
    """

    # テスト対象API
    apiurl = "/Token/Share"

    @staticmethod
    def share_token_attribute(exchange_address, personal_info_address):
        attribute = {
            "name": "テスト株式",
            "symbol": "SHARE",
            "tradableExchange": exchange_address,
            "personalInfoAddress": personal_info_address,
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
        token_list_item = IDXTokenListRegister()
        token_list_item.token_address = token["address"]
        token_list_item.token_template = "IbetShare"
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
        config.SHARE_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：株式新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = self.share_token_attribute(exchange_address, personal_info)
        share_token = issue_share_token(issuer, attribute)
        register_share_list(issuer, share_token, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, share_token)

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        query_string = ""
        resp = client.get(self.apiurl, params=query_string)
        tokens = [
            {
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
                "require_personal_info_registered": True,
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
        config.SHARE_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：株式新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])

        token_address_list = []

        attribute_token1 = self.share_token_attribute(
            exchange_address,
            personal_info,
        )
        attribute_token1["name"] = "テスト株式1"
        share_token1 = issue_share_token(issuer, attribute_token1)
        token_address_list.append(share_token1["address"])
        register_share_list(issuer, share_token1, token_list)

        attribute_token2 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token2["name"] = "テスト株式2"
        share_token2 = issue_share_token(issuer, attribute_token2)
        token_address_list.append(share_token2["address"])
        register_share_list(issuer, share_token2, token_list)

        attribute_token3 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token3["name"] = "テスト株式3"
        share_token3 = issue_share_token(issuer, attribute_token3)
        token_address_list.append(share_token3["address"])
        register_share_list(issuer, share_token3, token_list)

        attribute_token4 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token4["name"] = "テスト株式4"
        share_token4 = issue_share_token(issuer, attribute_token4)
        token_address_list.append(share_token4["address"])
        register_share_list(issuer, share_token4, token_list)

        attribute_token5 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token5["name"] = "テスト株式5"
        share_token5 = issue_share_token(issuer, attribute_token5)
        token_address_list.append(share_token5["address"])
        register_share_list(issuer, share_token5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, share_token1)
        self.list_token(session, share_token2)
        self.list_token(session, share_token3)
        self.list_token(session, share_token4)
        self.list_token(session, share_token5)

        # 事前準備
        processor.SEC_PER_RECORD = 1
        asyncio.run(processor.process())

        target_token_addrss_list = token_address_list[1:4]

        resp = client.get(
            self.apiurl, params={"address_list": target_token_addrss_list}
        )
        tokens = [
            {
                "token_address": token_address_list[i],
                "token_template": "IbetShare",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": f"テスト株式{i + 1}",
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
                "require_personal_info_registered": True,
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
        config.SHARE_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：株式新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])

        token_address_list = []

        attribute_token1 = self.share_token_attribute(
            exchange_address,
            personal_info,
        )
        attribute_token1["name"] = "テスト株式1"
        share_token1 = issue_share_token(issuer, attribute_token1)
        token_address_list.append(share_token1["address"])
        register_share_list(issuer, share_token1, token_list)

        attribute_token2 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token2["name"] = "テスト株式2"
        share_token2 = issue_share_token(issuer, attribute_token2)
        token_address_list.append(share_token2["address"])
        register_share_list(issuer, share_token2, token_list)

        attribute_token3 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token3["name"] = "テスト株式3"
        share_token3 = issue_share_token(issuer, attribute_token3)
        token_address_list.append(share_token3["address"])
        register_share_list(issuer, share_token3, token_list)

        attribute_token4 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token4["name"] = "テスト株式4"
        share_token4 = issue_share_token(issuer, attribute_token4)
        token_address_list.append(share_token4["address"])
        register_share_list(issuer, share_token4, token_list)

        attribute_token5 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token5["name"] = "テスト株式5"
        share_token5 = issue_share_token(issuer, attribute_token5)
        token_address_list.append(share_token5["address"])
        register_share_list(issuer, share_token5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, share_token1)
        self.list_token(session, share_token2)
        self.list_token(session, share_token3)
        self.list_token(session, share_token4)
        self.list_token(session, share_token5)

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
                "token_template": "IbetShare",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": f"テスト株式{i + 1}",
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
                "require_personal_info_registered": True,
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
        config.SHARE_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：株式新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])

        token_address_list = []

        attribute_token1 = self.share_token_attribute(
            exchange_address,
            personal_info,
        )
        attribute_token1["name"] = "テスト株式1"
        share_token1 = issue_share_token(issuer, attribute_token1)
        token_address_list.append(share_token1["address"])
        register_share_list(issuer, share_token1, token_list)

        attribute_token2 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token2["name"] = "テスト株式2"
        share_token2 = issue_share_token(issuer, attribute_token2)
        token_address_list.append(share_token2["address"])
        register_share_list(issuer, share_token2, token_list)

        attribute_token3 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token3["name"] = "テスト株式3"
        share_token3 = issue_share_token(issuer, attribute_token3)
        token_address_list.append(share_token3["address"])
        register_share_list(issuer, share_token3, token_list)

        attribute_token4 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token4["name"] = "テスト株式4"
        share_token4 = issue_share_token(issuer, attribute_token4)
        token_address_list.append(share_token4["address"])
        register_share_list(issuer, share_token4, token_list)

        attribute_token5 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token5["name"] = "テスト株式5"
        share_token5 = issue_share_token(issuer, attribute_token5)
        token_address_list.append(share_token5["address"])
        register_share_list(issuer, share_token5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, share_token1)
        self.list_token(session, share_token2)
        self.list_token(session, share_token3)
        self.list_token(session, share_token4)
        self.list_token(session, share_token5)

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        resp = client.get(self.apiurl, params={"offset": 7})
        tokens: list = []

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
        config.SHARE_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：株式新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])

        token_address_list = []

        attribute_token1 = self.share_token_attribute(
            exchange_address,
            personal_info,
        )
        attribute_token1["name"] = "テスト株式1"
        share_token1 = issue_share_token(issuer, attribute_token1)
        token_address_list.append(share_token1["address"])
        register_share_list(issuer, share_token1, token_list)

        attribute_token2 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token2["name"] = "テスト株式2"
        share_token2 = issue_share_token(issuer, attribute_token2)
        token_address_list.append(share_token2["address"])
        register_share_list(issuer, share_token2, token_list)

        attribute_token3 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token3["name"] = "テスト株式3"
        share_token3 = issue_share_token(issuer, attribute_token3)
        token_address_list.append(share_token3["address"])
        register_share_list(issuer, share_token3, token_list)

        attribute_token4 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token4["name"] = "テスト株式4"
        share_token4 = issue_share_token(issuer, attribute_token4)
        token_address_list.append(share_token4["address"])
        register_share_list(issuer, share_token4, token_list)

        attribute_token5 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token5["name"] = "テスト株式5"
        share_token5 = issue_share_token(issuer, attribute_token5)
        token_address_list.append(share_token5["address"])
        register_share_list(issuer, share_token5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, share_token1)
        self.list_token(session, share_token2)
        self.list_token(session, share_token3)
        self.list_token(session, share_token4)
        self.list_token(session, share_token5)

        # 事前準備
        processor.SEC_PER_RECORD = 1
        asyncio.run(processor.process())

        resp = client.get(
            self.apiurl,
            params={
                "name": "テスト株式",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "symbol": "SHA",
                "is_offering": False,
                "transferable": True,
                "status": True,
                "transfer_approval_required": False,
                "is_canceled": False,
                "tradable_exchange": exchange_address,
                "personal_info_address": personal_info,
                "require_personal_info_registered": True,
            },
        )
        tokens = [
            {
                "token_address": token_address_list[i],
                "token_template": "IbetShare",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": f"テスト株式{i + 1}",
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
                "require_personal_info_registered": True,
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
        config.SHARE_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：株式新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])

        token_address_list = []

        attribute_token1 = self.share_token_attribute(
            exchange_address,
            personal_info,
        )
        attribute_token1["name"] = "テスト株式1"
        share_token1 = issue_share_token(issuer, attribute_token1)
        token_address_list.append(share_token1["address"])
        register_share_list(issuer, share_token1, token_list)

        attribute_token2 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token2["name"] = "テスト株式2"
        share_token2 = issue_share_token(issuer, attribute_token2)
        token_address_list.append(share_token2["address"])
        register_share_list(issuer, share_token2, token_list)

        attribute_token3 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token3["name"] = "テスト株式3"
        share_token3 = issue_share_token(issuer, attribute_token3)
        token_address_list.append(share_token3["address"])
        register_share_list(issuer, share_token3, token_list)

        attribute_token4 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token4["name"] = "テスト株式4"
        share_token4 = issue_share_token(issuer, attribute_token4)
        token_address_list.append(share_token4["address"])
        register_share_list(issuer, share_token4, token_list)

        attribute_token5 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token5["name"] = "テスト株式5"
        share_token5 = issue_share_token(issuer, attribute_token5)
        token_address_list.append(share_token5["address"])
        register_share_list(issuer, share_token5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, share_token1)
        self.list_token(session, share_token2)
        self.list_token(session, share_token3)
        self.list_token(session, share_token4)
        self.list_token(session, share_token5)

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        not_matched_key_value = {
            "name": "not_matched_value",
            "owner_address": "0x0000000000000000000000000000000000000000",
            "company_name": "not_matched_value",
            "symbol": "not_matched_value",
            "is_offering": True,
            "transferable": False,
            "status": False,
            "transfer_approval_required": True,
            "is_canceled": True,
            "tradable_exchange": "0x0000000000000000000000000000000000000000",
            "personal_info_address": "0x0000000000000000000000000000000000000000",
            "require_personal_info_registered": False,
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
        config.SHARE_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：株式新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])

        token_address_list = []

        attribute_token1 = self.share_token_attribute(
            exchange_address,
            personal_info,
        )
        attribute_token1["name"] = "テスト株式1"
        share_token1 = issue_share_token(issuer, attribute_token1)
        token_address_list.append(share_token1["address"])
        register_share_list(issuer, share_token1, token_list)

        attribute_token2 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token2["name"] = "テスト株式2"
        share_token2 = issue_share_token(issuer, attribute_token2)
        token_address_list.append(share_token2["address"])
        register_share_list(issuer, share_token2, token_list)

        attribute_token3 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token3["name"] = "テスト株式3"
        share_token3 = issue_share_token(issuer, attribute_token3)
        token_address_list.append(share_token3["address"])
        register_share_list(issuer, share_token3, token_list)

        attribute_token4 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token4["name"] = "テスト株式4"
        share_token4 = issue_share_token(issuer, attribute_token4)
        token_address_list.append(share_token4["address"])
        register_share_list(issuer, share_token4, token_list)

        attribute_token5 = self.share_token_attribute(exchange_address, personal_info)
        attribute_token5["name"] = "テスト株式5"
        share_token5 = issue_share_token(issuer, attribute_token5)
        token_address_list.append(share_token5["address"])
        register_share_list(issuer, share_token5, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, share_token1)
        self.list_token(session, share_token2)
        self.list_token(session, share_token3)
        self.list_token(session, share_token4)
        self.list_token(session, share_token5)

        # 事前準備
        processor.SEC_PER_RECORD = 1
        asyncio.run(processor.process())

        resp = client.get(
            self.apiurl,
            params={
                "name": "テスト株式",
                "is_canceled": False,
                "sort_item": "name",
                "sort_order": 1,
            },
        )
        tokens = [
            {
                "token_address": token_address_list[i],
                "token_template": "IbetShare",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": f"テスト株式{i + 1}",
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
                "require_personal_info_registered": True,
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
        config.SHARE_TOKEN_ENABLED = False
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：株式新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = self.share_token_attribute(exchange_address, personal_info)
        share_token = issue_share_token(issuer, attribute)
        register_share_list(issuer, share_token, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, share_token)

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        query_string = ""
        resp = client.get(self.apiurl, params=query_string)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "description": "method: GET, url: /Token/Share",
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
        config.SHARE_TOKEN_ENABLED = True

        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：株式新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = self.share_token_attribute(exchange_address, personal_info)
        share_token = issue_share_token(issuer, attribute)
        register_share_list(issuer, share_token, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, share_token)

        # 事前準備
        processor.SEC_PER_RECORD = 0
        asyncio.run(processor.process())

        invalid_key_value_1 = {
            "is_offering": "invalid_param",
            "transferable": "invalid_param",
            "status": "invalid_param",
            "transfer_approval_required": "invalid_param",
            "is_canceled": "invalid_param",
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
