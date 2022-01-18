"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""
import json
import sys

from eth_utils import to_checksum_address
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.model.db import Listing
from app import config
from app.contracts import Contract

from tests.account_config import eth_account
from tests.contract_modules import (
    issue_coupon_token,
    coupon_register_list,
    invalidate_coupon_token
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestV2TokenCouponTokens:
    """
    Test Case for v2.token.CouponTokens
    """

    # テスト対象API
    apiurl = '/v2/Token/Coupon'

    @staticmethod
    def token_attribute(exchange_address):
        attribute = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 10000,
            'tradableExchange': exchange_address,
            'details': 'クーポン詳細',
            'returnDetails': 'リターン詳細',
            'memo': 'クーポンメモ欄',
            'expirationDate': '20191231',
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
        }
        return attribute

    @staticmethod
    def tokenlist_contract():
        deployer = eth_account['deployer']
        web3.eth.defaultAccount = deployer['account_address']
        contract_address, abi = Contract.deploy_contract('TokenList', [], deployer['account_address'])
        return {'address': contract_address, 'abi': abi}

    @staticmethod
    def list_token(session, token):
        listed_token = Listing()
        listed_token.token_address = token['address']
        listed_token.is_public = True
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
        session.add(listed_token)

    # ＜正常系1＞
    # 発行済クーポンあり（1件）
    # cursor=設定なし、 limit=設定なし
    # -> 1件返却
    def test_couponlist_normal_1(self, client, session, shared_contract):
        config.COUPON_TOKEN_ENABLED = True
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenCouponTokens.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：新規発行
        exchange_address = to_checksum_address(shared_contract['IbetCouponExchange']['address'])
        attribute = TestV2TokenCouponTokens.token_attribute(exchange_address)
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # 取扱トークンデータ挿入
        TestV2TokenCouponTokens.list_token(session, token)

        query_string = ''
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [
            {
                'id': 0,
                'token_address': token['address'],
                'token_template': 'IbetCoupon',
                'owner_address': issuer['account_address'],
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
                'status': True,
                'initial_offering_status': False,
                'image_url': [
                    {'id': 1, 'url': ''},
                    {'id': 2, 'url': ''},
                    {'id': 3, 'url': ''}
                ],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'tradable_exchange': exchange_address,
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2＞
    # 発行済クーポンあり（2件）
    # cursor=設定なし、 limit=設定なし
    # -> 登録が新しい順にリストが返却
    def test_couponlist_normal_2(self, client, session, shared_contract):
        config.COUPON_TOKEN_ENABLED = True
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenCouponTokens.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：新規発行
        issued_list = []
        exchange_address = to_checksum_address(shared_contract['IbetCouponExchange']['address'])
        for i in range(0, 2):
            attribute = TestV2TokenCouponTokens.token_attribute(exchange_address)
            token = issue_coupon_token(issuer, attribute)
            coupon_register_list(issuer, token, token_list)
            issued_list.append(token)
            # 取扱トークンデータ挿入
            TestV2TokenCouponTokens.list_token(session, token)

        query_string = ''
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [
            {
                'id': 1,
                'token_address': issued_list[1]['address'],
                'token_template': 'IbetCoupon',
                'owner_address': issuer['account_address'],
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
                'status': True,
                'initial_offering_status': False,
                'image_url': [
                    {'id': 1, 'url': ''},
                    {'id': 2, 'url': ''},
                    {'id': 3, 'url': ''}
                ],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'tradable_exchange': exchange_address,
            }, {
                'id': 0,
                'token_address': issued_list[0]['address'],
                'token_template': 'IbetCoupon',
                'owner_address': issuer['account_address'],
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
                'status': True,
                'initial_offering_status': False,
                'image_url': [
                    {'id': 1, 'url': ''},
                    {'id': 2, 'url': ''},
                    {'id': 3, 'url': ''}
                ],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'tradable_exchange': exchange_address,
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系3＞
    # 発行済クーポンあり（2件）
    # cursor=2、 limit=2
    # -> 登録が新しい順にリストが返却（2件）
    def test_couponlist_normal_3(self, client, session, shared_contract):
        config.COUPON_TOKEN_ENABLED = True
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenCouponTokens.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：新規発行
        issued_list = []
        exchange_address = to_checksum_address(shared_contract['IbetCouponExchange']['address'])
        for i in range(0, 2):
            attribute = TestV2TokenCouponTokens. \
                token_attribute(exchange_address)
            token = issue_coupon_token(issuer, attribute)
            coupon_register_list(issuer, token, token_list)
            issued_list.append(token)
            # 取扱トークンデータ挿入
            TestV2TokenCouponTokens.list_token(session, token)

        query_string = 'cursor=2&limit=2'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [
            {
                'id': 1,
                'token_address': issued_list[1]['address'],
                'token_template': 'IbetCoupon',
                'owner_address': issuer['account_address'],
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
                'status': True,
                'initial_offering_status': False,
                'image_url': [
                    {'id': 1, 'url': ''},
                    {'id': 2, 'url': ''},
                    {'id': 3, 'url': ''}
                ],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'tradable_exchange': exchange_address,
            }, {
                'id': 0,
                'token_address': issued_list[0]['address'],
                'token_template': 'IbetCoupon',
                'owner_address': issuer['account_address'],
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
                'status': True,
                'initial_offering_status': False,
                'image_url': [
                    {'id': 1, 'url': ''},
                    {'id': 2, 'url': ''},
                    {'id': 3, 'url': ''}
                ],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'tradable_exchange': exchange_address,
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系4＞
    # 発行済クーポンあり（2件）
    # cursor=1、 limit=1
    # -> 登録が新しい順にリストが返却（1件）
    def test_couponlist_normal_4(self, client, session, shared_contract):
        config.COUPON_TOKEN_ENABLED = True
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenCouponTokens.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：新規発行
        issued_list = []
        exchange_address = to_checksum_address(shared_contract['IbetCouponExchange']['address'])
        for i in range(0, 2):
            attribute = TestV2TokenCouponTokens.token_attribute(exchange_address)
            token = issue_coupon_token(issuer, attribute)
            coupon_register_list(issuer, token, token_list)
            issued_list.append(token)
            # 取扱トークンデータ挿入
            TestV2TokenCouponTokens.list_token(session, token)

        query_string = 'cursor=1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id': 0,
            'token_address': issued_list[0]['address'],
            'token_template': 'IbetCoupon',
            'owner_address': issuer['account_address'],
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
            'status': True,
            'initial_offering_status': False,
            'image_url': [
                {'id': 1, 'url': ''},
                {'id': 2, 'url': ''},
                {'id': 3, 'url': ''}
            ],
            'max_holding_quantity': 1,
            'max_sell_amount': 1000,
            'contact_information': '問い合わせ先',
            'privacy_policy': 'プライバシーポリシー',
            'tradable_exchange': exchange_address,
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系5＞
    # 発行済クーポンあり（2件）
    # cursor=1、 limit=2
    # -> 登録が新しい順にリストが返却（1件）
    def test_couponlist_normal_5(self, client, session, shared_contract):
        config.COUPON_TOKEN_ENABLED = True
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenCouponTokens.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：新規発行
        issued_list = []
        exchange_address = to_checksum_address(shared_contract['IbetCouponExchange']['address'])
        for i in range(0, 2):
            attribute = TestV2TokenCouponTokens.token_attribute(exchange_address)
            token = issue_coupon_token(issuer, attribute)
            coupon_register_list(issuer, token, token_list)
            issued_list.append(token)
            # 取扱トークンデータ挿入
            TestV2TokenCouponTokens.list_token(session, token)

        query_string = 'cursor=1&limit=2'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id': 0,
            'token_address': issued_list[0]['address'],
            'token_template': 'IbetCoupon',
            'owner_address': issuer['account_address'],
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
            'status': True,
            'initial_offering_status': False,
            'image_url': [
                {'id': 1, 'url': ''},
                {'id': 2, 'url': ''},
                {'id': 3, 'url': ''}
            ],
            'max_holding_quantity': 1,
            'max_sell_amount': 1000,
            'contact_information': '問い合わせ先',
            'privacy_policy': 'プライバシーポリシー',
            'tradable_exchange': exchange_address,
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系6＞
    # クーポン発行（1件）　→　無効化
    # cursor=設定なし、 limit=設定なし
    # -> 0件返却
    def test_couponlist_normal_6(self, client, session, shared_contract):
        config.COUPON_TOKEN_ENABLED = True
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenCouponTokens.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：新規発行
        exchange_address = to_checksum_address(shared_contract['IbetCouponExchange']['address'])
        attribute = TestV2TokenCouponTokens.token_attribute(exchange_address)
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # 取扱トークンデータ挿入
        TestV2TokenCouponTokens.list_token(session, token)

        # Tokenの無効化
        invalidate_coupon_token(issuer, token)

        query_string = ''
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー
    def test_couponlist_error_1(self, client, session):
        config.COUPON_TOKEN_ENABLED = True
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /v2/Token/Coupon'
        }

    # ＜エラー系2-1＞
    # cursorに文字が含まれる
    # -> 入力エラー
    def test_couponlist_error_2_1(self, client, session):
        config.COUPON_TOKEN_ENABLED = True
        query_string = 'cursor=a&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'cursor': [
                    "field 'cursor' cannot be coerced: invalid literal for int() with base 10: 'a'",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系2-2＞
    # cursorが負値
    # -> 入力エラー
    def test_couponlist_error_2_2(self, client, session):
        config.COUPON_TOKEN_ENABLED = True
        query_string = 'cursor=-1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'cursor': ['min value is 0']}
        }

    # ＜エラー系2-3＞
    # cursorが小数
    # -> 入力エラー
    def test_couponlist_error_2_3(self, client, session):
        config.COUPON_TOKEN_ENABLED = True
        query_string = 'cursor=0.1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'cursor': [
                    "field 'cursor' cannot be coerced: invalid literal for int() with base 10: '0.1'",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系2-4＞
    # cursorがint最大値
    # -> 入力エラー
    def test_couponlist_error_2_4(self, client, session):
        config.COUPON_TOKEN_ENABLED = True
        max_value = str(sys.maxsize)
        query_string = 'cursor=' + max_value + '&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'cursor parameter must be less than token list num'
        }

    # ＜エラー系3-1＞
    # limitに文字が含まれる
    # -> 入力エラー
    def test_couponlist_error_3_1(self, client, session):
        config.COUPON_TOKEN_ENABLED = True
        query_string = 'cursor=1&limit=a'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'limit': [
                    "field 'limit' cannot be coerced: invalid literal for int() with base 10: 'a'",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系3-2＞
    # limitが負値
    # -> 入力エラー
    def test_couponlist_error_3_2(self, client, session):
        config.COUPON_TOKEN_ENABLED = True
        query_string = 'cursor=1&limit=-1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'limit': ['min value is 0']}
        }

    # ＜エラー系3-3＞
    # limitが小数
    # -> 入力エラー
    def test_couponlist_error_3_3(self, client, session):
        config.COUPON_TOKEN_ENABLED = True
        query_string = 'cursor=1&limit=0.1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'limit': [
                    "field 'limit' cannot be coerced: invalid literal for int() with base 10: '0.1'",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系4＞
    #  取扱トークン対象外
    def test_error_4(self, client, session):
        config.COUPON_TOKEN_ENABLED = False
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v2/Token/Coupon'
        }
