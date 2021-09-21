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
from app.model.db import (
    IDXOrder as Order,
    IDXAgreement as Agreement
)


class TestV2CouponTick:
    """
    Test Case for v2.market_information.CouponTick
    """

    # テスト対象API
    apiurl = '/v2/Market/Tick/Coupon'

    def _insert_test_data(self, session):
        self.session = session

        # Order Record
        o = Order()
        o.exchange_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        o.token_address = '0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a'
        o.order_id = 1
        o.unique_order_id = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb' + "_" + str(1)
        o.counterpart_address = ''
        o.price = 70
        o.amount = 5
        o.is_buy = True
        o.is_cancelled = False
        session.add(o)

        o = Order()
        o.exchange_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        o.token_address = '0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a'
        o.order_id = 2
        o.unique_order_id = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb' + "_" + str(2)
        o.counterpart_address = ''
        o.price = 80
        o.amount = 5
        o.is_buy = True
        o.is_cancelled = False
        session.add(o)

        # Agreement Record
        a = Agreement()
        a.order_id = 1
        a.agreement_id = 101
        a.exchange_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.unique_order_id = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb' + "_" + str(1)
        a.buyer_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.seller_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.amount = 3
        a.status = 1
        a.settlement_timestamp = '2019-11-13 16:23:14.183706'
        a.created = '2019-11-13 16:26:14.183706'
        session.add(a)

        a = Agreement()
        a.order_id = 2
        a.agreement_id = 102
        a.exchange_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.unique_order_id = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb' + "_" + str(2)
        a.buyer_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.seller_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.amount = 3
        a.status = 1
        a.settlement_timestamp = '2019-11-13 16:24:14.183706'
        a.created = '2019-11-13 16:26:14.183706'
        session.add(a)

        # Order Record (other exchange)
        o = Order()
        o.exchange_address = '0x1234567890123456789012345678901234567890'
        o.token_address = '0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a'
        o.order_id = 1
        o.unique_order_id = '0x1234567890123456789012345678901234567890' + "_" + str(1)
        o.counterpart_address = ''
        o.price = 70
        o.amount = 5
        o.is_buy = True
        o.is_cancelled = False
        session.add(o)

    # 正常系1：存在しない取引コントラクトアドレスを指定
    #  -> ゼロ件リストが返却される
    def test_coupon_tick_normal_1(self, client, session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.COUPON_TOKEN_ENABLED = True
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{'token_address': token_address, 'tick': []}]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系2：約定イベントが有件の場合
    #  -> 約定イベントの情報が返却される
    def test_coupon_tick_normal_2(self, client, session):
        self._insert_test_data(session)

        request_params = {"address_list": ["0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a"]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        config.COUPON_TOKEN_ENABLED = True
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == [
            {
                'token_address': '0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a',
                'tick': [
                    {
                        'block_timestamp': '2019/11/13 16:24:14',
                        'buy_address': '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb',
                        'sell_address': '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb',
                        'order_id': 2,
                        'agreement_id': 102,
                        'price': 80,
                        'amount': 3
                    },
                    {
                        'block_timestamp': '2019/11/13 16:23:14',
                        'buy_address': '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb',
                        'sell_address': '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb',
                        'order_id': 1,
                        'agreement_id': 101,
                        'price': 70,
                        'amount': 3
                    }
                ]
            }
        ]

    # エラー系1：入力値エラー（request-bodyなし）
    def test_coupon_tick_error_1(self, client, session):
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
            'description': {'address_list': 'required field'}
        }

    # エラー系2：入力値エラー（headersなし）
    def test_coupon_tick_error_2(self, client, session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {}
        request_body = json.dumps(request_params)

        config.COUPON_TOKEN_ENABLED = True
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3：入力値エラー（token_addressがアドレスフォーマットではない）
    def test_coupon_tick_error_3(self, client, session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a74"  # アドレス長が短い
        request_params = {"address_list": [token_address]}

        headers = {}
        request_body = json.dumps(request_params)

        config.COUPON_TOKEN_ENABLED = True
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系4：HTTPメソッドが不正
    def test_coupon_tick_error_4(self, client, session):

        config.COUPON_TOKEN_ENABLED = True
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v2/Market/Tick/Coupon'
        }

    # エラー系5：取扱トークン対象外
    def test_coupon_tick_error_5(self, client, session):

        config.COUPON_TOKEN_ENABLED = False
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client.simulate_post(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /v2/Market/Tick/Coupon'
        }

    # エラー系6：exchangeアドレス未設定
    def test_coupon_tick_error_6(self, client, session):

        config.COUPON_TOKEN_ENABLED = True
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = None

        resp = client.simulate_post(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /v2/Market/Tick/Coupon'
        }
