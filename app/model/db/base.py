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

from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base

from app import log
from app.utils import alchemy

LOG = log.get_logger()


class BaseModel(object):
    created = Column(DateTime, default=datetime.utcnow)
    modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
