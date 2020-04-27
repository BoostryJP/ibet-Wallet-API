# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import String, BigInteger

from app.model import Base


class Transfer(Base):
    """
    トークン移転（Event）
    """
    __tablename__ = 'transfer'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    transaction_hash = Column(String(66), index=True)
    token_address = Column(String(42), index=True)
    from_address = Column(String(42))
    to_address = Column(String(42))
    value = Column(BigInteger)

    def __repr__(self):
        return "<Transfer(transaction_hash='%s', token_address='%s', from_address='%s', to_address='%s', value='%d')>" % \
               (self.transaction_hash, self.token_address, self.from_address, self.to_address, self.value)

    FIELDS = {
        'id': int,
        'transaction_hash': str,
        'token_address': str,
        'from_address': str,
        'to_address': str,
        'value': int,
    }

    FIELDS.update(Base.FIELDS)
