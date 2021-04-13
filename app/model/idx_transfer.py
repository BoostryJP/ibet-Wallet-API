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
from sqlalchemy import (
    Column,
    String,
    BigInteger
)
from datetime import (
    datetime,
    timedelta,
    timezone
)

from app.model import Base

UTC = timezone(timedelta(hours=0), "UTC")
JST = timezone(timedelta(hours=+9), "JST")


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

    @staticmethod
    def format_timestamp(_datetime: datetime) -> str:
        """UTCからJSTへ変換
        :param _datetime:
        :return:
        """
        if _datetime is None:
            return ""
        datetime_jp = _datetime.replace(tzinfo=UTC).astimezone(JST)
        return datetime_jp.strftime("%Y/%m/%d %H:%M:%S")

    def json(self):
        return {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": self.value,
            "created": self.format_timestamp(self.created),
        }

    FIELDS = {
        "id": int,
        "transaction_hash": str,
        "token_address": str,
        "from_address": str,
        "to_address": str,
        "value": int,
    }
    FIELDS.update(Base.FIELDS)
