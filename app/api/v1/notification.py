# -*- coding: utf-8 -*-
import falcon
from cerberus import Validator
from eth_utils import to_checksum_address
from sqlalchemy import desc
from web3 import Web3

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError
from app.model import Notification
from app.utils.hooks import VerifySignature

LOG = log.get_logger()

# ------------------------------
# 通知一覧
# ------------------------------
class Notifications(BaseResource):
    '''
    Handle for endpoint: /v1/Notifications/
    '''
    @falcon.before(VerifySignature())
    def on_get(self, req, res):
        LOG.info('v1.Notification.Notifications')

        session = req.context["session"]

        # 入力値チェック
        request_json = Notifications.validate(req)

        # リクエストから情報を抽出
        address = to_checksum_address(req.context["address"])

        # クエリを設定
        query = session.query(Notification).\
            filter(Notification.address == address)

        if request_json["status"] == "flagged":
            query = query.filter(Notification.is_flagged == True)
        elif request_json["status"] == "deleted":
            query = query.filter(Notification.is_deleted == True)

        if not (request_json["cursor"] is None):
            query = query.filter(Notification.notification_id < request_json["cursor"])

        if request_json["sort"] == "priority":
            query = query.order_by(desc(Notification.priority), desc(Notification.notification_id))
        else:
            query = query.order_by(desc(Notification.notification_id))

        query = query.limit(request_json["limit"])

        # 結果を抽出
        notifications = query.all()
        notification_list = []
        for n in notifications:
            notification_list.append({
                "notification_type": n.notification_type,
                "id": n.notification_id,
                "priority": n.priority,
                "block_timestamp": Notification._format_block_timestamp(n.block_timestamp),
                "is_read": n.is_read,
                "is_flagged": n.is_flagged,
                "is_deleted": n.is_deleted,
                "deleted_at": n.deleted_at,
                "args": n.args,
                "metainfo": n.metainfo,
            })

        self.on_success(res, address)
        #self.on_success(res, notification_list)

    @staticmethod
    def _format_block_timestamp(datetime):
        return datetime.strftime("%Y/%m/%d %H:%M:%S")

    @staticmethod
    def validate(req):
        request_json = {
            "cursor": req.get_param("cursor"),
            "limit": req.get_param("limit", default="10"),
            "sort": req.get_param("sort"),
            "status": req.get_param("status"),
        }

        validator = Validator({
            "cursor": {
                "type": "string",
                "required": False,
                "nullable": True,
            },
            "limit": {
                "type": "integer",
                "coerce": int,
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

        return request_json

