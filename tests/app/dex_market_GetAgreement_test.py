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
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import config
from tests.account_config import eth_account
from tests.contract_modules import (
    coupon_offer,
    get_latest_agreementid,
    get_latest_orderid,
    issue_bond_token,
    issue_coupon_token,
    issue_share_token,
    membership_issue,
    membership_offer,
    offer_bond_token,
    register_payment_gateway,
    register_personalinfo,
    share_offer,
    take_buy,
)


class TestDEXMarketGetAgreement:
    # テスト対象API
    apiurl = "/DEX/Market/Agreement"

    # 約定イベントの作成（債券）
    # 発行体：Make売、投資家：Take買
    @staticmethod
    def _generate_agree_event_bond(exchange, personal_info, payment_gateway):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]

        attribute = {
            "name": "テスト債券",
            "symbol": "BOND",
            "totalSupply": 1000000,
            "tradableExchange": exchange["address"],
            "faceValue": 10000,
            "interestRate": 1000,
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
            "personalInfoAddress": personal_info["address"],
        }

        # 発行体オペレーション
        token = issue_bond_token(issuer, attribute)
        register_personalinfo(issuer, personal_info)
        register_payment_gateway(issuer, payment_gateway)
        offer_bond_token(issuer, exchange, token, 1000000, 1000)

        # 投資家オペレーション
        register_personalinfo(trader, personal_info)
        register_payment_gateway(trader, payment_gateway)
        latest_orderid = get_latest_orderid(exchange)
        take_buy(trader, exchange, latest_orderid, 100)
        latest_agreementid = get_latest_agreementid(exchange, latest_orderid)

        return token, latest_orderid, latest_agreementid

    # 約定イベントの作成（株式）
    # 発行体：Make売、投資家：Take買
    @staticmethod
    def _generate_agree_event_share(exchange, personal_info):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]

        attribute = {
            "name": "テスト株式",
            "symbol": "SHARE",
            "tradableExchange": exchange["address"],
            "personalInfoAddress": personal_info["address"],
            "issuePrice": 1000,
            "principalValue": 1000,
            "totalSupply": 1000000,
            "dividends": 101,
            "dividendRecordDate": "20200401",
            "dividendPaymentDate": "20200502",
            "cancellationDate": "20200603",
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
            "memo": "メモ",
            "transferable": True,
        }

        # ＜発行体オペレーション＞
        #   1) 株式トークン発行
        #   2) 株式トークンをトークンリストに登録
        #   3) 投資家名簿用個人情報コントラクト（PersonalInfo）に発行体の情報を登録
        #   4) 募集（Make売）
        token = issue_share_token(issuer, attribute)
        register_personalinfo(issuer, personal_info)
        share_offer(issuer, exchange, token, 100, 1000)

        # ＜投資家オペレーション＞
        #   1) 投資家名簿用個人情報コントラクト（PersonalInfo）に投資家の情報を登録
        #   2) Take買
        register_personalinfo(trader, personal_info)
        latest_orderid = get_latest_orderid(exchange)
        take_buy(trader, exchange, latest_orderid, 100)
        latest_agreementid = get_latest_agreementid(exchange, latest_orderid)

        return token, latest_orderid, latest_agreementid

    # 約定イベントの作成（会員権）
    # 発行体：Make売、投資家：Take買
    @staticmethod
    def _generate_agree_event_membership(exchange):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]

        attribute = {
            "name": "テスト会員権",
            "symbol": "MEMBERSHIP",
            "initialSupply": 1000000,
            "tradableExchange": exchange["address"],
            "details": "詳細",
            "returnDetails": "リターン詳細",
            "expirationDate": "20191231",
            "memo": "メモ",
            "transferable": True,
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
        }

        # 発行体オペレーション
        token = membership_issue(issuer, attribute)
        membership_offer(issuer, exchange, token, 1000000, 1000)

        # 投資家オペレーション
        latest_orderid = get_latest_orderid(exchange)
        take_buy(trader, exchange, latest_orderid, 100)
        latest_agreementid = get_latest_agreementid(exchange, latest_orderid)

        return token, latest_orderid, latest_agreementid

    # 約定イベントの作成（クーポン）
    # 発行体：Make売、投資家：Take買
    @staticmethod
    def _generate_agree_event_coupon(exchange):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]

        attribute = {
            "name": "テストクーポン",
            "symbol": "COUPON",
            "totalSupply": 1000000,
            "tradableExchange": exchange["address"],
            "details": "クーポン詳細",
            "returnDetails": "リターン詳細",
            "memo": "クーポンメモ欄",
            "expirationDate": "20191231",
            "transferable": True,
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
        }

        # 発行体オペレーション
        token = issue_coupon_token(issuer, attribute)
        coupon_offer(issuer, exchange, token, 1000000, 1000)

        # 投資家オペレーション
        latest_orderid = get_latest_orderid(exchange)
        take_buy(trader, exchange, latest_orderid, 100)
        latest_agreementid = get_latest_agreementid(exchange, latest_orderid)

        return token, latest_orderid, latest_agreementid

    ########################################################################################
    # Normal
    ########################################################################################

    # <Normal_1>
    # Membership
    def test_normal_1(self, client: TestClient, session: Session, shared_contract):
        exchange = shared_contract["IbetMembershipExchange"]

        _, order_id, agreement_id = self._generate_agree_event_membership(exchange)

        # 環境変数設定
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange["address"]
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = None

        query_string = f'order_id={order_id}&agreement_id={agreement_id}&exchange_address={exchange["address"]}'
        resp = client.get(self.apiurl, params=query_string)

        assumed_body = {
            "amount": 100,
            "canceled": False,
            "counterpart": eth_account["trader"]["account_address"],
            "buyer_address": eth_account["trader"]["account_address"],
            "seller_address": eth_account["issuer"]["account_address"],
            "paid": False,
            "price": 1000,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["amount"] == assumed_body["amount"]
        assert resp.json()["data"]["canceled"] == assumed_body["canceled"]
        assert resp.json()["data"]["counterpart"] == assumed_body["counterpart"]
        assert resp.json()["data"]["buyer_address"] == assumed_body["buyer_address"]
        assert resp.json()["data"]["seller_address"] == assumed_body["seller_address"]
        assert resp.json()["data"]["paid"] == assumed_body["paid"]
        assert resp.json()["data"]["price"] == assumed_body["price"]

    # <Normal_2>
    # Coupon
    def test_normal_2(self, client: TestClient, session: Session, shared_contract):
        exchange = shared_contract["IbetCouponExchange"]

        _, order_id, agreement_id = self._generate_agree_event_coupon(exchange)

        # 環境変数設定
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange["address"]
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = None

        query_string = f'order_id={order_id}&agreement_id={agreement_id}&exchange_address={exchange["address"]}'
        resp = client.get(self.apiurl, params=query_string)

        assumed_body = {
            "amount": 100,
            "canceled": False,
            "counterpart": eth_account["trader"]["account_address"],
            "buyer_address": eth_account["trader"]["account_address"],
            "seller_address": eth_account["issuer"]["account_address"],
            "paid": False,
            "price": 1000,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["amount"] == assumed_body["amount"]
        assert resp.json()["data"]["canceled"] == assumed_body["canceled"]
        assert resp.json()["data"]["counterpart"] == assumed_body["counterpart"]
        assert resp.json()["data"]["buyer_address"] == assumed_body["buyer_address"]
        assert resp.json()["data"]["seller_address"] == assumed_body["seller_address"]
        assert resp.json()["data"]["paid"] == assumed_body["paid"]
        assert resp.json()["data"]["price"] == assumed_body["price"]

    ########################################################################################
    # Error
    ########################################################################################

    # Error_1
    # 入力値エラー（query_stringなし）
    # 400
    def test_error_1(self, client: TestClient, session: Session):
        query_string = ""
        resp = client.get(self.apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "loc": ["query", "order_id"],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
                {
                    "loc": ["query", "agreement_id"],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
                {
                    "loc": ["query", "exchange_address"],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
            ],
            "message": "Invalid Parameter",
        }

    # Error_2
    # 入力値エラー（exchange_addressの型誤り）
    # 400
    def test_error_2(self, client: TestClient, session: Session):
        exchange_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3B"  # アドレス長が短い
        query_string = (
            f"order_id=2&agreement_id=102&exchange_address={exchange_address}"
        )
        resp = client.get(self.apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "loc": ["exchange_address"],
                    "msg": "owner_address is not a valid address",
                    "type": "value_error",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_3
    # 入力値エラー（数値項目の型誤り）
    # 400
    def test_error_3(self, client: TestClient, session: Session):
        exchange_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        query_string = (
            f"order_id=aa&agreement_id=bb&exchange_address={exchange_address}"
        )
        resp = client.get(self.apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "loc": ["query", "order_id"],
                    "msg": "value is not a valid integer",
                    "type": "type_error.integer",
                },
                {
                    "loc": ["query", "agreement_id"],
                    "msg": "value is not a valid integer",
                    "type": "type_error.integer",
                },
            ],
            "message": "Invalid Parameter",
        }

    # Error_4
    # 指定した約定情報が存在しない
    # 400
    def test_error_4(self, client: TestClient, session: Session, shared_contract):
        exchange = shared_contract["IbetMembershipExchange"]

        _, order_id, agreement_id = self._generate_agree_event_membership(exchange)
        not_exist_order_id = 999
        not_exist_agreement_id = 999

        # 環境変数設定
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange["address"]
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = None

        query_string = (
            f"order_id={not_exist_order_id}&agreement_id={not_exist_agreement_id}&"
            f'exchange_address={exchange["address"]}'
        )
        resp = client.get(self.apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "Data not found",
        }

    # Error_5
    # exchangeアドレスが環境変数の値と異なる
    # 400
    def test_error_5(self, client: TestClient, session: Session, shared_contract):
        exchange_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        order_id = 2
        agreement_id = 102

        # 環境変数設定
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = shared_contract[
            "IbetMembershipExchange"
        ]["address"]
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = None

        query_string = f"order_id={order_id}&agreement_id={agreement_id}&exchange_address={exchange_address}"
        resp = client.get(self.apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "Invalid Address",
        }

    # Error_6
    # exchangeアドレスが未設定
    # 404
    def test_error_6(self, client: TestClient, session: Session):
        exchange_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        order_id = 2
        agreement_id = 102

        # 環境変数設定
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = None
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = None

        query_string = f"order_id={order_id}&agreement_id={agreement_id}&exchange_address={exchange_address}"
        resp = client.get(self.apiurl, params=query_string)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /DEX/Market/Agreement",
        }
