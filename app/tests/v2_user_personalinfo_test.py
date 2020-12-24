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
from .account_config import eth_account
from .contract_modules import register_personalinfo


class TestPersonalInfo:

    # テスト対象API
    apiurl = '/v2/User/PersonalInfo'

    # ＜正常系1＞
    # 通常参照（登録済）
    def test_personalinfo_normal_1(self, client, shared_contract):
        # テスト用アカウント
        trader = eth_account['trader']
        issuer = eth_account['issuer']

        # 投資家名簿用個人情報コントラクト（PersonalInfo）
        personal_info = shared_contract['PersonalInfo']
        config.PERSONAL_INFO_CONTRACT_ADDRESS = personal_info['address']

        # データ準備：情報登録
        register_personalinfo(trader, personal_info)

        # 検索用クエリ
        query_string = 'account_address=' + trader['account_address'] + \
            '&owner_address=' + issuer['account_address']

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = {
            'account_address': trader['account_address'],
            'owner_address': issuer['account_address'],
            'registered': True
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2＞
    # 通常参照（登録なし）
    def test_personalinfo_normal_2(self, client, shared_contract):
        # テスト用アカウント（traderは任意のアドレス）
        trader = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        issuer = eth_account['issuer']['account_address']

        # 投資家名簿用個人情報コントラクト（PersonalInfo）
        personal_info = shared_contract['PersonalInfo']
        config.PERSONAL_INFO_CONTRACT_ADDRESS = personal_info['address']

        # 検索用クエリ
        query_string = 'account_address=' + trader + \
            '&owner_address=' + issuer

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = {
            'account_address': trader,
            'owner_address': issuer,
            'registered': False
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー
    def test_personalinfo_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /v2/User/PersonalInfo'
        }

    # ＜エラー系2-1＞
    # 入力エラー
    # account_addressが未設定
    def test_personalinfo_error_2_1(self, client):
        # テスト用アカウント
        issuer = eth_account['issuer']

        query_string = 'owner_address=' + issuer['account_address']

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'account_address':
                ['null value not allowed', 'must be of string type']
            }
        }

    # ＜エラー系2-2＞
    # 入力エラー
    # account_addressのアドレスフォーマットが正しくない
    def test_personalinfo_error_2_2(self, client):
        # テスト用アカウント
        trader = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9"  # アドレスが短い
        issuer = eth_account['issuer']

        query_string = 'account_address=' + trader + \
            '&owner_address=' + issuer['account_address']

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜エラー系3-1＞
    # 入力エラー
    # owner_addressが未設定
    def test_personalinfo_error_3_1(self, client):
        # テスト用アカウント
        trader = eth_account['trader']['account_address']

        query_string = 'account_address=' + trader

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'owner_address':
                ['null value not allowed', 'must be of string type']
            }
        }

    # ＜エラー系3-2＞
    # owner_addressのアドレスフォーマットが正しくない
    def test_personalinfo_error_3_2(self, client):
        # テスト用アカウント
        trader = eth_account['trader']['account_address']
        issuer = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9"  # アドレスが短い

        query_string = 'account_address=' + trader + \
            '&owner_address=' + issuer

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }
