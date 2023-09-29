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

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import JSON, BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config import TZ
from app.model.db.base import Base

UTC = timezone(timedelta(hours=0), "UTC")
local_tz = ZoneInfo(TZ)


class IDXLock(Base):
    """Token Lock Event (INDEX)"""

    __tablename__ = "lock"

    # Sequence Id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Transaction Hash
    transaction_hash: Mapped[str] = mapped_column(
        String(66), index=True, nullable=False
    )
    # Message Sender of Transaction
    msg_sender: Mapped[str | None] = mapped_column(
        String(42), index=True, nullable=True
    )
    # Block Number
    block_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Token Address
    token_address: Mapped[str] = mapped_column(String(42), index=True, nullable=False)
    # Lock Address
    lock_address: Mapped[str] = mapped_column(String(42), index=True, nullable=False)
    # Account Address
    account_address: Mapped[str] = mapped_column(String(42), index=True, nullable=False)
    # Locked Amount
    value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Data
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Lock Datetime
    block_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    FIELDS = {
        "id": int,
        "transaction_hash": str,
        "msg_sender": str,
        "block_number": int,
        "token_address": str,
        "lock_address": str,
        "account_address": str,
        "value": int,
        "data": dict,
        "block_timestamp": datetime,
    }
    FIELDS.update(Base.FIELDS)

    @staticmethod
    def replace_to_local_tz(_datetime: datetime) -> datetime | None:
        """Convert timestamp from UTC to local timezone
        :param _datetime:
        :return: datetime | None
        """
        if _datetime is None:
            return None
        datetime_local = _datetime.replace(tzinfo=UTC).astimezone(local_tz)
        return datetime_local

    def json(self):
        return {
            "id": self.id,
            "transaction_hash": self.transaction_hash,
            "msg_sender": self.msg_sender,
            "block_number": self.block_number,
            "token_address": self.token_address,
            "lock_address": self.lock_address,
            "account_address": self.account_address,
            "value": self.value,
            "data": self.data,
            "block_timestamp": self.replace_to_local_tz(self.block_timestamp),
        }


class IDXUnlock(Base):
    """Token Unlock Event (INDEX)"""

    __tablename__ = "unlock"

    # Sequence Id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Transaction Hash
    transaction_hash: Mapped[str] = mapped_column(
        String(66), index=True, nullable=False
    )
    # Message Sender of Transaction
    msg_sender: Mapped[str | None] = mapped_column(
        String(42), index=True, nullable=True
    )
    # Block Number
    block_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Token Address
    token_address: Mapped[str] = mapped_column(String(42), index=True, nullable=False)
    # Lock Address
    lock_address: Mapped[str] = mapped_column(String(42), index=True, nullable=False)
    # Account Address
    account_address: Mapped[str] = mapped_column(String(42), index=True, nullable=False)
    # Recipient Address
    recipient_address: Mapped[str] = mapped_column(
        String(42), index=True, nullable=False
    )
    # Locked Amount
    value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Data
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Lock Datetime
    block_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    FIELDS = {
        "id": int,
        "transaction_hash": str,
        "msg_sender": str,
        "block_number": int,
        "token_address": str,
        "lock_address": str,
        "account_address": str,
        "recipient_address": str,
        "value": int,
        "data": dict,
        "block_timestamp": datetime,
    }
    FIELDS.update(Base.FIELDS)

    @staticmethod
    def replace_to_local_tz(_datetime: datetime) -> datetime | None:
        """Convert timestamp from UTC to local timezone
        :param _datetime:
        :return: datetime | None
        """
        if _datetime is None:
            return None
        datetime_local = _datetime.replace(tzinfo=UTC).astimezone(local_tz)
        return datetime_local

    def json(self):
        return {
            "id": self.id,
            "transaction_hash": self.transaction_hash,
            "msg_sender": self.msg_sender,
            "block_number": self.block_number,
            "token_address": self.token_address,
            "lock_address": self.lock_address,
            "account_address": self.account_address,
            "recipient_address": self.recipient_address,
            "value": self.value,
            "data": self.data,
            "block_timestamp": self.replace_to_local_tz(self.block_timestamp),
        }
