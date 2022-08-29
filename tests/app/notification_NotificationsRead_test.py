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


class TestNotificationsRead:
    # テスト対象API
    apiurl = "/Notifications/Read"

    address_1 = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

    address_2 = "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF"

    address_3 = "0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69"

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
        n.block_timestamp = datetime(2017, 6, 10, 10, 0, 0).replace(tzinfo=JST)  # JST時間として保存する
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
        n.block_timestamp = datetime(2017, 5, 10, 10, 0, 0).replace(tzinfo=JST)
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
        n.block_timestamp = datetime(2017, 4, 10, 10, 0, 0).replace(tzinfo=JST)
        n.args = {
            "hoge": "fuga",
        }
        n.metainfo = {}
        session.add(n)

        n = Notification()
        n.notification_id = "0x00000011032000000000000000"
        n.notification_type = "SampleNotification4"
        n.priority = 1
        n.address = "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF"
        n.is_read = False
        n.is_flagged = False
        n.is_deleted = False
        n.deleted_at = None
        n.block_timestamp = datetime(2017, 3, 10, 10, 0, 0).replace(tzinfo=JST)
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
        n.block_timestamp = datetime(2017, 2, 10, 10, 0, 0).replace(tzinfo=JST)
        n.args = {
            "hoge": "fuga",
        }
        n.metainfo = {}
        session.add(n)

        session.commit()

    # ＜正常系1＞
    #   全件既読化
    def test_post_notification_read_normal_1(self, client: TestClient, session: Session):
        self._insert_test_data(session)

        resp = client.post(
            self.apiurl,
            json={
                "address": TestNotificationsRead.address_1,
                "is_read": True,
            },
        )

        notification_1_list = \
            session.query(Notification). \
                filter(Notification.address == TestNotificationsRead.address_1). \
                all()

        notification_2_list = \
            session.query(Notification). \
                filter(Notification.address == TestNotificationsRead.address_2). \
                all()

        assert resp.status_code == 200
        assert len(notification_1_list) == 4
        assert len(notification_2_list) == 1

        for notification_1 in notification_1_list:
            assert notification_1.is_read == True

        for notification_2 in notification_2_list:
            assert notification_2.is_read == False

    # ＜正常系2＞
    #   全件未読化
    def test_post_notification_read_normal_2(self, client: TestClient, session: Session):
        self._insert_test_data(session)

        resp = client.post(
            self.apiurl,
            json={
                "address": TestNotificationsRead.address_1,
                "is_read": False,
            }
        )

        notification_list = session.query(Notification).all()

        assert resp.status_code == 200
        assert len(notification_list) == 5

        for notification in notification_list:
            assert notification.is_read == False

    # ＜正常系3＞
    #   存在しないアドレスの既読化
    def test_post_notification_read_normal_3(self, client: TestClient, session: Session):
        self._insert_test_data(session)

        resp = client.post(
            self.apiurl,
            json={
                "address": TestNotificationsRead.address_3,
                "is_read": True,
            },
        )

        assert resp.status_code == 200

    # ＜エラー系1＞
    #   入力値エラー：型誤り
    def test_post_notification_read_error_1(self, client: TestClient, session: Session):
        self._insert_test_data(session)

        resp = client.post(
            self.apiurl,
            json={
                "address": 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf,
                "is_read": "invalid_value",
            }
        )

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 1,
            "description": [
                {
                    "loc": ["body", "address"],
                    "msg": "address is not a valid address",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "is_read"],
                    "msg": "value could not be parsed to a boolean",
                    "type": "type_error.bool"
                }
            ],
            "message": "Request Validation Error"
        }

    # ＜エラー系2＞
    #   入力値エラー：必須入力値
    def test_post_notification_read_error_2(self, client: TestClient, session: Session):
        self._insert_test_data(session)

        resp = client.post(
            self.apiurl,
            json={
                "address": "",
                "is_read": None,
            }
        )

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 1,
            "description": [
                {
                    "loc": ["body", "address"],
                    "msg": "address is not a valid address",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "is_read"],
                    "msg": "none is not an allowed value",
                    "type": "type_error.none.not_allowed"
                }
            ],
            "message": "Request Validation Error"
        }

    # ＜エラー系3＞
    #   入力値エラー：アドレス形式誤り
    def test_post_notification_read_error_3(self, client: TestClient, session: Session):
        self._insert_test_data(session)

        resp = client.post(
            self.apiurl,
            json={
                "address": "0x123",
                "is_read": True,
            }
        )

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 1,
            "description": [
                {
                    "loc": ["body", "address"],
                    "msg": "address is not a valid address",
                    "type": "value_error"
                }
            ],
            "message": "Request Validation Error"
        }
