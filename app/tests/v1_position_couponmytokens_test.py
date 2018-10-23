# -*- coding: utf-8 -*-
import pytest
import json
import os

import app.model

from .account_config import eth_account
from .contract_modules import issue_coupon_token, deposit_coupon_token, \
    transfer_coupon_token, invalidate_coupon_token, coupon_register_list

# [クーポン]保有トークン一覧API
# /v1/Coupon/MyTokens/
class TestV1CouponMyTokens():

    # テスト対象API
    apiurl = '/v1/Coupon/MyTokens/'

    # クーポントークンの保有状態を作成
    @staticmethod
    def generate_coupon_position(coupon_exchange, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        attribute = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 10000,
            'details': 'クーポン詳細',
            'memo': 'クーポンメモ欄',
            'expirationDate': '20191231',
            'transferable': True
        }

        # ＜発行体オペレーション＞
        #   1) クーポントークン発行
        #   2) Exchangeにデポジット（10トークン）
        #   3) 投資家に付与（10トークン）
        coupon_token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, coupon_token, token_list)
        deposit_coupon_token(issuer, coupon_token, coupon_exchange, 10)
        transfer_coupon_token(issuer, coupon_token, coupon_exchange,
            trader['account_address'], 10)
        return coupon_token

    # 無効化クーポントークンの保有状態を作成
    @staticmethod
    def generate_coupon_position_invalid(coupon_exchange, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        attribute = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 10000,
            'details': 'クーポン詳細',
            'memo': 'クーポンメモ欄',
            'expirationDate': '20191231',
            'transferable': True
        }

        # ＜発行体オペレーション＞
        #   1) クーポントークン発行
        #   2) Exchangeにデポジット（10トークン）
        #   3) 投資家に付与（10トークン）
        #   4) クーポントークンを無効化
        coupon_token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, coupon_token, token_list)
        deposit_coupon_token(issuer, coupon_token, coupon_exchange, 10)
        transfer_coupon_token(issuer, coupon_token, coupon_exchange,
            trader['account_address'], 10)
        invalidate_coupon_token(issuer, coupon_token)
        return coupon_token

    # ＜正常系1-1＞
    # クーポントークン保有
    #  クーポン新規発行 -> 投資家割当
    #   -> 該当クーポンの保有情報が返却
    def test_position_normal_1_1(self, client, session, shared_contract):
        coupon_exchange = shared_contract['IbetCouponExchange']
        token_list = shared_contract['TokenList']

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        coupon_token = TestV1CouponMyTokens.\
            generate_coupon_position(coupon_exchange, token_list)
        coupon_address = coupon_token['address']

        os.environ["IBET_CP_EXCHANGE_CONTRACT_ADDRESS"] = coupon_exchange['address']
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': coupon_address,
                'token_template': 'IbetCoupon',
                'owner_address': eth_account['issuer']['account_address'],
                'company_name': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'totalSupply': 10000,
                'details': 'クーポン詳細',
                'memo': 'クーポンメモ欄',
                'expirationDate': '20191231',
                'transferable': True,
                'image_url': [{
                    'type': 'small',
                    'url': ''
                }, {
                    'type': 'medium',
                    'url': ''
                }, {
                    'type': 'large',
                    'url': ''
                }]
            },
            'balance': 10,
            'used': 0
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        count = 0
        for token in resp.json['data']:
            if token['token']['token_address'] == coupon_address:
                count = 1
                assert token == assumed_body
        assert count == 1

    # ＜正常系1-2＞
    # クーポントークン保有（無効化済）
    #  クーポン新規発行 -> 投資家割当 -> クーポン無効化
    #   -> 該当クーポンの保有情報が返却されない
    def test_position_normal_1_2(self, client, session, shared_contract):
        coupon_exchange = shared_contract['IbetCouponExchange']
        token_list = shared_contract['TokenList']

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        coupon_token = TestV1CouponMyTokens.\
            generate_coupon_position_invalid(coupon_exchange, token_list)
        coupon_address = coupon_token['address']

        os.environ["IBET_CP_EXCHANGE_CONTRACT_ADDRESS"] = coupon_exchange['address']
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        for token in resp.json['data']:
            assert token['token']['token_address'] != coupon_address

    # エラー系1：入力値エラー（request-bodyなし）
    def test_position_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'account_address_list': 'required field'
            }
        }

    # エラー系2：入力値エラー（headersなし）
    def test_position_error_2(self, client):
        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3-1：入力値エラー（account_addressがアドレスフォーマットではない）
    def test_position_error_3_1(self, client):
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  #アドレスが短い
        request_params = {"account_address_list": [account_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3-2：入力値エラー（account_addressがstring以外）
    def test_position_error_3_2(self, client):
        account_address = 123456789123456789123456789123456789
        request_params = {"account_address_list": [account_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'account_address_list': {
                    '0': 'must be of string type'
                }
            }
        }
