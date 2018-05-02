# -*- coding: utf-8 -*-
import pytest
import json
import os

from .account_config import eth_account
from .contract_modules import issue_bond_token, offer_bond_token, \
    register_personalinfo, register_whitelist, take_buy_bond_token, get_latest_orderid


# 歩み値参照API
# /v1/Tick/
class TestV1Tick():

    # テスト対象API
    apiurl = '/v1/Tick/'

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
            'purpose': '新商品の開発資金として利用。'
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
        take_buy_bond_token(trader, bond_exchange, latest_orderid-1, 100)

        return bond_token

    # 正常系1：約定（Agree）イベントがゼロ件の場合
    #   →ゼロ件リストが返却される
    def test_tick_normal_1(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{'token_address': token_address, 'tick': []}]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系2：約定イベントが有件の場合
    #   →約定イベントの情報が返却される
    def test_tick_normal_2(self, client, shared_contract):
        bond_exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']
        white_list = shared_contract['WhiteList']

        print("-- contract_address --")
        print(bond_exchange['address'])
        print(personal_info['address'])
        print(white_list['address'])

        bond_token = TestV1Tick.generate_agree_event(bond_exchange,
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

        assumed_body = [{'token_address': token_address, 'tick': []}]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'][0]['token_address'] == token_address
        assert resp.json['data'][0]['tick'][0]['buy_address'] == eth_account['trader']
        assert resp.json['data'][0]['tick'][0]['sell_address'] == eth_account['issuer']
        assert resp.json['data'][0]['tick'][0]['price'] == 1000
        assert resp.json['data'][0]['tick'][0]['amount'] == 100
