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
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.db import AccountTag
from tests.account_config import eth_account


class TestTaggingAccountAddress:
    # テスト対象API
    api_url = "/User/Tag"

    # テストアカウント
    test_account = eth_account["user1"]

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # 新規データ登録
    def test_normal_1(self, client: TestClient, session: Session, shared_contract):
        # Call API
        request_params = {
            "account_address": self.test_account["account_address"],
            "account_tag": "test_tag",
        }
        resp = client.post(self.api_url, json=request_params)

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        account_tag_af = session.scalars(select(AccountTag).limit(1)).first()
        assert account_tag_af.account_address == self.test_account["account_address"]
        assert account_tag_af.account_tag == "test_tag"

    # <Normal_2_1>
    # 更新登録
    def test_normal_2_1(self, client: TestClient, session: Session, shared_contract):
        # Prepare data
        account_tag = AccountTag()
        account_tag.account_address = self.test_account["account_address"]
        account_tag.account_tag = "test_tag_bf"
        session.add(account_tag)
        session.commit()

        # Call API
        request_params = {
            "account_address": self.test_account["account_address"],
            "account_tag": "test_tag_af",
        }
        resp = client.post(self.api_url, json=request_params)

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        account_tag_af = session.scalars(select(AccountTag).limit(1)).first()
        assert account_tag_af.account_address == self.test_account["account_address"]
        assert account_tag_af.account_tag == "test_tag_af"

    # <Normal_2_2>
    # 更新登録（Noneに更新）
    def test_normal_2_2(self, client: TestClient, session: Session, shared_contract):
        # Prepare data
        account_tag = AccountTag()
        account_tag.account_address = self.test_account["account_address"]
        account_tag.account_tag = "test_tag_bf"
        session.add(account_tag)
        session.commit()

        # Call API
        request_params = {
            "account_address": self.test_account["account_address"],
            "account_tag": None,
        }
        resp = client.post(self.api_url, json=request_params)

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        account_tag_af = session.scalars(select(AccountTag).limit(1)).first()
        assert account_tag_af.account_address == self.test_account["account_address"]
        assert account_tag_af.account_tag is None

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Invalid Parameter
    def test_error_1(self, client: TestClient, session: Session, shared_contract):
        # Call API
        request_params = {
            "account_address": "invalid_account_address",
            "account_tag": "a" * 51,
        }
        resp = client.post(self.api_url, json=request_params)

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["body", "account_address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": "invalid_account_address",
                    "ctx": {"error": {}},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "account_tag"],
                    "msg": "String should have at most 50 characters",
                    "input": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "ctx": {"max_length": 50},
                },
            ],
        }

        account_tag_af = session.scalars(select(AccountTag).limit(1)).first()
        assert account_tag_af is None
