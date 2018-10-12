from app import config
import omise
omise.api_secret = config.OMISE_SECRET
omise.api_public = config.OMISE_PUBLIC

class TestV1OmiseCreateCustomer():
    # テスト対象API
    apiurl = "/v1/Omise/Customers"

    private_key_1 = "0000000000000000000000000000000000000000000000000000000000000001"
    address_1 = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

    # ＜エラー系1＞
    # ヘッダー（Signature）なし
    def test_omise_createcustomer_error_1(self, client, session):
        resp = client.simulate_post(
            self.apiurl
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'signature is empty'
        }

    # ＜エラー系2-1＞
    # 必須項目なし：token_id
    def test_omise_createcustomer_error_2_1(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {},
            private_key = TestV1OmiseCreateCustomer.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'token_id': 'required field'
            }
        }

    # ＜エラー系2-2＞
    # token_idの値が空
    def test_omise_createcustomer_error_2_2(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {"token_id": ""},
            private_key = TestV1OmiseCreateCustomer.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'token_id': 'empty values not allowed'
            }
        }

    # ＜エラー系2-3＞
    # token_idの値が数字
    def test_omise_createcustomer_error_2_3(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {"token_id": 1234},
            private_key = TestV1OmiseCreateCustomer.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'token_id': 'must be of string type'
            }
        }
