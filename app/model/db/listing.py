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
from sqlalchemy.dialects.mysql import DATETIME as MySQLDATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.config import TZ
from app.database import engine
from app.model.db.base import Base, naive_utcnow

UTC = timezone(timedelta(hours=0), "UTC")
local_tz = ZoneInfo(TZ)


class Listing(Base):
    """
    取扱対象トークン
    """

    __tablename__ = "listing"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    token_address: Mapped[str | None] = mapped_column(
        String(256), index=True
    )  # トークンアドレス
    is_public: Mapped[bool | None] = mapped_column(Boolean)
    max_holding_quantity: Mapped[int | None] = mapped_column(BigInteger)  # 最大保有数量
    max_sell_amount: Mapped[int | None] = mapped_column(BigInteger)  # 売却価格上限
    owner_address: Mapped[str | None] = mapped_column(String(256))  # 発行体アドレス

    if engine.name == "mysql":
        # NOTE:MySQLではDatetime型で小数秒桁を指定しない場合、整数秒しか保存されない
        created: Mapped[datetime | None] = mapped_column(
            MySQLDATETIME(fsp=6), default=naive_utcnow, index=True
        )
    else:
        created: Mapped[datetime | None] = mapped_column(
            DateTime, default=naive_utcnow, index=True
        )

    def __repr__(self):
        return "<Listing id='%d'>" % self.id

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
            "id": self.id,
            "token_address": self.token_address,
            "is_public": self.is_public,
            "max_holding_quantity": self.max_holding_quantity,
            "max_sell_amount": self.max_sell_amount,
            "owner_address": self.owner_address,
            "created": self.format_timestamp(self.created),
        }
