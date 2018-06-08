# -*- cofing: utf-8 -*-
import pytest

from app.model import Notification
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=0), "JST")
UTC = timezone(timedelta(hours=0), "UTC")

class TestNotification():
    # バグ対応：通知情報をDBに保存する際にUTCに変換されるため、表示の際はJSTで表示する
    def test_format_timestamp(self, session):
        n = Notification()
        n.notification_id = "0x0"
        n.block_timestamp = datetime(2017, 3, 5, 12, tzinfo=JST)
        session.add(n)

        n2 = session.query(Notification).\
          filter(Notification.notification_id == "0x0").\
          first()

        json = n2.json()
        assert json["block_timestamp"] == "2017/03/05 21:00:00"
