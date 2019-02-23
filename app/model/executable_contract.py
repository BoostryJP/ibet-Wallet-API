# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import String, Integer, BigInteger, Boolean

from app.model import Base

class ExecutableContract(Base):
    __tablename__ = 'executable_contract'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    contract_address = Column(String(256), index=True)

    def __repr__(self):
        return "<Listing id='%d' contract_address='%s'>" % \
            (self.id, self.contract_address)

    FIELDS = {
        'id': int,
        'contract_address': str,
    }

    FIELDS.update(Base.FIELDS)
