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

from app.model.db import ChatWebhook


class TestChatWebhook:
    # Target API endpoint
    api_url = "/Chat/Webhook"

    ####################################################################
    # Normal
    ####################################################################

    # Normal_1
    def test_normal_1(self, client: TestClient, session: Session):
        message_body = {"title": "test_title", "text": "test_text"}
        params = {"message": json.dumps(message_body)}
        resp = client.post(self.api_url, json=params)

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {"meta": {"code": 200, "message": "OK"}, "data": {}}

        hook_list = session.scalars(select(ChatWebhook)).all()
        assert len(hook_list) == 1

        hook = hook_list[0]
        assert hook.id == 1
        assert hook.message == json.dumps(message_body)

    ####################################################################
    # Error
    ####################################################################

    # Error_1
    # Invalid Parameter
    # field required
    def test_error_1(self, client: TestClient, session: Session):
        params = {}
        resp = client.post(self.api_url, json=params)

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 88,
                "message": "Invalid Parameter",
                "description": [
                    {
                        "input": {},
                        "loc": ["body", "message"],
                        "msg": "Field required",
                        "type": "missing",
                    }
                ],
            }
        }

    # Error_2
    # Invalid Parameter
    # Invalid JSON
    def test_error_2(self, client: TestClient, session: Session):
        params = {"message": "text"}
        resp = client.post(self.api_url, json=params)

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 88,
                "message": "Invalid Parameter",
                "description": [
                    {
                        "ctx": {"error": "expected ident at line 1 column 2"},
                        "input": "text",
                        "loc": ["body", "message"],
                        "msg": "Invalid JSON: expected ident at line 1 column 2",
                        "type": "json_invalid",
                    }
                ],
            }
        }
