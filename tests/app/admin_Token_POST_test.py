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
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.model.db import (
    Listing,
    ExecutableContract
)


class TestAdminTokenPOST:
    # テスト対象API
    apiurl_base = "/Admin/Tokens/"

    default_token = {
        "token_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
        "is_public": True,
        "max_holding_quantity": 100,
        "max_sell_amount": 50000,
        "owner_address": "0x56f63dc2351BeC560a422f0C646d64Ca718e11D6"
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

        request_params = {
            "is_public": False,
            "max_holding_quantity": 200,
            "max_sell_amount": 25000,
            "owner_address": "0x34C987DDe783EfbFe1E573727165E6c15D660590"
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + str(token["token_address"])
        resp = client.post(apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 200
        assert resp.json() == {"data": {}, "meta": {"code": 200, "message": "OK"}}

        listing: Listing = session.query(Listing). \
            filter(Listing.token_address == token["token_address"]). \
            first()
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
            "owner_address": "0x34C987DDe783EfbFe1E573727165E6c15D660590"
        }
        headers = {"Content-Type": "invalid_type"}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + str(self.default_token["token_address"])
        resp = client.post(apiurl, headers=headers, json=json.loads(request_body))
        assert resp.status_code == 400
        assert resp.json() == {
            'meta': {
                'code': 1,
                'description': [
                    {
                        'loc': ['body'],
                        'msg': 'value is not a valid dict',
                        'type': 'type_error.dict'
                    }
                ],
                'message': 'Request Validation Error'
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
            "owner_address": "0x34C987DDe783EfbFe1E573727165E6c15D66059"  # アドレスが短い
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + str(self.default_token["token_address"])
        resp = client.post(apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "description": [
                    {
                        "loc": ["body", "owner_address"],
                        "msg": "owner_address is not a valid address",
                        "type": "value_error"
                    }
                ],
                "message": "Request Validation Error"
            }
        }

    # ＜Error_2_2＞
    # 入力値の型誤り
    # 400（InvalidParameterError）
    def test_error_2_2(self, client: TestClient, session: Session):
        request_params = {
            "is_public": "False",
            "max_holding_quantity": "200",
            "max_sell_amount": "25000",
            "owner_address": 1234
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + str(self.default_token["token_address"])
        resp = client.post(apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "description": [
                    {
                        "loc": ["body", "owner_address"],
                        "msg": "owner_address is not a valid address",
                        "type": "value_error"
                    }
                ],
                "message": "Request Validation Error"
            }
        }

    # ＜Error_2_3＞
    # 最小値チェック
    # 400（InvalidParameterError）
    def test_error_2_3(self, client: TestClient, session: Session):
        request_params = {
            "is_public": False,
            "max_holding_quantity": -1,
            "max_sell_amount": -1,
            "owner_address": "0x34C987DDe783EfbFe1E573727165E6c15D660590"
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + str(self.default_token["token_address"])
        resp = client.post(apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "description": [
                    {
                        "ctx": {"limit_value": 0},
                        "loc": ["body", "max_holding_quantity"],
                        "msg": "ensure this value is greater than or equal to 0",
                        "type": "value_error.number.not_ge"
                    },
                    {
                        "ctx": {"limit_value": 0},
                        "loc": ["body", "max_sell_amount"],
                        "msg": "ensure this value is greater than or equal to 0",
                        "type": "value_error.number.not_ge"
                    }
                ],
                "message": "Request Validation Error"
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
            "owner_address": "0x34C987DDe783EfbFe1E573727165E6c15D660590"
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + str(self.default_token["token_address"])
        resp = client.post(apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 30,
                "message": "Data Not Exists"
            }
        }