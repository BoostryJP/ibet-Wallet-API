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

import sys
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    Sequence,
    String,
)
from sqlalchemy.dialects.mysql import DATETIME as MySQLDATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.database import engine
from app.model.db.base import Base


# 通知データをキャッシュするためのテーブル
# 既読情報や重要フラグの情報なども保存される
class Notification(Base):
    __tablename__ = "notification"

    # レコードID
    if engine.name == "mysql":
        # NOTE:MySQLの場合はSEQ機能が利用できない
        id: Mapped[int | None] = mapped_column(BigInteger, autoincrement=True)
    else:
        # レコードIDのシーケンス
        notification_id_seq = Sequence(
            "notification_id_seq",
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=sys.maxsize,
            cache=1,
        )
        id: Mapped[int | None] = mapped_column(
            BigInteger,
            server_default=Sequence("notification_id_seq").next_value(),
            autoincrement=True,
        )

    # 通知ID
    # Spec: 0x | <blockNumber> | <transactionIndex> | <logIndex> | <optionType>
    #   ( | は文字列連結 )
    #   <blockNumber>: blockNumberをhexstringで表現したもの。12桁
    #   <transactionIndex>: transactionIndex（block内でのトランザクションの採番）をhexstringで表現したもの。6桁
    #   <logIndex>: logIndex（transaction内でのログの採番）をhexstringで表現したもの。6桁
    #   <optionType>: blockNumber, transactionIndex, logIndexが等しいが、通知としては複数にしたい場合に使用する識別子。2桁(デフォルトは00)
    notification_id: Mapped[str] = mapped_column(String(256), primary_key=True)

    # 通知タイプ(例：BuySettlementOK, BuyAgreementなど)
    notification_type: Mapped[str | None] = mapped_column(String(256), index=True)

    # 通知の重要度
    #   0: Low
    #   1: Medium
    #   2: High
    priority: Mapped[int | None] = mapped_column(Integer, index=True)

    # 通知対象のユーザーのアドレス
    address: Mapped[str | None] = mapped_column(String(256), index=True)

    # 既読フラグ
    is_read: Mapped[bool | None] = mapped_column(Boolean, default=False)
    # 重要フラグ
    is_flagged: Mapped[bool | None] = mapped_column(Boolean, default=False)
    # 削除フラグ
    is_deleted: Mapped[bool | None] = mapped_column(Boolean, default=False)
    # 削除日付
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    # 通知が発生した日付（blockTime）
    # NOTE:
    #  Postgres: Stored as UTC datetime.
    #  MySQL: Before 23.3, stored as JST datetime.
    #         From 23.3, stored as UTC datetime.
    block_timestamp: Mapped[datetime | None] = mapped_column(DateTime)

    # 通知イベントの内容
    args: Mapped[dict | None] = mapped_column(JSON)
    # 通知のメタデータ（通知イベントには入っていないが、取りたい情報。トークン名など）
    metainfo: Mapped[dict | None] = mapped_column(JSON)

    if engine.name == "mysql":
        # NOTE:MySQLではDatetime型で小数秒桁を指定しない場合、整数秒しか保存されない
        created: Mapped[datetime | None] = mapped_column(
            MySQLDATETIME(fsp=6), default=datetime.utcnow, index=True
        )
    else:
        created: Mapped[datetime | None] = mapped_column(
            DateTime, default=datetime.utcnow, index=True
        )

    def __repr__(self):
        return "<Notification(notification_id='{}', notification_type='{}')>".format(
            self.notification_id, self.notification_type
        )

    def json(self):
        return {
            "notification_type": self.notification_type,
            "id": self.notification_id,
            "priority": self.priority,
            "block_timestamp": "{}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
                self.block_timestamp.year,
                self.block_timestamp.month,
                self.block_timestamp.day,
                self.block_timestamp.hour,
                self.block_timestamp.minute,
                self.block_timestamp.second,
            )
            if self.block_timestamp is not None
            else None,
            "is_read": self.is_read,
            "is_flagged": self.is_flagged,
            "is_deleted": self.is_deleted,
            "deleted_at": "{}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
                self.deleted_at.year,
                self.deleted_at.month,
                self.deleted_at.day,
                self.deleted_at.hour,
                self.deleted_at.minute,
                self.deleted_at.second,
            )
            if self.deleted_at is not None
            else None,
            "args": self.args,
            "metainfo": self.metainfo,
            "account_address": self.address,
        }

    FIELDS = {
        "notification_id": int,
        "notification_type": str,
        "priority": int,
        "address": str,
        "is_read": bool,
        "is_flagged": bool,
        "is_deleted": bool,
        "deleted_at": datetime,
        "args": dict,
        "metainfo": dict,
    }

    FIELDS.update(Base.FIELDS)


# 通知を新着順でソート時に使用
Index("notification_index_1", Notification.address, Notification.notification_id)
# 通知を重要度→新着順でソート時に使用
Index(
    "notification_index_2",
    Notification.address,
    Notification.priority,
    Notification.notification_id,
)


class NotificationType(str, Enum):
    NEW_ORDER = "NewOrder"
    NEW_ORDER_COUNTERPART = "NewOrderCounterpart"
    CANCEL_ORDER = "CancelOrder"
    CANCEL_ORDER_COUNTERPART = "CancelOrderCounterpart"
    FORCE_CANCEL_ORDER = "ForceCancelOrder"
    BUY_AGREEMENT = "BuyAgreement"
    BUY_SETTLEMENT_OK = "BuySettlementOK"
    BUY_SETTLEMENT_NG = "BuySettlementNG"
    SELL_AGREEMENT = "SellAgreement"
    SELL_SETTLEMENT_OK = "SellSettlementOK"
    SELL_SETTLEMENT_NG = "SellSettlementNG"
    TRANSFER = "Transfer"
    APPLY_FOR_TRANSFER = "ApplyForTransfer"
    APPROVE_TRANSFER = "ApproveTransfer"
    CANCEL_TRANSFER = "CancelTransfer"


class NotificationBlockNumber(Base):
    """Synchronized blockNumber of Notification"""

    __tablename__ = "notification_block_number"

    # notification type: NotificationType
    notification_type = mapped_column(String(256), primary_key=True)
    # contract address
    contract_address = mapped_column(String(42), primary_key=True)
    # latest blockNumber
    latest_block_number = mapped_column(BigInteger)

    FIELDS = {
        "notification_type": str,
        "contract_address": str,
        "latest_block_number": int,
    }

    FIELDS.update(Base.FIELDS)
