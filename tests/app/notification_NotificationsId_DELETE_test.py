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

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.model.db import Notification


class TestNotificationsIdDELETE:
    # Test API
    apiurl = "/Notifications/{id}"

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
        n.created = datetime.strptime("2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S")
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
        n.created = datetime.strptime("2022/01/01 16:20:30", "%Y/%m/%d %H:%M:%S")
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
        n.created = datetime.strptime("2022/01/01 17:20:30", "%Y/%m/%d %H:%M:%S")
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
        n.created = datetime.strptime("2022/01/01 18:20:30", "%Y/%m/%d %H:%M:%S")
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
        n.created = datetime.strptime("2022/01/01 19:20:30", "%Y/%m/%d %H:%M:%S")
        session.add(n)

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client: TestClient, session: Session):
        # Prepare data
        self._insert_test_data(session)
        session.commit()

        notification_id = "0x00000011032000000000000000"

        # Request target API
        resp = client.delete(
            self.apiurl.format(id=notification_id),
        )

        # Assertion
        session.rollback()
        assert resp.status_code == 200
        _notification_list = session.query(Notification).all()
        assert len(_notification_list) == 4
        _notification = (
            session.query(Notification)
            .filter(Notification.notification_id == notification_id)
            .first()
        )
        assert _notification is None

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Not Fount
    def test_error_1(self, client: TestClient, session: Session):
        # Prepare data
        self._insert_test_data(session)
        session.commit()

        notification_id = "xxxxx"

        # Request target API
        resp = client.delete(
            self.apiurl.format(id=notification_id),
        )

        # Assertion
        session.rollback()
        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": "id: xxxxx",
        }
