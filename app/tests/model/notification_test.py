# -*- cofing: utf-8 -*-
import pytest

from app.model import Notification
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=+9), "JST")

class TestNotification():
    # HACK: 実際にcommitをしないとDBに書き込まれず、タイムゾーンの変化が再現できないため
    def teardown_method(self, method):
        self.session.query(Notification).delete()
        self.session.commit()

    # バグ対応：PostgreSQLがUTCに設定されていると想定した場合、
    #   表示時にJSTに変換する必要がある
    def test_format_timestamp(self, session):
        self.session = session

        utime = 1528450912 # == '2018/06/08 18:41:52' in JST

        n = Notification()
        n.notification_id = "0x0"
        n.block_timestamp = datetime.fromtimestamp(utime, JST)
        session.add(n)
        session.commit()

        n2 = session.query(Notification).\
            filter(Notification.notification_id == "0x0").\
            first()

        json = n2.json()
        assert json["block_timestamp"] == "2018/06/08 18:41:52"
