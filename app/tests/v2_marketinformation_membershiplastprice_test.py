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

import json

from .account_config import eth_account
from app import config
from .contract_modules import membership_issue, membership_offer, \
    membership_get_latest_orderid, membership_take_buy, membership_get_latest_agreementid, membership_confirm_agreement


class TestV2MembershipLastPrice:
    """
    Test Case for v2.market_information.MembershipLastPrice
    """

    # テスト対象API
    apiurl = '/v2/Market/LastPrice/Membership'

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
        latest_orderid = membership_get_latest_orderid(exchange)
        membership_take_buy(trader, exchange, latest_orderid, 100)

        # 決済業者オペレーション
        latest_agreementid = membership_get_latest_agreementid(exchange, latest_orderid)
        membership_confirm_agreement(agent, exchange, latest_orderid, latest_agreementid)

        return token

    # 正常系1：存在しない取引コントラクトアドレスを指定
    #  -> 現在値：0円
    def test_membership_lastprice_normal_1(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token_address': '0xe883a6f441ad5682d37df31d34fc012bcb07a740',
            'last_price': 0
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系2：約定が発生していないトークンアドレスを指定した場合
    #  -> 現在値：0円
    def test_membership_lastprice_normal_2(self, client, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = \
            exchange['address']

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token_address': '0xe883a6f441ad5682d37df31d34fc012bcb07a740',
            'last_price': 0
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系3：1000円で約定
    #  -> 現在値1000円が返却される
    def test_membership_lastprice_normal_3(self, client, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token = TestV2MembershipLastPrice.generate_agree_event(exchange)
        token_address = token['address']
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = \
            exchange['address']

        request_params = {"address_list": [token_address]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token_address': token_address,
            'last_price': 1000
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # エラー系1：入力値エラー（request-bodyなし）
    def test_membership_lastprice_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'address_list': 'required field'
            }
        }

    # エラー系2：入力値エラー（headersなし）
    def test_membership_lastprice_error_2(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3：入力値エラー（token_addressがアドレスフォーマットではない）
    def test_membership_lastprice_error_3(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a74"  # アドレス長が短い
        request_params = {"address_list": [token_address]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系4：HTTPメソッドが不正
    def test_membership_lastprice_error_4(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v2/Market/LastPrice/Membership'
        }
