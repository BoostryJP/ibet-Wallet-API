# -*- coding: utf-8 -*-
import sys
from enum import Enum
from sqlalchemy import Column, Index, BigInteger, Sequence
from sqlalchemy import String, Integer, Boolean, DateTime, JSON

from datetime import datetime, timedelta, timezone

from app.model import Base

UTC = timezone(timedelta(hours=0), "UTC")
JST = timezone(timedelta(hours=+9), "JST")


# 通知データをキャッシュするためのテーブル
# 既読情報や重要フラグの情報なども保存される
class Notification(Base):
    __tablename__ = 'notification'

    # レコードIDのシーケンス
    notification_id_seq = Sequence(
        "notification_id_seq",
        start=1,
        increment=1,
        minvalue=1,
        maxvalue=sys.maxsize,
        cache=1
    )

    # レコードID
    id = Column(BigInteger, server_default=Sequence("notification_id_seq").next_value(), autoincrement=True)

    # 通知ID
    # Spec: 0x | <blockNumber> | <transactionIndex> | <logIndex> | <optionType>
    #   ( | は文字列連結 )
    #   <blockNumber>: blockNumberをhexstringで表現したもの。12桁
    #   <transactionIndex>: transactionIndex（block内でのトランザクションの採番）をhexstringで表現したもの。6桁
    #   <logIndex>: logIndex（transaction内でのログの採番）をhexstringで表現したもの。6桁
    #   <optionType>: blockNumber, transactionIndex, logIndexが等しいが、通知としては複数にしたい場合に使用する識別子。2桁(デフォルトは00)
    notification_id = Column(String(256), primary_key=True)

    # 通知タイプ(例：BuySettlementOK, BuyAgreementなど)
    notification_type = Column(String(256))

    # 通知の重要度
    #   0: Low
    #   1: Medium
    #   2: High
    priority = Column(Integer)

    # 通知対象のユーザーのアドレス
    address = Column(String(256))

    # 既読フラグ
    is_read = Column(Boolean, default=False)
    # 重要フラグ
    is_flagged = Column(Boolean, default=False)
    # 削除フラグ
    is_deleted = Column(Boolean, default=False)
    # 削除日付
    deleted_at = Column(DateTime, default=None)

    # 通知が発生した日付（blockTime）
    block_timestamp = Column(DateTime)

    # 通知イベントの内容
    args = Column(JSON)
    # 通知のメタデータ（通知イベントには入っていないが、取りたい情報。トークン名など）
    metainfo = Column(JSON)

    def __repr__(self):
        return "<Notification(notification_id='{}', notification_type='{}')>" \
            .format(self.notification_id, self.notification_type)

    @staticmethod
    def format_timestamp(datetime):
        if datetime is None:
            return None
        # DBにはUTCで書き込まれているため、UTC -> JSTへの変換を実施
        datetimejp = datetime.replace(tzinfo=UTC).astimezone(JST)
        return datetimejp.strftime("%Y/%m/%d %H:%M:%S")

    def json(self):
        return {
            "notification_type": self.notification_type,
            "id": self.notification_id,
            "priority": self.priority,
            "block_timestamp": Notification.format_timestamp(self.block_timestamp),
            "is_read": self.is_read,
            "is_flagged": self.is_flagged,
            "is_deleted": self.is_deleted,
            "deleted_at": Notification.format_timestamp(self.deleted_at),
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
Index("notification_index_2", Notification.address, Notification.priority, Notification.notification_id)


class NotificationType(Enum):
    NEW_ORDER = "NewOrder"
    CANCEL_ORDER = "CancelOrder"
    BUY_AGREEMENT = "BuyAgreement"
    BUY_SETTLEMENT_OK = "BuySettlementOK"
    BUY_SETTLEMENT_NG = "BuySettlementNG"
    SELL_AGREEMENT = "SellAgreement"
    SELL_SETTLEMENT_OK = "SellSettlementOK"
    SELL_SETTLEMENT_NG = "SellSettlementNG"
    START_INITIAL_OFFERING = "StartInitialOffering"
    STOP_INITIAL_OFFERING = "StopInitialOffering"
    REDEEM = "Redeem"
    APPLY_FOR_OFFERING = "ApplyForOffering"
    ALLOT = "Allot"
    TRANSFER = "Transfer"
    PAYMENT_ACCOUNT_REGISTER = "PaymentAccountRegister"
    PAYMENT_ACCOUNT_APPROVE = "PaymentAccountApprove"
    PAYMENT_ACCOUNT_UNAPPROVE = "PaymentAccountUnapprove"
    PAYMENT_ACCOUNT_WARN = "PaymentAccountWarn"
    PAYMENT_ACCOUNT_BAN = "PaymentAccountBan"
