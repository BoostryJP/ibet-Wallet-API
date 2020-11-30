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

from eth_utils import to_checksum_address
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.model import Listing
from app import config
from app.contracts import Contract

from .account_config import eth_account
from .contract_modules import issue_bond_token, register_bond_list, bond_invalidate, bond_untransferable

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


class TestV2TokenTokenStatus:
    """
    Test Case for v2.token.TokenStatus
    """

    # テスト対象API
    apiurl_base = '/v2/Token/{contract_address}/Status'

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
            'personalInfoAddress': personal_info_address
        }
        return attribute

    @staticmethod
    def tokenlist_contract():
        deployer = eth_account['deployer']
        web3.eth.defaultAccount = deployer['account_address']
        web3.personal.unlockAccount(deployer['account_address'], deployer['password'])

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
    #   データあり（取扱ステータス = True, 譲渡可否 = True）
    def test_tokenstatus_normal_1(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(shared_contract['PersonalInfo']['address'])
        attribute = TestV2TokenTokenStatus.bond_token_attribute(exchange_address, personal_info)
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)

        # 取扱トークンデータ挿入
        TestV2TokenTokenStatus.list_token(session, bond_token)

        apiurl = self.apiurl_base.format(contract_address=bond_token['address'])
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = {
            'status': True,
            'transferable': True
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2＞
    #   データ有り（トークン無効化済み）
    def test_tokenstatus_normal_2(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(shared_contract['PersonalInfo']['address'])
        attribute = TestV2TokenTokenStatus.bond_token_attribute(exchange_address, personal_info)
        token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, token, token_list)

        # 取扱トークンデータ挿入
        TestV2TokenTokenStatus.list_token(session, token)

        # Tokenの無効化
        bond_invalidate(issuer, token)

        apiurl = self.apiurl_base.format(contract_address=token['address'])
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = {
            'status': False,
            'transferable': True
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系3＞
    #   データあり（取扱ステータス = True, 譲渡可否 = False）
    def test_tokenstatus_normal_3(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：債券新規発行
        exchange_address = to_checksum_address(shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(shared_contract['PersonalInfo']['address'])
        attribute = TestV2TokenTokenStatus.bond_token_attribute(exchange_address, personal_info)
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)

        # 取扱トークンデータ挿入
        TestV2TokenTokenStatus.list_token(session, bond_token)

        # Tokenの譲渡不可
        bond_untransferable(issuer, bond_token)

        apiurl = self.apiurl_base.format(contract_address=bond_token['address'])
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = {
            'status': True,
            'transferable': False
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜エラー系1＞
    #   無効なコントラクトアドレス
    #   -> 400エラー
    def test_tokenstatus_error_1(self, client):
        apiurl = self.apiurl_base.format(contract_address='0xabcd')

        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'invalid contract_address'
        }

    # ＜エラー系2＞
    #   取扱トークン（DB）に情報が存在しない
    def test_tokenstatus_error_2(self, client, shared_contract, session):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：新規発行
        exchange_address = to_checksum_address(shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(shared_contract['PersonalInfo']['address'])
        attribute = TestV2TokenTokenStatus.bond_token_attribute(exchange_address, personal_info)
        token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, token, token_list)

        # NOTE:取扱トークンデータを挿入しない

        apiurl = self.apiurl_base.format(contract_address=token['address'])
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 30,
            'message': 'Data Not Exists',
            'description': 'contract_address: ' + token['address']
        }
