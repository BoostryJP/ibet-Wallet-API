# -*- coding: utf-8 -*-
from app.model import Listing, PrivateListing
from .contract_modules import *


class TestV2CouponMyTokens:
    """
    Test Case for v2.position.CouponMyTokens
    """
    
    # テスト対象API
    apiurl = '/v2/Position/Coupon'

    # クーポントークンの保有状態を作成（譲渡イベント）
    @staticmethod
    def transfer_coupon(coupon_exchange, token_list):
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
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
        }

        # ＜発行体オペレーション＞
        #   1) クーポントークン発行
        #   2) Exchangeにデポジット（10トークン）
        #   3) 投資家に付与（10トークン）
        coupon_token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, coupon_token, token_list)
        deposit_coupon_token(issuer, coupon_token, coupon_exchange, 10)
        transfer_coupon_token(issuer, coupon_token, coupon_exchange, trader['account_address'], 10)
        return coupon_token

    # 無効化クーポントークンの保有状態を作成（譲渡イベント）
    @staticmethod
    def transfer_coupon_invalid(coupon_exchange, token_list):
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
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
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

    # クーポントークンの保有状態を作成（買約定イベント）
    @staticmethod
    def create_balance(exchange, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 1000000,
            'tradableExchange': exchange['address'],
            'details': 'クーポン詳細',
            'returnDetails': 'リターン詳細',
            'memo': 'クーポンメモ欄',
            'expirationDate': '20191231',
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
        }

        # ＜発行体オペレーション＞
        #   1) トークン発行
        #   2) トークンをトークンリストに登録
        #   3) 募集（Make売）
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)
        coupon_offer(issuer, exchange, token, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) Take買
        latest_orderid = coupon_get_latest_orderid(exchange)
        coupon_take_buy(trader, exchange, latest_orderid, 100)

        # ＜決済業者オペレーション＞
        #   1）　決済
        latest_agreementid = \
            coupon_get_latest_agreementid(exchange, latest_orderid)
        coupon_confirm_agreement(
            agent, exchange, latest_orderid, latest_agreementid)

        return token

    # クーポントークンの売注文中状態を作成
    @staticmethod
    def create_commitment(exchange, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 1000000,
            'tradableExchange': exchange['address'],
            'details': 'クーポン詳細',
            'returnDetails': 'リターン詳細',
            'memo': 'クーポンメモ欄',
            'expirationDate': '20191231',
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
        }

        # ＜発行体オペレーション＞
        #   1) トークン発行
        #   2) トークンをトークンリストに登録
        #   3) 募集（Make売）
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)
        coupon_offer(issuer, exchange, token, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) Take買
        latest_orderid = coupon_get_latest_orderid(exchange)
        coupon_take_buy(trader, exchange, latest_orderid, 100)

        # ＜決済業者オペレーション＞
        #   1）　決済
        latest_agreementid = \
            coupon_get_latest_agreementid(exchange, latest_orderid)
        coupon_confirm_agreement(
            agent, exchange, latest_orderid, latest_agreementid)

        # ＜投資家オペレーション＞
        #   1) Make売
        coupon_offer(trader, exchange, token, 50, 1001)

        return token

    # クーポントークンの保有0、売注文中0の状態を作成（過去の保有状態）
    @staticmethod
    def create_zero(exchange, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 1000000,
            'tradableExchange': exchange['address'],
            'details': 'クーポン詳細',
            'returnDetails': 'リターン詳細',
            'memo': 'クーポンメモ欄',
            'expirationDate': '20191231',
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
        }

        # ＜発行体オペレーション①＞
        #   1) トークン発行
        #   2) トークンをトークンリストに登録
        #   3) 募集（Make売）
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)
        coupon_offer(issuer, exchange, token, 1000000, 1000)

        # ＜投資家オペレーション①＞
        #   1) Take買
        latest_orderid = coupon_get_latest_orderid(exchange)
        coupon_take_buy(trader, exchange, latest_orderid, 100)

        # ＜決済業者オペレーション①＞
        #   1）　決済
        latest_agreementid = \
            coupon_get_latest_agreementid(exchange, latest_orderid)
        coupon_confirm_agreement(
            agent, exchange, latest_orderid, latest_agreementid)

        # ＜投資家オペレーション②＞
        #   1) Make売
        coupon_offer(trader, exchange, token, 100, 1001)

        # ＜発行体オペレーション②＞
        #   1) Take買
        latest_orderid = coupon_get_latest_orderid(exchange)
        coupon_take_buy(issuer, exchange, latest_orderid, 100)

        # ＜決済業者オペレーション②＞
        #   1）　決済
        latest_agreementid = \
            coupon_get_latest_agreementid(exchange, latest_orderid)
        coupon_confirm_agreement(
            agent, exchange, latest_orderid, latest_agreementid)

        return token

    @staticmethod
    def list_token(session, token):
        listed_token = Listing()
        listed_token.token_address = token['address']
        listed_token.payment_method_credit_card = True
        listed_token.payment_method_bank = True
        session.add(listed_token)

    @staticmethod
    def list_private_token(session, token):
        listed_token = PrivateListing()
        listed_token.token_address = token['address']
        listed_token.payment_method_credit_card = True
        listed_token.payment_method_bank = True
        session.add(listed_token)

    # ＜正常系1-1＞
    # クーポントークン保有
    #  クーポン新規発行 -> 投資家割当
    #   -> 該当クーポンの保有情報が返却
    def test_coupon_position_normal_1_1(self, client, session, shared_contract):
        coupon_exchange = shared_contract['IbetCouponExchange']
        token_list = shared_contract['TokenList']

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        coupon_token = TestV2CouponMyTokens. \
            transfer_coupon(coupon_exchange, token_list)
        coupon_address = coupon_token['address']

        # 取扱トークンデータ挿入
        TestV2CouponMyTokens.list_token(session, coupon_token)

        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = coupon_exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': coupon_address,
                'token_template': 'IbetCoupon',
                'owner_address': eth_account['issuer']['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'total_supply': 10000,
                'details': 'クーポン詳細',
                'return_details': 'リターン詳細',
                'memo': 'クーポンメモ欄',
                'expiration_date': '20191231',
                'transferable': True,
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
                'status': True,
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 10,
            'commitment': 0,
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
    #   -> 該当クーポンの保有情報が返却される（status:False）
    def test_coupon_position_normal_1_2(self, client, session, shared_contract):
        coupon_exchange = shared_contract['IbetCouponExchange']
        token_list = shared_contract['TokenList']

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        coupon_token = TestV2CouponMyTokens. \
            transfer_coupon_invalid(coupon_exchange, token_list)
        coupon_address = coupon_token['address']

        # 取扱トークンデータ挿入
        TestV2CouponMyTokens.list_token(session, coupon_token)

        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = coupon_exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': coupon_address,
                'token_template': 'IbetCoupon',
                'owner_address': eth_account['issuer']['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'total_supply': 10000,
                'details': 'クーポン詳細',
                'return_details': 'リターン詳細',
                'memo': 'クーポンメモ欄',
                'expiration_date': '20191231',
                'transferable': True,
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
                'status': False,
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 10,
            'commitment': 0,
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

    # ＜正常系1-3＞
    # クーポントークン保有
    #  未公開トークンリストの場合
    def test_coupon_position_normal_1_3(self, client, session, shared_contract):
        coupon_exchange = shared_contract['IbetCouponExchange']
        token_list = shared_contract['TokenList']

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        coupon_token = TestV2CouponMyTokens. \
            transfer_coupon(coupon_exchange, token_list)
        coupon_address = coupon_token['address']

        # 取扱トークンデータ挿入
        TestV2CouponMyTokens.list_private_token(session, coupon_token)

        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = coupon_exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': coupon_address,
                'token_template': 'IbetCoupon',
                'owner_address': eth_account['issuer']['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'total_supply': 10000,
                'details': 'クーポン詳細',
                'return_details': 'リターン詳細',
                'memo': 'クーポンメモ欄',
                'expiration_date': '20191231',
                'transferable': True,
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
                'status': True,
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 10,
            'commitment': 0,
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

    # ＜正常系1-4＞
    # クーポントークン保有
    #  特殊系：公開トークンと未公開トークンが重複
    def test_coupon_position_normal_1_4(self, client, session, shared_contract):
        coupon_exchange = shared_contract['IbetCouponExchange']
        token_list = shared_contract['TokenList']

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        coupon_token = TestV2CouponMyTokens. \
            transfer_coupon(coupon_exchange, token_list)
        coupon_address = coupon_token['address']

        # 取扱トークンデータ挿入
        TestV2CouponMyTokens.list_token(session, coupon_token)
        TestV2CouponMyTokens.list_private_token(session, coupon_token)

        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = coupon_exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': coupon_address,
                'token_template': 'IbetCoupon',
                'owner_address': eth_account['issuer']['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'total_supply': 10000,
                'details': 'クーポン詳細',
                'return_details': 'リターン詳細',
                'memo': 'クーポンメモ欄',
                'expiration_date': '20191231',
                'transferable': True,
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
                'status': True,
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 10,
            'commitment': 0,
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

    # ＜正常系2-1＞
    # 残高あり、売注文中なし
    # 発行体：新規発行　→　発行体：募集（Make売）　→　投資家：Take買 →　決済業者：決済
    def test_coupon_position_normal_2_1(self, client, session, shared_contract):
        exchange = shared_contract['IbetCouponExchange']
        token_list = shared_contract['TokenList']
        account = eth_account['trader']

        token = TestV2CouponMyTokens.create_balance(exchange, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV2CouponMyTokens.list_token(session, token)

        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetCoupon',
                'owner_address': eth_account['issuer']['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'total_supply': 1000000,
                'details': 'クーポン詳細',
                'return_details': 'リターン詳細',
                'memo': 'クーポンメモ欄',
                'expiration_date': '20191231',
                'transferable': True,
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
                'status': True,
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 100,
            'commitment': 0,
            'used': 0
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        for token in resp.json['data']:
            if token['token']['token_address'] == token_address:
                assert token == assumed_body

    # ＜正常系2-2＞
    # 残高あり、売注文中あり
    # 発行体：新規発行　→　発行体：募集（Make売）　→　投資家：Take買
    #   →　決済代行：決済　→　投資家：Make売
    def test_coupon_position_normal_2_2(self, client, session, shared_contract):
        exchange = shared_contract['IbetCouponExchange']
        token_list = shared_contract['TokenList']
        account = eth_account['trader']

        token = TestV2CouponMyTokens.create_commitment(exchange, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV2CouponMyTokens.list_token(session, token)

        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetCoupon',
                'owner_address': eth_account['issuer']['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'total_supply': 1000000,
                'details': 'クーポン詳細',
                'return_details': 'リターン詳細',
                'memo': 'クーポンメモ欄',
                'expiration_date': '20191231',
                'transferable': True,
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
                'status': True,
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 50,
            'commitment': 50,
            'used': 0
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        for token in resp.json['data']:
            if token['token']['token_address'] == token_address:
                assert token == assumed_body

    # ＜正常系2-3＞
    # 残高なし、売注文中なし
    # 発行体：新規発行　→　発行体：募集（Make売）　→　投資家：Take買
    #   →　決済代行：決済①
    #       →　投資家：Make売　→　発行体：Take買
    #           →　決済代行：決済②
    def test_coupon_position_normal_2_3(self, client, session, shared_contract):
        exchange = shared_contract['IbetCouponExchange']
        token_list = shared_contract['TokenList']
        account = eth_account['trader']

        token = TestV2CouponMyTokens.create_zero(exchange, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV2CouponMyTokens.list_token(session, token)

        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        # リスト0件の確認
        count = 0
        for token in resp.json['data']:
            if token['token']['token_address'] == token_address:
                count = 1
        assert count == 0

    # エラー系1：入力値エラー（request-bodyなし）
    def test_coupon_position_error_1(self, client):
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
    def test_coupon_position_error_2(self, client):
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
    def test_coupon_position_error_3_1(self, client):
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

    # エラー系3-2：入力値エラー（account_addressがstring以外）
    def test_coupon_position_error_3_2(self, client):
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
