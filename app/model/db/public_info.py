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
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config import TZ
from app.model.db.base import Base

UTC = timezone(timedelta(hours=0), "UTC")
local_tz = ZoneInfo(TZ)


class TokenList(Base):
    """
    Token List

    - Information on issued tokens and associated institutions (key managers)
    """

    __tablename__ = "token_list"

    # Token Address
    token_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # Token Template
    token_template: Mapped[
        Literal["ibetBond", "ibetShare", "ibetMembership", "ibetCoupon"]
    ] = mapped_column(String(50), nullable=False)
    # Key Manager
    key_manager: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    # Product Type
    product_type: Mapped[int] = mapped_column(Integer, nullable=False)

    def json(self):
        return {
            "token_address": self.token_address,
            "token_template": self.token_template,
            "key_manager": self.key_manager,
            "product_type": self.product_type,
        }


class PublicAccountList(Base):
    """
    Public Account List

    - Public account information of ibet consortium members
    """

    __tablename__ = "public_account_list"

    # Key Manager
    key_manager: Mapped[str] = mapped_column(String(20), primary_key=True)
    # Key Manager Name
    key_manager_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Account Type
    account_type: Mapped[Literal[1, 2, 3, 4]] = mapped_column(Integer, primary_key=True)
    # Account Address
    account_address: Mapped[str] = mapped_column(String(42), nullable=False)

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
            "key_manager": self.key_manager,
            "key_manager_name": self.key_manager_name,
            "account_type": self.account_type,
            "account_address": self.account_address,
            "modified": self.format_timestamp(self.modified),
        }
