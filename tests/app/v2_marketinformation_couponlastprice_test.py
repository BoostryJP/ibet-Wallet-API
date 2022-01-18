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

from tests.account_config import eth_account
from app import config
from tests.contract_modules import (
issue_coupon_token,
coupon_offer,
get_latest_orderid,
take_buy,
get_latest_agreementid,
confirm_agreement
)


class TestV2CouponLastPrice:
    """
    Test Case for v2.market_information.CouponLastPrice
    """

    # テスト対象API
    apiurl = '/v2/Market/LastPrice/Coupon'

    # 約定イベントの作成
    @staticmethod
    def generate_agree_event(exchange):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 10000,
            'tradableExchange': exchange['address'],
            'details': 'クーポン詳細',
            'returnDetails': 'リターン詳細',
            'memo': 'クーポンメモ欄',
            'expirationDate': '20191231',
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
        }

        # 発行体オペレーション
        token = issue_coupon_token(issuer, attribute)
        coupon_offer(issuer, exchange, token, 10000, 1000)

        # 投資家オペレーション
        latest_orderid = get_latest_orderid(exchange)
        take_buy(trader, exchange, latest_orderid, 100)

        # 決済業者オペレーション
        latest_agreementid = get_latest_agreementid(exchange, latest_orderid)
        confirm_agreement(agent, exchange, latest_orderid, latest_agreementid)

        return token

    # 正常系1：存在しない取引コントラクトアドレスを指定
    #  -> 現在値：0円
    def test_coupon_lastprice_normal_1(self, client, session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.COUPON_TOKEN_ENABLED = True
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
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
    def test_coupon_lastprice_normal_2(self, client, session, shared_contract):
        exchange = shared_contract['IbetCouponExchange']
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.COUPON_TOKEN_ENABLED = True
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
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
    def test_coupon_lastprice_normal_3(self, client, session, shared_contract):
        exchange = shared_contract['IbetCouponExchange']
        token = TestV2CouponLastPrice.generate_agree_event(exchange)
        token_address = token['address']
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
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
    def test_coupon_lastprice_error_1(self, client, session):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        config.COUPON_TOKEN_ENABLED = True
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'address_list': ['required field']
            }
        }

    # エラー系2：入力値エラー（headersなし）
    def test_coupon_lastprice_error_2(self, client, session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        config.COUPON_TOKEN_ENABLED = True
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

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
    def test_coupon_lastprice_error_3(self, client, session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a74"  # アドレス長が短い
        request_params = {"address_list": [token_address]}

        config.COUPON_TOKEN_ENABLED = True
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

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
    def test_coupon_lastprice_error_4(self, client, session):

        config.COUPON_TOKEN_ENABLED = True
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v2/Market/LastPrice/Coupon'
        }

    # エラー系5：取扱トークン対象外
    def test_coupon_lastprice_error_5(self, client, session):

        config.COUPON_TOKEN_ENABLED = False
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client.simulate_post(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /v2/Market/LastPrice/Coupon'
        }

    # エラー系6：exchangeアドレス未設定
    def test_coupon_lastprice_error_6(self, client, session):

        config.COUPON_TOKEN_ENABLED = True
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = None

        resp = client.simulate_post(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /v2/Market/LastPrice/Coupon'
        }
