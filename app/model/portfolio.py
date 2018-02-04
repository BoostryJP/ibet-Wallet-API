# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import String, Integer

from app.model import Base

class Portfolio(Base):
    __tablename__ = 'portfolio'
    id = Column(Integer, primary_key=True)
    account_address = Column(String(64), nullable=True)
    contract_address = Column(String(64), nullable=True)

    def __repr__(self):
        return "<Portfolio(account_address'='%s',contract_address='%s')>" % \
            (self.account_address, self.contract_address)

    @classmethod
    def get_id(cls):
        return Portfolio.id

    FIELDS = {
        'account_address': str,
        'contract_address': str,
        }

    FIELDS.update(Base.FIELDS)
