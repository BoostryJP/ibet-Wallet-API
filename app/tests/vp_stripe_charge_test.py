from falcon.util import json as util_json

from app.model import Agreement, AgreementStatus
from .contract_modules import *

import stripe
stripe.api_key = config.STRIPE_SECRET


class TestV1StripeCharge:
    # テスト対象API
    apiurl = "/v1/Stripe/Charge"
    default_account_address = "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51"
    private_key_1 = "0000000000000000000000000000000000000000000000000000000000000001"
    api_key = config.STRIPE_SECRET

    order_id = 23
    agreement_id = 23
    amount = 2000
    exchange_address = "0x476Bd2837d42868C4ddf355841602d3A792d4dbC"

    # ※テストではない
    # ヘッダー（Signature）作成
    def test_generate_signature(self, client):
        request_json = {
            "order_id": 1,
            "agreement_id": 2,
            "amount": 100,
            "exchange_address": "0xF56a5c03A2c1b2f929e9f41F34F043706f23A9E9"
        }
        canonical_body = util_json.dumps(request_json, ensure_ascii=False)
        print("---- canonical_body ----")
        print(canonical_body)

        signature = client._generate_signature(
            TestV1StripeCharge.private_key_1,
            method="POST",
            path=self.apiurl,
            request_body=canonical_body,
            query_string=""
        )
        print("---- signature ----")
        print(signature)

    # エラー系1-1
    # 認証認可
    #   Signatureなし
    def test_stripe_charge_error_1_1(self, client):
        resp = client.simulate_post(
            self.apiurl,
            json={
                "order_id": self.order_id,
                "agreement_id": self.agreement_id,
                "amount": self.amount,
                "exchange_address": self.exchange_address
            },
        )
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'description': 'signature is empty',
            'message': 'Invalid Parameter'
        }

    # エラー系1-2
    # 認証認可
    #   Signature誤り
    def test_stripe_charge_error_1_2(self, client):
        resp = client.simulate_post(
            self.apiurl,
            json={
                "order_id": self.order_id,
                "agreement_id": self.agreement_id,
                "amount": self.amount,
                "exchange_address": self.exchange_address
            },
            headers={"X-ibet-Signature":"some_wrong_signature"}
        )
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'description': 'failed to recover hash',
            'message': 'Invalid Parameter'
        }

    # エラー系2
    # 入力値チェック：必須入力チェック
    #   400 Bad Request
    def test_stripe_charge_error_2(self, client):
        resp = client.simulate_auth_post(
            self.apiurl,
            json={},
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'description': {
                'order_id': 'required field',
                'amount': 'required field',
                'agreement_id': 'required field',
                'exchange_address': 'required field'
            },
            'message': 'Invalid Parameter'
        }

    # エラー系3
    # 入力値チェック：型誤り
    #   400 Bad Request
    def test_stripe_charge_error_3(self, client):
        resp = client.simulate_auth_post(
            self.apiurl,
            json={
                "order_id": "1",  # String型
                "agreement_id": "1",  # String型
                "amount": "1",  # String型
                "exchange_address": 12345  # Integer型
            },
            private_key=TestV1StripeCharge.private_key_1
        )
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'description': {
                'order_id': 'must be of integer type',
                'agreement_id': 'must be of integer type',
                'amount': 'must be of integer type',
                'exchange_address': 'must be of string type'
            },
            'message': 'Invalid Parameter'
        }

    # エラー系4-1
    # 決済代金：amount
    #   金額チェック（最小金額：STRIPE_MINIMUM_VALUE = 50）
    def test_stripe_charge_error_4_1(self, client, session, shared_contract):
        membership_exchange = shared_contract['IbetMembershipExchange']
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = membership_exchange['address']

        # Agreementの情報を挿入
        agreement = Agreement()
        agreement.order_id = self.order_id
        agreement.agreement_id = self.agreement_id
        agreement.exchange_address = membership_exchange['address']
        agreement.seller_address = "0x31b98d14007bdee637298086988a0bbd31184527"
        agreement.amount = self.amount
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        resp = client.simulate_auth_post(
            self.apiurl,
            json={
                "order_id": self.order_id,
                "agreement_id": self.agreement_id,
                "amount": 49,
                "exchange_address": membership_exchange['address']
            },
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系4-2
    # 決済代金：amount
    #   金額チェック（最大金額：STRIPE_MAXIMUM_VALUE = 500000）
    def test_stripe_charge_error_4_2(self, client, session, shared_contract):
        membership_exchange = shared_contract['IbetMembershipExchange']
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = membership_exchange['address']

        # Agreementの情報を挿入
        agreement = Agreement()
        agreement.order_id = self.order_id
        agreement.agreement_id = self.agreement_id
        agreement.exchange_address = membership_exchange['address']
        agreement.seller_address = "0x31b98d14007bdee637298086988a0bbd31184527"
        agreement.amount = self.amount
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        resp = client.simulate_auth_post(
            self.apiurl,
            json={
                "order_id": self.order_id,
                "agreement_id": self.agreement_id,
                "amount": 500001,
                "exchange_address": membership_exchange['address']
            },
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系5
    # HTTP Method
    def test_stripe_charge_error_5(self, client):
        # getは提供していないため、エラーとなる
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            'code': 10,
            'description': 'method: GET, url: /v1/Stripe/Charge',
            'message': 'Not Supported'
        }

    # エラー系6
    # DBチェック
    #   約定情報存在なし
    def test_stripe_charge_error_6(self, client):
        resp = client.simulate_auth_post(
            self.apiurl,
            json={
                "order_id": self.order_id,
                "agreement_id": self.agreement_id,
                "amount": self.amount,
                "exchange_address": "0x476Bd2837d42868C4ddf355841602d3A792d4dbD"
            },
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'description': 'Data not found.',
            'message': 'Invalid Parameter'
        }

    # TODO: テスト追加）約定明細がキャンセル済み
    # TODO: テスト追加）StripeAccountテーブルに買手の情報が存在しない
    # TODO: テスト追加）StripeAccountテーブルに売手の情報が存在しない
    # TODO: テスト追加）二重課金チェック