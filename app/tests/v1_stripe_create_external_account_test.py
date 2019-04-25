import json
from falcon.util import json as util_json
from app import config
import stripe
stripe.api_key = config.STRIPE_SECRET


class TestV1StripeCreateExternalAccount():
    # テスト対象API
    apiurl = "/v1/Stripe/CreateExternalAccount/"
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
            TestV1StripeCreateExternalAccount.private_key_1,
            method="POST",
            path=self.apiurl,
            request_body=canonical_body,
            query_string=""
        )
        print("---- signature ----")
        print(signature)

    # 正常系1： Externalアカウント(銀行口座)の登録に成功
    # StripeAPIによる使い捨て銀行トークンの発行を行い、Externalアカウントを作成する
    def test_normal(self, client, session):
        print("TODO")

    # エラー系1-1
    # 必須項目なし (bank_token)
    # 400 Bad Request
    def test_stripe_create_external_account_error_1_1(self, client, session):
        request_params = {
            'account_address': self.default_account_address
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateExternalAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系1-2
    # bank_tokenの値が空
    def test_stripe_create_external_account_error_1_2(self, client, session):
        request_params = {
            'account_address': self.default_account_address,
            'bank_token': ""
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateExternalAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系1-3
    # bank_tokenの値が数字
    def test_stripe_create_external_account_error_1_3(self, client, session):
        request_params = {
            'account_address': self.default_account_address,
            'bank_token': 1234
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateExternalAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系1-4
    # bank_tokenのフォーマットが誤り
    def test_stripe_create_external_account_error_1_4(self, client, session):
        request_params = {
            'account_address': self.default_account_address,
            'bank_token': "abc"
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateExternalAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系2-1
    # 必須項目なし (account_address)
    def test_stripe_create_external_account_error_2_1(self, client, session):
        request_params = {
            'bank_token': "btok_1ET1GOHgQLLPjBO2yBcRAOXS"
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateExternalAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系2-2
    # account_addressの値が空
    def test_stripe_create_external_account_error_2_2(self, client, session):
        request_params = {
            'account_address': "",
            'bank_token': "btok_1ET1GOHgQLLPjBO2yBcRAOXS"
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateExternalAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系2-3
    # account_addressの値が数字
    def test_stripe_create_external_account_error_2_3(self, client, session):
        request_params = {
            'account_address': 1234,
            'bank_token': "btok_1ET1GOHgQLLPjBO2yBcRAOXS"
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateExternalAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系2-4
    # account_addressのアドレスフォーマットが誤り
    def test_stripe_create_external_account_error_2_4(self, client, session):
        request_params = {
            'account_address': "0x2B5AD5c4795c026514f8317c7a215E218DcCD6c",  # 短い
            'bank_token': "btok_1ET1GOHgQLLPjBO2yBcRAOXS"
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateExternalAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3
    # 自サーバー起因エラー時 405 Error
    def test_stripe_create_external_account_error_3(self, client, session):
        # getは提供していないため、エラーとなる
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            'code': 10,
            'description': 'method: GET, url: /v1/Stripe/CreateExternalAccount',
            'message': 'Not Supported'
        }
