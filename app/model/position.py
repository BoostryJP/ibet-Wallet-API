# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import String, BigInteger

from app.model import Base

"""
トークン保有残高
"""
class Position(Base):
    __tablename__ = 'position'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    token_address = Column(String(42), index=True)
    account_address = Column(String(42))
    balance = Column(BigInteger)

    def __repr__(self):
        return "<Position(token_address='%s', account_address='%s', balance='%d')>" % \
            (self.token_address, self.account_address, self.balance)

    FIELDS = {
        'id': int,
        'token_address': str,
        'account_address': str,
        'position': int,
    }

    FIELDS.update(Base.FIELDS)