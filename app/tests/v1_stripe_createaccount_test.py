import json
from falcon.util import json as util_json
from app import config
import stripe
stripe.api_key = config.STRIPE_SECRET


class TestV1StripeCreateAccount():
    # テスト対象API
    apiurl = "/v1/Stripe/CreateAccount/"
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
            TestV1StripeCreateAccount.private_key_1,
            method="POST",
            path=self.apiurl,
            request_body=canonical_body,
            query_string=""
        )
        print("---- signature ----")
        print(signature)

    # 正常系1： Connectアカウントの登録に成功
    # StripeAPIによる使い捨てトークンの発行を行い、アカウントを作成する
    def test_normal(self, client, session):
        account_token = stripe.Token.create(
            account={
                'individual': {
                    'first_name': 'Jane',
                    'last_name': 'Doe',
                },
                'business_type': 'individual',
                'tos_shown_and_accepted': True,
            },
        )
        print(account_token)

        account_token_id = account_token.id

        request_body = json.dumps({
            'account_address': self.default_account_address,
            'account_token': account_token_id
        })

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateAccount.private_key_1
        )

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

    # エラー系1-1
    # 必須項目なし (account_token)
    # 400 Bad Request
    def test_stripe_createaccount_1_1(self, client, session):
        request_params = {
            'account_address': self.default_account_address
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系1-2
    # account_tokenの値が空
    def test_stripe_createaccount_1_2(self, client, session):
        request_params = {
            'account_address': self.default_account_address,
            'account_token': ""
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系1-3
    # account_tokenの値が数字
    def test_stripe_createaccount_1_3(self, client, session):
        request_params = {
            'account_address': self.default_account_address,
            'account_token': 1234
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系1-4
    # account_tokenのフォーマットが誤り
    def test_stripe_createaccount_1_4(self, client, session):
        request_params = {
            'account_address': self.default_account_address,
            'account_token': "abc"
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系2-1
    # 必須項目なし (account_address)
    def test_stripe_createaccount_2_1(self, client, session):
        request_params = {
            'account_token': "ct_1EPLU9HgQLLPjBO2760HyH5v"
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系2-2
    # account_addressの値が空
    def test_stripe_createaccount_2_2(self, client, session):
        request_params = {
            'account_address': ""
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系2-3
    # account_addressの値が数字
    def test_stripe_createaccount_2_3(self, client, session):
        request_params = {
            'account_address': 1234
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系2-4
    # exchange_addressのアドレスフォーマットが誤り
    def test_stripe_createaccount_2_4(self, client, session):
        request_params = {
            'account_address': "0x2B5AD5c4795c026514f8317c7a215E218DcCD6c"  # 短い,
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_auth_post(
            self.apiurl,
            body=request_body,
            private_key=TestV1StripeCreateAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3
    # 自サーバー起因エラー時 405 Error
    def test_stripe_createaccount_1(self, client, session):
        # getは提供していないため、エラーとなる
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            'code': 10,
            'description': 'method: GET, url: /v1/Stripe/CreateAccount',
            'message': 'Not Supported'
        }
