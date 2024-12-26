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
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.db import ExecutableContract, Listing


class TestAdminTokenPOST:
    # テスト対象API
    apiurl_base = "/Admin/Tokens/"

    default_token = {
        "token_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
        "is_public": True,
        "max_holding_quantity": 100,
        "max_sell_amount": 50000,
        "owner_address": "0x56f63dc2351BeC560a422f0C646d64Ca718e11D6",
    }

    @staticmethod
    def insert_listing_data(session: Session, _token):
        token = Listing()
        token.token_address = _token["token_address"]
        token.is_public = _token["is_public"]
        token.max_holding_quantity = _token["max_holding_quantity"]
        token.max_sell_amount = _token["max_sell_amount"]
        token.owner_address = _token["owner_address"]
        session.add(token)

    @staticmethod
    def insert_executable_contract_data(session: Session, _contract):
        contract = ExecutableContract()
        contract.contract_address = _contract["contract_address"]
        session.add(contract)

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client: TestClient, session: Session):
        token = self.default_token
        self.insert_listing_data(session, token)
        session.commit()

        request_params = {
            "is_public": False,
            "max_holding_quantity": 200,
            "max_sell_amount": 25000,
            "owner_address": "0x34C987DDe783EfbFe1E573727165E6c15D660590",
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + str(token["token_address"])
        resp = client.post(apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 200
        assert resp.json() == {"data": {}, "meta": {"code": 200, "message": "OK"}}

        listing = session.scalars(
            select(Listing)
            .where(Listing.token_address == token["token_address"])
            .limit(1)
        ).first()
        assert listing.token_address == token["token_address"]
        assert listing.is_public == request_params["is_public"]
        assert listing.max_holding_quantity == request_params["max_holding_quantity"]
        assert listing.max_sell_amount == request_params["max_sell_amount"]
        assert listing.owner_address == request_params["owner_address"]

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # headersなし
    # 400（InvalidParameterError）
    def test_error_1(self, client: TestClient, session: Session):
        request_params = {
            "is_public": False,
            "max_holding_quantity": 200,
            "max_sell_amount": 25000,
            "owner_address": "0x34C987DDe783EfbFe1E573727165E6c15D660590",
        }
        headers = {"Content-Type": "invalid_type"}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + str(self.default_token["token_address"])
        resp = client.post(apiurl, headers=headers, json=json.loads(request_body))
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 88,
                "description": [
                    {
                        "input": '{"is_public":false,"max_holding_quantity":200,"max_sell_amount":25000,"owner_address":"0x34C987DDe783EfbFe1E573727165E6c15D660590"}',
                        "loc": ["body"],
                        "msg": "Input should be a valid dictionary or "
                        "object to extract fields from",
                        "type": "model_attributes_type",
                    }
                ],
                "message": "Invalid Parameter",
            }
        }

    # ＜Error_2_1＞
    # owner_addressのフォーマット誤り
    # 400（InvalidParameterError）
    def test_error_2_1(self, client: TestClient, session: Session):
        request_params = {
            "is_public": False,
            "max_holding_quantity": 200,
            "max_sell_amount": 25000,
            "owner_address": "0x34C987DDe783EfbFe1E573727165E6c15D66059",  # アドレスが短い
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + str(self.default_token["token_address"])
        resp = client.post(apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["body", "owner_address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": "0x34C987DDe783EfbFe1E573727165E6c15D66059",
                    "ctx": {"error": {}},
                }
            ],
        }

    # ＜Error_2_2＞
    # 入力値の型誤り
    # 400（InvalidParameterError）
    def test_error_2_2(self, client: TestClient, session: Session):
        request_params = {
            "is_public": "Trueee",
            "max_holding_quantity": "aaaa",
            "max_sell_amount": "bbbb",
            "owner_address": "0x34C987DDe783EfbFe1E573727165E6c15D660590",
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + str(self.default_token["token_address"])
        resp = client.post(apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "bool_parsing",
                    "loc": ["body", "is_public"],
                    "msg": "Input should be a valid boolean, unable to interpret input",
                    "input": "Trueee",
                },
                {
                    "type": "int_parsing",
                    "loc": ["body", "max_holding_quantity"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "aaaa",
                },
                {
                    "type": "int_parsing",
                    "loc": ["body", "max_sell_amount"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "bbbb",
                },
            ],
        }

    # ＜Error_2_3＞
    # 最小値チェック
    # 400（InvalidParameterError）
    def test_error_2_3(self, client: TestClient, session: Session):
        request_params = {
            "is_public": False,
            "max_holding_quantity": -1,
            "max_sell_amount": -1,
            "owner_address": "0x34C987DDe783EfbFe1E573727165E6c15D660590",
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + str(self.default_token["token_address"])
        resp = client.post(apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 88,
                "description": [
                    {
                        "ctx": {"ge": 0},
                        "input": -1,
                        "loc": ["body", "max_holding_quantity"],
                        "msg": "Input should be greater than or equal to 0",
                        "type": "greater_than_equal",
                    },
                    {
                        "ctx": {"ge": 0},
                        "input": -1,
                        "loc": ["body", "max_sell_amount"],
                        "msg": "Input should be greater than or equal to 0",
                        "type": "greater_than_equal",
                    },
                ],
                "message": "Invalid Parameter",
            }
        }

    # <Error_3>
    # 更新対象のレコードが存在しない
    # 404
    def test_error_3(self, client: TestClient, session: Session):
        request_params = {
            "is_public": False,
            "max_holding_quantity": 200,
            "max_sell_amount": 25000,
            "owner_address": "0x34C987DDe783EfbFe1E573727165E6c15D660590",
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + str(self.default_token["token_address"])
        resp = client.post(apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 404
        assert resp.json() == {"meta": {"code": 30, "message": "Data Not Exists"}}
