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
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import config
from tests.account_config import eth_account
from tests.contract_modules import register_payment_gateway


class TestUserInfoPaymentAccount:

    # テスト対象API
    apiurl = '/User/PaymentAccount'

    # ＜正常系1＞
    # 通常参照（登録 -> 認可済）
    def test_paymentaccount_normal_1(self, client: TestClient, session: Session, shared_contract):
        # テスト用アカウント
        trader = eth_account['trader']
        agent = eth_account['agent']

        # 収納代行コントラクト（PaymentGateway）
        payment_gateway = shared_contract['PaymentGateway']
        config.PAYMENT_GATEWAY_CONTRACT_ADDRESS = payment_gateway['address']

        # データ準備：受領用銀行口座情報登録->認可
        register_payment_gateway(trader, payment_gateway)

        query_string = 'account_address=' + trader['account_address'] + \
            '&agent_address=' + agent['account_address']

        resp = client.get(self.apiurl, params=query_string)

        assumed_body = {
            'account_address': trader['account_address'],
            'agent_address': agent['account_address'],
            'approval_status': 2
        }

        assert resp.status_code == 200
        assert resp.json()['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json()['data'] == assumed_body

    # ＜正常系2＞
    # 通常参照（登録なし）
    def test_paymentaccount_normal_2(self, client: TestClient, session: Session, shared_contract):
        # テスト用アカウント（traderは任意のアドレス）
        trader = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent = eth_account['agent']

        # 収納代行コントラクト（PaymentGateway）
        payment_gateway = shared_contract['PaymentGateway']
        config.PAYMENT_GATEWAY_CONTRACT_ADDRESS = payment_gateway['address']

        query_string = 'account_address=' + trader + \
            '&agent_address=' + agent['account_address']

        resp = client.get(self.apiurl, params=query_string)

        assumed_body = {
            'account_address': trader,
            'agent_address': agent['account_address'],
            'approval_status': 0
        }

        assert resp.status_code == 200
        assert resp.json()['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json()['data'] == assumed_body

    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー
    def test_paymentaccount_error_1(self, client: TestClient, session: Session):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.post(
            self.apiurl, headers=headers, data=request_body)

        assert resp.status_code == 405
        assert resp.json()['meta'] == {
            'code': 1,
            'message': 'Method Not Allowed',
            'description': 'method: POST, url: /User/PaymentAccount'
        }

    # ＜エラー系2-1＞
    # 入力エラー
    # account_addressが未設定
    def test_paymentaccount_error_2_1(self, client: TestClient, session: Session):
        # テスト用アカウント
        agent = eth_account['agent']

        query_string = 'agent_address=' + agent['account_address']

        resp = client.get(self.apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()['meta'] == {
            "code": 1,
            "description": [
                {
                    "loc": ["query", "account_address"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ],
            "message": "Request Validation Error"
        }

    # ＜エラー系2-2＞
    # 入力エラー
    # account_addressのアドレスフォーマットが正しくない
    def test_paymentaccount_error_2_2(self, client: TestClient, session: Session):
        # テスト用アカウント
        trader = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9"  # アドレスが短い
        agent = eth_account['agent']

        query_string = 'account_address=' + trader + \
            '&agent_address=' + agent['account_address']

        resp = client.get(self.apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 1,
            "description": [
                {
                    "loc": ["query", "account_address"],
                    "msg": "account_address is not a valid address",
                    "type": "value_error"
                }
            ],
            "message": "Request Validation Error"
        }

    # ＜エラー系3-1＞
    # 入力エラー
    # agent_addressが未設定
    def test_paymentaccount_error_3_1(self, client: TestClient, session: Session):
        # テスト用アカウント
        trader = eth_account['trader']['account_address']

        query_string = 'account_address=' + trader

        resp = client.get(self.apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 1,
            "description": [
                {
                    "loc": ["query", "agent_address"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ],
            "message": "Request Validation Error"
        }

    # ＜エラー系3-2＞
    # agent_addressのアドレスフォーマットが正しくない
    def test_paymentaccount_error_3_2(self, client: TestClient, session: Session):
        # テスト用アカウント
        trader = eth_account['trader']['account_address']
        agent = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9"  # アドレスが短い

        query_string = 'account_address=' + trader + \
            '&agent_address=' + agent

        resp = client.get(self.apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 1,
            "description": [
                {
                    "loc": ["query", "agent_address"],
                    "msg": "agent_address is not a valid address",
                    "type": "value_error"
                }
            ],
            "message": "Request Validation Error"
        }
