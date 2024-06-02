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
    bond_invalidate,
    bond_untransferable,
    coupon_register_list,
    invalidate_coupon_token,
    invalidate_share_token,
    issue_bond_token,
    issue_coupon_token,
    issue_share_token,
    membership_invalidate,
    membership_issue,
    membership_register_list,
    membership_untransferable,
    register_bond_list,
    register_share_list,
    untransferable_coupon_token,
    untransferable_share_token,
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class TestTokenTokenStatus:
    """
    Test Case for token.TokenStatus
    """

    # テスト対象API
    apiurl_base = "/Token/{contract_address}/Status"

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
    def share_token_attribute(exchange_address, personal_info_address):
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
    def membership_token_attribute(exchange_address):
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
    def coupon_token_attribute(exchange_address):
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

    # ＜正常系1＞
    #   債券：データあり（取扱ステータス = True, 譲渡可否 = True）
    def test_tokenstatus_normal_1(
        self, client: TestClient, session: Session, shared_contract
    ):
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = TestTokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = TestTokenTokenStatus.bond_token_attribute(
            exchange_address, personal_info
        )
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)

        # 取扱トークンデータ挿入
        TestTokenTokenStatus.list_token(session, bond_token)

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=bond_token["address"])
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assumed_body = {
            "token_template": "IbetStraightBond",
            "status": True,
            "transferable": True,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系2＞
    #   債券：データ有り（トークン無効化済み）
    def test_tokenstatus_normal_2(
        self, client: TestClient, session: Session, shared_contract
    ):
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = TestTokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = TestTokenTokenStatus.bond_token_attribute(
            exchange_address, personal_info
        )
        token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, token, token_list)

        # 取扱トークンデータ挿入
        TestTokenTokenStatus.list_token(session, token)

        # Tokenの無効化
        bond_invalidate(issuer, token)

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=token["address"])
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assumed_body = {
            "token_template": "IbetStraightBond",
            "status": False,
            "transferable": True,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系3＞
    #   債券：データあり（取扱ステータス = True, 譲渡可否 = False）
    def test_tokenstatus_normal_3(
        self, client: TestClient, session: Session, shared_contract
    ):
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = TestTokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = TestTokenTokenStatus.bond_token_attribute(
            exchange_address, personal_info
        )
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)

        # 取扱トークンデータ挿入
        TestTokenTokenStatus.list_token(session, bond_token)

        # Tokenの譲渡不可
        bond_untransferable(issuer, bond_token)

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=bond_token["address"])
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assumed_body = {
            "token_template": "IbetStraightBond",
            "status": True,
            "transferable": False,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系4＞
    #   株式：データあり（取扱ステータス = True, 譲渡可否 = True）
    def test_tokenstatus_normal_4(
        self, client: TestClient, session: Session, shared_contract
    ):
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = TestTokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：株式新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = TestTokenTokenStatus.share_token_attribute(
            exchange_address, personal_info
        )
        share_token = issue_share_token(issuer, attribute)
        register_share_list(issuer, share_token, token_list)

        # 取扱トークンデータ挿入
        TestTokenTokenStatus.list_token(session, share_token)

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=share_token["address"])
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assumed_body = {
            "token_template": "IbetShare",
            "status": True,
            "transferable": True,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系5＞
    #   株式：データ有り（トークン無効化済み）
    def test_tokenstatus_normal_5(
        self, client: TestClient, session: Session, shared_contract
    ):
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = TestTokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：株式新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = TestTokenTokenStatus.share_token_attribute(
            exchange_address, personal_info
        )
        share_token = issue_share_token(issuer, attribute)
        register_share_list(issuer, share_token, token_list)

        # 取扱トークンデータ挿入
        TestTokenTokenStatus.list_token(session, share_token)

        # Tokenの無効化
        invalidate_share_token(issuer, share_token)

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=share_token["address"])
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assumed_body = {
            "token_template": "IbetShare",
            "status": False,
            "transferable": True,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系6＞
    #   株式：データあり（取扱ステータス = True, 譲渡可否 = False）
    def test_tokenstatus_normal_6(
        self, client: TestClient, session: Session, shared_contract
    ):
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = TestTokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：株式新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = TestTokenTokenStatus.share_token_attribute(
            exchange_address, personal_info
        )
        share_token = issue_share_token(issuer, attribute)
        register_share_list(issuer, share_token, token_list)

        # 取扱トークンデータ挿入
        TestTokenTokenStatus.list_token(session, share_token)

        # Tokenの譲渡不可
        untransferable_share_token(issuer, share_token)

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=share_token["address"])
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assumed_body = {
            "token_template": "IbetShare",
            "status": True,
            "transferable": False,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系7＞
    #   会員権：データあり（取扱ステータス = True, 譲渡可否 = True）
    def test_tokenstatus_normal_7(
        self, client: TestClient, session: Session, shared_contract
    ):
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = TestTokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        attribute = TestTokenTokenStatus.membership_token_attribute(exchange_address)
        membership_token = membership_issue(issuer, attribute)
        membership_register_list(issuer, membership_token, token_list)

        # 取扱トークンデータ挿入
        TestTokenTokenStatus.list_token(session, membership_token)

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=membership_token["address"])
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assumed_body = {
            "token_template": "IbetMembership",
            "status": True,
            "transferable": True,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系8＞
    #   会員権：データ有り（トークン無効化済み）
    def test_tokenstatus_normal_8(
        self, client: TestClient, session: Session, shared_contract
    ):
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = TestTokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        attribute = TestTokenTokenStatus.membership_token_attribute(exchange_address)
        membership_token = membership_issue(issuer, attribute)
        membership_register_list(issuer, membership_token, token_list)

        # 取扱トークンデータ挿入
        TestTokenTokenStatus.list_token(session, membership_token)

        # Tokenの無効化
        membership_invalidate(issuer, membership_token)

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=membership_token["address"])
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assumed_body = {
            "token_template": "IbetMembership",
            "status": False,
            "transferable": True,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系9＞
    #   会員権：データあり（取扱ステータス = True, 譲渡可否 = False）
    def test_tokenstatus_normal_9(
        self, client: TestClient, session: Session, shared_contract
    ):
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = TestTokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：会員権新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        attribute = TestTokenTokenStatus.membership_token_attribute(exchange_address)
        membership_token = membership_issue(issuer, attribute)
        membership_register_list(issuer, membership_token, token_list)

        # 取扱トークンデータ挿入
        TestTokenTokenStatus.list_token(session, membership_token)

        # Tokenの譲渡不可
        membership_untransferable(issuer, membership_token)

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=membership_token["address"])
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assumed_body = {
            "token_template": "IbetMembership",
            "status": True,
            "transferable": False,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系10＞
    #   クーポン：データあり（取扱ステータス = True, 譲渡可否 = True）
    def test_tokenstatus_normal_10(
        self, client: TestClient, session: Session, shared_contract
    ):
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = TestTokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：クーポン新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        attribute = TestTokenTokenStatus.coupon_token_attribute(exchange_address)
        coupon_token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, coupon_token, token_list)

        # 取扱トークンデータ挿入
        TestTokenTokenStatus.list_token(session, coupon_token)

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=coupon_token["address"])
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assumed_body = {
            "token_template": "IbetCoupon",
            "status": True,
            "transferable": True,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系11＞
    #   クーポン：データ有り（トークン無効化済み）
    def test_tokenstatus_normal_11(
        self, client: TestClient, session: Session, shared_contract
    ):
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = TestTokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：クーポン新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        attribute = TestTokenTokenStatus.coupon_token_attribute(exchange_address)
        coupon_token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, coupon_token, token_list)

        # 取扱トークンデータ挿入
        TestTokenTokenStatus.list_token(session, coupon_token)

        # Tokenの無効化
        invalidate_coupon_token(issuer, coupon_token)

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=coupon_token["address"])
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assumed_body = {
            "token_template": "IbetCoupon",
            "status": False,
            "transferable": True,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系12＞
    #   クーポン：データあり（取扱ステータス = True, 譲渡可否 = False）
    def test_tokenstatus_normal_12(
        self, client: TestClient, session: Session, shared_contract
    ):
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = TestTokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：クーポン新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetShareExchange"]["address"]
        )
        attribute = TestTokenTokenStatus.coupon_token_attribute(exchange_address)
        coupon_token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, coupon_token, token_list)

        # 取扱トークンデータ挿入
        TestTokenTokenStatus.list_token(session, coupon_token)

        # Tokenの譲渡不可
        untransferable_coupon_token(issuer, coupon_token)

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=coupon_token["address"])
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assumed_body = {
            "token_template": "IbetCoupon",
            "status": True,
            "transferable": False,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜エラー系1＞
    #   無効なコントラクトアドレス（不正な形式）
    #   -> 400エラー
    def test_tokenstatus_error_1(self, client: TestClient, session: Session):
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

    # ＜エラー系2＞
    #   取扱トークン（DB）に情報が存在しない
    def test_tokenstatus_error_2(
        self, client: TestClient, shared_contract, session: Session
    ):
        # テスト用アカウント
        issuer = eth_account["issuer"]

        # TokenListコントラクト
        token_list = TestTokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]

        # データ準備：新規発行
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = TestTokenTokenStatus.bond_token_attribute(
            exchange_address, personal_info
        )
        token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, token, token_list)

        session.commit()

        # NOTE:取扱トークンデータを挿入しない

        apiurl = self.apiurl_base.format(contract_address=token["address"])
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": "token_address: " + token["address"],
        }

    # ＜エラー系3＞
    #   無効なコントラクトアドレス（TokenInterfaceを継承しているが譲渡可否を持たないコントラクト）
    #   -> 404エラー
    def test_tokenstatus_error_3(
        self, client: TestClient, session: Session, shared_contract
    ):
        share_exchange = shared_contract["IbetShareExchange"]

        # 取扱トークンデータ挿入
        TestTokenTokenStatus.list_token(session, share_exchange)

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=share_exchange["address"])

        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": "token_address: " + share_exchange["address"],
        }
