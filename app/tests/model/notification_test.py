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

    # バグ対応：DBにはUTC設定で書き込まれているため、表示の際にはJSTに変換して表示する
    def test_format_timestamp(self, session):
        self.session = session

        # JST: 2018/06/08 18:41:52
        # UTC: 2018/06/08 09:41:52
        utime = 1528450912

        n = Notification()
        n.notification_id = "0x0"
        n.block_timestamp = datetime.fromtimestamp(utime, JST)
        session.add(n)
        session.commit() # DBはUTC設定になっているので、保存時にUTCに変換される

        n2 = session.query(Notification).\
            filter(Notification.notification_id == "0x0").\
            first()

        json = n2.json() # DBから取り出し、表示する際にJSTに変換する
        assert json["block_timestamp"] == "2018/06/08 18:41:52"
