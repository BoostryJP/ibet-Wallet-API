import json
from falcon.util import json as util_json
from app import config
import stripe
stripe.api_key = config.STRIPE_SECRET
from app.model import StripeAccount, StripeAccountStatus


class TestV1StripeAccountStatus():
    # テスト対象API
    apiurl = "/v1/Stripe/AccountStatus"
    create_account_apiurl = "/v1/Stripe/CreateAccount"
    default_account_address = "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51"
    private_key_1 = "0000000000000000000000000000000000000000000000000000000000000001"
    private_key_2 = "0000000000000000000000000000000000000000000000000000000000000002"    
    api_key = config.STRIPE_SECRET

    # 仕込み
    @staticmethod
    def create_account_record(self, session, client):
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
        resp = client.simulate_auth_post(
            self.create_account_apiurl,
            json = {"account_token": account_token.id},
            private_key = TestV1StripeAccountStatus.private_key_1
        )

    @staticmethod
    def update_account_record(self, session, account_id):
        # Charge情報を挿入
        raw = session.query(StripeAccount).first()
        raw.account_id = account_id
        session.commit()

    # ※テストではない
    # ヘッダー（Signature）作成
    def test_generate_signature(self, client, session):
        json = {
        }
        canonical_body = util_json.dumps(json, ensure_ascii=False)
        print("---- canonical_body ----")
        print(canonical_body)

        signature = client._generate_signature(
            TestV1StripeAccountStatus.private_key_1,
            method="POST",
            path=self.apiurl,
            request_body=canonical_body,
            query_string=""
        )
        print("---- signature ----")
        print(signature)

    # 正常系1： 新規アカウントに対するステータスの取得(unverified)
    def test_normal_1(self, client, session):
        TestV1StripeAccountStatus.create_account_record(self, session, client)
        TestV1StripeAccountStatus.update_account_record(self, session, "acct_1EaEQrCakyv4TsYL")
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {},
            private_key = TestV1StripeAccountStatus.private_key_1
        )
        assumed_body = {
            "verified_status": "UNVERIFIED"
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系2： 既存アカウントに対するステータスの取得(verified)
    def test_normal_2(self, client, session):
        TestV1StripeAccountStatus.update_account_record(self, session, "acct_1EaHUYCJ5LJ0Mtg3")
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {},
            private_key = TestV1StripeAccountStatus.private_key_1
        )
        assumed_body = {
            "verified_status": "VERIFIED"
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系3： 存在しないアカウントに対するステータスの取得(NONE)
    def test_normal_3(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {},
            private_key = TestV1StripeAccountStatus.private_key_2
        )
        assumed_body = {
            "verified_status": "NONE"
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜エラー系2＞
    # ヘッダー（Signature）なし
    def test_stripe_get_acocunt_status_error_1(self, client, session):
        resp = client.simulate_post(
            self.apiurl
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'signature is empty'
        }
    # エラー系3
    # 自サーバー起因エラー時 405 Error
    def test_stripe_get_acocunt_status_error_2(self, client, session):
        # getは提供していないため、エラーとなる
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            'code': 10,
            'description': 'method: GET, url: /v1/Stripe/AccountStatus',
            'message': 'Not Supported'
        }
        