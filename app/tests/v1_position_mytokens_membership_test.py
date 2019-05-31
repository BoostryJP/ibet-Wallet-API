# -*- coding: utf-8 -*-
import json
import os

from app.model import Listing

from .account_config import eth_account
from .contract_modules import membership_issue, membership_register_list, \
    membership_offer, membership_get_latest_orderid, \
    membership_take_buy, membership_get_latest_agreementid, \
    membership_confirm_agreement


# [会員権]保有トークン一覧API
# /v1/Membership/MyTokens/
class TestV1MembershipMyTokens:
    # テスト対象API
    apiurl = '/v1/Membership/MyTokens/'

    # 会員権トークンの保有状態を作成
    @staticmethod
    def create_balance(exchange, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = {
            'name': 'テスト会員権',
            'symbol': 'MEMBERSHIP',
            'initialSupply': 1000000,
            'tradableExchange': exchange['address'],
            'details': '詳細',
            'returnDetails': 'リターン詳細',
            'expirationDate': '20191231',
            'memo': 'メモ',
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
        }

        # ＜発行体オペレーション＞
        #   1) 会員権トークン発行
        #   2) 会員権トークンをトークンリストに登録
        #   3) 募集（Make売）
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)
        membership_offer(issuer, exchange, token, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) Take買
        latest_orderid = membership_get_latest_orderid(exchange)
        membership_take_buy(trader, exchange, latest_orderid, 100)

        # ＜決済業者オペレーション＞
        #   1）　決済
        latest_agreementid = \
            membership_get_latest_agreementid(exchange, latest_orderid)
        membership_confirm_agreement(
            agent, exchange, latest_orderid, latest_agreementid)

        return token

    # 会員権トークンの売注文中状態を作成
    @staticmethod
    def create_commitment(exchange, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = {
            'name': 'テスト会員権',
            'symbol': 'MEMBERSHIP',
            'initialSupply': 1000000,
            'tradableExchange': exchange['address'],
            'details': '詳細',
            'returnDetails': 'リターン詳細',
            'expirationDate': '20191231',
            'memo': 'メモ',
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
        }

        # ＜発行体オペレーション＞
        #   1) 会員権トークン発行
        #   2) 会員権トークンをトークンリストに登録
        #   3) 募集（Make売）
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)
        membership_offer(issuer, exchange, token, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) Take買
        latest_orderid = membership_get_latest_orderid(exchange)
        membership_take_buy(trader, exchange, latest_orderid, 100)

        # ＜決済業者オペレーション＞
        #   1）　決済
        latest_agreementid = \
            membership_get_latest_agreementid(exchange, latest_orderid)
        membership_confirm_agreement(
            agent, exchange, latest_orderid, latest_agreementid)

        # ＜投資家オペレーション＞
        #   1) Make売
        membership_offer(trader, exchange, token, 50, 1001)

        return token

    # 会員権トークンの保有0、売注文中0の状態を作成
    @staticmethod
    def create_zero(exchange, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = {
            'name': 'テスト会員権',
            'symbol': 'MEMBERSHIP',
            'initialSupply': 1000000,
            'tradableExchange': exchange['address'],
            'details': '詳細',
            'returnDetails': 'リターン詳細',
            'expirationDate': '20191231',
            'memo': 'メモ',
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
        }

        # ＜発行体オペレーション①＞
        #   1) 会員権トークン発行
        #   2) 会員権トークンをトークンリストに登録
        #   3) 募集（Make売）
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)
        membership_offer(issuer, exchange, token, 1000000, 1000)

        # ＜投資家オペレーション①＞
        #   1) Take買
        latest_orderid = membership_get_latest_orderid(exchange)
        membership_take_buy(trader, exchange, latest_orderid, 100)

        # ＜決済業者オペレーション①＞
        #   1）　決済
        latest_agreementid = \
            membership_get_latest_agreementid(exchange, latest_orderid)
        membership_confirm_agreement(
            agent, exchange, latest_orderid, latest_agreementid)

        # ＜投資家オペレーション②＞
        #   1) Make売
        membership_offer(trader, exchange, token, 100, 1001)

        # ＜発行体オペレーション②＞
        #   1) Take買
        latest_orderid = membership_get_latest_orderid(exchange)
        membership_take_buy(issuer, exchange, latest_orderid, 100)

        # ＜決済業者オペレーション②＞
        #   1）　決済
        latest_agreementid = \
            membership_get_latest_agreementid(exchange, latest_orderid)
        membership_confirm_agreement(
            agent, exchange, latest_orderid, latest_agreementid)

        return token

    @staticmethod
    def list_token(session, token):
        listed_token = Listing()
        listed_token.token_address = token['address']
        listed_token.payment_method_credit_card = True
        listed_token.payment_method_bank = True
        session.add(listed_token)

    # 正常系1
    # 残高あり、売注文中なし
    # 発行体：新規発行　→　発行体：募集（Make売）　→　投資家：Take買 →　決済業者：決済
    def test_membership_position_normal_1(self, client, session, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token_list = shared_contract['TokenList']
        account = eth_account['trader']

        token = TestV1MembershipMyTokens.create_balance(exchange, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV1MembershipMyTokens.list_token(session, token)

        os.environ["IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS"] = \
            exchange['address']
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetMembership',
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト会員権',
                'symbol': 'MEMBERSHIP',
                'total_supply': 1000000,
                'details': '詳細',
                'return_details': 'リターン詳細',
                'expiration_date': '20191231',
                'memo': 'メモ',
                'transferable': True,
                'status': True,
                'image_url': [{
                    'id': 1,
                    'url': ''
                }, {
                    'id': 2,
                    'url': ''
                }, {
                    'id': 3,
                    'url': ''
                }],
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
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

    # 正常系2
    # 残高あり、売注文中あり
    # 発行体：新規発行　→　発行体：募集（Make売）　→　投資家：Take買
    #   →　決済代行：決済　→　投資家：Make売
    def test_membership_position_normal_2(self, client, session, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token_list = shared_contract['TokenList']
        account = eth_account['trader']

        token = TestV1MembershipMyTokens.create_commitment(exchange, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV1MembershipMyTokens.list_token(session, token)

        os.environ["IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS"] = \
            exchange['address']
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetMembership',
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト会員権',
                'symbol': 'MEMBERSHIP',
                'total_supply': 1000000,
                'details': '詳細',
                'return_details': 'リターン詳細',
                'expiration_date': '20191231',
                'memo': 'メモ',
                'transferable': True,
                'status': True,
                'image_url': [{
                    'id': 1,
                    'url': ''
                }, {
                    'id': 2,
                    'url': ''
                }, {
                    'id': 3,
                    'url': ''
                }],
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 50,
            'commitment': 50
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        count = 0
        for token in resp.json['data']:
            if token['token']['token_address'] == token_address:
                count = 1
                assert token == assumed_body
        assert count == 1

    # 正常系3
    # 残高なし、売注文中なし
    # 発行体：新規発行　→　発行体：募集（Make売）　→　投資家：Take買
    #   →　決済代行：決済①
    #       →　投資家：Make売　→　発行体：Take買
    #           →　決済代行：決済②
    def test_membership_position_normal_3(self, client, session, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token_list = shared_contract['TokenList']
        account = eth_account['trader']

        token = TestV1MembershipMyTokens.create_zero(exchange, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV1MembershipMyTokens.list_token(session, token)

        os.environ["IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS"] = \
            exchange['address']
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        # リストが返却されないことを確認
        count = 0
        for token in resp.json['data']:
            if token['token']['token_address'] == token_address:
                count = 1
        assert count == 0

    # エラー系1
    # 入力値エラー（request-bodyなし）
    def test_membership_position_error_1(self, client):
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

    # エラー系2
    # 入力値エラー（headersなし）
    def test_membership_position_error_2(self, client):
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

    # エラー系3-1
    # 入力値エラー（account_addressがアドレスフォーマットではない）
    def test_membership_position_error_3_1(self, client):
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  # アドレスが短い
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

    # エラー系3-2
    # 入力値エラー（account_addressがstring以外）
    def test_membership_position_error_3_2(self, client):
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
