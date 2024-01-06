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
from app import config
from app.model.db import IDXConsumeCoupon


class TestListAllCouponConsumptions:
    # Test API
    apiurl = "/Position/{account_address}/Coupon/{token_address}/Consumptions/"

    def _insert_test_data(self, session):
        self.session = session
        consume_coupon = IDXConsumeCoupon()
        consume_coupon.transaction_hash = (
            "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455"
        )
        consume_coupon.token_address = "0xE0C95ECa44f2A1A23C4AfeA84dba62e15A35a69b"
        consume_coupon.account_address = "0x16f39D63d156f9abCe0a9aB46F751E2eFdEB040f"
        consume_coupon.amount = 100
        consume_coupon.block_timestamp = "2020-01-15 13:56:12.183706"
        session.add(consume_coupon)

    def _insert_test_data_2(self, session):
        self.session = session
        consume_coupon = IDXConsumeCoupon()
        consume_coupon.transaction_hash = (
            "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455"
        )
        consume_coupon.token_address = "0xE0C95ECa44f2A1A23C4AfeA84dba62e15A35a69b"
        consume_coupon.account_address = "0x28e0ad30c43b3d55851b881e25586926894de3e9"
        consume_coupon.amount = 100
        consume_coupon.block_timestamp = "2020-01-15 13:56:12.183705"
        session.add(consume_coupon)

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    # No record
    def test_normal_1(self, client, session):
        config.COUPON_TOKEN_ENABLED = True

        resp = client.get(
            self.apiurl.format(
                account_address="0x16f39D63d156f9abCe0a9aB46F751E2eFdEB040f",
                token_address="0x0000000000000000000000000000000000000000",
            )
        )

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == []

    # Normal_2
    # Multiple records
    def test_normal_2(self, client, session):
        config.COUPON_TOKEN_ENABLED = True

        # Prepare test data
        self._insert_test_data(session)

        session.commit()

        # Request target API
        resp = client.get(
            self.apiurl.format(
                account_address="0x16f39D63d156f9abCe0a9aB46F751E2eFdEB040f",
                token_address="0xE0C95ECa44f2A1A23C4AfeA84dba62e15A35a69b",
            )
        )

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == [
            {
                "account_address": "0x16f39D63d156f9abCe0a9aB46F751E2eFdEB040f",
                "block_timestamp": "2020/01/15 13:56:12",
                "value": 100,
            }
        ]

    ###########################################################################
    # Normal
    ###########################################################################

    # Error_1_1
    # Invalid token_address
    def test_error_1_1(self, client, session):
        config.COUPON_TOKEN_ENABLED = True

        resp = client.get(
            self.apiurl.format(
                account_address="0x16f39D63d156f9abCe0a9aB46F751E2eFdEB040f",
                token_address="0xeb6e99675595fb052cc68da0eeecb2d5a382637",  # short address
            )
        )

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["path", "token_address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": "0xeb6e99675595fb052cc68da0eeecb2d5a382637",
                    "ctx": {"error": {}},
                }
            ],
        }

    # Error_1_2
    # Invalid account_address
    def test_error_1_2(self, client, session):
        config.COUPON_TOKEN_ENABLED = True

        resp = client.get(
            self.apiurl.format(
                account_address="0x16f39D63d156f9abCe0a9aB46F751E2eFdEB040",  # short address
                token_address="0x0000000000000000000000000000000000000000",
            )
        )

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["path", "account_address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": "0x16f39D63d156f9abCe0a9aB46F751E2eFdEB040",
                    "ctx": {"error": {}},
                }
            ],
        }

    # Error_2
    # Not Supported Error
    def test_error_2(self, client, session):
        config.COUPON_TOKEN_ENABLED = False

        resp = client.get(
            self.apiurl.format(
                account_address="0x16f39D63d156f9abCe0a9aB46F751E2eFdEB040f",
                token_address="0x0000000000000000000000000000000000000000",
            )
        )

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /Position/0x16f39D63d156f9abCe0a9aB46F751E2eFdEB040f/Coupon/0x0000000000000000000000000000000000000000/Consumptions",
        }
