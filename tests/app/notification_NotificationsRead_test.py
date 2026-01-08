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
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import TZ
from app.model.db import Notification

local_tz = ZoneInfo(TZ)


class TestNotificationsRead:
    # テスト対象API
    apiurl = "/Notifications/Read"

    address_1 = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

    address_2 = "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF"

    address_3 = "0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69"

    def _insert_test_data(self, session: Session) -> None:
        self.session = session  # HACK: updateでcommitされてしまう対策

        n = Notification()
        n.notification_category = "event_log"
        n.notification_id = "0x00000021034300000000000000"
        n.notification_type = "SampleNotification1"
        n.priority = 1
        n.address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
        n.is_read = True
        n.is_flagged = False
        n.is_deleted = False
        n.deleted_at = None
        n.block_timestamp = datetime(2017, 6, 10, 10, 0, 0).replace(
            tzinfo=local_tz
        )  # ローカルタイムゾーンとして保存する
        n.args = {
            "hoge": "fuga",
        }
        n.metainfo = {
            "aaa": "bbb",
        }
        session.add(n)

        n = Notification()
        n.notification_category = "event_log"
        n.notification_id = "0x00000021034000000000000000"
        n.notification_type = "SampleNotification2"
        n.priority = 1
        n.address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
        n.is_read = False
        n.is_flagged = False
        n.is_deleted = True
        n.deleted_at = None
        n.block_timestamp = datetime(2017, 5, 10, 10, 0, 0).replace(tzinfo=local_tz)
        n.args = {
            "hoge": "fuga",
        }
        n.metainfo = {}
        session.add(n)

        n = Notification()
        n.notification_category = "event_log"
        n.notification_id = "0x00000011034000000000000000"
        n.notification_type = "SampleNotification3"
        n.priority = 2
        n.address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
        n.is_read = False
        n.is_flagged = True
        n.is_deleted = False
        n.deleted_at = None
        n.block_timestamp = datetime(2017, 4, 10, 10, 0, 0).replace(tzinfo=local_tz)
        n.args = {
            "hoge": "fuga",
        }
        n.metainfo = {}
        session.add(n)

        n = Notification()
        n.notification_category = "event_log"
        n.notification_id = "0x00000011032000000000000000"
        n.notification_type = "SampleNotification4"
        n.priority = 1
        n.address = "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF"
        n.is_read = False
        n.is_flagged = False
        n.is_deleted = False
        n.deleted_at = None
        n.block_timestamp = datetime(2017, 3, 10, 10, 0, 0).replace(tzinfo=local_tz)
        n.args = {
            "hoge": "fuga",
        }
        n.metainfo = {}
        session.add(n)

        n = Notification()
        n.notification_category = "event_log"
        n.notification_id = "0x00000001034000000000000000"
        n.notification_type = "SampleNotification5"
        n.priority = 0
        n.address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
        n.is_read = False
        n.is_flagged = False
        n.is_deleted = False
        n.deleted_at = None
        n.block_timestamp = datetime(2017, 2, 10, 10, 0, 0).replace(tzinfo=local_tz)
        n.args = {
            "hoge": "fuga",
        }
        n.metainfo = {}
        session.add(n)

        session.commit()

    # ＜正常系1＞
    #   全件既読化
    def test_post_notification_read_normal_1(
        self, client: TestClient, session: Session
    ):
        self._insert_test_data(session)

        # Request target API
        resp = client.post(
            self.apiurl,
            json={
                "address": TestNotificationsRead.address_1,
                "is_read": True,
            },
        )

        # Assertion
        assert resp.status_code == 200

        notification_1_list = session.scalars(
            select(Notification).where(
                Notification.address == TestNotificationsRead.address_1
            )
        ).all()

        notification_2_list = session.scalars(
            select(Notification).where(
                Notification.address == TestNotificationsRead.address_2
            )
        ).all()

        assert len(notification_1_list) == 4
        assert len(notification_2_list) == 1

        for notification_1 in notification_1_list:
            assert notification_1.is_read == True

        for notification_2 in notification_2_list:
            assert notification_2.is_read == False

    # ＜正常系2＞
    #   全件未読化
    def test_post_notification_read_normal_2(
        self, client: TestClient, session: Session
    ):
        self._insert_test_data(session)

        resp = client.post(
            self.apiurl,
            json={
                "address": TestNotificationsRead.address_1,
                "is_read": False,
            },
        )

        notification_list = session.scalars(select(Notification)).all()
        assert resp.status_code == 200
        assert len(notification_list) == 5

        for notification in notification_list:
            assert notification.is_read == False

    # ＜正常系3＞
    #   存在しないアドレスの既読化
    def test_post_notification_read_normal_3(
        self, client: TestClient, session: Session
    ):
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
                "address": 0x7E5F4552091A69125D5DFCB7B8C2659029395BDF,
                "is_read": "invalid_value",
            },
        )

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["body", "address"],
                    "msg": "Value error, Value must be of string",
                    "input": 721457446580647751014191829380889690493307935711,
                    "ctx": {"error": {}},
                },
                {
                    "type": "bool_parsing",
                    "loc": ["body", "is_read"],
                    "msg": "Input should be a valid boolean, unable to interpret input",
                    "input": "invalid_value",
                },
            ],
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
            },
        )

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["body", "address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": "",
                    "ctx": {"error": {}},
                },
                {
                    "type": "bool_type",
                    "loc": ["body", "is_read"],
                    "msg": "Input should be a valid boolean",
                    "input": None,
                },
            ],
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
            },
        )

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["body", "address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": "0x123",
                    "ctx": {"error": {}},
                }
            ],
        }
