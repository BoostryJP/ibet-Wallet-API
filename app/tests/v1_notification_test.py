from app.model import Notification
from datetime import datetime

class TestV1Notification():
    # テスト対象API
    apiurl = "/v1/Notifications"

    private_key = "0000000000000000000000000000000000000000000000000000000000000001"
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
    # 全ての通知を表示
    def test_get_notification_normal_1(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_auth_get(self.apiurl, private_key=TestV1Notification.private_key)

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
            },
        ]

        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body

    # ＜正常系1-2＞
    # フラグ済みの通知のみ表示
    def test_get_notification_normal_2(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_auth_get(self.apiurl,
                                        params={
                                            "status": "flagged",
                                        },
                                        private_key=TestV1Notification.private_key)

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
            },
        ]

        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body

    # ＜正常系1-3＞
    # 削除済みの通知のみ表示
    def test_get_notification_normal_3(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_auth_get(self.apiurl,
                                        params={
                                            "status": "deleted",
                                        },
                                        private_key=TestV1Notification.private_key)

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
            },
        ]

        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body

    # ＜正常系1-4＞
    # 優先度順にソート
    def test_get_notification_normal_4(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_auth_get(self.apiurl,
                                        params={
                                            "sort": "priority",
                                        },
                                        private_key=TestV1Notification.private_key)

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
            },
        ]

        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body

    # ＜正常系1-5＞
    # 全ての通知を表示 + カーソル使用
    def test_get_notification_normal_5(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_auth_get(self.apiurl,
                                        params = {
                                          "cursor": "1",
                                        },
                                        private_key=TestV1Notification.private_key)

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
            },
        ]

        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body

    # ＜正常系1-6＞
    # 全ての通知を表示 + カーソル使用 + リミット使用
    def test_get_notification_normal_6(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_auth_get(self.apiurl,
                                        params = {
                                            "cursor": "1",
                                            "limit": "1",
                                        },
                                        private_key=TestV1Notification.private_key)

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
            },
        ]

        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body


    # ＜正常系1-1＞
    # 重要フラグの更新
    def test_post_notification_normal_1(self, client, session):
        self._insert_test_data(session)

        notification_id = "0x00000021034300000000000000"
        resp = client.simulate_auth_post(self.apiurl,
                                         json={
                                             "id": notification_id,
                                             "is_flagged": True,
                                         },
                                         private_key=TestV1Notification.private_key)

        n = session.query(Notification).\
            filter(Notification.notification_id == notification_id).\
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
        }

        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body
        assert n.is_flagged == True

    # ＜正常系1-2＞
    # 重要フラグ・既読フラグの更新
    def test_post_notification_normal_2(self, client, session):
        self._insert_test_data(session)

        notification_id = "0x00000011034000000000000000"
        resp = client.simulate_auth_post(self.apiurl,
                                         json={
                                             "id": notification_id,
                                             "is_flagged": False,
                                             "is_read": True,
                                         },
                                         private_key=TestV1Notification.private_key)

        n = session.query(Notification). \
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
        }

        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body
        assert n.is_flagged == False
        assert n.is_read == True
