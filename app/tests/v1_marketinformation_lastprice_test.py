# -*- coding: utf-8 -*-
import pytest
import json
import os

from .account_config import eth_account
from .contract_modules import issue_bond_token, offer_bond_token, \
    register_personalinfo, register_whitelist, take_buy_bond_token, get_latest_orderid


# 現在値取得API
# /v1/LastPrice/
class TestV1LastPrice():

    # テスト対象API
    apiurl = '/v1/LastPrice/'

    # 約定イベントの作成
    @staticmethod
    def generate_agree_event(bond_exchange, personal_info, white_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']

        attribute = {
            'name': 'テスト債券',
            'symbol': 'BOND',
            'totalSupply': 1000000,
            'faceValue': 10000,
            'interestRate': 1000,
            'interestPaymentDate1': '0331',
            'interestPaymentDate2': '0930',
            'redemptionDate': '20191231',
            'redemptionAmount': 10000,
            'returnDate': '20191231',
            'returnAmount': '商品券をプレゼント',
            'purpose': '新商品の開発資金として利用。',
            'memo': 'メモ'
        }

        # 発行体オペレーション
        bond_token = issue_bond_token(issuer, attribute)
        register_personalinfo(issuer, personal_info)
        register_whitelist(issuer, white_list)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)

        # 投資家オペレーション
        register_personalinfo(trader, personal_info)
        register_whitelist(trader, white_list)
        latest_orderid = get_latest_orderid(bond_exchange)
        take_buy_bond_token(trader, bond_exchange, latest_orderid - 1, 100)

        return bond_token

    # 正常系1：存在しない取引コントラクトアドレスを指定
    #  -> 現在値：0円
    def test_lastprice_normal_1(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        os.environ[
            "IBET_SB_EXCHANGE_CONTRACT_ADDRESS"] = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token_address':
            '0xe883a6f441ad5682d37df31d34fc012bcb07a740',
            'last_price':
            0
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系2：約定が発生していないトークンアドレスを指定した場合
    #  -> 現在値：0円
    def test_lastprice_normal_2(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token_address':
            '0xe883a6f441ad5682d37df31d34fc012bcb07a740',
            'last_price':
            0
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系3：1000円で約定
    #  -> 現在値1000円が返却される
    def test_lastprice_normal_3(self, client, shared_contract):
        bond_exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']
        white_list = shared_contract['WhiteList']

        print("-- contract_address --")
        print(bond_exchange['address'])
        print(personal_info['address'])
        print(white_list['address'])

        bond_token = TestV1LastPrice.generate_agree_event(bond_exchange,
                                                     personal_info, white_list)

        token_address = bond_token['address']
        request_params = {"address_list": [token_address]}

        print("-- token_address --")
        print(token_address)

        os.environ["IBET_SB_EXCHANGE_CONTRACT_ADDRESS"] = bond_exchange['address']

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token_address':token_address,
            'last_price':1000
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # エラー系1：入力値エラー（request-bodyなし）
    def test_lastprice_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'address_list': 'required field'
            }
        }

    # エラー系2：入力値エラー（headersなし）
    def test_lastprice_error_2(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3：入力値エラー（token_addressがアドレスフォーマットではない）
    def test_lastprice_error_3(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a74"  #アドレス長が短い
        request_params = {"address_list": [token_address]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系4：HTTPメソッドが不正
    def test_lastprice_error_4(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v1/LastPrice'
        }
