# -*- coding: utf-8 -*-
import pytest
import json
import os

import app.model

from .account_config import eth_account
from .contract_config import IbetStraightBond
from .contract_modules import issue_bond_token, offer_bond_token, \
    register_personalinfo, register_whitelist, take_buy_bond_token, get_latest_orderid, \
    register_bond_list, get_latest_agreementid, bond_confirm_agreement


# 注文一覧・約定一覧API
# /v1/OrderList/
class TestV1OrderList():

    # テスト対象API
    apiurl = '/v1/OrderList/'

    def bond_token_attribute():
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
        return attribute

    # 注文中明細の作成：発行体
    @staticmethod
    def order_event(bond_exchange, personal_info, white_list, token_list):
        issuer = eth_account['issuer']

        attribute = TestV1OrderList.bond_token_attribute()

        # ＜発行体オペレーション＞
        #   1) 債券トークン発行
        #   2) 債券トークンをトークンリストに登録
        #   3) 投資家名簿用個人情報コントラクト（PersonalInfo）に発行体の情報を登録
        #   4) 決済用口座情報コントラクト（WhiteList）に発行体の情報を登録
        #   5) 募集
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)
        register_personalinfo(issuer, personal_info)
        register_whitelist(issuer, white_list)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)

        order_id = get_latest_orderid(bond_exchange) - 1
        agreement_id = get_latest_agreementid(bond_exchange, order_id)

        return bond_token, order_id, agreement_id

    # 約定明細（決済中）の作成：投資家
    @staticmethod
    def agreement_event(bond_exchange, personal_info, white_list, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = TestV1OrderList.bond_token_attribute()

        # ＜発行体オペレーション＞
        #   1) 債券トークン発行
        #   2) 債券トークンをトークンリストに登録
        #   3) 投資家名簿用個人情報コントラクト（PersonalInfo）に発行体の情報を登録
        #   4) 決済用口座情報コントラクト（WhiteList）に発行体の情報を登録
        #   5) 募集
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)
        register_personalinfo(issuer, personal_info)
        register_whitelist(issuer, white_list)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) 投資家名簿用個人情報コントラクト（PersonalInfo）に投資家の情報を登録
        #   2) 決済用口座情報コントラクト（WhiteList）に投資家の情報を登録
        #   3) 買い注文
        register_personalinfo(trader, personal_info)
        register_whitelist(trader, white_list)
        order_id = get_latest_orderid(bond_exchange) - 1
        take_buy_bond_token(trader, bond_exchange, order_id, 100)
        agreement_id = get_latest_agreementid(bond_exchange, order_id) - 1

        return bond_token, order_id, agreement_id

    # 決済済明細の作成：決済業者
    @staticmethod
    def settlement_event(bond_exchange, personal_info, white_list, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = TestV1OrderList.bond_token_attribute()

        # ＜発行体オペレーション＞
        #   1) 債券トークン発行
        #   2) 債券トークンをトークンリストに登録
        #   3) 投資家名簿用個人情報コントラクト（PersonalInfo）に発行体の情報を登録
        #   4) 決済用口座情報コントラクト（WhiteList）に発行体の情報を登録
        #   5) 募集
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)
        register_personalinfo(issuer, personal_info)
        register_whitelist(issuer, white_list)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) 投資家名簿用個人情報コントラクト（PersonalInfo）に投資家の情報を登録
        #   2) 決済用口座情報コントラクト（WhiteList）に投資家の情報を登録
        #   3) 買い注文
        register_personalinfo(trader, personal_info)
        register_whitelist(trader, white_list)
        order_id = get_latest_orderid(bond_exchange) - 1
        take_buy_bond_token(trader, bond_exchange, order_id, 100)

        # ＜決済業者オペレーション＞
        agreement_id = get_latest_agreementid(bond_exchange, order_id) - 1
        bond_confirm_agreement(agent, bond_exchange, order_id, agreement_id)

        return bond_token, order_id, agreement_id

    # ＜正常系1＞
    # 注文中なし、決済中なし、約定済なし
    #  -> リストゼロ件で返却
    def test_orderlist_normal_1(self, client, shared_contract):
        # テスト用アカウント
        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        bond_exchange = shared_contract['IbetStraightBondExchange']
        token_list = shared_contract['TokenList']
        os.environ["IBET_SB_EXCHANGE_CONTRACT_ADDRESS"] = bond_exchange[
            'address']
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'order_list': [],
            'settlement_list': [],
            'complete_list': []
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2＞
    # 注文中あり（1件）、決済中なし、約定済なし
    #  -> order_listが1件返却
    def test_orderlist_normal_2(self, client, session, shared_contract):
        bond_exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']
        white_list = shared_contract['WhiteList']
        token_list = shared_contract['TokenList']

        os.environ["IBET_SB_EXCHANGE_CONTRACT_ADDRESS"] = bond_exchange[
            'address']
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        bond_token, order_id, agreement_id = TestV1OrderList.order_event(
            bond_exchange, personal_info, white_list, token_list)

        token_address = bond_token['address']

        print("-- token_address --")
        print(token_address)

        account = eth_account['issuer']
        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token': {
                'token_address':
                bond_token['address'],
                'token_template':
                'IbetStraightBond',
                'company_name':
                '',
                'name':
                'テスト債券',
                'symbol':
                'BOND',
                'totalSupply':
                1000000,
                'faceValue':
                10000,
                'interestRate':
                1000,
                'interestPaymentDate1':
                '0331',
                'interestPaymentDate2':
                '0930',
                'redemptionDate':
                '20191231',
                'redemptionAmount':
                10000,
                'returnDate':
                '20191231',
                'returnAmount':
                '商品券をプレゼント',
                'purpose':
                '新商品の開発資金として利用。',
                'image_url': [{
                    'type': 'small',
                    'url': ''
                }, {
                    'type': 'medium',
                    'url': ''
                }, {
                    'type': 'large',
                    'url': ''
                }],
                'certification': []
            },
            'order': {
                'order_id': order_id,
                'amount': 1000000,
                'price': 1000,
                'isBuy': False,
                'canceled': False
            }
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data']['order_list'] == assumed_body

    # ＜正常系3＞
    # 注文中なし、決済中あり（1件）、約定済なし
    #  -> settlement_listが1件返却
    def test_orderlist_normal_3(self, client, session, shared_contract):
        bond_exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']
        white_list = shared_contract['WhiteList']
        token_list = shared_contract['TokenList']

        os.environ["IBET_SB_EXCHANGE_CONTRACT_ADDRESS"] = bond_exchange[
            'address']
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        bond_token, order_id, agreement_id = TestV1OrderList.agreement_event(
            bond_exchange, personal_info, white_list, token_list)

        token_address = bond_token['address']

        print("-- token_address --")
        print(token_address)

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token': {
                'token_address':
                bond_token['address'],
                'token_template':
                'IbetStraightBond',
                'company_name':
                '',
                'name':
                'テスト債券',
                'symbol':
                'BOND',
                'totalSupply':
                1000000,
                'faceValue':
                10000,
                'interestRate':
                1000,
                'interestPaymentDate1':
                '0331',
                'interestPaymentDate2':
                '0930',
                'redemptionDate':
                '20191231',
                'redemptionAmount':
                10000,
                'returnDate':
                '20191231',
                'returnAmount':
                '商品券をプレゼント',
                'purpose':
                '新商品の開発資金として利用。',
                'image_url': [{
                    'type': 'small',
                    'url': ''
                }, {
                    'type': 'medium',
                    'url': ''
                }, {
                    'type': 'large',
                    'url': ''
                }],
                'certification': []
            },
            'agreement': {
                'order_id': order_id,
                'agreementId': agreement_id,
                'amount': 100,
                'price': 1000,
                'isBuy': True,
                'canceled': False
            }
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data']['settlement_list'] == assumed_body

    # ＜正常系4＞
    # 注文中なし、決済中なし、約定済あり（1件）
    #  -> complete_listが1件返却
    def test_orderlist_normal_4(self, client, session, shared_contract):
        bond_exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']
        white_list = shared_contract['WhiteList']
        token_list = shared_contract['TokenList']

        os.environ["IBET_SB_EXCHANGE_CONTRACT_ADDRESS"] = bond_exchange[
            'address']
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        bond_token, order_id, agreement_id = TestV1OrderList.settlement_event(
            bond_exchange, personal_info, white_list, token_list)

        token_address = bond_token['address']

        print("-- token_address --")
        print(token_address)

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token': {
                'token_address':
                bond_token['address'],
                'token_template':
                'IbetStraightBond',
                'company_name':
                '',
                'name':
                'テスト債券',
                'symbol':
                'BOND',
                'totalSupply':
                1000000,
                'faceValue':
                10000,
                'interestRate':
                1000,
                'interestPaymentDate1':
                '0331',
                'interestPaymentDate2':
                '0930',
                'redemptionDate':
                '20191231',
                'redemptionAmount':
                10000,
                'returnDate':
                '20191231',
                'returnAmount':
                '商品券をプレゼント',
                'purpose':
                '新商品の開発資金として利用。',
                'image_url': [{
                    'type': 'small',
                    'url': ''
                }, {
                    'type': 'medium',
                    'url': ''
                }, {
                    'type': 'large',
                    'url': ''
                }],
                'certification': []
            },
            'agreement': {
                'order_id': order_id,
                'agreementId': agreement_id,
                'amount': 100,
                'price': 1000,
                'isBuy': True
            }
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data']['complete_list'] == assumed_body

    # ＜エラー系1＞
    # request-bodyなし
    # -> 入力値エラー
    def test_orderlist_error_1(self, client):
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

    # ＜エラー系2＞
    # headersなし
    # -> 入力値エラー
    def test_orderlist_error_2(self, client):
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

    # ＜エラー系3-1＞
    # account_addressがアドレスフォーマットではない
    # -> 入力値エラー
    def test_orderlist_error_3_1(self, client):
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

    # ＜エラー系3-2＞
    # account_addressがstring以外
    # -> 入力エラー
    def test_orderlist_error_3_2(self, client):
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

    # ＜エラー系4＞
    # HTTPメソッドが不正
    def test_orderlist_error_4(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v1/OrderList'
        }
