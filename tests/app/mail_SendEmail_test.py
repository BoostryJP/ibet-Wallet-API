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

from app.model.db import Mail


class TestSendEmail:

    # Target API endpoint
    api_url = "/Mail"

    ####################################################################
    # Normal
    ####################################################################

    # Normal_1_1
    def test_normal_1_1(self, client: TestClient, session: Session):
        params = {
            "to_emails": ["test@example.com"],
            "subject": "Test email",
            "text_content": "text content",
            "html_content": "<p>html content</p>"
        }
        resp = client.post(
            self.api_url,
            json=params
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            'meta': {
                'code': 200,
                'message': 'OK'
            },
            'data': {}
        }

        mail_list = session.query(Mail).all()
        assert len(mail_list) == 1

        mail = mail_list[0]
        assert mail.id == 1
        assert mail.to_email == "test@example.com"
        assert mail.subject == "Test email"
        assert mail.text_content == "text content"
        assert mail.html_content == "<p>html content</p>"

    # Normal_1_2
    # content is None
    def test_normal_1_2(self, client: TestClient, session: Session):
        params = {
            "to_emails": ["test@example.com"],
            "subject": "Test email"
        }
        resp = client.post(
            self.api_url,
            json=params
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            'meta': {
                'code': 200,
                'message': 'OK'
            },
            'data': {}
        }

        mail_list = session.query(Mail).all()
        assert len(mail_list) == 1

        mail = mail_list[0]
        assert mail.id == 1
        assert mail.to_email == "test@example.com"
        assert mail.subject == "Test email"
        assert mail.text_content == ""
        assert mail.html_content == ""

    # Normal_2
    # Multiple to_email
    def test_normal_2(self, client: TestClient, session: Session):
        params = {
            "to_emails": ["test1@example.com", "test2@example.com"],
            "subject": "Test email",
            "text_content": "text content",
            "html_content": "<p>html content</p>"
        }
        resp = client.post(
            self.api_url,
            json=params
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            'meta': {
                'code': 200,
                'message': 'OK'
            },
            'data': {}
        }

        mail_list = session.query(Mail).all()
        assert len(mail_list) == 2

        mail = mail_list[0]
        assert mail.id == 1
        assert mail.to_email == "test1@example.com"
        assert mail.subject == "Test email"
        assert mail.text_content == "text content"
        assert mail.html_content == "<p>html content</p>"

        mail = mail_list[1]
        assert mail.id == 2
        assert mail.to_email == "test2@example.com"
        assert mail.subject == "Test email"
        assert mail.text_content == "text content"
        assert mail.html_content == "<p>html content</p>"

    ####################################################################
    # Error
    ####################################################################

    # Error_1
    # Invalid Parameter
    # field required
    def test_error_1(self, client: TestClient, session: Session):
        params = {}
        resp = client.post(
            self.api_url,
            json=params
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            'meta': {
                'code': 88,
                'message': 'Invalid Parameter',
                'description': [
                    {
                        'loc': ['body', 'to_emails'],
                        'msg': 'field required',
                        'type': 'value_error.missing'
                    },
                    {
                        'loc': ['body', 'subject'],
                        'msg': 'field required',
                        'type': 'value_error.missing'
                    }
                ]
            }
        }

    # Error_2
    # Invalid Parameter
    def test_error_2(self, client: TestClient, session: Session):
        params = {
            "to_emails": ["invalid_email"],
            "subject": "a" * 101
        }
        resp = client.post(
            self.api_url,
            json=params
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            'meta': {
                'code': 88,
                'message': 'Invalid Parameter',
                'description': [
                    {
                        'loc': ['body', 'to_emails', 0],
                        'msg': 'value is not a valid email address',
                        'type': 'value_error.email'
                    },
                    {
                        'loc': ['body', 'subject'],
                        'msg': 'ensure this value has at most 100 characters',
                        'type': 'value_error.any_str.max_length',
                        'ctx': {'limit_value': 100}
                    }
                ]
            }
        }
