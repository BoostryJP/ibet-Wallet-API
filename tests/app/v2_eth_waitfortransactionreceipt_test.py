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


class TestEthWaitForTransactionReceipt:

    # テスト対象API
    apiurl = '/v2/Eth/WaitForTransactionReceipt/'

    ###################################################################
    # Error
    ###################################################################

    # Error_1
    # timeout設定なし（デフォルト採用）
    # -> 404エラー（Data not exists）
    def test_error_1(self, client, session):
        request_params = {
            "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455"
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl,
            headers=headers,
            body=request_body
        )

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 30,
            'message': 'Data Not Exists'
        }

    # Error_2
    # timeout設定あり
    # -> 404エラー（Data not exists）
    def test_error_2(self, client, session):
        request_params = {
            "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455",
            "timeout": 1
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl,
            headers=headers,
            body=request_body
        )

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 30,
            'message': 'Data Not Exists'
        }

    # Error_3
    # HTTPメソッド不正
    # -> 404エラー（Not Supported）
    def test_error_3(self, client, session):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v2/Eth/WaitForTransactionReceipt'
        }

    # Error_4
    # headersなし
    # -> 400エラー（InvalidParameterError）
    def test_error_4(self, client, session):
        request_params = {
            "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455"
        }
        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # Error_5_1
    # 入力エラー（timeout最小値）
    # -> 400エラー
    def test_error_5_1(self, client, session):
        request_params = {
            "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455",
            "timeout": 0
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl,
            headers=headers,
            body=request_body
        )

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'timeout': ['min value is 1']}
        }

    # Error_5_2
    # 入力エラー（timeout最大値）
    # -> 400エラー
    def test_error_5_2(self, client, session):
        request_params = {
            "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455",
            "timeout": 31
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl,
            headers=headers,
            body=request_body
        )

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'timeout': ['max value is 30']}
        }

    # Error_6_1
    # 入力型エラー（transaction_hash）
    # -> 400エラー
    def test_error_6_1(self, client, session):
        request_params = {
            "transaction_hash": 1234,
            "timeout": 1
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl,
            headers=headers,
            body=request_body
        )

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'transaction_hash': ['must be of string type']}
        }

    # Error_6_2
    # 入力型エラー（timeout）
    # -> 400エラー
    def test_error_6_2(self, client, session):
        request_params = {
            "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455",
            "timeout": "aaaa"
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl,
            headers=headers,
            body=request_body
        )

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'timeout': ['must be of integer type']}
        }
