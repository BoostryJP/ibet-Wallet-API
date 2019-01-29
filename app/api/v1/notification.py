# -*- coding: utf-8 -*-
from datetime import datetime, timezone, timedelta

import falcon
from cerberus import Validator
from eth_utils import to_checksum_address
from sqlalchemy import asc
from web3 import Web3

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError, DataNotExistsError
from app.model import Notification
from app.utils.hooks import VerifySignature

LOG = log.get_logger()
JST = timezone(timedelta(hours=+9), "JST")

# ------------------------------
# 通知一覧
# ------------------------------
class Notifications(BaseResource):
    '''
    Handle for endpoint: /v1/Notifications/
    '''

    @falcon.before(VerifySignature())
    def on_get(self, req, res):
        LOG.info('v1.Notification.Notifications(GET)')

        session = req.context["session"]

        # 入力値チェック
        request_json = Notifications.validate_get(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context["address"])

        # クエリを設定
        query = session.query(Notification). \
            filter(Notification.address == address)

        if request_json["status"] == "flagged":
            query = query.filter(Notification.is_flagged == True,
                                 Notification.is_deleted == False)
        elif request_json["status"] == "deleted":
            query = query.filter(Notification.is_deleted == True)
        else:
            query = query.filter(Notification.is_deleted == False)

        if request_json["sort"] == "priority":
            # 優先度の昇順＞通知の古い順（notification_idの昇順）にソート
            query = query.order_by(asc(Notification.priority), asc(Notification.notification_id))
        else:
            # 通知の古い順（notification_idの昇順）にソート
            query = query.order_by(asc(Notification.notification_id))

        query = query.offset(request_json["cursor"]).\
            limit(request_json["limit"])

        # 結果を抽出
        notifications = query.all()
        notification_list = []
        sort_id = request_json["cursor"]
        for n in notifications:
            sort_id += 1
            notification = n.json()
            notification["sort_id"] = sort_id
            notification_list.append(notification)

        self.on_success(res, {"notifications": notification_list})

    @falcon.before(VerifySignature())
    def on_post(self, req, res):
        LOG.info('v1.Notification.Notifications(POST)')

        session = req.context["session"]

        # 入力値チェック
        request_json = Notifications.validate_post(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context["address"])

        # データを更新
        notification = session.query(Notification).\
            filter(Notification.notification_id == request_json["id"]).\
            first()

        if notification is None:
            raise DataNotExistsError("notification not found")

        if notification.address != address:
            raise InvalidParameterError("authentication failed")

        if "is_read" in request_json:
            notification.is_read = request_json["is_read"]

        if "is_flagged" in request_json:
            notification.is_flagged = request_json["is_flagged"]

        if "is_deleted" in request_json:
            notification.is_deleted = request_json["is_deleted"]
            if request_json["is_deleted"]:
                notification.deleted_at = datetime.now(tz=JST)
            else:
                notification.deleted_at = None

        session.commit()

        self.on_success(res, notification.json())

    @staticmethod
    def format_block_timestamp(datetime):
        return datetime.strftime("%Y/%m/%d %H:%M:%S")

    @staticmethod
    def validate_get(req):
        request_json = {
            "cursor": req.get_param("cursor", default="0"),
            "limit": req.get_param("limit", default="10"),
            "sort": req.get_param("sort"),
            "status": req.get_param("status"),
        }

        validator = Validator({
            "cursor": {
                "type": "integer",
                "coerce": int,
                "min":0,
                "required": False,
                "nullable": True,
            },
            "limit": {
                "type": "integer",
                "coerce": int,
                "min":0,
                "required": False,
                "nullable": True,
            },
            "sort": {
                "type": "string",
                "required": False,
                "nullable": True,
            },
            "status": {
                "type": "string",
                "required": False,
                "nullable": True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(req.context["address"]):
            raise InvalidParameterError

        return validator.document

    @staticmethod
    def validate_post(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "id": {
                "type": "string",
                "required": True,
                "empty": False,
            },
            "is_read": {
                "type": "boolean",
                "required": False,
            },
            "is_flagged": {
                "type": "boolean",
                "required": False,
            },
            "is_deleted": {
                "type": "boolean",
                "required": False,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(req.context["address"]):
            raise InvalidParameterError

        return validator.document

# ------------------------------
# 通知全件既読
# ------------------------------
class NotificationsRead(BaseResource):
    '''
    Handle for endpoint: /v1/Notifications/Read/
    '''

    @falcon.before(VerifySignature())
    def on_post(self, req, res):
        LOG.info('v1.Notification.Read')

        session = req.context["session"]

        # 入力値チェック
        request_json = NotificationsRead.validate_post(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context["address"])

        # データを更新
        session.query(Notification).\
            filter(Notification.address == address).\
            update({'is_read': request_json["is_read"]})
        session.commit()

        self.on_success(res)

    @staticmethod
    def validate_post(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "is_read": {
                "type": "boolean",
                "required": True,
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(req.context["address"]):
            raise InvalidParameterError

        return validator.document

# ------------------------------
# 通知一覧
# ------------------------------
class NotificationCount(BaseResource):
    '''
    Handle for endpoint: /v1/NotificationCount/
    '''

    @falcon.before(VerifySignature())
    def on_get(self, req, res):
        LOG.info("v1.Notification.NotificationCount")

        session = req.context["session"]

        # 入力値チェック
        NotificationCount.validate(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context["address"])

        # 未読数を取得
        count = session.query(Notification).\
            filter(Notification.address == address).\
            filter(Notification.is_read == False).\
            filter(Notification.is_deleted == False).\
            count()

        self.on_success(res, {
            "unread_counts": count,
        })

    @staticmethod
    def validate(req):
        if not Web3.isAddress(req.context["address"]):
            raise InvalidParameterError

        return {}
