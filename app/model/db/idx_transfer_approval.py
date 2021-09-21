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
from datetime import (
    datetime,
    timezone,
    timedelta
)

from sqlalchemy import (
    Column,
    String,
    BigInteger,
    DateTime,
    Boolean
)

from app.model import Base
from app.utils import alchemy

UTC = timezone(timedelta(hours=0), "UTC")
JST = timezone(timedelta(hours=+9), "JST")


class IDXTransferApproval(Base):
    """Token Transfer Approval Events (INDEX)"""
    __tablename__ = "transfer_approval"

    # Sequence Id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Token Address
    token_address = Column(String(42), index=True)
    # Application Id
    application_id = Column(BigInteger, index=True)
    # Transfer From
    from_address = Column(String(42))
    # Transfer To
    to_address = Column(String(42))
    # Transfer Amount
    value = Column(BigInteger)
    # Application Datetime
    application_datetime = Column(DateTime)
    # Application Blocktimestamp
    application_blocktimestamp = Column(DateTime)
    # Approval Datetime
    approval_datetime = Column(DateTime)
    # Approval Blocktimestamp
    approval_blocktimestamp = Column(DateTime)
    # Cancellation Status
    cancelled = Column(Boolean)

    @staticmethod
    def format_datetime(_datetime: datetime) -> str:
        if _datetime is None:
            return ""
        _datetime = _datetime.replace(tzinfo=UTC).astimezone(JST)
        return _datetime.strftime("%Y/%m/%d %H:%M:%S.%f")

    def json(self):
        return {
            "token_address": self.token_address,
            "application_id": self.application_id,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": self.value,
            "application_datetime": self.format_datetime(self.application_datetime),
            "application_blocktimestamp": self.format_datetime(self.application_blocktimestamp),
            "approval_datetime": self.format_datetime(self.approval_datetime),
            "approval_blocktimestamp": self.format_datetime(self.approval_blocktimestamp),
            "cancelled": self.cancelled
        }

    FIELDS = {
        "id": int,
        "token_address": str,
        "application_id": int,
        "from_address": str,
        "to_address": str,
        "value": int,
        "application_datetime": alchemy.datetime_to_timestamp,
        "application_blocktimestamp": alchemy.datetime_to_timestamp,
        "approval_datetime": alchemy.datetime_to_timestamp,
        "approval_blocktimestamp": alchemy.datetime_to_timestamp,
        "cancelled": bool
    }
    FIELDS.update(Base.FIELDS)
