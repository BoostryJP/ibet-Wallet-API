# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer, BigInteger, Boolean

from app.model import Base

class Push(Base):
    __tablename__ = 'push'
    id = Column(BigInteger, primary_key=True)
    device_id = Column(String(256), index=True)
    account_address = Column(String(256))
    device_token = Column(String(256))
    device_endpoint_arn = Column(String(256))
    platform = Column(String(32))
    
    def __repr__(self):
        return "<Push id='%d'>" % \
            (self.id)

    FIELDS = {
        'id': int,
        'device_id': str,
        'account_address': str,
        'device_token': str,
        'device_endpoint_arn': str,
        'platform':str
    }

    FIELDS.update(Base.FIELDS)
