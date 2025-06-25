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

from unittest import mock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.model.db import PublicAccountList


class TestListAllPublicAccounts:
    """
    Test Case for token.ListAllPublicAccounts
    """

    test_key_manager_1 = "test_key_manager_1"
    test_key_manager_name_1 = "test_key_manager_name_1"
    test_account_address_1 = "0x16f39D63d156f9abCe0a9aB46F751E2eFdEB040f"

    test_key_manager_2 = "test_key_manager_2"
    test_key_manager_name_2 = "test_key_manager_name_2"
    test_account_address_2 = "0x28e0ad30c43B3D55851b881E25586926894de3e9"

    # Test API
    api_url = "/PublicInfo/PublicAccounts"

    ###########################################################################
    # Normal
    ###########################################################################
    # ＜Normal_1＞
    # 0 Record
    def test_normal_1(self, client: TestClient, session: Session):
        # Call API
        resp = client.get(self.api_url, params={})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 0, "limit": None, "offset": None, "total": 0},
            "accounts": [],
        }

    # ＜Normal_2＞
    # Multiple Records
    def test_normal_2(self, client: TestClient, session: Session):
        # Prepare data
        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_1
        _account.key_manager_name = self.test_key_manager_name_1
        _account.account_type = 1
        _account.account_address = self.test_account_address_1
        session.add(_account)

        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_2
        _account.key_manager_name = self.test_key_manager_name_2
        _account.account_type = 2
        _account.account_address = self.test_account_address_2
        session.add(_account)

        session.commit()

        # Call API
        resp = client.get(self.api_url, params={})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 2, "limit": None, "offset": None, "total": 2},
            "accounts": [
                {
                    "key_manager": self.test_key_manager_1,
                    "key_manager_name": self.test_key_manager_name_1,
                    "account_type": 1,
                    "account_address": self.test_account_address_1,
                    "modified": mock.ANY,
                },
                {
                    "key_manager": self.test_key_manager_2,
                    "key_manager_name": self.test_key_manager_name_2,
                    "account_type": 2,
                    "account_address": self.test_account_address_2,
                    "modified": mock.ANY,
                },
            ],
        }

    # ＜Normal_3_1＞
    # Filter: key_manager
    def test_normal_3_1(self, client: TestClient, session: Session):
        # Prepare data
        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_1
        _account.key_manager_name = self.test_key_manager_name_1
        _account.account_type = 1
        _account.account_address = self.test_account_address_1
        session.add(_account)

        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_2
        _account.key_manager_name = self.test_key_manager_name_2
        _account.account_type = 2
        _account.account_address = self.test_account_address_2
        session.add(_account)

        session.commit()

        # Call API
        resp = client.get(self.api_url, params={"key_manager": self.test_key_manager_2})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 2},
            "accounts": [
                {
                    "key_manager": self.test_key_manager_2,
                    "key_manager_name": self.test_key_manager_name_2,
                    "account_type": 2,
                    "account_address": self.test_account_address_2,
                    "modified": mock.ANY,
                },
            ],
        }

    # ＜Normal_3_2＞
    # Filter: key_manager_name
    def test_normal_3_2(self, client: TestClient, session: Session):
        # Prepare data
        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_1
        _account.key_manager_name = self.test_key_manager_name_1
        _account.account_type = 1
        _account.account_address = self.test_account_address_1
        session.add(_account)

        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_2
        _account.key_manager_name = self.test_key_manager_name_2
        _account.account_type = 2
        _account.account_address = self.test_account_address_2
        session.add(_account)

        session.commit()

        # Call API
        resp = client.get(self.api_url, params={"key_manager_name": "2"})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 2},
            "accounts": [
                {
                    "key_manager": self.test_key_manager_2,
                    "key_manager_name": self.test_key_manager_name_2,
                    "account_type": 2,
                    "account_address": self.test_account_address_2,
                    "modified": mock.ANY,
                },
            ],
        }

    # ＜Normal_4_1＞
    # Sort: key_manager
    def test_normal_4_1(self, client: TestClient, session: Session):
        # Prepare data
        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_1
        _account.key_manager_name = self.test_key_manager_name_1
        _account.account_type = 1
        _account.account_address = self.test_account_address_1
        session.add(_account)

        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_1
        _account.key_manager_name = self.test_key_manager_name_1
        _account.account_type = 2
        _account.account_address = self.test_account_address_1
        session.add(_account)

        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_2
        _account.key_manager_name = self.test_key_manager_name_2
        _account.account_type = 2
        _account.account_address = self.test_account_address_2
        session.add(_account)

        session.commit()

        # Call API
        resp = client.get(
            self.api_url, params={"sort_item": "key_manager", "sort_order": 1}
        )

        # Assertion
        # - The primary sorting should be by `key_manager`,
        #   and the secondary sorting should be by `account_type`.
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 3, "limit": None, "offset": None, "total": 3},
            "accounts": [
                {
                    "key_manager": self.test_key_manager_2,
                    "key_manager_name": self.test_key_manager_name_2,
                    "account_type": 2,
                    "account_address": self.test_account_address_2,
                    "modified": mock.ANY,
                },
                {
                    "key_manager": self.test_key_manager_1,
                    "key_manager_name": self.test_key_manager_name_1,
                    "account_type": 1,
                    "account_address": self.test_account_address_1,
                    "modified": mock.ANY,
                },
                {
                    "key_manager": self.test_key_manager_1,
                    "key_manager_name": self.test_key_manager_name_1,
                    "account_type": 2,
                    "account_address": self.test_account_address_1,
                    "modified": mock.ANY,
                },
            ],
        }

    # ＜Normal_4_2＞
    # Sort: key_manager_name
    def test_normal_4_2(self, client: TestClient, session: Session):
        # Prepare data
        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_1
        _account.key_manager_name = self.test_key_manager_name_1
        _account.account_type = 1
        _account.account_address = self.test_account_address_1
        session.add(_account)

        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_1
        _account.key_manager_name = self.test_key_manager_name_1
        _account.account_type = 2
        _account.account_address = self.test_account_address_1
        session.add(_account)

        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_2
        _account.key_manager_name = self.test_key_manager_name_2
        _account.account_type = 2
        _account.account_address = self.test_account_address_2
        session.add(_account)

        session.commit()

        # Call API
        resp = client.get(
            self.api_url, params={"sort_item": "key_manager_name", "sort_order": 1}
        )

        # Assertion
        # - The primary sorting should be by `account_address`,
        #   the secondary sorting by `key_manager`,
        #   and the tertiary sorting by `account_type`.
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 3, "limit": None, "offset": None, "total": 3},
            "accounts": [
                {
                    "key_manager": self.test_key_manager_2,
                    "key_manager_name": self.test_key_manager_name_2,
                    "account_type": 2,
                    "account_address": self.test_account_address_2,
                    "modified": mock.ANY,
                },
                {
                    "key_manager": self.test_key_manager_1,
                    "key_manager_name": self.test_key_manager_name_1,
                    "account_type": 1,
                    "account_address": self.test_account_address_1,
                    "modified": mock.ANY,
                },
                {
                    "key_manager": self.test_key_manager_1,
                    "key_manager_name": self.test_key_manager_name_1,
                    "account_type": 2,
                    "account_address": self.test_account_address_1,
                    "modified": mock.ANY,
                },
            ],
        }

    # ＜Normal_4_3＞
    # Sort: account_address
    def test_normal_4_3(self, client: TestClient, session: Session):
        # Prepare data
        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_1
        _account.key_manager_name = self.test_key_manager_name_1
        _account.account_type = 1
        _account.account_address = self.test_account_address_1
        session.add(_account)

        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_1
        _account.key_manager_name = self.test_key_manager_name_1
        _account.account_type = 2
        _account.account_address = self.test_account_address_1
        session.add(_account)

        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_2
        _account.key_manager_name = self.test_key_manager_name_2
        _account.account_type = 2
        _account.account_address = self.test_account_address_2
        session.add(_account)

        session.commit()

        # Call API
        resp = client.get(
            self.api_url, params={"sort_item": "account_address", "sort_order": 1}
        )

        # Assertion
        # - The primary sorting should be by `account_address`,
        #   the secondary sorting by `key_manager`,
        #   and the tertiary sorting by `account_type`.
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 3, "limit": None, "offset": None, "total": 3},
            "accounts": [
                {
                    "key_manager": self.test_key_manager_2,
                    "key_manager_name": self.test_key_manager_name_2,
                    "account_type": 2,
                    "account_address": self.test_account_address_2,
                    "modified": mock.ANY,
                },
                {
                    "key_manager": self.test_key_manager_1,
                    "key_manager_name": self.test_key_manager_name_1,
                    "account_type": 1,
                    "account_address": self.test_account_address_1,
                    "modified": mock.ANY,
                },
                {
                    "key_manager": self.test_key_manager_1,
                    "key_manager_name": self.test_key_manager_name_1,
                    "account_type": 2,
                    "account_address": self.test_account_address_1,
                    "modified": mock.ANY,
                },
            ],
        }

    # ＜Normal_5＞
    # Pagination
    def test_normal_5(self, client: TestClient, session: Session):
        # Prepare data
        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_1
        _account.key_manager_name = self.test_key_manager_name_1
        _account.account_type = 1
        _account.account_address = self.test_account_address_1
        session.add(_account)

        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_1
        _account.key_manager_name = self.test_key_manager_name_1
        _account.account_type = 2
        _account.account_address = self.test_account_address_1
        session.add(_account)

        _account = PublicAccountList()
        _account.key_manager = self.test_key_manager_2
        _account.key_manager_name = self.test_key_manager_name_2
        _account.account_type = 2
        _account.account_address = self.test_account_address_2
        session.add(_account)

        session.commit()

        # Call API
        resp = client.get(self.api_url, params={"offset": 1, "limit": 1})

        # Assertion
        # - The primary sorting should be by `key_manager`,
        #   and the secondary sorting should be by `account_type`.
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 3, "limit": 1, "offset": 1, "total": 3},
            "accounts": [
                {
                    "key_manager": self.test_key_manager_1,
                    "key_manager_name": self.test_key_manager_name_1,
                    "account_type": 2,
                    "account_address": self.test_account_address_1,
                    "modified": mock.ANY,
                },
            ],
        }

    ###########################################################################
    # Error
    ###########################################################################

    # ＜Error_1＞
    # InvalidParameterError
    def test_error_1(self, client: TestClient, session: Session):
        # Call API
        resp = client.get(
            self.api_url, params={"sort_item": "invalid_sort_item", "sort_order": -1}
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "enum",
                    "loc": ["query", "sort_item"],
                    "msg": "Input should be 'key_manager', 'key_manager_name' or 'account_address'",
                    "input": "invalid_sort_item",
                    "ctx": {
                        "expected": "'key_manager', 'key_manager_name' or 'account_address'"
                    },
                },
                {
                    "type": "enum",
                    "loc": ["query", "sort_order"],
                    "msg": "Input should be 0 or 1",
                    "input": "-1",
                    "ctx": {"expected": "0 or 1"},
                },
            ],
        }
