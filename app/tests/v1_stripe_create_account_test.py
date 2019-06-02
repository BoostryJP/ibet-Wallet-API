import time

from falcon.util import json as util_json
from app import config
import stripe
stripe.api_key = config.STRIPE_SECRET


class TestV1StripeCreateAccount():
    # テスト対象API
    apiurl = "/v1/Stripe/CreateAccount"
    default_account_address = "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51"
    private_key_1 = "0000000000000000000000000000000000000000000000000000000000000001"
    api_key = config.STRIPE_SECRET

    # ※テストではない
    # ヘッダー（Signature）作成
    def test_generate_signature(self, client, session):
        json = {
            "account_token": "ct_1EabAmHgQLLPjBO2ynN9ue2Q",
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
        time.sleep(5)
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {"account_token": account_token.id},
            private_key = TestV1StripeCreateAccount.private_key_1
        )

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

    # エラー系1-1
    # 必須項目なし (account_token)
    # 400 Bad Request
    def test_stripe_create_account_error_1_1(self, client, session):

        resp = client.simulate_auth_post(
            self.apiurl,
            json={},
            private_key=TestV1StripeCreateAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {'code': 88, 'description': {'account_token': 'required field'}, 'message': 'Invalid Parameter'}

    # エラー系1-2
    # account_tokenの値が空
    def test_stripe_create_account_error_1_2(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json={'account_token': ""},
            private_key=TestV1StripeCreateAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {'code': 88,'description': {'account_token': 'empty values not allowed'},'message': 'Invalid Parameter'}

    # エラー系1-3
    # account_tokenの値が数字
    def test_stripe_create_account_error_1_3(self, client, session):

        resp = client.simulate_auth_post(
            self.apiurl,
            json={'account_token': 1234},
            private_key=TestV1StripeCreateAccount.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {'code': 88,'description': {'account_token': 'must be of string type'},'message': 'Invalid Parameter'}

    # ＜エラー系2＞
    # ヘッダー（Signature）なし
    def test_stripe_create_account_error_2(self, client, session):
        resp = client.simulate_post(
            self.apiurl
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'signature is empty'
        }
    # <エラー系3>
    # 自サーバー起因エラー時 405 Error
    def test_stripe_create_account_error_3(self, client, session):
        # getは提供していないため、エラーとなる
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            'code': 10,
            'description': 'method: GET, url: /v1/Stripe/CreateAccount',
            'message': 'Not Supported'
        }
