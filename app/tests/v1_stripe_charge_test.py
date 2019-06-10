import os
from falcon.util import json as util_json

from app import config
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
    def test_generate_signature(self, client, session):
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
    # 必須項目なし (order_id)
    # 400 Bad Request
    def test_stripe_charge_error_1_1(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json={
                # "order_id": self.order_id,
                "agreement_id": self.agreement_id,
                "amount": self.amount,
                "exchange_address": self.exchange_address
            },
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'description': {'order_id': 'required field'},
            'message': 'Invalid Parameter'
        }

    # エラー系1-2
    # order_idの値が不正（型誤り）
    def test_stripe_charge_error_1_2(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json={
                "order_id": "a",
                "agreement_id": self.agreement_id,
                "amount": self.amount,
                "exchange_address": self.exchange_address
            },
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'description': {'order_id': 'must be of integer type'},
            'message': 'Invalid Parameter'
        }

    # エラー系2-1
    # 必須項目なし (agreement_id)
    # 400 Bad Request
    def test_stripe_charge_error_2_1(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json={
                "order_id": "a",
                # "agreement_id": self.agreement_id,
                "amount": self.amount,
                "exchange_address": self.exchange_address
            },
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'description': {
                'agreement_id': 'required field',
                'order_id': 'must be of integer type'
            },
            'message': 'Invalid Parameter'
        }

    # エラー系2-2
    # agreement_idの値が不正（型誤り）
    def test_stripe_charge_error_2_2(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json={
                "order_id": self.order_id,
                "agreement_id": "a",
                "amount": self.amount,
                "exchange_address": self.exchange_address
            },
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'description': {'agreement_id': 'must be of integer type'},
            'message': 'Invalid Parameter'
        }

    # エラー系3-1
    # 必須項目なし (amount)
    # 400 Bad Request
    def test_stripe_charge_error_3_1(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json={
                "order_id": self.order_id,
                "agreement_id": self.agreement_id,
                # "amount": self.amount,
                "exchange_address": self.exchange_address
            },
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'description': {'amount': 'required field'},
            'message': 'Invalid Parameter'
        }

    # エラー系3-2
    # amountの値が不正
    def test_stripe_charge_error_3_2(self, client, session, shared_contract):
        membership_exchange = shared_contract['IbetMembershipExchange']
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = membership_exchange['address']

        # Agreementの情報を挿入
        agreement = Agreement()
        agreement.order_id = self.order_id
        agreement.agreement_id = self.agreement_id
        agreement.exchange_address = self.exchange_address
        agreement.unique_order_id = self.exchange_address + '_' + str(1)
        agreement.seller_address = "0x31b98d14007bdee637298086988a0bbd31184527"
        agreement.counterpart_address = "0x31b98d14007bdee637298086988a0bbd31184527"
        agreement.amount = self.amount  # 2000
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        resp = client.simulate_auth_post(
            self.apiurl,
            json={
                "order_id": self.order_id,
                "agreement_id": self.agreement_id,
                "amount": 0,
                "exchange_address": membership_exchange['address']
            },
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3-3
    # amountの値が文字列
    def test_stripe_charge_error_3_3(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json={
                "order_id": self.order_id,
                "agreement_id": self.agreement_id,
                "amount": "a",
                "exchange_address": self.exchange_address
            },
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'description': {'amount': 'must be of integer type'},
            'message': 'Invalid Parameter'
        }

    # ＜エラー系4＞
    # ヘッダー（Signature）なし
    def test_stripe_charge_error_4(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # <エラー系5>
    # 自サーバー起因エラー時 405 Error
    def test_stripe_charge_error_5(self, client, session):
        # getは提供していないため、エラーとなる
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            'code': 10,
            'description': 'method: GET, url: /v1/Stripe/Charge',
            'message': 'Not Supported'
        }
