# -*- coding: utf-8 -*-
from enum import Enum

from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer, BigInteger, Boolean

from app.model import Base

class Agreement(Base):
    __tablename__ = 'agreement'
    id = Column(BigInteger, autoincrement=True)
    exchange_address = Column(String(256), primary_key=True)
    order_id = Column(BigInteger, primary_key=True)
    agreement_id = Column(BigInteger, primary_key=True)
    unique_order_id = Column(String(256), index=True)
    buyer_address = Column(String(256), index=True)
    seller_address = Column(String(256), index=True)
    counterpart_address = Column(String(256))
    amount = Column(BigInteger)
    status = Column(Integer)

    def __repr__(self):
        return "<Agreement(exchange_address='%s', order_id='%d', agreement_id='%d')>" % \
            (self.exchange_address, self.order_id, self.agreement_id)

    FIELDS = {
        'id': int,    
        'exchange_address': str,
        'order_id': int,
        'agreement_id': int,
        'unique_order_id': str,
        'buyer_address': str,
        'seller_address': str,
        'counterpart_address': str,
        'amount': int,
        'status': int,
    }

    FIELDS.update(Base.FIELDS)

class AgreementStatus(Enum):
    PENDING=0
    DONE=1
    CANCELED=2
