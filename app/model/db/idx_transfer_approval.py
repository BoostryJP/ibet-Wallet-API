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

from sqlalchemy import BigInteger, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config import TZ
from app.model.db.base import Base

UTC = timezone(timedelta(hours=0), "UTC")
local_tz = ZoneInfo(TZ)


class IDXTransferApproval(Base):
    """Token Transfer Approval Events (INDEX)"""

    __tablename__ = "transfer_approval"

    # Sequence Id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Token Address
    token_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # Exchange Address (value is set if the event is from exchange)
    exchange_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # Application Id
    application_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    # Transfer From
    from_address: Mapped[str | None] = mapped_column(String(42))
    # Transfer To
    to_address: Mapped[str | None] = mapped_column(String(42))
    # Transfer Amount
    value: Mapped[int | None] = mapped_column(BigInteger)
    # Application Datetime
    application_datetime: Mapped[datetime | None] = mapped_column(DateTime)
    # Application Blocktimestamp
    application_blocktimestamp: Mapped[datetime | None] = mapped_column(DateTime)
    # Approval Datetime (ownership vesting datetime)
    approval_datetime: Mapped[datetime | None] = mapped_column(DateTime)
    # Approval Blocktimestamp (ownership vesting block timestamp)
    approval_blocktimestamp: Mapped[datetime | None] = mapped_column(DateTime)
    # Cancellation Status
    cancelled: Mapped[bool | None] = mapped_column(Boolean)
    # Escrow Finished Status
    escrow_finished: Mapped[bool | None] = mapped_column(Boolean)
    # Approve Status
    transfer_approved: Mapped[bool | None] = mapped_column(Boolean)

    @staticmethod
    def format_datetime(_datetime: datetime) -> str:
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
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": self.application_id,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": self.value,
            "application_datetime": self.format_datetime(self.application_datetime),
            "application_blocktimestamp": self.format_datetime(
                self.application_blocktimestamp
            ),
            "approval_datetime": self.format_datetime(self.approval_datetime),
            "approval_blocktimestamp": self.format_datetime(
                self.approval_blocktimestamp
            ),
            "cancelled": self.cancelled,
            "escrow_finished": self.escrow_finished,
            "transfer_approved": self.transfer_approved,
        }


class IDXTransferApprovalBlockNumber(Base):
    """Synchronized blockNumber of IDXTransferApproval"""

    __tablename__ = "idx_transfer_approval_block_number"

    # sequence id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # target token address
    token_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # target exchange address
    exchange_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # latest blockNumber
    latest_block_number: Mapped[int | None] = mapped_column(BigInteger)
