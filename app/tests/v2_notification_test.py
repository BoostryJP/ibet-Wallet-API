from datetime import datetime, timedelta, timezone

from app.model import Notification

JST = timezone(timedelta(hours=+9), "JST")


class TestNotification:
    # テスト対象API
    apiurl = "/v2/Notifications"

    address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

    address_2 = "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF"

    # HACK: updateでcommitされてしまう対策
    def teardown_method(self, method):
        self.session.query(Notification).delete()
        self.session.commit()

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

    # ---------------------------------------------------------------------------
    # GET
    # ---------------------------------------------------------------------------

    # ＜正常系1-1＞
    # 全ての通知を表示
    def test_get_notification_normal_1(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(self.apiurl, params={"address": TestNotification.address})

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

    # ＜正常系1-2＞
    # フラグ済みの通知のみ表示
    def test_get_notification_normal_2(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": TestNotification.address,
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

    # ＜正常系1-3＞
    # 削除済みの通知のみ表示
    def test_get_notification_normal_3(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": TestNotification.address,
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

    # ＜正常系1-4＞
    # 優先度順にソート
    def test_get_notification_normal_4(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": TestNotification.address,
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

    # ＜正常系1-5＞
    # 全ての通知を表示 + カーソル使用
    def test_get_notification_normal_5(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": TestNotification.address,
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

    # ＜正常系1-6＞
    # 全ての通知を表示 + カーソル使用 + リミット使用
    def test_get_notification_normal_6(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": TestNotification.address,
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

    # ＜正常系1-7＞
    # 0件データの場合
    def test_get_notification_normal_7(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={"address": TestNotification.address_2}
        )

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json["data"]["notifications"] == assumed_body

    # ＜エラー系1-1＞
    # cursorがマイナス
    def test_get_notification_error_1_1(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": TestNotification.address,
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

    # ＜エラー系1-2＞
    # cursorが小数
    def test_get_notification_error_1_2(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": TestNotification.address,
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

    # ＜エラー系2-1＞
    # limitがマイナス
    def test_get_notification_error_2_1(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": TestNotification.address,
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

    # ＜エラー系2-2＞
    # limitが小数
    def test_get_notification_error_2_2(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_get(
            self.apiurl,
            params={
                "address": TestNotification.address,
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

    # ＜エラー系3-1＞
    # addressなし
    def test_get_notification_error_3_1(self, client, session):
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

    # ＜エラー系3-2＞
    # address形式が不正
    def test_get_notification_error_3_2(self, client, session):
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

    # ---------------------------------------------------------------------------
    # POST
    # ---------------------------------------------------------------------------

    # ＜正常系1-1＞
    # 重要フラグの更新
    def test_post_notification_normal_1(self, client, session):
        self._insert_test_data(session)

        notification_id = "0x00000021034300000000000000"
        resp = client.simulate_post(
            self.apiurl,
            json={
                "address": TestNotification.address,
                "id": notification_id,
                "is_flagged": True,
            }
        )

        n = session.query(Notification). \
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

        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body
        assert n.is_flagged == True

    # ＜正常系1-2＞
    # 重要フラグ・既読フラグの更新
    def test_post_notification_normal_2(self, client, session):
        self._insert_test_data(session)

        notification_id = "0x00000011034000000000000000"
        resp = client.simulate_post(
            self.apiurl,
            json={
                "address": TestNotification.address,
                "id": notification_id,
                "is_flagged": False,
                "is_read": True,
            }
        )

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
            "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
        }

        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body
        assert n.is_flagged == False
        assert n.is_read == True

    # ＜正常系1-3＞
    # 削除フラグの更新（オン）
    def test_post_notification_normal_3(self, client, session):
        self._insert_test_data(session)

        notification_id = "0x00000011034000000000000000"
        resp = client.simulate_post(
            self.apiurl,
            json={
                "address": TestNotification.address,
                "id": notification_id,
                "is_deleted": True,
            }
        )

        n = session.query(Notification). \
            filter(Notification.notification_id == notification_id). \
            first()

        assert resp.status_code == 200
        assert n.is_read == False
        assert n.is_flagged == True
        assert n.is_deleted == True
        assert n.deleted_at is not None

    # ＜正常系1-3＞
    # 削除フラグの更新（オン→オフ）
    def test_post_notification_normal_4(self, client, session):
        self._insert_test_data(session)

        notification_id = "0x00000011034000000000000000"
        client.simulate_post(
            self.apiurl,
            json={
                "address": TestNotification.address,
                "id": notification_id,
                "is_deleted": True,
            }
        )

        resp = client.simulate_post(
            self.apiurl,
            json={
                "address": TestNotification.address,
                "id": notification_id,
                "is_deleted": False,
            }
        )

        n = session.query(Notification). \
            filter(Notification.notification_id == notification_id). \
            first()

        assert resp.status_code == 200
        assert n.is_read == False
        assert n.is_flagged == True
        assert n.is_deleted == False
        assert n.deleted_at is None

    # ＜異常系1-1＞
    # 権限なしパターン。重要フラグの更新
    def test_post_notification_fail_1_1(self, client, session):
        self._insert_test_data(session)

        notification_id = "0x00000021034300000000000000"
        resp = client.simulate_post(
            self.apiurl,
            json={
                "address": TestNotification.address_2,
                "id": notification_id,
                "is_flagged": True,
            }
        )

        assert resp.status_code == 400
        assert resp.json["meta"]["code"] == 88

    # ＜異常系1-2＞
    # 存在しない通知の更新
    def test_post_notification_fail_1_2(self, client, session):
        self._insert_test_data(session)

        notification_id = "0x00000021034100000000000003"
        resp = client.simulate_post(
            self.apiurl,
            json={
                "address": TestNotification.address,
                "id": notification_id,
                "is_flagged": True,
            }
        )

        assert resp.status_code == 404
        assert resp.json["meta"]["code"] == 30

    # ＜異常系2-1＞
    # addressなし
    def test_post_notification_fail_2_1(self, client, session):
        self._insert_test_data(session)

        notification_id = "0x00000021034300000000000000"
        resp = client.simulate_post(
            self.apiurl,
            json={
                "address": "",
                "id": notification_id,
                "is_flagged": True,
            }
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'address': 'empty values not allowed'}
        }

    # ＜異常系2-2＞
    # address形式が不正
    def test_post_notification_fail_2_2(self, client, session):
        self._insert_test_data(session)

        notification_id = "0x00000021034300000000000000"
        resp = client.simulate_post(
            self.apiurl,
            json={
                "address": "0xabc",
                "id": notification_id,
                "is_flagged": True,
            }
        )

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
        }
