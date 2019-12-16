# -*- coding: utf-8 -*-
import json
import os

from app import config
from .account_config import eth_account
from .contract_modules import register_payment_gateway


# 決済用口座登録状況参照API
# /v1/User/PaymentAccount
class TestV1PaymentAccount:

    # テスト対象API
    apiurl = '/v1/User/PaymentAccount'

    # ＜正常系1＞
    # 通常参照（登録 -> 認可済）
    def test_paymentaccount_normal_1(self, client, shared_contract):
        # テスト用アカウント
        trader = eth_account['trader']
        agent = eth_account['agent']

        # 収納代行コントラクト（PaymentGateway）
        payment_gateway = shared_contract['PaymentGateway']
        config.PAYMENT_GATEWAY_CONTRACT_ADDRESS = payment_gateway['address']

        # データ準備：決済用口座情報登録->認可
        register_payment_gateway(trader, payment_gateway)

        query_string = 'account_address=' + trader['account_address'] + \
            '&agent_address=' + agent['account_address']

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = {
            'account_address': trader['account_address'],
            'agent_address': agent['account_address'],
            'approval_status': 2
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2＞
    # 通常参照（登録なし）
    def test_paymentaccount_normal_2(self, client, shared_contract):
        # テスト用アカウント（traderは任意のアドレス）
        trader = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent = eth_account['agent']

        # 収納代行コントラクト（PaymentGateway）
        payment_gateway = shared_contract['PaymentGateway']
        config.PAYMENT_GATEWAY_CONTRACT_ADDRESS = payment_gateway['address']

        query_string = 'account_address=' + trader + \
            '&agent_address=' + agent['account_address']

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = {
            'account_address': trader,
            'agent_address': agent['account_address'],
            'approval_status': 0
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー
    def test_paymentaccount_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /v1/User/PaymentAccount'
        }

    # ＜エラー系2-1＞
    # 入力エラー
    # account_addressが未設定
    def test_paymentaccount_error_2_1(self, client):
        # テスト用アカウント
        agent = eth_account['agent']

        query_string = 'agent_address=' + agent['account_address']

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'account_address':
                ['null value not allowed', 'must be of string type']
            }
        }

    # ＜エラー系2-2＞
    # 入力エラー
    # account_addressのアドレスフォーマットが正しくない
    def test_paymentaccount_error_2_2(self, client):
        # テスト用アカウント
        trader = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9"  # アドレスが短い
        agent = eth_account['agent']

        query_string = 'account_address=' + trader + \
            '&agent_address=' + agent['account_address']

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜エラー系3-1＞
    # 入力エラー
    # agent_addressが未設定
    def test_paymentaccount_error_3_1(self, client):
        # テスト用アカウント
        trader = eth_account['trader']['account_address']

        query_string = 'account_address=' + trader

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'agent_address':
                ['null value not allowed', 'must be of string type']
            }
        }

    # ＜エラー系3-2＞
    # agent_addressのアドレスフォーマットが正しくない
    def test_paymentaccount_error_3_2(self, client):
        # テスト用アカウント
        trader = eth_account['trader']['account_address']
        agent = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9"  # アドレスが短い

        query_string = 'account_address=' + trader + \
            '&agent_address=' + agent

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }
