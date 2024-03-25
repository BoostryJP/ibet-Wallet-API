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


class TestContractABI:
    # テスト対象API
    apiurl_base = "/ABI"

    # ＜正常系1＞
    #   普通債券ABI取得
    def test_straightbondabi_normal(
        self, client: TestClient, session: Session, shared_contract
    ):
        config.BOND_TOKEN_ENABLED = True
        apiurl = self.apiurl_base + "/StraightBond"
        resp = client.get(apiurl, params={})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] is not None

    # ＜正常系2＞
    #   株式ABI取得
    def test_shareabi_normal(
        self, client: TestClient, session: Session, shared_contract
    ):
        config.SHARE_TOKEN_ENABLED = True
        apiurl = self.apiurl_base + "/Share"
        resp = client.get(apiurl, params={})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] is not None

    # ＜正常系3＞
    #   会員権ABI取得
    def test_membershipabi_normal(
        self, client: TestClient, session: Session, shared_contract
    ):
        config.MEMBERSHIP_TOKEN_ENABLED = True
        apiurl = self.apiurl_base + "/Membership"
        resp = client.get(apiurl, params={})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] is not None

    # ＜正常系4＞
    #   クーポンABI取得
    def test_couponabi_normal(
        self, client: TestClient, session: Session, shared_contract
    ):
        config.COUPON_TOKEN_ENABLED = True
        apiurl = self.apiurl_base + "/Coupon"
        resp = client.get(apiurl, params={})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] is not None

    # ＜異常系1＞
    #   存在しないABI
    def test_error_1(self, client: TestClient, session: Session, shared_contract):
        apiurl = self.apiurl_base + "/Unknown"
        resp = client.get(apiurl, params={})

        assert resp.status_code == 404

    # ＜異常系2＞
    #   普通債券ABI ENABLED=false
    def test_error_2(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = False
        apiurl = self.apiurl_base + "/StraightBond"
        resp = client.get(apiurl, params={})

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /ABI/StraightBond",
        }

    # ＜異常系3＞
    #   株式ABI ENABLED=false
    def test_error_3(self, client: TestClient, session: Session, shared_contract):
        config.SHARE_TOKEN_ENABLED = False
        apiurl = self.apiurl_base + "/Share"
        resp = client.get(apiurl, params={})

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /ABI/Share",
        }

    # ＜異常系4＞
    #   会員権ABI ENABLED=false
    def test_error_4(self, client: TestClient, session: Session, shared_contract):
        config.MEMBERSHIP_TOKEN_ENABLED = False
        apiurl = self.apiurl_base + "/Membership"
        resp = client.get(apiurl, params={})

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /ABI/Membership",
        }

    # ＜異常系5＞
    #   クーポンABI ENABLED=false
    def test_error_5(self, client: TestClient, session: Session, shared_contract):
        config.COUPON_TOKEN_ENABLED = False
        apiurl = self.apiurl_base + "/Coupon"
        resp = client.get(apiurl, params={})

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /ABI/Coupon",
        }
