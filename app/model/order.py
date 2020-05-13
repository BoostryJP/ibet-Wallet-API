# -*- coding: utf-8 -*-
from sqlalchemy import Column, DateTime
from sqlalchemy import String, BigInteger, Boolean

from app.model import Base
from app.utils import alchemy


class Order(Base):
    __tablename__ = 'order'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    transaction_hash = Column(String(66))
    token_address = Column(String(42), index=True)
    exchange_address = Column(String(42), index=True)
    order_id = Column(BigInteger, index=True)
    unique_order_id = Column(String(256), index=True)
    account_address = Column(String(42))
    is_buy = Column(Boolean)
    price = Column(BigInteger)
    amount = Column(BigInteger)
    agent_address = Column(String(42))
    is_cancelled = Column(Boolean)
    order_timestamp = Column(DateTime, default=None)

    def __repr__(self):
        return "<Order(exchange_address='%s', order_id='%d')>" % \
               (self.exchange_address, self.order_id)

    FIELDS = {
        'id': int,
        'transaction_hash': str,
        'token_address': str,
        'exchange_address': str,
        'order_id': int,
        'account_address': str,
        'is_buy': bool,
        'price': int,
        'amount': int,
        'agent_address': str,
        'is_cancelled': bool,
        'order_timestamp': alchemy.datetime_to_timestamp,
    }

    FIELDS.update(Base.FIELDS)
