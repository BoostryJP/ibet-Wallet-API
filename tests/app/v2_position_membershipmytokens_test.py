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

from app import config
from app.model.db import Listing

from tests.account_config import eth_account
from tests.contract_modules import (
    membership_issue,
    membership_register_list,
    membership_offer,
    get_latest_orderid,
    take_buy,
    get_latest_agreementid,
    confirm_agreement
)


class TestV2MembershipMyTokens:
    """
    Test Case for v2.position.MembershipMyTokens
    """

    # テスト対象API
    apiurl = '/v2/Position/Membership'

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
        latest_orderid = get_latest_orderid(exchange)
        take_buy(trader, exchange, latest_orderid, 100)

        # ＜決済業者オペレーション＞
        #   1）　決済
        latest_agreementid = \
            get_latest_agreementid(exchange, latest_orderid)
        confirm_agreement(
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
        latest_orderid = get_latest_orderid(exchange)
        take_buy(trader, exchange, latest_orderid, 100)

        # ＜決済業者オペレーション＞
        #   1）　決済
        latest_agreementid = \
            get_latest_agreementid(exchange, latest_orderid)
        confirm_agreement(
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
        latest_orderid = get_latest_orderid(exchange)
        take_buy(trader, exchange, latest_orderid, 100)

        # ＜決済業者オペレーション①＞
        #   1）　決済
        latest_agreementid = \
            get_latest_agreementid(exchange, latest_orderid)
        confirm_agreement(
            agent, exchange, latest_orderid, latest_agreementid)

        # ＜投資家オペレーション②＞
        #   1) Make売
        membership_offer(trader, exchange, token, 100, 1001)

        # ＜発行体オペレーション②＞
        #   1) Take買
        latest_orderid = get_latest_orderid(exchange)
        take_buy(issuer, exchange, latest_orderid, 100)

        # ＜決済業者オペレーション②＞
        #   1）　決済
        latest_agreementid = \
            get_latest_agreementid(exchange, latest_orderid)
        confirm_agreement(
            agent, exchange, latest_orderid, latest_agreementid)

        return token

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

    # 正常系1
    # 残高あり、売注文中なし
    # 発行体：新規発行　→　発行体：募集（Make売）　→　投資家：Take買 →　決済業者：決済
    def test_membership_position_normal_1(self, client, session, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token_list = shared_contract['TokenList']
        account = eth_account['trader']

        token = TestV2MembershipMyTokens.create_balance(exchange, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV2MembershipMyTokens.list_token(session, token)

        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetMembership',
                'owner_address': eth_account['issuer']['account_address'],
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
                'initial_offering_status': False,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 100,
            'exchange_balance': 0,
            'exchange_commitment': 0,
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        count = 0
        for token in resp.json['data']:
            if token['token']['token_address'] == token_address:
                count = 1
                assert token == assumed_body
        assert count == 1

    # 正常系2-1
    # 残高あり、売注文中あり
    # 発行体：新規発行　→　発行体：募集（Make売）　→　投資家：Take買
    #   →　決済代行：決済　→　投資家：Make売
    def test_membership_position_normal_2_1(self, client, session, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token_list = shared_contract['TokenList']
        account = eth_account['trader']

        token = TestV2MembershipMyTokens.create_commitment(exchange, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV2MembershipMyTokens.list_token(session, token)

        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetMembership',
                'owner_address': eth_account['issuer']['account_address'],
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
                'initial_offering_status': False,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 50,
            'exchange_balance': 0,
            'exchange_commitment': 50,
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        count = 0
        for token in resp.json['data']:
            if token['token']['token_address'] == token_address:
                count = 1
                assert token == assumed_body
        assert count == 1

    # 正常系2-2
    # 残高あり、exchangeアドレス未設定
    # 発行体：新規発行　→　発行体：募集（Make売）　→　投資家：Take買
    #   →　決済代行：決済　→　投資家：Make売
    def test_membership_position_normal_2_2(self, client, session, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token_list = shared_contract['TokenList']
        account = eth_account['trader']

        token = TestV2MembershipMyTokens.create_commitment(exchange, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV2MembershipMyTokens.list_token(session, token)

        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = None
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetMembership',
                'owner_address': eth_account['issuer']['account_address'],
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
                'initial_offering_status': False,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 50,
            'exchange_balance': 0,
            'exchange_commitment': 0,
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

        token = TestV2MembershipMyTokens.create_zero(exchange, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV2MembershipMyTokens.list_token(session, token)

        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
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
    def test_membership_position_normal_4(self, client, session, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token_list = shared_contract['TokenList']
        account = eth_account['trader']

        token = TestV2MembershipMyTokens.create_balance(exchange, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV2MembershipMyTokens.list_private_token(session, token)

        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetMembership',
                'owner_address': eth_account['issuer']['account_address'],
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
                'initial_offering_status': False,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 100,
            'exchange_balance': 0,
            'exchange_commitment': 0,
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
    def test_membership_position_normal_5(self, client, session, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token_list = shared_contract['TokenList']
        account = eth_account['trader']

        token = TestV2MembershipMyTokens.create_balance(exchange, token_list)
        token_address = token['address']

        # 取扱トークンデータ挿入
        TestV2MembershipMyTokens.list_token(session, token)
        TestV2MembershipMyTokens.list_private_token(session, token)

        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetMembership',
                'owner_address': eth_account['issuer']['account_address'],
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
                'initial_offering_status': False,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 100,
            'exchange_balance': 0,
            'exchange_commitment': 0,
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
    def test_membership_position_normal_6(self, client, session, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token_list = shared_contract['TokenList']
        account = eth_account['trader']

        # 会員権①
        token_1 = TestV2MembershipMyTokens.create_balance(exchange, token_list)
        token_address_1 = token_1['address']

        # 会員権②
        token_2 = TestV2MembershipMyTokens.create_balance(exchange, token_list)
        token_address_2 = token_2['address']

        # 取扱トークンデータ挿入
        TestV2MembershipMyTokens.list_token(session, token_1)
        TestV2MembershipMyTokens.list_private_token(session, token_2)

        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body_1 = {
            'token': {
                'token_address': token_address_1,
                'token_template': 'IbetMembership',
                'owner_address': eth_account['issuer']['account_address'],
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
                'initial_offering_status': False,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 100,
            'exchange_balance': 0,
            'exchange_commitment': 0,
        }

        assumed_body_2 = {
            'token': {
                'token_address': token_address_2,
                'token_template': 'IbetMembership',
                'owner_address': eth_account['issuer']['account_address'],
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
                'initial_offering_status': False,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            'balance': 100,
            'exchange_balance': 0,
            'exchange_commitment': 0,
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
    def test_membership_position_error_1(self, client, session):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        config.MEMBERSHIP_TOKEN_ENABLED = True

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
    def test_membership_position_error_2(self, client, session):
        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        headers = {}
        request_body = json.dumps(request_params)

        config.MEMBERSHIP_TOKEN_ENABLED = True

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3-1
    # 入力値エラー（account_addressがアドレスフォーマットではない）
    def test_membership_position_error_3_1(self, client, session):
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  # アドレスが短い
        request_params = {"account_address_list": [account_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.MEMBERSHIP_TOKEN_ENABLED = True

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3-2
    # 入力値エラー（account_addressがstring以外）
    def test_membership_position_error_3_2(self, client, session):
        account_address = 123456789123456789123456789123456789
        request_params = {"account_address_list": [account_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.MEMBERSHIP_TOKEN_ENABLED = True

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

    # エラー系4
    # 取扱トークン対象外
    def test_membership_position_error_4(self, client, session):

        config.MEMBERSHIP_TOKEN_ENABLED = False

        resp = client.simulate_post(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /v2/Position/Membership'
        }
