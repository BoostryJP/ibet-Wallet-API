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

from tests.account_config import eth_account
from app import config
from tests.contract_modules import (
    membership_issue,
    membership_offer,
    get_latest_orderid,
    take_buy,
    get_latest_agreementid,
    confirm_agreement
)


class TestDEXMarketMembershipLastPrice:
    # テスト対象API
    apiurl = '/DEX/Market/LastPrice/Membership'

    # 約定イベントの作成
    @staticmethod
    def generate_agree_event(exchange):
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

        # 発行体オペレーション
        token = membership_issue(issuer, attribute)
        membership_offer(issuer, exchange, token, 1000000, 1000)

        # 投資家オペレーション
        latest_orderid = get_latest_orderid(exchange)
        take_buy(trader, exchange, latest_orderid, 100)

        # 決済業者オペレーション
        latest_agreementid = get_latest_agreementid(exchange, latest_orderid)
        confirm_agreement(agent, exchange, latest_orderid, latest_agreementid)

        return token

    # 正常系1：存在しない取引コントラクトアドレスを指定
    #  -> 現在値：0円
    def test_membership_lastprice_normal_1(self, client: TestClient, session: Session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client. \
            post(self.apiurl, headers=headers, data=request_body)

        assumed_body = [{
            'token_address': '0xe883a6f441ad5682d37df31d34fc012bcb07a740',
            'last_price': 0
        }]

        assert resp.status_code == 200
        assert resp.json()['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json()['data'] == assumed_body

    # 正常系2：約定が発生していないトークンアドレスを指定した場合
    #  -> 現在値：0円
    def test_membership_lastprice_normal_2(self, client: TestClient, session: Session, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = \
            exchange['address']

        resp = client. \
            post(self.apiurl, headers=headers, data=request_body)

        assumed_body = [{
            'token_address': '0xe883a6f441ad5682d37df31d34fc012bcb07a740',
            'last_price': 0
        }]

        assert resp.status_code == 200
        assert resp.json()['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json()['data'] == assumed_body

    # 正常系3：1000円で約定
    #  -> 現在値1000円が返却される
    def test_membership_lastprice_normal_3(self, client: TestClient, session: Session, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token = TestDEXMarketMembershipLastPrice.generate_agree_event(exchange)
        token_address = token['address']
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = \
            exchange['address']

        request_params = {"address_list": [token_address]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl, headers=headers, data=request_body)

        assumed_body = [{
            'token_address': token_address,
            'last_price': 1000
        }]

        assert resp.status_code == 200
        assert resp.json()['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json()['data'] == assumed_body

    # エラー系1：入力値エラー（request-bodyなし）
    def test_membership_lastprice_error_1(self, client: TestClient, session: Session):
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.post(
            self.apiurl, headers=headers, data=request_body)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "loc": ["body", "address_list"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ],
            "message": "Invalid Parameter"
        }

    # エラー系2：入力値エラー（headers Content-Type不正）
    def test_membership_lastprice_error_2(self, client: TestClient, session: Session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        headers: dict = {"Content-Type": "invalid type"}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl, headers=headers, data=request_body)

        assert resp.status_code == 400
        assert resp.json()['meta'] == {
            'code': 88,
            'description': [
                {
                    'loc': ['body'],
                    'msg': 'value is not a valid dict',
                    'type': 'type_error.dict'
                }
            ],
            'message': 'Invalid Parameter'
        }

    # エラー系3：入力値エラー（token_addressがアドレスフォーマットではない）
    def test_membership_lastprice_error_3(self, client: TestClient, session: Session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a74"  # アドレス長が短い
        request_params = {"address_list": [token_address]}

        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        headers: dict = {}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl, headers=headers, data=request_body)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "loc": ["body", "address_list"],
                    "msg": "address_list has not a valid address",
                    "type": "value_error"
                }
            ],
            "message": "Invalid Parameter"
        }

    # エラー系4：HTTPメソッドが不正
    def test_membership_lastprice_error_4(self, client: TestClient, session: Session):
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client.get(self.apiurl)

        assert resp.status_code == 405
        assert resp.json()['meta'] == {
            'code': 1,
            'message': 'Method Not Allowed',
            'description': 'method: GET, url: /DEX/Market/LastPrice/Membership'
        }

    # エラー系5：取扱トークン対象外
    def test_membership_lastprice_error_5(self, client: TestClient, session: Session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}
        request_body = json.dumps(request_params)

        config.MEMBERSHIP_TOKEN_ENABLED = False
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client.post(self.apiurl, data=request_body)

        assert resp.status_code == 404
        assert resp.json()['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /DEX/Market/LastPrice/Membership'
        }

    # エラー系6：exchangeアドレス未設定
    def test_membership_lastprice_error_6(self, client: TestClient, session: Session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}
        request_body = json.dumps(request_params)

        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = None

        resp = client.post(self.apiurl, data=request_body)

        assert resp.status_code == 404
        assert resp.json()['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /DEX/Market/LastPrice/Membership'
        }
