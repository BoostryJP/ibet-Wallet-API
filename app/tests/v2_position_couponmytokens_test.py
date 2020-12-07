"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed onan "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

from app.model import Listing, Transfer
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
        #   2) 投資家に付与（10トークン）
        coupon_token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, coupon_token, token_list)
        transfer_coupon_token(issuer, coupon_token, trader['account_address'], 10)
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
        #   2) 投資家に付与（10トークン）
        #   3) クーポントークンを無効化
        coupon_token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, coupon_token, token_list)
        transfer_coupon_token(issuer, coupon_token, trader['account_address'], 10)
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
        """クーポントークンの保有0、売注文中0の状態（過去に保有）

        :param exchange: Exchangeコントラクト
        :param token_list: TokenListコントラクト
        :return:
        """
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
        latest_agreementid = coupon_get_latest_agreementid(exchange, latest_orderid)
        coupon_confirm_agreement(agent, exchange, latest_orderid, latest_agreementid)

        # ＜投資家オペレーション②＞
        #   1) Make売
        coupon_offer(trader, exchange, token, 100, 1001)

        # ＜発行体オペレーション②＞
        #   1) Take買
        latest_orderid = coupon_get_latest_orderid(exchange)
        coupon_take_buy(issuer, exchange, latest_orderid, 100)

        # ＜決済業者オペレーション②＞
        #   1）　決済
        latest_agreementid = coupon_get_latest_agreementid(exchange, latest_orderid)
        coupon_confirm_agreement(agent, exchange, latest_orderid, latest_agreementid)

        return token

    @staticmethod
    def insert_transfer_record(session, token_address, from_address, to_address):
        record = Transfer()
        record.token_address = token_address
        record.from_address = from_address
        record.to_address = to_address
        session.add(record)

    @staticmethod
    def list_token(session, token):
        listed_token = Listing()
        listed_token.token_address = token['address']
        listed_token.is_public = True
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
        session.add(listed_token)

    @staticmethod
    def list_private_token(session, token):
        listed_token = Listing()
        listed_token.token_address = token['address']
        listed_token.is_public = False
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
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
                'initial_offering_status': False,
                'status': True,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
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
                'initial_offering_status': False,
                'status': False,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
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
                'initial_offering_status': False,
                'status': True,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
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
                'initial_offering_status': False,
                'status': True,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
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

    # ＜正常系1-5＞
    # 複数保有
    #  公開トークンと未公開トークンの複数保有
    def test_coupon_position_normal_1_5(self, client, session, shared_contract):
        coupon_exchange = shared_contract['IbetCouponExchange']
        token_list = shared_contract['TokenList']

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        # クーポン①
        coupon_token_1 = TestV2CouponMyTokens.transfer_coupon(coupon_exchange, token_list)
        coupon_address_1 = coupon_token_1['address']

        # クーポン②
        coupon_token_2 = TestV2CouponMyTokens.transfer_coupon(coupon_exchange, token_list)
        coupon_address_2 = coupon_token_2['address']

        # 取扱トークンデータ挿入
        TestV2CouponMyTokens.list_token(session, coupon_token_1)
        TestV2CouponMyTokens.list_private_token(session, coupon_token_2)

        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = coupon_exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body_1 = {
            'token': {
                'token_address': coupon_address_1,
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
                'initial_offering_status': False,
                'status': True,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 10,
            'commitment': 0,
            'used': 0
        }

        assumed_body_2 = {
            'token': {
                'token_address': coupon_address_2,
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
                'initial_offering_status': False,
                'status': True,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
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
            if token['token']['token_address'] == coupon_address_1:
                count += 1
                assert token == assumed_body_1
            if token['token']['token_address'] == coupon_address_2:
                count += 1
                assert token == assumed_body_2
        assert count == 2

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
                'initial_offering_status': False,
                'status': True,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
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
                'initial_offering_status': False,
                'status': True,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
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
    # 残高なし、売注文中なし（過去の保有履歴あり）
    # 発行体：新規発行　→　発行体：募集（Make売）　→　投資家：Take買
    #   →　決済代行：決済①
    #       →　投資家：Make売　→　発行体：Take買
    #           →　決済代行：決済②
    def test_coupon_position_normal_2_3(self, client, session, shared_contract):
        exchange = shared_contract['IbetCouponExchange']
        token_list = shared_contract['TokenList']
        issuer = eth_account['issuer']
        account = eth_account['trader']

        # 残高ゼロの状態を再現
        token = TestV2CouponMyTokens.create_zero(exchange, token_list)
        token_address = token['address']

        # トークン移転履歴（保有履歴）の挿入
        self.insert_transfer_record(
            session=session,
            token_address=token['address'],
            from_address=issuer['account_address'],
            to_address=account['account_address']
        )

        # 取扱トークンデータ挿入
        TestV2CouponMyTokens.list_token(session, token)

        # 環境変数設定
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        # テスト対象API呼び出し
        resp = client.simulate_post(
            self.apiurl,
            headers=headers,
            body=request_body
        )

        # 結果検証
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
                'initial_offering_status': False,
                'status': True,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 0,
            'commitment': 0,
            'used': 0
        }
        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        for token in resp.json['data']:
            if token['token']['token_address'] == token_address:
                assert token == assumed_body

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
