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

from app.model.db import Notification
from datetime import datetime


class TestNotificationCount:
    # テスト対象API
    apiurl = "/v2/NotificationCount"

    address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

    def _insert_test_data(self, session):
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

    # ＜正常系1-1＞
    # 未読カウントを表示
    def test_notificationcount_normal_1(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(self.apiurl, params={"address": TestNotificationCount.address})

        assumed_body = {
            "unread_counts": 2,
        }

        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body

    # ＜正常系1-2＞
    # 未読カウントが0の場合
    def test_notificationcount_normal_2(self, client, session):
        resp = client.simulate_get(self.apiurl, params={"address": TestNotificationCount.address})

        assumed_body = {
            "unread_counts": 0,
        }

        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body

    # ＜エラー系1＞
    #   入力値エラー：必須入力値
    def test_notificationcount_error_1(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(self.apiurl, params={})

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'address': ['null value not allowed', 'must be of string type']
            }
        }

    # ＜エラー系2＞
    #   入力値エラー：アドレス形式誤り
    def test_notificationcount_error_2(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(self.apiurl, params={"address": "0x123"})

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }
