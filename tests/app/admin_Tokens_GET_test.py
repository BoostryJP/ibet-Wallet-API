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

from app.model.db import Listing


class TestAdminTokensGET:
    # テスト対象API
    apiurl = "/Admin/Tokens"

    @staticmethod
    def insert_listing_data(session, _token):
        token = Listing()
        token.token_address = _token["token_address"]
        token.is_public = _token["is_public"]
        token.max_holding_quantity = _token["max_holding_quantity"]
        token.max_sell_amount = _token["max_sell_amount"]
        token.owner_address = _token["owner_address"]
        session.add(token)

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # データ1件
    def test_normal_1(self, client: TestClient, session: Session):
        token = {
            "token_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
            "owner_address": "0x56f63dc2351BeC560a429f0C646d64Ca718e11D6",
        }
        self.insert_listing_data(session, token)

        resp = client.get(self.apiurl)

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        for i, resp_body in enumerate(reversed(resp.json()["data"])):
            assert resp_body["id"] == i + 1
            del resp_body["created"]
            del resp_body["id"]
            assert resp_body == token

    # <Normal_2>
    # データ複数件
    def test_normal_2(self, client: TestClient, session: Session):
        token = {
            "token_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
            "owner_address": "0x56f63dc2351BeC560a429f0C646d64Ca718e11D6",
        }
        self.insert_listing_data(session, token)
        self.insert_listing_data(session, token)

        resp = client.get(self.apiurl)

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        for i, resp_body in enumerate(reversed(resp.json()["data"])):
            assert resp_body["id"] == i + 1
            del resp_body["created"]
            del resp_body["id"]
            assert resp_body == token
