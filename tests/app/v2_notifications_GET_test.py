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

from datetime import datetime, timedelta, timezone

from app.model.db import Notification

JST = timezone(timedelta(hours=+9), "JST")


class TestNotificationsGet:

    # Test API
    apiurl = "/v2/Notifications"

    address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

    address_2 = "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF"

    def _insert_test_data(self, session):
        self.session = session  # HACK: updateでcommitされてしまう対策

        n = Notification()
        n.notification_id = "0x00000021034300000000000000"
        n.notification_type = "SampleNotification1"
        n.priority = 1
        n.address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
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
        session.add(n)

        n = Notification()
        n.notification_id = "0x00000021034000000000000000"
        n.notification_type = "SampleNotification2"
        n.priority = 1
        n.address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
        n.is_read = False
        n.is_flagged = False
        n.is_deleted = True
        n.deleted_at = None
        n.block_timestamp = datetime(2017, 5, 10, 10, 0, 0)
        n.args = {
            "hoge": "fuga",
        }
        n.metainfo = {}
        session.add(n)

        n = Notification()
        n.notification_id = "0x00000011034000000000000000"
        n.notification_type = "SampleNotification3"
        n.priority = 2
        n.address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
        n.is_read = False
        n.is_flagged = True
        n.is_deleted = False
        n.deleted_at = None
        n.block_timestamp = datetime(2017, 4, 10, 10, 0, 0)
        n.args = {
            "hoge": "fuga",
        }
        n.metainfo = {}
        session.add(n)

        n = Notification()
        n.notification_id = "0x00000011032000000000000000"
        n.notification_type = "SampleNotification4"
        n.priority = 1
        n.address = "0x7E5F4552091A69125d5DfCb7b8C2659029395B00"
        n.is_read = True
        n.is_flagged = False
        n.is_deleted = False
        n.deleted_at = None
        n.block_timestamp = datetime(2017, 3, 10, 10, 0, 0)
        n.args = {
            "hoge": "fuga",
        }
        n.metainfo = {}
        session.add(n)

        n = Notification()
        n.notification_id = "0x00000001034000000000000000"
        n.notification_type = "SampleNotification5"
        n.priority = 0
        n.address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
        n.is_read = False
        n.is_flagged = False
        n.is_deleted = False
        n.deleted_at = None
        n.block_timestamp = datetime(2017, 2, 10, 10, 0, 0)
        n.args = {
            "hoge": "fuga",
        }
        n.metainfo = {}
        session.add(n)

        session.commit()

    ###########################################################################
    # Normal
    ###########################################################################
    
    # <Normal_1>
    # List all notifications
    def test_normal_1(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(self.apiurl, params={"address": self.address})

        assumed_body = [
            {
                "notification_type": "SampleNotification1",
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
                "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
            },
            {
                "notification_type": "SampleNotification3",
                "id": "0x00000011034000000000000000",
                "sort_id": 2,
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
                "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
            },
            {
                "notification_type": "SampleNotification5",
                "id": "0x00000001034000000000000000",
                "sort_id": 3,
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
                "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
            },
        ]

        assert resp.status_code == 200
        assert resp.json["data"]["notifications"] == assumed_body

    # <Normal_2>
    # List only flagged notifications
    def test_normal_2(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": self.address,
                "status": "flagged"
            }
        )

        assumed_body = [
            {
                "notification_type": "SampleNotification3",
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
                "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
            },
        ]

        assert resp.status_code == 200
        assert resp.json["data"]["notifications"] == assumed_body

    # <Normal_3>
    # List only deleted notifications
    def test_normal_3(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": self.address,
                "status": "deleted",
            }
        )

        assumed_body = [
            {
                "notification_type": "SampleNotification2",
                "id": "0x00000021034000000000000000",
                "sort_id": 1,
                "priority": 1,
                "block_timestamp": "2017/05/10 10:00:00",
                "is_read": False,
                "is_flagged": False,
                "is_deleted": True,
                "deleted_at": None,
                "args": {
                    "hoge": "fuga",
                },
                "metainfo": {
                },
                "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
            },
        ]

        assert resp.status_code == 200
        assert resp.json["data"]["notifications"] == assumed_body

    # <Normal_4_1>
    # Sort by priority
    def test_normal_4_1(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": self.address,
                "sort": "priority"
            },
        )

        assumed_body = [
            {
                "notification_type": "SampleNotification3",
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
                "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
            },
            {
                "notification_type": "SampleNotification1",
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
                "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
            },
            {
                "notification_type": "SampleNotification5",
                "id": "0x00000001034000000000000000",
                "sort_id": 3,
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
                "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
            },
        ]

        assert resp.status_code == 200
        assert resp.json["data"]["notifications"] == assumed_body

    # <Normal_4_2>
    # Sort by flagged
    def test_normal_4_2(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": self.address,
                "sort": "is_flagged"
            },
        )

        assumed_body = [
            {
                "notification_type": "SampleNotification3",
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
                "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
            },
            {
                "notification_type": "SampleNotification1",
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
                "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
            },
            {
                "notification_type": "SampleNotification5",
                "id": "0x00000001034000000000000000",
                "sort_id": 3,
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
                "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
            },
        ]

        assert resp.status_code == 200
        assert resp.json["data"]["notifications"] == assumed_body

    # <Normal_5>
    # Set cursor
    def test_normal_5(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": self.address,
                "cursor": "1",
            },
        )

        assumed_body = [
            {
                "notification_type": "SampleNotification3",
                "id": "0x00000011034000000000000000",
                "sort_id": 2,
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
                "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
            },
            {
                "notification_type": "SampleNotification5",
                "id": "0x00000001034000000000000000",
                "sort_id": 3,
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
                "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
            },
        ]

        assert resp.status_code == 200
        assert resp.json["data"]["notifications"] == assumed_body

    # <Normal_6>
    # Set cursor and limit
    def test_normal_6(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": self.address,
                "cursor": "1",
                "limit": "1",
            }
        )

        assumed_body = [
            {
                "notification_type": "SampleNotification3",
                "id": "0x00000011034000000000000000",
                "sort_id": 2,
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
                "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
            },
        ]

        assert resp.status_code == 200
        assert resp.json["data"]["notifications"] == assumed_body

    # <Normal_7>
    # Zero data
    def test_normal_7(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={"address": self.address_2}
        )

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json["data"]["notifications"] == assumed_body

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1_1>
    # Invalid Parameter (cursor is minus)
    def test_error_1_1(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": self.address,
                "cursor": "-1",
                "limit": "1",
            }
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'cursor': 'min value is 0'}
        }

    # <Error_1_2>
    # Invalid Parameter (cursor is not an integer)
    def test_error_1_2(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": self.address,
                "cursor": "0.1",
                "limit": "1",
            }
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'cursor': [
                    "field 'cursor' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # <Error_2_1>
    # Invalid Parameter (limit is minus)
    def test_error_2_1(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": self.address,
                "cursor": "1",
                "limit": "-1",
            }
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'limit': 'min value is 0'}
        }

    # <Error_2_2>
    # Invalid Parameter (limit is not an integer)
    def test_error_2_2(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": self.address,
                "cursor": "1",
                "limit": "0.1",
            }
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'limit': [
                    "field 'limit' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # <Error_3_1>
    # Invalid Parameter (address is null)
    def test_error_3_1(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
            }
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'address': ['null value not allowed', 'must be of string type']}
        }

    # <Error_3_2>
    # Invalid Parameter (invalid address)
    def test_error_3_2(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": "0x11"
            }
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }
