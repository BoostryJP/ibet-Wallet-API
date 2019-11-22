# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import String, BigInteger, Boolean

from app.model import Base

class Listing(Base):
    __tablename__ = 'listing'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    token_address = Column(String(256), index=True)
    max_holding_quantity = Column(BigInteger)
    max_sell_amount = Column(BigInteger)
    payment_method_credit_card = Column(Boolean)
    payment_method_bank = Column(Boolean)

    def __repr__(self):
        return "<Listing id='%d'>" % \
            (self.id)

    FIELDS = {
        'id': int,
        'token_address': str,
        'token_template': str,
        'max_holding_quantity': int,
        'max_sell_amount': int,
        'payment_method_credit_card': bool,
        'payment_method_bank': bool,
    }

    FIELDS.update(Base.FIELDS)
