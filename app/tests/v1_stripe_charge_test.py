import json
from falcon.util import json as util_json
from app import config
import stripe
stripe.api_key = config.STRIPE_SECRET


class TestV1StripeCharge():
    # テスト対象API
    apiurl = "/v1/Stripe/Charge"
    default_account_address = "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51"
    private_key_1 = "0000000000000000000000000000000000000000000000000000000000000001"
    api_key = config.STRIPE_SECRET

    # ※テストではない
    # ヘッダー（Signature）作成
    def test_generate_signature(self, client, session):
        json = {
            "customer_id": "",
            "amount": 10000,
            "exchange_address": self.default_account_address,
            "order_id": 1,
            "agreement_id": 1
        }
        canonical_body = util_json.dumps(json, ensure_ascii=False)
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

    # 正常系1： Chargeの作成に成功
    def test_normal(self, client, session):
        request_body = json.dumps({
            "order_id": 1,
            "agreement_id": 1,
            "amount": 2000
        })

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

    # エラー系1-1
    # 必須項目なし (order_id)
    # 400 Bad Request
    def test_stripe_charge_error_1_1(self, client, session):
        request_params = {
            "agreement_id": 1,
            "amount": 2000
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系1-2
    # order_idの値が不正
    def test_stripe_charge_error_1_2(self, client, session):
        request_params = {
            "order_id": -1,
            "agreement_id": 1,
            "amount": 2000
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系1-3
    # order_idの値が文字列
    def test_stripe_charge_error_1_3(self, client, session):
        request_params = {
            "order_id": "a",
            "agreement_id": 1,
            "amount": 2000
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系2-1
    # 必須項目なし (agreement_id)
    # 400 Bad Request
    def test_stripe_charge_error_2_1(self, client, session):
        request_params = {
            "order_id": 1,
            "amount": 2000
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系2-2
    # account_addressの値が不正
    def test_stripe_charge_error_2_2(self, client, session):
        request_params = {
            "order_id": 1,
            "agreement_id": -1,
            "amount": 2000
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系2-3
    # account_addressの値が文字列
    def test_stripe_charge_error_2_3(self, client, session):
        request_params = {
            "order_id": 1,
            "agreement_id": "1",
            "amount": 2000
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3-1
    # 必須項目なし (amount)
    # 400 Bad Request
    def test_stripe_charge_error_3_1(self, client, session):
        request_params = {
            "order_id": 1,
            "agreement_id": 1
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3-2
    # amountの値が不正
    def test_stripe_charge_error_3_2(self, client, session):
        request_params = {
            "order_id": 1,
            "agreement_id": 1,
            "amount": -1000
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
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
        request_params = {
            "order_id": 1,
            "agreement_id": 1,
            "amount": "a"
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }