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
from datetime import datetime

from sqlalchemy import DateTime, create_engine
from sqlalchemy.dialects.mysql import DATETIME as MySQLDATETIME
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

from app import config, log
from app.utils import alchemy

LOG = log.get_logger()

URI = config.DATABASE_URL
engine = create_engine(URI, echo=False)


class BaseModel(object):
    if engine.name == "mysql":
        # NOTE:MySQLではDatetime型で小数秒桁を指定しない場合、整数秒しか保存されない
        created: Mapped[datetime | None] = mapped_column(
            MySQLDATETIME(fsp=6), default=datetime.utcnow
        )
        modified: Mapped[datetime | None] = mapped_column(
            MySQLDATETIME(fsp=6), default=datetime.utcnow, onupdate=datetime.utcnow
        )
    else:
        created: Mapped[datetime | None] = mapped_column(
            DateTime, default=datetime.utcnow
        )
        modified: Mapped[datetime | None] = mapped_column(
            DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
        )

    @classmethod
    def find_one(cls, session, id):
        return session.query(cls).filter(cls.get_id() == id).one()

    @classmethod
    def find_update(cls, session, id, args):
        return (
            session.query(cls)
            .filter(cls.get_id() == id)
            .update(args, synchronize_session=False)
        )

    @classmethod
    def get_id(cls):
        pass

    def to_dict(self):
        intersection = set(self.__table__.columns.keys()) & set(self.FIELDS)
        return dict(
            map(
                lambda key: (
                    key,
                    (lambda value: self.FIELDS[key](value) if value else None)(
                        getattr(self, key)
                    ),
                ),
                intersection,
            )
        )

    FIELDS = {
        "created": alchemy.datetime_to_timestamp,
        "modified": alchemy.datetime_to_timestamp,
    }


Base = declarative_base(cls=BaseModel)
