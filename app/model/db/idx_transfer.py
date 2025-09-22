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
from enum import StrEnum
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from sqlalchemy import JSON, BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config import TZ
from app.model.db.base import Base

UTC = timezone(timedelta(hours=0), "UTC")
local_tz = ZoneInfo(TZ)


class IDXTransferSourceEventType(StrEnum):
    """Transfer source event type"""

    TRANSFER = "Transfer"
    UNLOCK = "Unlock"
    FORCE_UNLOCK = "ForceUnlock"
    FORCE_CHANGE_LOCKED_ACCOUNT = "ForceChangeLockedAccount"
    REALLOCATION = "Reallocation"


class TransferDataMessage(BaseModel):
    message: Literal[
        "garnishment",
        "force_unlock",
        "ibet_wst_bridge",
    ]


class IDXTransfer(Base):
    """Token Transfer Events (INDEX)"""

    __tablename__ = "transfer"

    # Sequence Id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Transaction Hash
    transaction_hash: Mapped[str | None] = mapped_column(String(66), index=True)
    # Token Address
    token_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # Transfer From
    from_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # Transfer To
    to_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # Transfer Amount
    value: Mapped[int | None] = mapped_column(BigInteger, index=True)
    # Source Event
    source_event: Mapped[IDXTransferSourceEventType] = mapped_column(
        String(50), nullable=False
    )
    # Data
    #   source_event = "Transfer", "Reallocation"
    #     => None
    #   source_event = "Unlock", "ForceUnlock", "ForceChangeLockedAccount"
    #     =>  DataMessage
    data: Mapped[dict | None] = mapped_column(JSON)
    # Message
    #   source_event = "Transfer", "Reallocation"
    #     => None
    #   source_event = "Unlock", "ForceUnlock"
    #     => "force_unlock", "garnishment" or "inheritance"
    #   source_event = "ForceChangeLockedAccount"
    #     => "ibet_wst_bridge"
    message: Mapped[str | None] = mapped_column(String(50), index=True)

    @staticmethod
    def format_timestamp(_datetime: datetime) -> str:
        """Convert timestamp from UTC to local timezone str
        :param _datetime:
        :return: str
        """
        if _datetime is None:
            return ""
        datetime_local = _datetime.replace(tzinfo=UTC).astimezone(local_tz)
        return "{}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
            datetime_local.year,
            datetime_local.month,
            datetime_local.day,
            datetime_local.hour,
            datetime_local.minute,
            datetime_local.second,
        )

    def json(self):
        return {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": self.value,
            "source_event": self.source_event,
            "data": self.data,
            "message": self.message,
            "created": self.format_timestamp(self.created),
        }

    FIELDS = {
        "id": int,
        "transaction_hash": str,
        "token_address": str,
        "from_address": str,
        "to_address": str,
        "value": int,
        "source_event": str,
        "data": dict,
        "message": str,
    }
    FIELDS.update(Base.FIELDS)


class IDXTransferBlockNumber(Base):
    """Synchronized blockNumber of IDXTransfer"""

    __tablename__ = "idx_transfer_block_number"

    # target address
    contract_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # latest blockNumber
    latest_block_number: Mapped[int | None] = mapped_column(BigInteger)

    FIELDS = {
        "contract_address": str,
        "latest_block_number": int,
    }

    FIELDS.update(Base.FIELDS)
