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

from app.model.node import Node


def insert_node_data(session, is_synced):
    node = Node()
    node.is_synced = is_synced
    session.add(node)


class TestEthSendRawTransaction():
    # テスト対象API
    apiurl = '/v2/Eth/SendRawTransaction/'

    # ＜正常系1＞
    # 入力リストが空
    def test_sendraw_normal_1(self, client, session):
        insert_node_data(session, is_synced=True)

        request_params = {"raw_tx_hex_list": []}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー（Not Supported）
    def test_sendraw_error_1(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v2/Eth/SendRawTransaction'
        }

    # ＜エラー系2＞
    # headersなし
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_2(self, client):
        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": raw_tx_1}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜エラー系3＞
    # 入力値なし
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_3(self, client):
        request_params = {}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'raw_tx_hex_list': 'required field'
            }
        }

    # ＜エラー系4＞
    # 入力値が正しくない（リストではない）
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_4(self, client):
        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": raw_tx_1}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'raw_tx_hex_list': 'must be of list type'
            }
        }

    # ＜エラー系5＞
    # 入力値が正しくない（String型ではない）
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_5(self, client):
        raw_tx_1 = 1234
        request_params = {"raw_tx_hex_list": [raw_tx_1]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'raw_tx_hex_list': {
                    '0': 'must be of string type'
                }
            }
        }

    # ＜エラー系6：ステータスコードは200＞
    # 入力値が正しくない（rawtransactionではない）
    # -> status = 0
    def test_sendraw_error_6(self, client, session):
        insert_node_data(session, is_synced=True)

        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": [raw_tx_1]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == [{'id': 1, 'status': 0}]

    # ＜エラー系7＞
    # ブロック同期停止中
    def test_sendraw_error_7(self, client, session):
        insert_node_data(session, is_synced=False)

        raw_tx_1 = 'raw_tx_1'
        request_params = {'raw_tx_hex_list': [raw_tx_1]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)
        assert resp.status_code == 503
        assert resp.json['meta'] == {
            'code': 503,
            'message': 'Service Unavailable',
            'description': 'Block synchronization has stopped',
        }


# sendRawTransaction API (No Wait)
# /v2/Eth/SendRawTransactionNoWait
class TestEthSendRawTransactionNoWait():
    # テスト対象API
    apiurl = '/v2/Eth/SendRawTransactionNoWait/'

    # ＜正常系1＞
    # 入力リストが空
    def test_sendraw_normal_1(self, client, session):
        insert_node_data(session, is_synced=True)

        request_params = {"raw_tx_hex_list": []}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー（Not Supported）
    def test_sendraw_error_1(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v2/Eth/SendRawTransactionNoWait'
        }

    # ＜エラー系2＞
    # headersなし
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_2(self, client):
        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": raw_tx_1}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜エラー系3＞
    # 入力値なし
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_3(self, client):
        request_params = {}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'raw_tx_hex_list': 'required field'
            }
        }

    # ＜エラー系4＞
    # 入力値が正しくない（リストではない）
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_4(self, client):
        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": raw_tx_1}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'raw_tx_hex_list': 'must be of list type'
            }
        }

    # ＜エラー系5＞
    # 入力値が正しくない（String型ではない）
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_5(self, client):
        raw_tx_1 = 1234
        request_params = {"raw_tx_hex_list": [raw_tx_1]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'raw_tx_hex_list': {
                    '0': 'must be of string type'
                }
            }
        }

    # ＜エラー系6：ステータスコードは200＞
    # 入力値が正しくない（rawtransactionではない）
    # -> status = 0
    def test_sendraw_error_6(self, client, session):
        insert_node_data(session, is_synced=True)

        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": [raw_tx_1]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == [{'id': 1, 'status': 0}]

    # ＜エラー系7＞
    # ブロック同期停止中
    def test_sendraw_error_7(self, client, session):
        insert_node_data(session, is_synced=False)

        raw_tx_1 = 'raw_tx_1'
        request_params = {'raw_tx_hex_list': [raw_tx_1]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)
        assert resp.status_code == 503
        assert resp.json['meta'] == {
            'code': 503,
            'message': 'Service Unavailable',
            'description': 'Block synchronization has stopped',
        }
