"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed onan "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

from cerberus import Validator
from datetime import datetime
from eth_utils import to_checksum_address
from sqlalchemy import desc
from web3 import Web3

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError, DataNotExistsError
from app.model import Notification

LOG = log.get_logger()


# ------------------------------
# 通知一覧
# ------------------------------
class Notifications(BaseResource):
    """
    Endpoint: /Notifications/
    """

    def on_get(self, req, res):
        LOG.info('v2.notification.Notifications(GET)')

        session = req.context["session"]

        # 入力値チェック
        request_json = Notifications.validate_get(req)

        # リクエストから情報を抽出
        address = to_checksum_address(request_json["address"])

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
            query = query.order_by(desc(Notification.priority), desc(Notification.notification_id))
        else:
            query = query.order_by(desc(Notification.notification_id))

        query = query.offset(request_json["cursor"]). \
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

    def on_post(self, req, res):
        LOG.info('v2.notification.Notifications(POST)')

        session = req.context["session"]

        # 入力値チェック
        request_json = Notifications.validate_post(req)

        # リクエストから情報を抽出
        address = to_checksum_address(request_json["address"])

        # データを更新
        notification = session.query(Notification). \
            filter(Notification.notification_id == request_json["id"]). \
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
                notification.deleted_at = datetime.utcnow()
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
            "address": req.get_param("address"),
            "cursor": req.get_param("cursor", default="0"),
            "limit": req.get_param("limit", default="10"),
            "sort": req.get_param("sort"),
            "status": req.get_param("status"),
        }

        validator = Validator({
            "address": {
                "type": "string",
                "required": True,
                "empty": False,
            },
            "cursor": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
            "limit": {
                "type": "integer",
                "coerce": int,
                "min": 0,
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

        if not Web3.isAddress(request_json["address"]):
            raise InvalidParameterError

        return validator.document

    @staticmethod
    def validate_post(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "address": {
                "type": "string",
                "required": True,
                "empty": False,
            },
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

        if not Web3.isAddress(request_json["address"]):
            raise InvalidParameterError

        return validator.document


# ------------------------------
# 通知全件既読
# ------------------------------
class NotificationsRead(BaseResource):
    """
    Endpoint: /Notifications/Read/
    """

    def on_post(self, req, res):
        LOG.info('v2.notification.NotificationsRead')

        session = req.context["session"]

        # 入力値チェック
        request_json = NotificationsRead.validate_post(req)

        # リクエストから情報を抽出
        address = to_checksum_address(request_json["address"])

        # データを更新
        session.query(Notification). \
            filter(Notification.address == address). \
            update({'is_read': request_json["is_read"]})
        session.commit()

        self.on_success(res)

    @staticmethod
    def validate_post(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "address": {
                "type": "string",
                "required": True,
                "empty": False,
            },
            "is_read": {
                "type": "boolean",
                "required": True,
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(request_json["address"]):
            raise InvalidParameterError

        return validator.document


# ------------------------------
# 通知一覧
# ------------------------------
class NotificationCount(BaseResource):
    """
    Endpoint: /NotificationCount/
    """

    def on_get(self, req, res):
        LOG.info("v2.notification.NotificationCount")

        session = req.context["session"]

        # 入力値チェック
        request_json = NotificationCount.validate(req)

        # リクエストから情報を抽出
        address = to_checksum_address(request_json["address"])

        # 未読数を取得
        count = session.query(Notification). \
            filter(Notification.address == address). \
            filter(Notification.is_read == False). \
            filter(Notification.is_deleted == False). \
            count()

        self.on_success(res, {
            "unread_counts": count,
        })

    @staticmethod
    def validate(req):
        request_json = {
            "address": req.get_param("address"),
        }

        validator = Validator({
            "address": {
                "type": "string",
                "required": True,
                "empty": False,
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(request_json["address"]):
            raise InvalidParameterError

        return validator.document
