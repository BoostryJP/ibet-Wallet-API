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

from app.model import IDXPosition, Listing
from app.tests.account_config import eth_account
from app.tests.contract_modules import issue_coupon_token


class TestV2StatisticsToken:
    """
    Test Case for v2.statistics.Token
    """

    # テスト対象API
    apiurl_base = '/v2/Statistics/Token/'  # {contract_address}

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
    def list_token(session, token, issuer):
        listed_token = Listing()
        listed_token.token_address = token['address']
        listed_token.is_public = True
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
        listed_token.owner_address = issuer['account_address']
        session.add(listed_token)

    @staticmethod
    def insert_position(session, token_address, account_address, balance):
        position = IDXPosition()
        position.token_address = token_address
        position.account_address = account_address
        position.balance = balance
        session.add(position)

    @staticmethod
    def prepare_token(session, shared_contract):
        issuer = eth_account['issuer']

        exchange_address = \
            to_checksum_address(
                shared_contract['IbetCouponExchange']['address'])
        token = issue_coupon_token(issuer, TestV2StatisticsToken.token_attribute(exchange_address))

        TestV2StatisticsToken.list_token(session, token, issuer)

        return token

    ####################################################################
    # Normal
    ####################################################################

    # Normal_1
    # Positionデータなし
    def test_normal_1(self, client, db, session, shared_contract):
        token = TestV2StatisticsToken.prepare_token(session, shared_contract)

        apiurl = self.apiurl_base + token['address']
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = {'holders_count': 0}  # 0件

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # Normal_2
    # Positionデータあり
    def test_normal_2(self, client, session, shared_contract):
        token = TestV2StatisticsToken.prepare_token(session, shared_contract)

        # データ準備 1
        self.insert_position(
            session,
            token['address'],
            "0x342d0BfeD067eF22e2818E8f8731108a45F6Dd35",
            100
        )

        # データ準備 2
        self.insert_position(
            session,
            token['address'],
            "0x8587F9Ba6E5910e693A5E6190C98F029689A1dA3",
            200
        )

        apiurl = self.apiurl_base + token['address']
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = {'holders_count': 2}  # 2件

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # Normal_3
    # Positionデータあり（残高0のデータが存在）
    def test_normal_3(self, client, session, shared_contract):
        token = TestV2StatisticsToken.prepare_token(session, shared_contract)

        # データ準備１
        self.insert_position(
            session,
            token['address'],
            "0x342d0BfeD067eF22e2818E8f8731108a45F6Dd35",
            100
        )

        # データ準備２
        self.insert_position(
            session,
            token['address'],
            "0x8587F9Ba6E5910e693A5E6190C98F029689A1dA3",
            0
        )

        apiurl = self.apiurl_base + token['address']
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = {'holders_count': 1}  # 1件

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # Normal_4
    # Positionデータあり（発行体、DEXのデータが存在）
    def test_normal_4(self, client, session, shared_contract):
        token = TestV2StatisticsToken.prepare_token(session, shared_contract)

        # データ準備１（発行体）
        self.insert_position(
            session,
            token['address'],
            eth_account['issuer']['account_address'],
            100
        )

        # データ準備２（DEX）
        self.insert_position(
            session,
            token['address'],
            shared_contract['IbetCouponExchange']['address'],
            100
        )

        # データ準備３（投資家）
        self.insert_position(
            session,
            token['address'],
            "0x342d0BfeD067eF22e2818E8f8731108a45F6Dd35",
            100
        )

        apiurl = self.apiurl_base + token['address']
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = {'holders_count': 1}  # 1件

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body
    ####################################################################
    # Error
    ####################################################################

    # Error_1
    # 無効なコントラクトアドレス
    # 400
    def test_error_1(self, client):
        apiurl = self.apiurl_base + '0xabcd'

        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'invalid contract_address'
        }

    # Error_2
    # 存在しないコントラクトアドレス
    # 404
    def test_error_2(self, client, session):
        error_address = '0xb9058D42bA2a08C512B1333684F3A94aCa6a6be4'
        apiurl = self.apiurl_base + error_address

        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 30,
            'message': 'Data Not Exists',
            'description': 'contract_address: ' + error_address
        }
