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
from datetime import datetime

from app.model import Notification


class TestNotificationsGet:
    # Test API
    apiurl = "/v3/Notifications"

    address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

    address_2 = "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF"

    def _insert_test_data(self, session):

        n = Notification()
        n.notification_id = "0x00000021034300000000000000"
        n.notification_type = "NewOrder"
        n.priority = 1
        n.address = self.address
        n.is_read = True
        n.is_flagged = False
        n.is_deleted = False
        n.deleted_at = None
        n.block_timestamp = datetime(2017, 6, 10, 10, 0, 0)
        n.args = {
            "hoge": "fuga",
        }
        n.metainfo = {
            "aaa": "bbb",
        }
        n.created = datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S')
        session.add(n)

        n = Notification()
        n.notification_id = "0x00000021034000000000000000"
        n.notification_type = "NewOrderCounterpart"
        n.priority = 1
        n.address = self.address
        n.is_read = False
        n.is_flagged = False
        n.is_deleted = True
        n.deleted_at = None
        n.block_timestamp = datetime(2017, 5, 10, 10, 0, 0)
        n.args = {
            "hoge": "fuga",
        }
        n.metainfo = {}
        n.created = datetime.strptime("2022/01/01 16:20:30", '%Y/%m/%d %H:%M:%S')
        session.add(n)

        n = Notification()
        n.notification_id = "0x00000011034000000000000000"
        n.notification_type = "NewOrder"
        n.priority = 2
        n.address = self.address
        n.is_read = False
        n.is_flagged = True
        n.is_deleted = False
        n.deleted_at = None
        n.block_timestamp = datetime(2017, 4, 10, 10, 0, 0)
        n.args = {
            "hoge": "fuga",
        }
        n.metainfo = {}
        n.created = datetime.strptime("2022/01/01 17:20:30", '%Y/%m/%d %H:%M:%S')
        session.add(n)

        n = Notification()
        n.notification_id = "0x00000011032000000000000000"
        n.notification_type = "NewOrderCounterpart"
        n.priority = 1
        n.address = self.address_2
        n.is_read = True
        n.is_flagged = False
        n.is_deleted = False
        n.deleted_at = None
        n.block_timestamp = datetime(2017, 3, 10, 10, 0, 0)
        n.args = {
            "hoge": "fuga",
        }
        n.metainfo = {}
        n.created = datetime.strptime("2022/01/01 18:20:30", '%Y/%m/%d %H:%M:%S')
        session.add(n)

        n = Notification()
        n.notification_id = "0x00000001034000000000000000"
        n.notification_type = "NewOrder"
        n.priority = 0
        n.address = self.address
        n.is_read = False
        n.is_flagged = False
        n.is_deleted = False
        n.deleted_at = None
        n.block_timestamp = datetime(2017, 2, 10, 10, 0, 0)
        n.args = {
            "hoge": "fuga",
        }
        n.metainfo = {}
        n.created = datetime.strptime("2022/01/01 19:20:30", '%Y/%m/%d %H:%M:%S')
        session.add(n)

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # List all notifications
    def test_normal_1(self, client, session):
        # Prepare data
        self._insert_test_data(session)

        # Request target API
        resp = client.simulate_get(
            self.apiurl
        )

        assumed_body = {
            "result_set": {
                "count": 5,
                "offset": None,
                "limit": None,
                "total": 5
            },
            "notifications": [
                {
                    "notification_type": "NewOrder",
                    "id": "0x00000021034300000000000000",
                    "sort_id": 1,
                    "priority": 1,
                    "block_timestamp": "2017/06/10 10:00:00",
                    "is_read": True,
                    "is_flagged": False,
                    "is_deleted": False,
                    "deleted_at": None,
                    "args": {
                        "hoge": "fuga",
                    },
                    "metainfo": {
                        "aaa": "bbb"
                    },
                    "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
                    "created": "2022/01/01 15:20:30"
                },
                {
                    "notification_type": "NewOrderCounterpart",
                    "id": "0x00000021034000000000000000",
                    "sort_id": 2,
                    "priority": 1,
                    "block_timestamp": "2017/05/10 10:00:00",
                    "is_read": False,
                    "is_flagged": False,
                    "is_deleted": True,
                    "deleted_at": None,
                    "args": {
                        "hoge": "fuga",
                    },
                    "metainfo": {},
                    "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
                    "created": "2022/01/01 16:20:30"
                },
                {
                    "notification_type": "NewOrder",
                    "id": "0x00000011034000000000000000",
                    "sort_id": 3,
                    "priority": 2,
                    "block_timestamp": "2017/04/10 10:00:00",
                    "is_read": False,
                    "is_flagged": True,
                    "is_deleted": False,
                    "deleted_at": None,
                    "args": {
                        "hoge": "fuga",
                    },
                    "metainfo": {
                    },
                    "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
                    "created": "2022/01/01 17:20:30"
                },
                {
                    "notification_type": "NewOrderCounterpart",
                    "id": "0x00000011032000000000000000",
                    "sort_id": 4,
                    "priority": 1,
                    "block_timestamp": "2017/03/10 10:00:00",
                    "is_read": True,
                    "is_flagged": False,
                    "is_deleted": False,
                    "deleted_at": None,
                    "args": {
                        "hoge": "fuga",
                    },
                    "metainfo": {
                    },
                    "account_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
                    "created": "2022/01/01 18:20:30"
                },
                {
                    "notification_type": "NewOrder",
                    "id": "0x00000001034000000000000000",
                    "sort_id": 5,
                    "priority": 0,
                    "block_timestamp": "2017/02/10 10:00:00",
                    "is_read": False,
                    "is_flagged": False,
                    "is_deleted": False,
                    "deleted_at": None,
                    "args": {
                        "hoge": "fuga",
                    },
                    "metainfo": {
                    },
                    "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
                    "created": "2022/01/01 19:20:30"
                },
            ]
        }

        # Assertion
        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body

    # <Normal_2>
    # Pagination
    def test_normal_2(self, client, session):
        # Prepare data
        self._insert_test_data(session)

        # Request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "offset": 1,
                "limit": 2,
            }
        )

        assumed_body = {
            "result_set": {
                "count": 5,
                "offset": 1,
                "limit": 2,
                "total": 5
            },
            "notifications": [
                {
                    "notification_type": "NewOrderCounterpart",
                    "id": "0x00000021034000000000000000",
                    "sort_id": 2,
                    "priority": 1,
                    "block_timestamp": "2017/05/10 10:00:00",
                    "is_read": False,
                    "is_flagged": False,
                    "is_deleted": True,
                    "deleted_at": None,
                    "args": {
                        "hoge": "fuga",
                    },
                    "metainfo": {},
                    "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
                    "created": "2022/01/01 16:20:30"
                },
                {
                    "notification_type": "NewOrder",
                    "id": "0x00000011034000000000000000",
                    "sort_id": 3,
                    "priority": 2,
                    "block_timestamp": "2017/04/10 10:00:00",
                    "is_read": False,
                    "is_flagged": True,
                    "is_deleted": False,
                    "deleted_at": None,
                    "args": {
                        "hoge": "fuga",
                    },
                    "metainfo": {
                    },
                    "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
                    "created": "2022/01/01 17:20:30"
                },
            ]
        }

        # Assertion
        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body

    # <Normal_3>
    # Pagination(over offset)
    def test_normal_3(self, client, session):
        # Prepare data
        self._insert_test_data(session)

        # Request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "offset": 5,
            }
        )

        assumed_body = {
            "result_set": {
                "count": 5,
                "offset": 5,
                "limit": None,
                "total": 5
            },
            "notifications": []
        }

        # Assertion
        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body

    # <Normal_4>
    # Search Filter
    def test_normal_4(self, client, session):
        # Prepare data
        self._insert_test_data(session)

        # Request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": self.address,
                "notification_type": "NewOrder",
                "priority": 2,
            }
        )

        assumed_body = {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 5
            },
            "notifications": [
                {
                    "notification_type": "NewOrder",
                    "id": "0x00000011034000000000000000",
                    "sort_id": 1,
                    "priority": 2,
                    "block_timestamp": "2017/04/10 10:00:00",
                    "is_read": False,
                    "is_flagged": True,
                    "is_deleted": False,
                    "deleted_at": None,
                    "args": {
                        "hoge": "fuga",
                    },
                    "metainfo": {
                    },
                    "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
                    "created": "2022/01/01 17:20:30"
                },
            ]
        }

        # Assertion
        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body

    # <Normal_5>
    # Search Filter(not hit)
    def test_normal_5(self, client, session):
        # Prepare data
        self._insert_test_data(session)

        # Request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": self.address_2,
                "notification_type": "NewOrder",
                "priority": 1,
            }
        )

        assumed_body = {
            "result_set": {
                "count": 0,
                "offset": None,
                "limit": None,
                "total": 5
            },
            "notifications": []
        }

        # Assertion
        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body

    # <Normal_6>
    # Sort
    def test_normal_6(self, client, session):
        # Prepare data
        self._insert_test_data(session)

        # Request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "sort_item": "priority",
                "sort_order": 1,
            }
        )

        assumed_body = {
            "result_set": {
                "count": 5,
                "offset": None,
                "limit": None,
                "total": 5
            },
            "notifications": [
                {
                    "notification_type": "NewOrder",
                    "id": "0x00000011034000000000000000",
                    "sort_id": 1,
                    "priority": 2,
                    "block_timestamp": "2017/04/10 10:00:00",
                    "is_read": False,
                    "is_flagged": True,
                    "is_deleted": False,
                    "deleted_at": None,
                    "args": {
                        "hoge": "fuga",
                    },
                    "metainfo": {
                    },
                    "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
                    "created": "2022/01/01 17:20:30"
                },
                {
                    "notification_type": "NewOrder",
                    "id": "0x00000021034300000000000000",
                    "sort_id": 2,
                    "priority": 1,
                    "block_timestamp": "2017/06/10 10:00:00",
                    "is_read": True,
                    "is_flagged": False,
                    "is_deleted": False,
                    "deleted_at": None,
                    "args": {
                        "hoge": "fuga",
                    },
                    "metainfo": {
                        "aaa": "bbb"
                    },
                    "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
                    "created": "2022/01/01 15:20:30"
                },
                {
                    "notification_type": "NewOrderCounterpart",
                    "id": "0x00000021034000000000000000",
                    "sort_id": 3,
                    "priority": 1,
                    "block_timestamp": "2017/05/10 10:00:00",
                    "is_read": False,
                    "is_flagged": False,
                    "is_deleted": True,
                    "deleted_at": None,
                    "args": {
                        "hoge": "fuga",
                    },
                    "metainfo": {},
                    "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
                    "created": "2022/01/01 16:20:30"
                },
                {
                    "notification_type": "NewOrderCounterpart",
                    "id": "0x00000011032000000000000000",
                    "sort_id": 4,
                    "priority": 1,
                    "block_timestamp": "2017/03/10 10:00:00",
                    "is_read": True,
                    "is_flagged": False,
                    "is_deleted": False,
                    "deleted_at": None,
                    "args": {
                        "hoge": "fuga",
                    },
                    "metainfo": {
                    },
                    "account_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
                    "created": "2022/01/01 18:20:30"
                },
                {
                    "notification_type": "NewOrder",
                    "id": "0x00000001034000000000000000",
                    "sort_id": 5,
                    "priority": 0,
                    "block_timestamp": "2017/02/10 10:00:00",
                    "is_read": False,
                    "is_flagged": False,
                    "is_deleted": False,
                    "deleted_at": None,
                    "args": {
                        "hoge": "fuga",
                    },
                    "metainfo": {
                    },
                    "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
                    "created": "2022/01/01 19:20:30"
                },
            ]
        }

        # Assertion
        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Invalid Parameter
    def test_error_1(self, client, session):
        # Request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "notification_type": "hoge",
                "priority": -1,
                "sort_item": "fuga",
                "sort_order": -1,
                "offset": -1,
                "limit": -1,
            }
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "notification_type": "unallowed value hoge",
                "priority": "min value is 0",
                "sort_item": "unallowed value fuga",
                "sort_order": "min value is 0",
                "offset": "min value is 0",
                "limit": "min value is 0",
            }
        }

    # <Error_2>
    # Invalid Parameter
    def test_error_2(self, client, session):
        # Request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": self.address,
                "priority": 3,
                "sort_order": 2,
            }
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "priority": "max value is 2",
                "sort_order": "max value is 1",
            }
        }

    # <Error_3>
    # Invalid Parameter (invalid address)
    def test_error_3(self, client, session):
        # Request target API
        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": "0x11"
            }
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter"
        }
