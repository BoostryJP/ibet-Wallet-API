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
    issue_bond_token,
    register_bond_list,
    bond_invalidate
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestV2TokenStraightBondTokens:
    """
    Test Case for v2.token.StraightBondTokens
    """

    # テスト対象API
    apiurl = '/v2/Token/StraightBond'

    @staticmethod
    def bond_token_attribute(exchange_address, personal_info_address):
        attribute = {
            'name': 'テスト債券',
            'symbol': 'BOND',
            'totalSupply': 1000000,
            'tradableExchange': exchange_address,
            'faceValue': 10000,
            'interestRate': 602,
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
            'redemptionValue': 10000,
            'returnDate': '20191231',
            'returnAmount': '商品券をプレゼント',
            'purpose': '新商品の開発資金として利用。',
            'memo': 'メモ',
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー',
            'personalInfoAddress': personal_info_address,
        }
        return attribute

    @staticmethod
    def tokenlist_contract():
        deployer = eth_account['deployer']
        web3.eth.default_account = deployer['account_address']
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
    # 発行済債券あり（1件）
    # cursor=設定なし、 limit=設定なし
    # -> 1件返却
    def test_bondlist_normal_1(self, client, session, shared_contract):
        config.BOND_TOKEN_ENABLED = True
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(shared_contract['PersonalInfo']['address'])
        attribute = self.bond_token_attribute(exchange_address, personal_info)
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)

        # 取扱トークンデータ挿入
        self.list_token(session, bond_token)

        query_string = ''
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id': 0,
            'token_address': bond_token['address'],
            'token_template': 'IbetStraightBond',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
            'name': 'テスト債券',
            'symbol': 'BOND',
            'total_supply': 1000000,
            'face_value': 10000,
            'interest_rate': 0.0602,
            'interest_payment_date1': '0101',
            'interest_payment_date2': '0201',
            'interest_payment_date3': '0301',
            'interest_payment_date4': '0401',
            'interest_payment_date5': '0501',
            'interest_payment_date6': '0601',
            'interest_payment_date7': '0701',
            'interest_payment_date8': '0801',
            'interest_payment_date9': '0901',
            'interest_payment_date10': '1001',
            'interest_payment_date11': '1101',
            'interest_payment_date12': '1201',
            'is_redeemed': False,
            'redemption_date': '20191231',
            'redemption_value': 10000,
            'return_date': '20191231',
            'return_amount': '商品券をプレゼント',
            'purpose': '新商品の開発資金として利用。',
            'is_offering': False,
            'max_holding_quantity': 1,
            'max_sell_amount': 1000,
            'contact_information': '問い合わせ先',
            'privacy_policy': 'プライバシーポリシー',
            'transferable': True,
            'tradable_exchange': exchange_address,
            'status': True,
            'memo': 'メモ',
            'personal_info_address': personal_info,
            'transfer_approval_required': False,
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2＞
    # 発行済債券あり（2件）
    # cursor=設定なし、 limit=設定なし
    # -> 登録が新しい順にリストが返却
    def test_bondlist_normal_2(self, client, session, shared_contract):
        config.BOND_TOKEN_ENABLED = True
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：債券新規発行
        bond_list = []
        exchange_address = to_checksum_address(shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(shared_contract['PersonalInfo']['address'])
        for i in range(0, 2):
            attribute = self.bond_token_attribute(exchange_address, personal_info)
            bond_token = issue_bond_token(issuer, attribute)
            register_bond_list(issuer, bond_token, token_list)
            bond_list.append(bond_token)
            # 取扱トークンデータ挿入
            self.list_token(session, bond_token)

        query_string = ''
        resp = client.simulate_get(self.apiurl, query_string=query_string)
        assumed_body = [{
            'id': 1,
            'token_address': bond_list[1]['address'],
            'token_template': 'IbetStraightBond',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
            'name': 'テスト債券',
            'symbol': 'BOND',
            'total_supply': 1000000,
            'face_value': 10000,
            'interest_rate': 0.0602,
            'interest_payment_date1': '0101',
            'interest_payment_date2': '0201',
            'interest_payment_date3': '0301',
            'interest_payment_date4': '0401',
            'interest_payment_date5': '0501',
            'interest_payment_date6': '0601',
            'interest_payment_date7': '0701',
            'interest_payment_date8': '0801',
            'interest_payment_date9': '0901',
            'interest_payment_date10': '1001',
            'interest_payment_date11': '1101',
            'interest_payment_date12': '1201',
            'is_redeemed': False,
            'redemption_date': '20191231',
            'redemption_value': 10000,
            'return_date': '20191231',
            'return_amount': '商品券をプレゼント',
            'purpose': '新商品の開発資金として利用。',
            'is_offering': False,
            'max_holding_quantity': 1,
            'max_sell_amount': 1000,
            'contact_information': '問い合わせ先',
            'privacy_policy': 'プライバシーポリシー',
            'transferable': True,
            'tradable_exchange': exchange_address,
            'status': True,
            'memo': 'メモ',
            'personal_info_address': personal_info,
            'transfer_approval_required': False,
        }, {
            'id': 0,
            'token_address': bond_list[0]['address'],
            'token_template': 'IbetStraightBond',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
            'name': 'テスト債券',
            'symbol': 'BOND',
            'total_supply': 1000000,
            'face_value': 10000,
            'interest_rate': 0.0602,
            'interest_payment_date1': '0101',
            'interest_payment_date2': '0201',
            'interest_payment_date3': '0301',
            'interest_payment_date4': '0401',
            'interest_payment_date5': '0501',
            'interest_payment_date6': '0601',
            'interest_payment_date7': '0701',
            'interest_payment_date8': '0801',
            'interest_payment_date9': '0901',
            'interest_payment_date10': '1001',
            'interest_payment_date11': '1101',
            'interest_payment_date12': '1201',
            'is_redeemed': False,
            'redemption_date': '20191231',
            'redemption_value': 10000,
            'return_date': '20191231',
            'return_amount': '商品券をプレゼント',
            'purpose': '新商品の開発資金として利用。',
            'is_offering': False,
            'max_holding_quantity': 1,
            'max_sell_amount': 1000,
            'contact_information': '問い合わせ先',
            'privacy_policy': 'プライバシーポリシー',
            'transferable': True,
            'tradable_exchange': exchange_address,
            'status': True,
            'memo': 'メモ',
            'personal_info_address': personal_info,
            'transfer_approval_required': False,
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系3＞
    # 発行済債券あり（2件）
    # cursor=2、 limit=2
    # -> 登録が新しい順にリストが返却（2件）
    def test_bondlist_normal_3(self, client, session, shared_contract):
        config.BOND_TOKEN_ENABLED = True
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：債券新規発行
        bond_list = []
        exchange_address = to_checksum_address(shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(shared_contract['PersonalInfo']['address'])
        for i in range(0, 2):
            attribute = self.bond_token_attribute(exchange_address, personal_info)
            bond_token = issue_bond_token(issuer, attribute)
            register_bond_list(issuer, bond_token, token_list)
            bond_list.append(bond_token)
            # 取扱トークンデータ挿入
            self.list_token(session, bond_token)

        query_string = 'cursor=2&limit=2'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id': 1,
            'token_address': bond_list[1]['address'],
            'token_template': 'IbetStraightBond',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
            'name': 'テスト債券',
            'symbol': 'BOND',
            'total_supply': 1000000,
            'face_value': 10000,
            'interest_rate': 0.0602,
            'interest_payment_date1': '0101',
            'interest_payment_date2': '0201',
            'interest_payment_date3': '0301',
            'interest_payment_date4': '0401',
            'interest_payment_date5': '0501',
            'interest_payment_date6': '0601',
            'interest_payment_date7': '0701',
            'interest_payment_date8': '0801',
            'interest_payment_date9': '0901',
            'interest_payment_date10': '1001',
            'interest_payment_date11': '1101',
            'interest_payment_date12': '1201',
            'is_redeemed': False,
            'redemption_date': '20191231',
            'redemption_value': 10000,
            'return_date': '20191231',
            'return_amount': '商品券をプレゼント',
            'purpose': '新商品の開発資金として利用。',
            'is_offering': False,
            'max_holding_quantity': 1,
            'max_sell_amount': 1000,
            'contact_information': '問い合わせ先',
            'privacy_policy': 'プライバシーポリシー',
            'transferable': True,
            'tradable_exchange': exchange_address,
            'status': True,
            'memo': 'メモ',
            'personal_info_address': personal_info,
            'transfer_approval_required': False,
        }, {
            'id': 0,
            'token_address': bond_list[0]['address'],
            'token_template': 'IbetStraightBond',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
            'name': 'テスト債券',
            'symbol': 'BOND',
            'total_supply': 1000000,
            'face_value': 10000,
            'interest_rate': 0.0602,
            'interest_payment_date1': '0101',
            'interest_payment_date2': '0201',
            'interest_payment_date3': '0301',
            'interest_payment_date4': '0401',
            'interest_payment_date5': '0501',
            'interest_payment_date6': '0601',
            'interest_payment_date7': '0701',
            'interest_payment_date8': '0801',
            'interest_payment_date9': '0901',
            'interest_payment_date10': '1001',
            'interest_payment_date11': '1101',
            'interest_payment_date12': '1201',
            'is_redeemed': False,
            'redemption_date': '20191231',
            'redemption_value': 10000,
            'return_date': '20191231',
            'return_amount': '商品券をプレゼント',
            'purpose': '新商品の開発資金として利用。',
            'is_offering': False,
            'max_holding_quantity': 1,
            'max_sell_amount': 1000,
            'contact_information': '問い合わせ先',
            'privacy_policy': 'プライバシーポリシー',
            'transferable': True,
            'tradable_exchange': exchange_address,
            'status': True,
            'memo': 'メモ',
            'personal_info_address': personal_info,
            'transfer_approval_required': False,
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系4＞
    # 発行済債券あり（2件）
    # cursor=1、 limit=1
    # -> 登録が新しい順にリストが返却（1件）
    def test_bondlist_normal_4(self, client, session, shared_contract):
        config.BOND_TOKEN_ENABLED = True
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：債券新規発行
        bond_list = []
        exchange_address = to_checksum_address(shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(shared_contract['PersonalInfo']['address'])
        for i in range(0, 2):
            attribute = self.bond_token_attribute(exchange_address, personal_info)
            bond_token = issue_bond_token(issuer, attribute)
            register_bond_list(issuer, bond_token, token_list)
            bond_list.append(bond_token)
            # 取扱トークンデータ挿入
            self.list_token(session, bond_token)

        query_string = 'cursor=1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id': 0,
            'token_address': bond_list[0]['address'],
            'token_template': 'IbetStraightBond',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
            'name': 'テスト債券',
            'symbol': 'BOND',
            'total_supply': 1000000,
            'face_value': 10000,
            'interest_rate': 0.0602,
            'interest_payment_date1': '0101',
            'interest_payment_date2': '0201',
            'interest_payment_date3': '0301',
            'interest_payment_date4': '0401',
            'interest_payment_date5': '0501',
            'interest_payment_date6': '0601',
            'interest_payment_date7': '0701',
            'interest_payment_date8': '0801',
            'interest_payment_date9': '0901',
            'interest_payment_date10': '1001',
            'interest_payment_date11': '1101',
            'interest_payment_date12': '1201',
            'is_redeemed': False,
            'redemption_date': '20191231',
            'redemption_value': 10000,
            'return_date': '20191231',
            'return_amount': '商品券をプレゼント',
            'purpose': '新商品の開発資金として利用。',
            'is_offering': False,
            'max_holding_quantity': 1,
            'max_sell_amount': 1000,
            'contact_information': '問い合わせ先',
            'privacy_policy': 'プライバシーポリシー',
            'transferable': True,
            'tradable_exchange': exchange_address,
            'status': True,
            'memo': 'メモ',
            'personal_info_address': personal_info,
            'transfer_approval_required': False,
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系5＞
    # 発行済債券あり（2件）
    # cursor=1、 limit=2
    # -> 登録が新しい順にリストが返却（1件）
    def test_bondlist_normal_5(self, client, session, shared_contract):
        config.BOND_TOKEN_ENABLED = True
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：債券新規発行
        bond_list = []
        exchange_address = to_checksum_address(shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(shared_contract['PersonalInfo']['address'])
        for i in range(0, 2):
            attribute = self.bond_token_attribute(exchange_address, personal_info)
            bond_token = issue_bond_token(issuer, attribute)
            register_bond_list(issuer, bond_token, token_list)
            bond_list.append(bond_token)
            # 取扱トークンデータ挿入
            self.list_token(session, bond_token)

        query_string = 'cursor=1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id': 0,
            'token_address': bond_list[0]['address'],
            'token_template': 'IbetStraightBond',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
            'name': 'テスト債券',
            'symbol': 'BOND',
            'total_supply': 1000000,
            'face_value': 10000,
            'interest_rate': 0.0602,
            'interest_payment_date1': '0101',
            'interest_payment_date2': '0201',
            'interest_payment_date3': '0301',
            'interest_payment_date4': '0401',
            'interest_payment_date5': '0501',
            'interest_payment_date6': '0601',
            'interest_payment_date7': '0701',
            'interest_payment_date8': '0801',
            'interest_payment_date9': '0901',
            'interest_payment_date10': '1001',
            'interest_payment_date11': '1101',
            'interest_payment_date12': '1201',
            'is_redeemed': False,
            'redemption_date': '20191231',
            'redemption_value': 10000,
            'return_date': '20191231',
            'return_amount': '商品券をプレゼント',
            'purpose': '新商品の開発資金として利用。',
            'is_offering': False,
            'max_holding_quantity': 1,
            'max_sell_amount': 1000,
            'contact_information': '問い合わせ先',
            'privacy_policy': 'プライバシーポリシー',
            'transferable': True,
            'tradable_exchange': exchange_address,
            'status': True,
            'memo': 'メモ',
            'personal_info_address': personal_info,
            'transfer_approval_required': False,
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系6＞
    # 発行済債券あり（2件）
    # cursor=2、 limit=2
    # -> 1件目のみtransferableを不可に変更
    def test_bondlist_normal_6(self, client, session, shared_contract):
        config.BOND_TOKEN_ENABLED = True
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：債券新規発行
        bond_list = []
        exchange_address = to_checksum_address(shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(shared_contract['PersonalInfo']['address'])
        for i in range(0, 2):
            attribute = self.bond_token_attribute(exchange_address, personal_info)
            bond_token = issue_bond_token(issuer, attribute)
            register_bond_list(issuer, bond_token, token_list)
            bond_list.append(bond_token)
            # 取扱トークンデータ挿入
            self.list_token(session, bond_token)

        # Tokenの無効化
        bond_invalidate(issuer, bond_list[0])

        query_string = 'cursor=2&limit=2'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id': 1,
            'token_address': bond_list[1]['address'],
            'token_template': 'IbetStraightBond',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
            'name': 'テスト債券',
            'symbol': 'BOND',
            'total_supply': 1000000,
            'face_value': 10000,
            'interest_rate': 0.0602,
            'interest_payment_date1': '0101',
            'interest_payment_date2': '0201',
            'interest_payment_date3': '0301',
            'interest_payment_date4': '0401',
            'interest_payment_date5': '0501',
            'interest_payment_date6': '0601',
            'interest_payment_date7': '0701',
            'interest_payment_date8': '0801',
            'interest_payment_date9': '0901',
            'interest_payment_date10': '1001',
            'interest_payment_date11': '1101',
            'interest_payment_date12': '1201',
            'is_redeemed': False,
            'redemption_date': '20191231',
            'redemption_value': 10000,
            'return_date': '20191231',
            'return_amount': '商品券をプレゼント',
            'purpose': '新商品の開発資金として利用。',
            'is_offering': False,
            'max_holding_quantity': 1,
            'max_sell_amount': 1000,
            'contact_information': '問い合わせ先',
            'privacy_policy': 'プライバシーポリシー',
            'transferable': True,
            'tradable_exchange': exchange_address,
            'status': True,
            'memo': 'メモ',
            'personal_info_address': personal_info,
            'transfer_approval_required': False,
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系7＞
    # 発行済債券あり（5件）
    # cursor=設定なし、 limit=設定なし、include_inactive_tokens=True
    # -> 5件返却
    def test_bondlist_normal_7(self, client, session, shared_contract):
        config.BOND_TOKEN_ENABLED = True
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = self.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(shared_contract['PersonalInfo']['address'])
        attribute = self.bond_token_attribute(exchange_address, personal_info)
        assumed_body = []
        for i in range(5):
            bond_token = issue_bond_token(issuer, attribute)
            register_bond_list(issuer, bond_token, token_list)
            # 取扱トークンデータ挿入
            self.list_token(session, bond_token)
            status = True
            if i % 2 == 0:
                bond_invalidate(issuer, bond_token)
                status = False
            assumed_body_element = {
                'id': i,
                'token_address': bond_token['address'],
                'token_template': 'IbetStraightBond',
                'owner_address': issuer['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト債券',
                'symbol': 'BOND',
                'total_supply': 1000000,
                'face_value': 10000,
                'interest_rate': 0.0602,
                'interest_payment_date1': '0101',
                'interest_payment_date2': '0201',
                'interest_payment_date3': '0301',
                'interest_payment_date4': '0401',
                'interest_payment_date5': '0501',
                'interest_payment_date6': '0601',
                'interest_payment_date7': '0701',
                'interest_payment_date8': '0801',
                'interest_payment_date9': '0901',
                'interest_payment_date10': '1001',
                'interest_payment_date11': '1101',
                'interest_payment_date12': '1201',
                'is_redeemed': False,
                'redemption_date': '20191231',
                'redemption_value': 10000,
                'return_date': '20191231',
                'return_amount': '商品券をプレゼント',
                'purpose': '新商品の開発資金として利用。',
                'is_offering': False,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'transferable': True,
                'tradable_exchange': exchange_address,
                'status': status,
                'memo': 'メモ',
                'personal_info_address': personal_info,
                'transfer_approval_required': False,
            }
            assumed_body = [assumed_body_element] + assumed_body

        resp = client.simulate_get(self.apiurl, params={
            'include_inactive_tokens': 'true'
        })

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー
    def test_bondlist_error_1(self, client, session):
        config.BOND_TOKEN_ENABLED = True
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /v2/Token/StraightBond'
        }

    # ＜エラー系2-1＞
    # cursorに文字が含まれる
    # -> 入力エラー
    def test_bondlist_error_2_1(self, client, session):
        config.BOND_TOKEN_ENABLED = True
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
    def test_bondlist_error_2_2(self, client, session):
        config.BOND_TOKEN_ENABLED = True
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
    def test_bondlist_error_2_3(self, client, session):
        config.BOND_TOKEN_ENABLED = True
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
    def test_bondlist_error_2_4(self, client, session):
        config.BOND_TOKEN_ENABLED = True
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
    def test_bondlist_error_3_1(self, client, session):
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
    def test_bondlist_error_3_2(self, client, session):
        config.BOND_TOKEN_ENABLED = True
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
    def test_bondlist_error_3_3(self, client, session):
        config.BOND_TOKEN_ENABLED = True
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

    # ＜エラー系3-4＞
    # statusが非boolean
    # -> 入力エラー
    def test_bondlist_error_3_4(self, client, session):
        config.BOND_TOKEN_ENABLED = True
        query_string = 'include_inactive_tokens=some_value'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'include_inactive_tokens': ['unallowed value some_value']}
        }

    # ＜エラー系4＞
    #  取扱トークン対象外
    def test_bondlist_error_4(self, client, session):
        config.BOND_TOKEN_ENABLED = False
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v2/Token/StraightBond'
        }
