# -*- coding: utf-8 -*-
from enum import Enum
from sqlalchemy import Column
from sqlalchemy import String, Integer, BigInteger
from sqlalchemy import UniqueConstraint

from app.model import Base

class StripeCharge(Base):
    __tablename__ = 'stripe_charge'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    exchange_address = Column(String(256))
    account_id = Column(BigInteger)
    customer_id = Column(BigInteger)
    order_id = Column(BigInteger)
    agreement_id = Column(BigInteger)
    status = Column(Integer)

    def __repr__(self):
        return "<StripeCharge(exchange_address='%s', order_id='%d', agreement_id='%d')>" % \
            (self.exchange_address, self.order_id, self.agreement_id)

    FIELDS = {
        'id': int,
        'exchange_address': str,
        'account_id': int,
        'customer_id': int,
        'order_id': int,
        'agreement_id': int,
        'status': int,
    }

    FIELDS.update(Base.FIELDS)

class StripeChargeStatus(Enum):
    PENDING = 0
    SUCCEEDED = 1
    FAILED = 2
