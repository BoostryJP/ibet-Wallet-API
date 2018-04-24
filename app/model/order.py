# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer, BigInteger, Boolean

from app.model import Base

class Order(Base):
    __tablename__ = 'order'
    id = Column(BigInteger, primary_key=True)
    token_address = Column(String(256))
    account_address = Column(String(256))
    is_buy = Column(Boolean)
    price = Column(BigInteger)
    amount = Column(BigInteger)
    agent_address = Column(String(256))
    is_cancelled = Column(Boolean)
