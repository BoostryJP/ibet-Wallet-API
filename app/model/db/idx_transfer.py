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
from enum import Enum
from zoneinfo import ZoneInfo

from sqlalchemy import JSON, BigInteger, Column, String

from app.config import TZ
from app.model.db.base import Base

UTC = timezone(timedelta(hours=0), "UTC")
local_tz = ZoneInfo(TZ)


class IDXTransferSourceEventType(str, Enum):
    """Transfer source event type"""

    TRANSFER = "Transfer"
    UNLOCK = "Unlock"


class IDXTransfer(Base):
    """Token Transfer Events (INDEX)"""

    __tablename__ = "transfer"

    # Sequence Id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Transaction Hash
    transaction_hash = Column(String(66), index=True)
    # Token Address
    token_address = Column(String(42), index=True)
    # Transfer From
    from_address = Column(String(42))
    # Transfer To
    to_address = Column(String(42))
    # Transfer Amount
    value = Column(BigInteger)
    # Source Event (IDXTransferSourceEventType)
    source_event = Column(String(50), nullable=False)
    # Data
    data = Column(JSON)

    @staticmethod
    def format_timestamp(_datetime: datetime) -> str:
        """Convert timestamp from UTC to local timezone str
        :param _datetime:
        :return: str
        """
        if _datetime is None:
            return ""
        datetime_local = _datetime.replace(tzinfo=UTC).astimezone(local_tz)
        return datetime_local.strftime("%Y/%m/%d %H:%M:%S")

    def json(self):
        return {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": self.value,
            "source_event": self.source_event,
            "data": self.data,
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
    }
    FIELDS.update(Base.FIELDS)


class IDXTransferBlockNumber(Base):
    """Synchronized blockNumber of IDXTransfer"""

    __tablename__ = "idx_transfer_block_number"

    # target address
    contract_address = Column(String(42), primary_key=True)
    # latest blockNumber
    latest_block_number = Column(BigInteger)

    FIELDS = {
        "contract_address": str,
        "latest_block_number": int,
    }

    FIELDS.update(Base.FIELDS)
