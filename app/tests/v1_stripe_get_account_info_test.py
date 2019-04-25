import json
from falcon.util import json as util_json
from app import config
import stripe
stripe.api_key = config.STRIPE_SECRET


class TestV1StripeGetAccountInfo():
    # テスト対象API
    apiurl = "/v1/Stripe/GetAccountInfo/"
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
            TestV1StripeGetAccountInfo.private_key_1,
            method="POST",
            path=self.apiurl,
            request_body=canonical_body,
            query_string=""
        )
        print("---- signature ----")
        print(signature)

    # 正常系1： アカウント情報の取得に成功
    def test_normal(self, client, session):
        print("TODO")

    # エラー系1-1
    # 必須項目なし (account_address_list)
    # 400 Bad Request
    def test_stripe_get_account_info_error_1_1(self, client, session):
        request_params = {
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeGetAccountInfo.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系1-2
    # account_address_listの値が空
    def test_stripe_get_account_info_error_1_2(self, client, session):
        request_params = {
            'account_address_list': [""]
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeGetAccountInfo.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系1-3
    # account_addressの値が数字
    def test_stripe_get_account_info_error_1_3(self, client, session):
        request_params = {
            'account_address_list': [1234]
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeGetAccountInfo.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系1-4
    # account_addressのアドレスフォーマットが誤り
    def test_stripe_get_account_info_error_1_4(self, client, session):
        request_params = {
            'account_address_list': ["0x2B5AD5c4795c026514f8317c7a215E218DcCD6c"]  # 短い
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeGetAccountInfo.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系2
    # 自サーバー起因エラー時 405 Error
    def test_stripe_get_account_info_error_2(self, client, session):
        # getは提供していないため、エラーとなる
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            'code': 10,
            'description': 'method: GET, url: /v1/Stripe/GetAccountInfo',
            'message': 'Not Supported'
        }