# -*- coding: utf-8 -*-
from enum import Enum
from sqlalchemy import Column
from sqlalchemy import String, Integer, BigInteger
from sqlalchemy import UniqueConstraint

from app.model import Base

class OmiseCharge(Base):
    __tablename__ = 'omise_charge'
    __table_args__ = (UniqueConstraint('exchange_address','order_id','agreement_id'),{})
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    exchange_address = Column(String(256))
    order_id = Column(BigInteger)
    agreement_id = Column(BigInteger)
    status = Column(Integer)

    def __repr__(self):
        return "<OmiseCharge(exchange_address='%s', order_id='%d', agreement_id='%d')>" % \
            (self.exchange_address, self.order_id, self.agreement_id)

    FIELDS = {
        'id': int,
        'exchange_address': str,
        'order_id': int,
        'agreement_id': int,
        'status': int,
    }

    FIELDS.update(Base.FIELDS)

class OmiseChargeStatus(Enum):
    PROCESSING=0
    SUCCESS=1
    ERROR=2
