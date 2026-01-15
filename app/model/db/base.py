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

from datetime import UTC, datetime

from sqlalchemy import DateTime, create_engine
from sqlalchemy.dialects.mysql import DATETIME as MySQLDATETIME
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app import config, log

LOG = log.get_logger()

URI = config.DATABASE_URL
engine = create_engine(URI, echo=False)


def aware_utcnow():
    return datetime.now(UTC)


def naive_utcnow():
    return aware_utcnow().replace(tzinfo=None)


class Base(DeclarativeBase):
    if engine.name == "mysql":
        # NOTE:MySQLではDatetime型で小数秒桁を指定しない場合、整数秒しか保存されない
        created: Mapped[datetime | None] = mapped_column(
            MySQLDATETIME(fsp=6), default=naive_utcnow
        )
        modified: Mapped[datetime | None] = mapped_column(
            MySQLDATETIME(fsp=6), default=naive_utcnow, onupdate=naive_utcnow
        )
    else:
        created: Mapped[datetime | None] = mapped_column(DateTime, default=naive_utcnow)
        modified: Mapped[datetime | None] = mapped_column(
            DateTime, default=naive_utcnow, onupdate=naive_utcnow
        )
