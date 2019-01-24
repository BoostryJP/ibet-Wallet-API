# -*- coding: utf-8 -*-
import pytest
import json
import os

from app.model import Listing

from .account_config import eth_account
from .contract_modules import issue_bond_token, offer_bond_token, \
    register_personalinfo, register_whitelist, take_buy_bond_token, get_latest_orderid, \
    register_bond_list, get_latest_agreementid, bond_confirm_agreement

# [普通社債]保有トークン一覧API
# /v1/MyTokens/
class TestV1MyTokens():

    # テスト対象API
    apiurl = '/v1/MyTokens/'

    # 債券トークンの保有状態（約定イベント）を作成
    @staticmethod
    def generate_bond_position(bond_exchange, personal_info,
        white_list, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = {
            'name': 'テスト債券',
            'symbol': 'BOND',
            'totalSupply': 1000000,
            'tradableExchange': bond_exchange['address'],
            'faceValue': 10000,
            'interestRate': 1000,
            'interestPaymentDate1': '0101',
            'interestPaymentDate2': '0201',
            'interestPaymentDate3': '0301',
            'interestPaymentDate4': '0401',
            'interestPaymentDate5': '0501',
            'interestPaymentDate6': '0601',
            'interestPaymentDate7': '0701',
            'interestPaymentDate8': '0801',
            'interestPaymentDate9': '0901',
            'interestPaymentDate10': '1001',
            'interestPaymentDate11': '1101',
            'interestPaymentDate12': '1201',
            'redemptionDate': '20191231',
            'redemptionAmount': 10000,
            'returnDate': '20191231',
            'returnAmount': '商品券をプレゼント',
            'purpose': '新商品の開発資金として利用。',
            'memo': 'メモ'
        }

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
        latest_orderid = get_latest_orderid(bond_exchange)
        take_buy_bond_token(trader, bond_exchange, latest_orderid - 1, 100)

        # ＜決済業者オペレーション＞
        latest_agreementid = get_latest_agreementid(bond_exchange,
                                                    latest_orderid - 1)
        bond_confirm_agreement(agent, bond_exchange, latest_orderid - 1,
                               latest_agreementid - 1)

        return bond_token

    @staticmethod
    def list_token(session, token):
        listed_token = Listing()
        listed_token.token_address = token['address']
        listed_token.credit_card_availability = True
        listed_token.bank_payment_availability = True
        session.add(listed_token)

    # ＜正常系1＞
    # 債券トークン保有
    #  債券新規発行 -> 約定（1件）
    #   -> 該当債券の預かりが返却
    def test_position_normal_1(self, client, session, shared_contract):
        bond_exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']
        white_list = shared_contract['WhiteList']
        token_list = shared_contract['TokenList']

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        bond_token = TestV1MyTokens.generate_bond_position(
            bond_exchange, personal_info, white_list, token_list)
        token_address = bond_token['address']

        # 取扱トークンデータ挿入
        TestV1MyTokens.list_token(session, bond_token)

        os.environ["IBET_SB_EXCHANGE_CONTRACT_ADDRESS"] = bond_exchange['address']
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetStraightBond',
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト債券',
                'symbol': 'BOND',
                'totalSupply': 1000000,
                'faceValue': 10000,
                'interestRate': 1000,
                'interestPaymentDate1': '0101',
                'interestPaymentDate2': '0201',
                'interestPaymentDate3': '0301',
                'interestPaymentDate4': '0401',
                'interestPaymentDate5': '0501',
                'interestPaymentDate6': '0601',
                'interestPaymentDate7': '0701',
                'interestPaymentDate8': '0801',
                'interestPaymentDate9': '0901',
                'interestPaymentDate10': '1001',
                'interestPaymentDate11': '1101',
                'interestPaymentDate12': '1201',
                'redemptionDate': '20191231',
                'redemptionAmount': 10000,
                'returnDate': '20191231',
                'returnAmount': '商品券をプレゼント',
                'purpose': '新商品の開発資金として利用。',
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
            'balance': 100,
            'commitment': 0
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        count = 0
        for token in resp.json['data']:
            if token['token']['token_address'] == token_address:
                count = 1
                assert token == assumed_body
        assert count == 1

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
