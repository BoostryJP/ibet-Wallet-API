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

from cerberus import Validator
from eth_utils import to_checksum_address
from sqlalchemy import desc
from web3 import Web3

from app import log
from app.api.common import BaseResource
from app.errors import (
    InvalidParameterError,
    DataNotExistsError
)
from app.model.db import Notification

LOG = log.get_logger()


class Notifications(BaseResource):
    """
    Endpoint: /Notifications/
    """

    def on_get(self, req, res, **kwargs):
        session = req.context["session"]

        # Validate Request Data
        request_json = self.validate_get(req)

        address = request_json["address"]
        notification_type = request_json["notification_type"]
        priority = request_json["priority"]
        sort_item = "created" if request_json["sort_item"] is None else request_json["sort_item"]
        sort_order = 0 if request_json["sort_order"] is None else request_json["sort_order"]  # default: asc
        offset = request_json["offset"]
        limit = request_json["limit"]

        query = session.query(Notification)
        total = query.count()

        # Search Filter
        if address is not None:
            query = query.filter(Notification.address == to_checksum_address(address))
        if notification_type is not None:
            query = query.filter(Notification.notification_type == notification_type)
        if priority is not None:
            query = query.filter(Notification.priority == priority)
        count = query.count()

        # Sort
        sort_attr = getattr(Notification, sort_item, None)
        if sort_order == 0:  # ASC
            query = query.order_by(sort_attr)
        else:  # DESC
            query = query.order_by(desc(sort_attr))
        if sort_item != "created":
            # NOTE: Set secondary sort for consistent results
            query = query.order_by(Notification.created)

        # Pagination
        if limit is not None:
            query = query.limit(limit)
        sort_id = 0
        if offset is not None:
            query = query.offset(offset)
            sort_id = offset

        _notification_list = query.all()

        notifications = []
        for _notification in _notification_list:
            sort_id += 1
            notification = _notification.json()
            notification["sort_id"] = sort_id
            notification["created"] = _notification.created.strftime("%Y/%m/%d %H:%M:%S")
            notifications.append(notification)

        data = {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": total
            },
            "notifications": notifications
        }
        self.on_success(res, data)

    @staticmethod
    def validate_get(req):
        request_json = {
            "address": req.get_param("address"),
            "notification_type": req.get_param("notification_type"),
            "priority": req.get_param("priority"),
            "sort_item": req.get_param("sort_item"),
            "sort_order": req.get_param("sort_order"),
            "offset": req.get_param("offset"),
            "limit": req.get_param("limit"),
        }

        validator = Validator({
            "address": {
                "type": "string",
                "required": False,
                "nullable": True,
                "empty": False,
            },
            "notification_type": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": [
                    "NewOrder",
                    "NewOrderCounterpart",
                    "CancelOrder",
                    "ForceCancelOrder",
                    "CancelOrderCounterpart",
                    "BuyAgreement",
                    "BuySettlementOK",
                    "BuySettlementNG",
                    "SellAgreement",
                    "SellSettlementOK",
                    "SellSettlementNG",
                    "Transfer",
                    "ApplyForTransfer",
                    "ApproveTransfer",
                    "CancelTransfer"
                ],
            },
            "priority": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "max": 2,
                "required": False,
                "nullable": True,
            },
            "sort_item": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": ["notification_type", "priority", "block_timestamp", "created"],
            },
            # NOTE: 0:asc, 1:desc
            "sort_order": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "max": 1,
                "required": False,
                "nullable": True,
            },
            "offset": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
            'limit': {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if request_json["address"] is not None:
            if not Web3.isAddress(request_json["address"]):
                raise InvalidParameterError

        return validator.document


class NotificationsRead(BaseResource):
    """
    Endpoint: /Notifications/Read/
    """

    def on_post(self, req, res, **kwargs):
        session = req.context["session"]

        # Validate Request Data
        request_json = self.validate(req)

        address = to_checksum_address(request_json["address"])

        # Update Data
        session.query(Notification). \
            filter(Notification.address == address). \
            update({'is_read': request_json["is_read"]})
        session.commit()

        self.on_success(res)

    @staticmethod
    def validate(req):
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


class NotificationsCount(BaseResource):
    """
    Endpoint: /Notifications/Count/
    """

    def on_get(self, req, res, **kwargs):
        session = req.context["session"]

        # 入力値チェック
        request_json = self.validate(req)

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


class NotificationsId(BaseResource):
    """
    Endpoint: /Notifications/{id}
    """

    def on_post(self, req, res, id=None, **kwargs):
        session = req.context["session"]

        # Validate Request Data
        request_json = self.validate_post(req)

        # Update Notification
        notification = session.query(Notification). \
            filter(Notification.notification_id == id). \
            first()
        if notification is None:
            raise DataNotExistsError("notification not found")

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
    def validate_post(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
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

        return validator.document

    def on_delete(self, req, res, id=None, **kwargs):
        session = req.context["session"]

        # Get Notification
        _notification = session.query(Notification). \
            filter(Notification.notification_id == id). \
            first()
        if _notification is None:
            raise DataNotExistsError("id: %s" % id)

        # Delete Notification
        session.delete(_notification)
        session.commit()

        self.on_success(res)
