from falcon.util import json as util_json

class TestV1OmiseCharge():
    # テスト対象API
    apiurl = "/v1/Omise/Charge"

    private_key_1 = "0000000000000000000000000000000000000000000000000000000000000001"
    address_1 = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

    # ※テストではない
    # ヘッダー（Signature）作成
    def test_generate_signature(self, client, session):
        json = {
            "customer_id":"cust_test_5dkkd1jbvrh12bd7p7j",
            "amount": 10000,
            "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
            "order_id": 1,
            "agreement_id": 1
        }
        canonical_body = util_json.dumps(json, ensure_ascii=False)
        print("---- canonical_body ----")
        print(canonical_body)

        signature = client._generate_signature(
            TestV1OmiseCharge.private_key_1,
            method = "POST",
            path = self.apiurl,
            request_body = canonical_body,
            query_string=""
        )
        print("---- signature ----")
        print(signature)

    # ＜エラー系1＞
    # ヘッダー（Signature）なし
    def test_omise_charge_error_1(self, client, session):
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
    # 必須項目なし：customer_id
    def test_omise_charge_error_2_1(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {
                "amount": 10000,
                "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
                "order_id": 1,
                "agreement_id": 1
            },
            private_key = TestV1OmiseCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'customer_id': 'required field'
            }
        }

    # ＜エラー系2-2＞
    # customer_idの値が空
    def test_omise_charge_error_2_2(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {
                "customer_id": "",
                "amount": 10000,
                "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
                "order_id": 1,
                "agreement_id": 1
            },
            private_key = TestV1OmiseCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'customer_id': 'empty values not allowed'
            }
        }

    # ＜エラー系2-3＞
    # customer_idの値が数字
    def test_omise_charge_error_2_3(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {
                "customer_id": 1234,
                "amount": 10000,
                "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
                "order_id": 1,
                "agreement_id": 1
            },
            private_key = TestV1OmiseCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'customer_id': 'must be of string type'
            }
        }

    # ＜エラー系3-1＞
    # 必須項目なし：amount
    def test_omise_charge_error_3_1(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {
                "customer_id":"cust_test_XXXXXXXXXXXXXXXXXXX",
                "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
                "order_id": 1,
                "agreement_id": 1
            },
            private_key = TestV1OmiseCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'amount': 'required field'
            }
        }

    # ＜エラー系3-2＞
    # amountの値がNull
    def test_omise_charge_error_3_2(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {
                "customer_id":"cust_test_XXXXXXXXXXXXXXXXXXX",
                "amount": None,
                "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
                "order_id": 1,
                "agreement_id": 1
            },
            private_key = TestV1OmiseCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'amount': [
                    'null value not allowed',
                    "field 'amount' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系3-3＞
    # amountの値がマイナス値
    def test_omise_charge_error_3_3(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {
                "customer_id": "cust_test_XXXXXXXXXXXXXXXXXXX",
                "amount": -1,
                "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
                "order_id": 1,
                "agreement_id": 1
            },
            private_key = TestV1OmiseCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'amount': 'min value is 0'
            }
        }

    # ＜エラー系4-1＞
    # 必須項目なし：exchange_address
    def test_omise_charge_error_4_1(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {
                "customer_id": "cust_test_XXXXXXXXXXXXXXXXXXX",
                "amount": 10000,
                "order_id": 1,
                "agreement_id": 1
            },
            private_key = TestV1OmiseCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'exchange_address': 'required field'
            }
        }

    # ＜エラー系4-2＞
    # exchange_addressの値が空
    def test_omise_charge_error_4_2(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {
                "customer_id": "cust_test_XXXXXXXXXXXXXXXXXXX",
                "amount": 10000,
                "exchange_address": "",
                "order_id": 1,
                "agreement_id": 1
            },
            private_key = TestV1OmiseCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'exchange_address': 'empty values not allowed'
            }
        }

    # ＜エラー系4-3＞
    # exchange_addressの値が数字
    def test_omise_charge_error_4_3(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {
                "customer_id": "cust_test_XXXXXXXXXXXXXXXXXXX",
                "amount": 10000,
                "exchange_address": 1234,
                "order_id": 1,
                "agreement_id": 1
            },
            private_key = TestV1OmiseCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'exchange_address': 'must be of string type'
            }
        }

    # ＜エラー系4-4＞
    # exchange_addressのアドレスフォーマットが誤り
    def test_omise_charge_error_4_4(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {
                "customer_id": "cust_test_XXXXXXXXXXXXXXXXXXX",
                "amount": 10000,
                "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6c", # 短い
                "order_id": 1,
                "agreement_id": 1
            },
            private_key = TestV1OmiseCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜エラー系5-1＞
    # 必須項目なし：order_id
    def test_omise_charge_error_5_1(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {
                "customer_id":"cust_test_XXXXXXXXXXXXXXXXXXX",
                "amount": 10000,
                "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
                "agreement_id": 1
            },
            private_key = TestV1OmiseCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'order_id': 'required field'
            }
        }

    # ＜エラー系5-2＞
    # order_idの値がNull
    def test_omise_charge_error_5_2(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {
                "customer_id":"cust_test_XXXXXXXXXXXXXXXXXXX",
                "amount": 10000,
                "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
                "order_id": None,
                "agreement_id": 1
            },
            private_key = TestV1OmiseCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'order_id': [
                    'null value not allowed',
                    "field 'order_id' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系5-3＞
    # order_idの値がマイナス値
    def test_omise_charge_error_5_3(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {
                "customer_id": "cust_test_XXXXXXXXXXXXXXXXXXX",
                "amount": 10000,
                "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
                "order_id": -1,
                "agreement_id": 1
            },
            private_key = TestV1OmiseCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'order_id': 'min value is 0'
            }
        }

    # ＜エラー系6-1＞
    # 必須項目なし：agreement_id
    def test_omise_charge_error_6_1(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {
                "customer_id":"cust_test_XXXXXXXXXXXXXXXXXXX",
                "amount": 10000,
                "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
                "order_id": 1
            },
            private_key = TestV1OmiseCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'agreement_id': 'required field'
            }
        }

    # ＜エラー系6-2＞
    # agreement_idの値がNull
    def test_omise_charge_error_6_2(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {
                "customer_id":"cust_test_XXXXXXXXXXXXXXXXXXX",
                "amount": 10000,
                "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
                "order_id": 1,
                "agreement_id": None
            },
            private_key = TestV1OmiseCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'agreement_id': [
                    'null value not allowed',
                    "field 'agreement_id' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系6-3＞
    # agreement_idの値がマイナス値
    def test_omise_charge_error_6_3(self, client, session):
        resp = client.simulate_auth_post(
            self.apiurl,
            json = {
                "customer_id": "cust_test_XXXXXXXXXXXXXXXXXXX",
                "amount": 10000,
                "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
                "order_id": 1,
                "agreement_id": -1
            },
            private_key = TestV1OmiseCharge.private_key_1
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'agreement_id': 'min value is 0'
            }
        }
