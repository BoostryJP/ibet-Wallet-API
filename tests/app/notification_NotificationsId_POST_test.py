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
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.model.db import Notification

JST = timezone(timedelta(hours=+9), "JST")


class TestNotificationsIdPOST:
    # テスト対象API
    apiurl = "/Notifications/{id}"

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
    # Update is_flagged
    def test_normal_1(self, client: TestClient, session: Session):
        self._insert_test_data(session)

        notification_id = "0x00000021034300000000000000"

        # Request target API
        resp = client.post(
            self.apiurl.format(id=notification_id),
            json={
                "is_flagged": True
            }
        )

        # Assertion
        n: Notification | None = session.query(Notification). \
            filter(Notification.notification_id == notification_id). \
            first()

        assumed_body = {
            "notification_type": "SampleNotification1",
            "id": "0x00000021034300000000000000",
            "priority": 1,
            "block_timestamp": "2017/06/10 10:00:00",
            "is_read": True,
            "is_flagged": True,
            "is_deleted": False,
            "deleted_at": None,
            "args": {
                "hoge": "fuga",
            },
            "metainfo": {
                "aaa": "bbb"
            },
            "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
        }

        assert n
        assert resp.status_code == 200
        assert resp.json()["data"] == assumed_body
        assert n.is_flagged == True

    # <Normal_2>
    # Update is_flagged and is_deleted
    def test_normal_2(self, client: TestClient, session: Session):
        self._insert_test_data(session)

        notification_id = "0x00000011034000000000000000"

        # Request target API
        resp = client.post(
            self.apiurl.format(id=notification_id),
            json={
                "is_flagged": False,
                "is_read": True,
            }
        )

        # Assertion
        n: Notification | None = session.query(Notification). \
            filter(Notification.notification_id == notification_id). \
            first()

        assumed_body = {
            "notification_type": "SampleNotification3",
            "id": "0x00000011034000000000000000",
            "priority": 2,
            "block_timestamp": "2017/04/10 10:00:00",
            "is_read": True,
            "is_flagged": False,
            "is_deleted": False,
            "deleted_at": None,
            "args": {
                "hoge": "fuga",
            },
            "metainfo": {
            },
            "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
        }

        assert n
        assert resp.status_code == 200
        assert resp.json()["data"] == assumed_body
        assert n.is_flagged == False
        assert n.is_read == True

    # <Normal_3>
    # Update is_deleted (True)
    def test_normal_3(self, client: TestClient, session: Session):
        self._insert_test_data(session)

        notification_id = "0x00000011034000000000000000"

        # Request target API
        resp = client.post(
            self.apiurl.format(id=notification_id),
            json={
                "is_deleted": True,
            }
        )

        # Assertion
        n: Notification | None = session.query(Notification). \
            filter(Notification.notification_id == notification_id). \
            first()

        assert n
        assert resp.status_code == 200
        assert n.is_read == False
        assert n.is_flagged == True
        assert n.is_deleted == True
        assert n.deleted_at is not None

    # <Normal_4>
    # Update is_deleted (True -> False)
    def test_normal_4(self, client: TestClient, session: Session):
        self._insert_test_data(session)

        notification_id = "0x00000011034000000000000000"

        # Request target API
        client.post(
            self.apiurl.format(id=notification_id),
            json={
                "is_deleted": True,
            }
        )

        resp = client.post(
            self.apiurl.format(id=notification_id),
            json={
                "is_deleted": False,
            }
        )

        # Assertion
        n: Notification | None = session.query(Notification). \
            filter(Notification.notification_id == notification_id). \
            first()

        assert n
        assert resp.status_code == 200
        assert n.is_read == False
        assert n.is_flagged == True
        assert n.is_deleted == False
        assert n.deleted_at is None

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # DataNotExistsError
    def test_error_1(self, client: TestClient, session: Session):
        self._insert_test_data(session)

        notification_id = "0x00000021034100000000000003"

        # Request target API
        resp = client.post(
            self.apiurl.format(id=notification_id),
            json={
                "is_flagged": True,
            }
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            'code': 30,
            'message': 'Data Not Exists',
            'description': 'notification not found'
        }
