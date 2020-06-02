# -*- coding: utf-8 -*-
import json

from app import config
from app.model import Listing, PrivateListing
from .account_config import eth_account
from .contract_modules import issue_share_token, register_share_list, \
    share_get_latest_orderid, share_offer, share_take_buy, share_confirm_agreement, \
    register_personalinfo, share_get_latest_agreementid


class TestV2ShareMyTokens:
    """
    Test Case for v2.position.ShareMyTokens
    """

    # テスト対象API
    apiurl = '/v2/Position/Share'

    # 株式トークンの保有状態を作成
    @staticmethod
    def create_balance(exchange, personal_info, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = {
            'name': 'テスト株式',
            'symbol': 'SHARE',
            'tradableExchange': exchange['address'],
            'personalInfoAddress': personal_info['address'],
            'issuePrice': 1000,
            'totalSupply': 1000000,
            'dividends': 100,
            'dividendRecordDate': '20200401',
            'dividendPaymentDate': '20200502',
            'cancellationDate': '20200603',
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー',
            'memo': 'メモ',
            'transferable': True
        }

        # ＜発行体オペレーション＞
        #   1) 株式トークン発行
        #   2) 株式トークンをトークンリストに登録
        #   3) 投資家名簿用個人情報コントラクト（PersonalInfo）に発行体の情報を登録
        #   4) 募集（Make売）
        token = issue_share_token(issuer, attribute)
        register_share_list(issuer, token, token_list)
        register_personalinfo(issuer, personal_info)
        share_offer(issuer, exchange, token, trader, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) 投資家名簿用個人情報コントラクト（PersonalInfo）に投資家の情報を登録
        #   2) Take買
        register_personalinfo(trader, personal_info)
        latest_orderid = share_get_latest_orderid(exchange)
        share_take_buy(trader, exchange, latest_orderid)

        # ＜決済業者オペレーション＞
        #   1）　決済
        latest_agreementid = \
            share_get_latest_agreementid(exchange, latest_orderid)
        share_confirm_agreement(
            agent, exchange, latest_orderid, latest_agreementid)

        return token

    # 株式トークンの売注文中状態を作成
    @staticmethod
    def create_commitment(exchange, personal_info, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = {
            'name': 'テスト株式',
            'symbol': 'SHARE',
            'tradableExchange': exchange['address'],
            'personalInfoAddress': personal_info['address'],
            'issuePrice': 1000,
            'totalSupply': 1000000,
            'dividends': 100,
            'dividendRecordDate': '20200401',
            'dividendPaymentDate': '20200502',
            'cancellationDate': '20200603',
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー',
            'memo': 'メモ',
            'transferable': True
        }

        # ＜発行体オペレーション＞
        #   1) 会員権トークン発行
        #   2) 会員権トークンをトークンリストに登録
        #   3) 投資家名簿用個人情報コントラクト（PersonalInfo）に発行体の情報を登録
        #   4) 募集（Make売）
        register_personalinfo(issuer, personal_info)
        token = issue_share_token(issuer, attribute)
        register_share_list(issuer, token, token_list)
        register_personalinfo(issuer, personal_info)
        share_offer(issuer, exchange, token, trader, 100, 1000)

        # ＜投資家オペレーション＞
        #   1) 投資家名簿用個人情報コントラクト（PersonalInfo）に投資家の情報を登録
        #   2) Take買
        register_personalinfo(trader, personal_info)
        latest_orderid = share_get_latest_orderid(exchange)
        share_take_buy(trader, exchange, latest_orderid)

        # ＜決済業者オペレーション＞
        #   1）　決済
        latest_agreementid = share_get_latest_agreementid(exchange, latest_orderid)
        share_confirm_agreement(agent, exchange, latest_orderid, latest_agreementid)

        # ＜投資家オペレーション＞
        #   1) Make売
        share_offer(trader, exchange, token, issuer, 50, 1001)

        return token

    # 会員権トークンの保有0、売注文中0の状態を作成
    @staticmethod
    def create_zero(exchange, personal_info, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = {
            'name': 'テスト株式',
            'symbol': 'SHARE',
            'tradableExchange': exchange['address'],
            'personalInfoAddress': personal_info['address'],
            'issuePrice': 1000,
            'totalSupply': 1000000,
            'dividends': 100,
            'dividendRecordDate': '20200401',
            'dividendPaymentDate': '20200502',
            'cancellationDate': '20200603',
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー',
            'memo': 'メモ',
            'transferable': True
        }

        # ＜発行体オペレーション①＞
        #   1) 会員権トークン発行
        #   2) 会員権トークンをトークンリストに登録
        #   3) 投資家名簿用個人情報コントラクト（PersonalInfo）に発行体の情報を登録
        #   4) 募集（Make売）
        token = issue_share_token(issuer, attribute)
        register_share_list(issuer, token, token_list)
        register_personalinfo(issuer, personal_info)
        share_offer(issuer, exchange, token, trader, 1000000, 1000)

        # ＜投資家オペレーション①＞
        #   1) 投資家名簿用個人情報コントラクト（PersonalInfo）に投資家の情報を登録
        #   2) Take買
        latest_orderid = share_get_latest_orderid(exchange)
        share_take_buy(trader, exchange, latest_orderid)

        # ＜決済業者オペレーション①＞
        #   1）　決済
        latest_agreementid = \
            share_get_latest_agreementid(exchange, latest_orderid)
        share_confirm_agreement(
            agent, exchange, latest_orderid, latest_agreementid)

        # ＜投資家オペレーション②＞
        #   1) Make売
        share_offer(trader, exchange, token, issuer, 1000000, 1001)

        # ＜発行体オペレーション②＞
        #   1) Take買
        latest_orderid = share_get_latest_orderid(exchange)
        share_take_buy(issuer, exchange, latest_orderid)

        # ＜決済業者オペレーション②＞
        #   1）　決済
        latest_agreementid = \
            share_get_latest_agreementid(exchange, latest_orderid)
        share_confirm_agreement(
            agent, exchange, latest_orderid, latest_agreementid)

        return token

    @staticmethod
    def list_token(session, token):
        listed_token = Listing()
        listed_token.id = 1
        listed_token.token_address = token['address']
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
        listed_token.payment_method_credit_card = True
        listed_token.payment_method_bank = True
        session.add(listed_token)

    @staticmethod
    def list_private_token(session, token):
        listed_token = PrivateListing()
        listed_token.id = 1
        listed_token.token_address = token['address']
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
        listed_token.payment_method_credit_card = True
        listed_token.payment_method_bank = True
        session.add(listed_token)

    # 正常系1
    # 残高あり、売注文中なし
    # 発行体：新規発行　→　発行体：募集（Make売）　→　投資家：Take買 →　決済業者：決済
    def test_share_position_normal_1(self, client, session, shared_contract):
        exchange = shared_contract['IbetOTCExchange']
        token_list = shared_contract['TokenList']
        personal_info = shared_contract['PersonalInfo']
        account = eth_account['trader']

        token = TestV2ShareMyTokens.create_balance(exchange, personal_info, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV2ShareMyTokens.list_token(session, token)

        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetShare',
                'owner_address': eth_account['issuer']['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト株式',
                'symbol': 'SHARE',
                'total_supply': 1000000,
                'issue_price': 1000,
                'dividend_information': {
                    'dividends': 100,
                    'dividendRecordDate': '20200401',
                    'dividendPaymentDate': '20200502'
                },
                'cancellation_date': '20200603',
                'memo': 'メモ',
                'transferable': True,
                'offering_status': False,
                'status': True,
                'reference_urls': [{
                    'id': 1,
                    'url': ''
                }, {
                    'id': 2,
                    'url': ''
                }, {
                    'id': 3,
                    'url': ''
                }],
                'image_url': [],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 1000000,
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
    def test_share_position_normal_2(self, client, session, shared_contract):
        exchange = shared_contract['IbetOTCExchange']
        token_list = shared_contract['TokenList']
        personal_info = shared_contract['PersonalInfo']
        account = eth_account['trader']

        token = TestV2ShareMyTokens.create_commitment(exchange, personal_info, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV2ShareMyTokens.list_token(session, token)

        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetShare',
                'owner_address': eth_account['issuer']['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト株式',
                'symbol': 'SHARE',
                'total_supply': 1000000,
                'issue_price': 1000,
                'dividend_information': {
                    'dividends': 100,
                    'dividendRecordDate': '20200401',
                    'dividendPaymentDate': '20200502'
                },
                'cancellation_date': '20200603',
                'memo': 'メモ',
                'transferable': True,
                'offering_status': False,
                'status': True,
                'reference_urls': [{
                    'id': 1,
                    'url': ''
                }, {
                    'id': 2,
                    'url': ''
                }, {
                    'id': 3,
                    'url': ''
                }],
                'image_url': [],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
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
    def test_share_position_normal_3(self, client, session, shared_contract):
        exchange = shared_contract['IbetOTCExchange']
        token_list = shared_contract['TokenList']
        personal_info = shared_contract['PersonalInfo']
        account = eth_account['trader']

        token = TestV2ShareMyTokens.create_zero(exchange, personal_info, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV2ShareMyTokens.list_token(session, token)

        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

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

    # 正常系4
    # 残高あり
    #   未公開トークンリストの場合
    def test_share_position_normal_4(self, client, session, shared_contract):
        exchange = shared_contract['IbetOTCExchange']
        token_list = shared_contract['TokenList']
        personal_info = shared_contract['PersonalInfo']
        account = eth_account['trader']

        token = TestV2ShareMyTokens.create_balance(exchange, personal_info, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV2ShareMyTokens.list_private_token(session, token)

        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetShare',
                'owner_address': eth_account['issuer']['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト株式',
                'symbol': 'SHARE',
                'total_supply': 1000000,
                'issue_price': 1000,
                'dividend_information': {
                    'dividends': 100,
                    'dividendRecordDate': '20200401',
                    'dividendPaymentDate': '20200502'
                },
                'cancellation_date': '20200603',
                'memo': 'メモ',
                'transferable': True,
                'offering_status': False,
                'status': True,
                'reference_urls': [{
                    'id': 1,
                    'url': ''
                }, {
                    'id': 2,
                    'url': ''
                }, {
                    'id': 3,
                    'url': ''
                }],
                'image_url': [],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 1000000,
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

    # 正常系5
    # 残高あり
    #   特殊系：公開トークンと未公開トークンが重複
    def test_share_position_normal_5(self, client, session, shared_contract):
        exchange = shared_contract['IbetOTCExchange']
        token_list = shared_contract['TokenList']
        personal_info = shared_contract['PersonalInfo']
        account = eth_account['trader']

        token = TestV2ShareMyTokens.create_balance(exchange, personal_info, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV2ShareMyTokens.list_token(session, token)
        TestV2ShareMyTokens.list_private_token(session, token)

        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetShare',
                'owner_address': eth_account['issuer']['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト株式',
                'symbol': 'SHARE',
                'total_supply': 1000000,
                'issue_price': 1000,
                'dividend_information': {
                    'dividends': 100,
                    'dividendRecordDate': '20200401',
                    'dividendPaymentDate': '20200502'
                },
                'cancellation_date': '20200603',
                'memo': 'メモ',
                'transferable': True,
                'offering_status': False,
                'status': True,
                'reference_urls': [{
                    'id': 1,
                    'url': ''
                }, {
                    'id': 2,
                    'url': ''
                }, {
                    'id': 3,
                    'url': ''
                }],
                'image_url': [],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 1000000,
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

    # 正常系6
    # 複数保有
    #  公開トークンと未公開トークンの複数保有
    def test_share_position_normal_6(self, client, session, shared_contract):
        exchange = shared_contract['IbetOTCExchange']
        token_list = shared_contract['TokenList']
        personal_info = shared_contract['PersonalInfo']
        account = eth_account['trader']

        # 会員権①
        token_1 = TestV2ShareMyTokens.create_balance(exchange, personal_info, token_list)
        token_address_1 = token_1['address']

        # 会員権②
        token_2 = TestV2ShareMyTokens.create_balance(exchange, personal_info, token_list)
        token_address_2 = token_2['address']

        # 取扱トークンデータ挿入
        TestV2ShareMyTokens.list_token(session, token_1)
        TestV2ShareMyTokens.list_private_token(session, token_2)

        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body_1 = {
            'token': {
                'token_address': token_address_1,
                'token_template': 'IbetShare',
                'owner_address': eth_account['issuer']['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト株式',
                'symbol': 'SHARE',
                'total_supply': 1000000,
                'issue_price': 1000,
                'dividend_information': {
                    'dividends': 100,
                    'dividendRecordDate': '20200401',
                    'dividendPaymentDate': '20200502'
                },
                'cancellation_date': '20200603',
                'memo': 'メモ',
                'transferable': True,
                'offering_status': False,
                'status': True,
                'reference_urls': [{
                    'id': 1,
                    'url': ''
                }, {
                    'id': 2,
                    'url': ''
                }, {
                    'id': 3,
                    'url': ''
                }],
                'image_url': [],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },

            'balance': 1000000,
            'commitment': 0
        }

        assumed_body_2 = {
            'token': {
                'token_address': token_address_2,
                'token_template': 'IbetShare',
                'owner_address': eth_account['issuer']['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト株式',
                'symbol': 'SHARE',
                'total_supply': 1000000,
                'issue_price': 1000,
                'dividend_information': {
                    'dividends': 100,
                    'dividendRecordDate': '20200401',
                    'dividendPaymentDate': '20200502'
                },
                'cancellation_date': '20200603',
                'memo': 'メモ',
                'transferable': True,
                'offering_status': False,
                'status': True,
                'reference_urls': [{
                    'id': 1,
                    'url': ''
                }, {
                    'id': 2,
                    'url': ''
                }, {
                    'id': 3,
                    'url': ''
                }],
                'image_url': [],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 1000000,
            'commitment': 0
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        count = 0
        for token in resp.json['data']:
            if token['token']['token_address'] == token_address_1:
                count += 1
                assert token == assumed_body_1
            if token['token']['token_address'] == token_address_2:
                count += 1
                assert token == assumed_body_2

        assert count == 2

    # エラー系1
    # 入力値エラー（request-bodyなし）
    def test_share_position_error_1(self, client):
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
    def test_share_position_error_2(self, client):
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
    def test_share_position_error_3_1(self, client):
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
    def test_share_position_error_3_2(self, client):
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
