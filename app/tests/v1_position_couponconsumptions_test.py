# -*- coding: utf-8 -*-
import json

from .account_config import eth_account
from .contract_modules import issue_coupon_token, deposit_coupon_token, \
    transfer_coupon_token, consume_coupon_token


# クーポン消費履歴API
# /v1/CouponConsumptions/
class TestV1CouponConsumptions():
    # テスト対象API
    apiurl = '/v1/CouponConsumptions/'

    # クーポン消費イベント（1件）を作成
    @staticmethod
    def generate_consumption_one(coupon_exchange):
        issuer = eth_account['issuer']
        trader = eth_account['trader']

        attribute = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 10000,
            'tradableExchange': coupon_exchange['address'],
            'details': 'クーポン詳細',
            'returnDetails': 'リターン詳細',
            'memo': 'クーポンメモ欄',
            'expirationDate': '20191231',
            'transferable': True
        }

        # ＜発行体オペレーション＞
        #   1) クーポントークン発行
        #   2) Exchangeにデポジット（10トークン）
        #   3) 投資家に付与（10トークン）
        coupon_token = issue_coupon_token(issuer, attribute)
        deposit_coupon_token(issuer, coupon_token, coupon_exchange, 10)
        transfer_coupon_token(issuer, coupon_token, coupon_exchange,
                              trader['account_address'], 10)

        # ＜投資家オペレーション＞
        #   1) クーポン消費
        consume_coupon_token(trader, coupon_token, 1)

        return coupon_token

    # クーポン消費イベント（3件）を作成
    @staticmethod
    def generate_consumption_three(coupon_exchange):
        issuer = eth_account['issuer']
        trader = eth_account['trader']

        attribute = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 10000,
            'tradableExchange': coupon_exchange['address'],
            'details': 'クーポン詳細',
            'returnDetails': 'リターン詳細',
            'memo': 'クーポンメモ欄',
            'expirationDate': '20191231',
            'transferable': True
        }

        # ＜発行体オペレーション＞
        #   1) クーポントークン発行
        #   2) Exchangeにデポジット（10トークン）
        #   3) 投資家に付与（10トークン）
        coupon_token = issue_coupon_token(issuer, attribute)
        deposit_coupon_token(issuer, coupon_token, coupon_exchange, 10)
        transfer_coupon_token(issuer, coupon_token, coupon_exchange, trader['account_address'], 10)

        # ＜投資家オペレーション＞
        #   1) クーポン消費
        consume_coupon_token(trader, coupon_token, 1)
        consume_coupon_token(trader, coupon_token, 1)
        consume_coupon_token(trader, coupon_token, 1)

        return coupon_token

    # ＜正常系1＞
    #  クーポン消費（1件）
    def test_couponconsumptions_normal_1(self, client, session, shared_contract):
        coupon_exchange = shared_contract['IbetCouponExchange']

        coupon_token = TestV1CouponConsumptions. \
            generate_consumption_one(coupon_exchange)

        account = eth_account['trader']
        request_params = {
            "token_address": coupon_token['address'],
            "account_address_list": [account['account_address']]
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        for consumption_event in resp.json['data']:
            assert consumption_event['account_address'] == account['account_address']
            assert consumption_event['value'] == 1

    # ＜正常系2＞
    #  クーポン消費（3件）
    def test_couponconsumptions_normal_2(self, client, session, shared_contract):
        coupon_exchange = shared_contract['IbetCouponExchange']

        coupon_token = TestV1CouponConsumptions. \
            generate_consumption_three(coupon_exchange)

        account = eth_account['trader']
        request_params = {
            "token_address": coupon_token['address'],
            "account_address_list": [account['account_address']]
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert len(resp.json['data']) == 3
        for consumption_event in resp.json['data']:
            assert consumption_event['account_address'] == account['account_address']
            assert consumption_event['value'] == 1

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
