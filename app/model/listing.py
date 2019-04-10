# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer, BigInteger, Boolean

from app.model import Base

class Listing(Base):
    __tablename__ = 'listing'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    token_address = Column(String(256), index=True)
    payment_method_credit_card = Column(Boolean)
    payment_method_bank = Column(Boolean)

    def __repr__(self):
        return "<Listing id='%d'>" % \
            (self.id)

    FIELDS = {
        'id': int,
        'token_address': str,
        'payment_method_credit_card': bool,
        'payment_method_bank': bool,
    }

    FIELDS.update(Base.FIELDS)
