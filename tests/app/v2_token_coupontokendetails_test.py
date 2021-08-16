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
from eth_utils import to_checksum_address
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.model import Listing
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


class TestV2TokenCouponTokenDetails:
    """
    Test Case for v2.token.CouponTokenDetails
    """

    # テスト対象API
    apiurl_base = '/v2/Token/Coupon/'  # {contract_address}

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
        contract_address, abi = Contract. \
            deploy_contract('TokenList', [], deployer['account_address'])
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
    #   データあり
    def test_coupondetails_normal_1(self, client, session, shared_contract):
        config.COUPON_TOKEN_ENABLED = True
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenCouponTokenDetails.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：新規発行
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetCouponExchange']['address'])
        attribute = TestV2TokenCouponTokenDetails.token_attribute(exchange_address)
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # 取扱トークンデータ挿入
        TestV2TokenCouponTokenDetails.list_token(session, token)

        apiurl = self.apiurl_base + token['address']
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = {
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
            'privacy_policy': 'プライバシーポリシー'
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜エラー系1＞
    #   無効なコントラクトアドレス
    #   -> 400エラー
    def test_coupondetails_error_1(self, client):
        config.COUPON_TOKEN_ENABLED = True
        apiurl = self.apiurl_base + '0xabcd'

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
    def test_coupondetails_error_2(self, client, shared_contract, session):
        config.COUPON_TOKEN_ENABLED = True
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenCouponTokenDetails.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：新規発行
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetCouponExchange']['address'])
        attribute = TestV2TokenCouponTokenDetails.token_attribute(exchange_address)
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # NOTE:取扱トークンデータを挿入しない

        apiurl = self.apiurl_base + token['address']
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 30,
            'message': 'Data Not Exists',
            'description': 'contract_address: ' + token['address']
        }

    # ＜エラー系3＞
    #   トークン無効化（データなし）
    def test_coupondetails_error_3(self, client, session, shared_contract):
        config.COUPON_TOKEN_ENABLED = True
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenCouponTokenDetails.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：新規発行
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetCouponExchange']['address'])
        attribute = TestV2TokenCouponTokenDetails.token_attribute(exchange_address)
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # 取扱トークンデータ挿入
        TestV2TokenCouponTokenDetails.list_token(session, token)

        # Tokenの無効化
        invalidate_coupon_token(issuer, token)

        apiurl = self.apiurl_base + token['address']
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 30,
            'message': 'Data Not Exists',
            'description': 'contract_address: ' + token['address']
        }

    # ＜エラー系4＞
    #  取扱トークン対象外
    def test_error_4(self, client):
        config.COUPON_TOKEN_ENABLED = False
        resp = client.simulate_get(self.apiurl_base + "0xe6A75581C7299c75392a63BCF18a3618B30ff765")

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v2/Token/Coupon/0xe6A75581C7299c75392a63BCF18a3618B30ff765'
        }
