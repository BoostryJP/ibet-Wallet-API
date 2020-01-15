# -*- coding: utf-8 -*-
import json

from .account_config import eth_account
from app.model import ConsumeCoupon

# クーポン消費履歴API
# /v2/Position/Coupon/Consumptions/
class TestV2CouponConsumptions():
    # テスト対象API
    apiurl = '/v2/Position/Coupon/Consumptions/'

    def _insert_test_data(self, session):
        self.session = session
        consume_coupon = ConsumeCoupon()
        consume_coupon.transaction_hash = "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455"
        consume_coupon.token_address = "0xE0C95ECa44f2A1A23C4AfeA84dba62e15A35a69b"
        consume_coupon.account_address = "0x16f39D63d156f9abCe0a9aB46F751E2eFdEB040f"
        consume_coupon.amount = 100
        consume_coupon.block_timestamp = "2020-01-15 13:56:12.183706"
        session.add(consume_coupon)

    # ＜正常系1＞
    #  クーポン消費（0件）
    def test_couponconsumptions_normal_1(self, client):
        request_params = {
            "token_address": "0x0000000000000000000000000000000000000000",
            "account_address_list": ["0x16f39D63d156f9abCe0a9aB46F751E2eFdEB040f"]
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == []

    # ＜正常系2＞
    #  クーポン消費（1件）
    def test_couponconsumptions_normal_2(self, client, session):
        self._insert_test_data(session)

        request_params = {
            "token_address": "0xE0C95ECa44f2A1A23C4AfeA84dba62e15A35a69b",
            "account_address_list": ["0x16f39D63d156f9abCe0a9aB46F751E2eFdEB040f"]
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == [
            {
                'account_address': '0x16f39D63d156f9abCe0a9aB46F751E2eFdEB040f',
                'block_timestamp': '2020/01/15 13:56:12',
                'value': 100
            }
        ]

    # ＜エラー系1＞
    #  入力値エラー
    #    request-bodyなし
    def test_couponconsumptions_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})
        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'token_address': 'required field',
                'account_address_list': 'required field'
            }
        }

    # ＜エラー系2＞
    #  入力値エラー
    #    headersなし
    def test_couponconsumptions_error_2(self, client):
        request_params = {}
        headers = {}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜エラー系3-1＞
    #  入力値エラー
    #    token_addressがアドレスフォーマットではない
    def test_couponconsumptions_error_3_1(self, client):
        token_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  # アドレスが短い
        account = eth_account['trader']

        request_params = {
            "token_address": token_address,
            "account_address_list": [account['account_address']]
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜エラー系3-2＞
    #  入力値エラー
    #    token_addressがstring以外
    def test_couponconsumptions_error_3_2(self, client):
        token_address = 123456789123456789123456789123456789
        account = eth_account['trader']

        request_params = {
            "token_address": token_address,
            "account_address_list": [account['account_address']]
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'token_address': 'must be of string type'}
        }

    # ＜エラー系4-1＞
    #  入力値エラー
    #    account_addressがアドレスフォーマットではない
    def test_couponconsumptions_error_4_1(self, client):
        token_address = "0xeb6e99675595fb052cc68da0eeecb2d5a3826378"
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  # アドレスが短い

        request_params = {
            "token_address": token_address,
            "account_address_list": [account_address]
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜エラー系4-2＞
    #  入力値エラー
    #    account_addressがstring以外
    def test_couponconsumptions_error_4_2(self, client):
        token_address = "0xeb6e99675595fb052cc68da0eeecb2d5a3826378"
        account_address = 123456789123456789123456789123456789

        request_params = {
            "token_address": token_address,
            "account_address_list": [account_address]
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'account_address_list': {'0': 'must be of string type'}
            }
        }
