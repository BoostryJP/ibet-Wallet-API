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
from tests.account_config import eth_account
from tests.contract_modules import register_personalinfo


class TestUserInfoPersonalInfo:
    # Target API
    apiurl = "/User/PersonalInfo"

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1_1
    # Registered
    # environment variable (default)
    def test_normal_1_1(self, client: TestClient, session: Session, shared_contract):
        trader = eth_account["trader"]["account_address"]
        issuer = eth_account["issuer"]["account_address"]

        # Get PersonalInfo contract address
        personal_info = shared_contract["PersonalInfo"]
        config.PERSONAL_INFO_CONTRACT_ADDRESS = personal_info["address"]

        # Prepare data
        register_personalinfo(eth_account["trader"], personal_info)

        # Request target API
        query_string = f"account_address={trader}&owner_address={issuer}"
        resp = client.get(self.apiurl, params=query_string)

        # Assertion
        assumed_body = {
            "account_address": trader,
            "owner_address": issuer,
            "registered": True,
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_1_2
    # Registered
    # query parameter
    def test_normal_1_2(self, client: TestClient, session: Session, shared_contract):
        trader = eth_account["trader"]["account_address"]
        issuer = eth_account["issuer"]["account_address"]

        # Get PersonalInfo contract address
        personal_info = shared_contract["PersonalInfo"]
        _personal_info_address = personal_info["address"]

        # Prepare data
        register_personalinfo(eth_account["trader"], personal_info)

        # Request target API
        query_string = (
            f"account_address={trader}&"
            f"owner_address={issuer}&"
            f"personal_info_address{_personal_info_address}"
        )
        resp = client.get(self.apiurl, params=query_string)

        # Assertion
        assumed_body = {
            "account_address": trader,
            "owner_address": issuer,
            "registered": True,
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_2
    # Not registered
    def test_normal_2(self, client: TestClient, session: Session, shared_contract):
        trader = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        issuer = eth_account["issuer"]["account_address"]

        # Get PersonalInfo contract address
        personal_info = shared_contract["PersonalInfo"]
        config.PERSONAL_INFO_CONTRACT_ADDRESS = personal_info["address"]

        # Request target API
        query_string = f"account_address={trader}&owner_address={issuer}"
        resp = client.get(self.apiurl, params=query_string)

        # Assertion
        assumed_body = {
            "account_address": trader,
            "owner_address": issuer,
            "registered": False,
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # Unsupported HTTP method
    # 404: Not Supported
    def test_error_1(self, client: TestClient, session: Session):
        headers = {"Content-Type": "application/json"}

        # Request target API
        resp = client.post(self.apiurl, headers=headers, json={})

        # Assertion
        assert resp.status_code == 405
        assert resp.json()["meta"] == {
            "code": 1,
            "message": "Method Not Allowed",
            "description": "method: POST, url: /User/PersonalInfo",
        }

    # Error_2_1
    # Invalid parameter: null value
    # 400
    def test_error_2_1(self, client: TestClient, session: Session):
        # Request target API
        query_string = ""
        resp = client.get(self.apiurl, params=query_string)

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": {},
                    "loc": ["query", "account_address"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": {},
                    "loc": ["query", "owner_address"],
                    "msg": "Field required",
                    "type": "missing",
                },
            ],
            "message": "Invalid Parameter",
        }

    # Error_2_2
    # Invalid parameter: invalid account address
    def test_error_2_2(self, client: TestClient, session: Session):
        trader = eth_account["issuer"]["account_address"][:-1]  # short address
        issuer = eth_account["issuer"]["account_address"]

        # Request target API
        query_string = f"account_address={trader}&owner_address={issuer}"
        resp = client.get(self.apiurl, params=query_string)

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["query", "account_address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": trader,
                    "ctx": {"error": {}},
                }
            ],
        }

    # Error_2_3
    # Invalid parameter: invalid owner address
    def test_error_2_3(self, client: TestClient, session: Session):
        trader = eth_account["trader"]["account_address"]
        issuer = eth_account["issuer"]["account_address"][:-1]  # short address

        # Request target API
        query_string = f"account_address={trader}&owner_address={issuer}"
        resp = client.get(self.apiurl, params=query_string)

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["query", "owner_address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": issuer,
                    "ctx": {"error": {}},
                }
            ],
        }
