# -*- coding: utf-8 -*-
from enum import Enum
from sqlalchemy import Column
from sqlalchemy import String, Integer, BigInteger

from app.model import Base

class OmiseCharge(Base):
    __tablename__ = 'omise_charge'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    exchange_address = Column(String(256), primary_key=True)
    order_id = Column(BigInteger, primary_key=True)
    agreement_id = Column(BigInteger, primary_key=True)
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
