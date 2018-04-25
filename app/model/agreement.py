# -*- coding: utf-8 -*-
from enum import Enum

from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer, BigInteger, Boolean

from app.model import Base

class Agreement(Base):
    __tablename__ = 'agreement'
    order_id = Column(BigInteger, primary_key=True)
    agreement_id = Column(BigInteger, primary_key=True)
    counterpart_address = Column(String(256))
    amount = Column(BigInteger)
    status = Column(Integer)

    def __repr__(self):
        return "<Agreement(order_id='%d', agreement_id='%d')>" % \
            (self.order_id, self.agreement_id)

    FIELDS = {
        'order_id': int,
        'agreement_id': int,
        'counterpart_address': int,
        'amount': int,
        'status': int,
    }

    FIELDS.update(Base.FIELDS)

class AgreementStatus(Enum):
    PENDING=0
    DONE=1
    CANCELED=2

