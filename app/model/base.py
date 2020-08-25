# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy.ext.declarative import declarative_base

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
        return session.query(cls).filter(cls.get_id() == id).update(args, synchronize_session=False)

    @classmethod
    def get_id(cls):
        pass

    def to_dict(self):
        intersection = set(self.__table__.columns.keys()) & set(self.FIELDS)
        return dict(map(
            lambda key:
                (key,
                    (lambda value: self.FIELDS[key](value) if value else None)
                    (getattr(self, key))),
                intersection))

    FIELDS = {
        'created': alchemy.datetime_to_timestamp,
        'modified': alchemy.datetime_to_timestamp,
    }

Base = declarative_base(cls=BaseModel)
