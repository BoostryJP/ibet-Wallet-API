# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer, BigInteger, Boolean

from app.model import Base

class Listing(Base):
    __tablename__ = 'listing'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    token_address = Column(String(256), index=True)
    exchange_address = Column(String(256), index=True)
    credit_card_availability = Column(Boolean)
    bank_payment_availability = Column(Boolean)

    def __repr__(self):
        return "<Listing id='%d'>" % \
            (self.id)

    FIELDS = {
        'id': int,
        'token_address': str,
        'credit_card_availability': bool,
        'bank_payment_availability': bool,
    }

    FIELDS.update(Base.FIELDS)
