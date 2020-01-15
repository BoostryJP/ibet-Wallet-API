# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import String, BigInteger, DateTime

from app.model import Base

class ConsumeCoupon(Base):
    __tablename__ = 'consume_coupon'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    transaction_hash = Column(String(66), index=True)
    token_address = Column(String(42), index=True)
    account_address = Column(String(42), index=True)
    amount = Column(BigInteger)
    block_timestamp = Column(DateTime, default=None)

    def __repr__(self):
        return "<ConsumeCoupon id='%d'>" % \
            (self.id)

    FIELDS = {
        'id': int,
        'transaction_hash': str,
        'token_address': str,
        'account_address': str,
        'amount': int,
        'block_timestamp': str
    }

    FIELDS.update(Base.FIELDS)
