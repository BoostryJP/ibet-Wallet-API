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
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import config
from app.model.db import IDXAgreement as Agreement, IDXOrder as Order


class TestDEXMarketCouponTick:
    # テスト対象API
    apiurl = "/DEX/Market/Tick/Coupon"

    def _insert_test_data(self, session):
        self.session = session

        # Order Record
        o = Order()
        o.exchange_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        o.token_address = "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a"
        o.order_id = 1
        o.unique_order_id = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb" + "_" + str(1)
        o.counterpart_address = ""
        o.price = 70
        o.amount = 5
        o.is_buy = True
        o.is_cancelled = False
        session.add(o)

        o = Order()
        o.exchange_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        o.token_address = "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a"
        o.order_id = 2
        o.unique_order_id = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb" + "_" + str(2)
        o.counterpart_address = ""
        o.price = 80
        o.amount = 5
        o.is_buy = True
        o.is_cancelled = False
        session.add(o)

        # Agreement Record
        a = Agreement()
        a.order_id = 1
        a.agreement_id = 101
        a.exchange_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        a.unique_order_id = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb" + "_" + str(1)
        a.buyer_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        a.seller_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        a.amount = 3
        a.status = 1
        a.settlement_timestamp = "2019-11-13 16:23:14.183706"
        a.created = "2019-11-13 16:26:14.183706"
        session.add(a)

        a = Agreement()
        a.order_id = 2
        a.agreement_id = 102
        a.exchange_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        a.unique_order_id = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb" + "_" + str(2)
        a.buyer_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        a.seller_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        a.amount = 3
        a.status = 1
        a.settlement_timestamp = "2019-11-13 16:24:14.183706"
        a.created = "2019-11-13 16:26:14.183706"
        session.add(a)

        # Order Record (other exchange)
        o = Order()
        o.exchange_address = "0x1234567890123456789012345678901234567890"
        o.token_address = "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a"
        o.order_id = 1
        o.unique_order_id = "0x1234567890123456789012345678901234567890" + "_" + str(1)
        o.counterpart_address = ""
        o.price = 70
        o.amount = 5
        o.is_buy = True
        o.is_cancelled = False
        session.add(o)

    ###########################################################################
    # Normal
    ###########################################################################

    # 正常系1：存在しない取引コントラクトアドレスを指定
    #  -> ゼロ件リストが返却される
    def test_normal_1(self, client: TestClient, session: Session):
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = (
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        )

        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = [{"token_address": token_address, "tick": []}]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # 正常系2：約定イベントが有件の場合
    #  -> 約定イベントの情報が返却される
    def test_normal_2(self, client: TestClient, session: Session):
        self._insert_test_data(session)

        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = (
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        )

        request_params = {
            "address_list": ["0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a"]
        }
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "token_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
                "tick": [
                    {
                        "block_timestamp": "2019/11/13 16:24:14",
                        "buy_address": "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb",
                        "sell_address": "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb",
                        "order_id": 2,
                        "agreement_id": 102,
                        "price": 80,
                        "amount": 3,
                    },
                    {
                        "block_timestamp": "2019/11/13 16:23:14",
                        "buy_address": "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb",
                        "sell_address": "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb",
                        "order_id": 1,
                        "agreement_id": 101,
                        "price": 70,
                        "amount": 3,
                    },
                ],
            }
        ]

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # field required
    # Invalid Parameter
    def test_error_1(self, client: TestClient, session: Session):
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = (
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        )

        resp = client.get(self.apiurl, params={})

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "loc": ["query", "address_list"],
                    "msg": "field required",
                    "type": "value_error.missing",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_2
    # token_address is not a valid address
    # Invalid Parameter
    def test_error_2(self, client: TestClient, session: Session):
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = (
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        )

        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a74"  # アドレス長が短い
        request_params = {"address_list": [token_address]}
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "loc": ["address_list"],
                    "msg": "address_list has not a valid address",
                    "type": "value_error",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_3
    # Method Not Allowed
    def test_error_3(self, client: TestClient, session: Session):
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = (
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        )

        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}
        resp = client.post(self.apiurl, params=request_params)

        assert resp.status_code == 405
        assert resp.json()["meta"] == {
            "code": 1,
            "message": "Method Not Allowed",
            "description": "method: POST, url: /DEX/Market/Tick/Coupon",
        }

    # Error_4_1
    # Coupon token is not enabled
    def test_error_4_1(self, client: TestClient, session: Session):
        config.COUPON_TOKEN_ENABLED = False
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = (
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        )

        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /DEX/Market/Tick/Coupon",
        }

    # Error_4_2
    # Exchange address is not set
    def test_error_4_2(self, client: TestClient, session: Session):
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = None

        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /DEX/Market/Tick/Coupon",
        }
