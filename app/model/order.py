# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer, BigInteger, Boolean

from app.model import Base

class Order(Base):
    __tablename__ = 'order'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    token_address = Column(String(256), index=True)
    exchange_address = Column(String(256), index=True)
    order_id = Column(BigInteger, index=True)
    unique_order_id = Column(String(256), index=True)
    account_address = Column(String(256))
    is_buy = Column(Boolean)
    price = Column(BigInteger)
    amount = Column(BigInteger)
    agent_address = Column(String(256))
    is_cancelled = Column(Boolean)

    def __repr__(self):
        return "<Order id='%d'>" % \
            (self.id)

    FIELDS = {
        'id': int,
        'token_address': str,
        'exchange_address': str,
        'order_id': int,
        'account_address': str,
        'is_buy': bool,
        'price': int,
        'amount': int,
        'agent_address': str,
        'is_cancelled': bool,
    }

    FIELDS.update(Base.FIELDS)
