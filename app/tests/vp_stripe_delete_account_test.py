import json
from falcon.util import json as util_json
from app import config
from app.model import StripeAccount


class TestV1StripeDeleteStripeAccount():
    # テスト対象API
    apiurl = "/v1/Stripe/DeleteAccount"
    private_key_1 = "0000000000000000000000000000000000000000000000000000000000000005"
    private_key_2 = "0000000000000000000000000000000000000000000000000000000000000006"
    default_address = "0xe1AB8145F7E55DC933d51a18c793F901A3A0b276"

    # 仕込み
    @staticmethod
    def create_account_record(self, session, address, account_id, customer_id):
        # StripeAccount情報の登録
        stripe_account = StripeAccount()
        stripe_account.account_address = address
        stripe_account.account_id = account_id
        stripe_account.customer_id = customer_id
        session.add(stripe_account)

    # ※テストではない
    # ヘッダー（Signature）作成
    def test_generate_signature(self, client, session):
        json = {
        }
        canonical_body = util_json.dumps(json, ensure_ascii=False)
        print("---- canonical_body ----")
        print(canonical_body)

        signature = client._generate_signature(
            TestV1StripeDeleteStripeAccount.private_key_1,
            method="POST",
            path=self.apiurl,
            request_body=canonical_body,
            query_string=""
        )
        print("---- signature ----")
        print(signature)

    # 正常系1： 存在するアカウント情報のクリア
    def test_normal(self, client, session):
        # 仕込み
        TestV1StripeDeleteStripeAccount.create_account_record(self, session, self.default_address, "acct_1EiD9NJBgumdVGyE", "cus_F8v7DUru68icz2")
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {},
            private_key = TestV1StripeDeleteStripeAccount.private_key_1
        )
        raw = session.query(StripeAccount).filter(StripeAccount.account_address == self.default_address).first()

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert raw.account_id == ""
        assert raw.customer_id == ""

    # 正常系1： DBに存在しないアドレスへのリクエスト
    def test_normal2(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {},
            private_key = TestV1StripeDeleteStripeAccount.private_key_2
        )

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
