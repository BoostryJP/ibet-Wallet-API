# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import String, Integer

from app.model import Base

class Contract(Base):
    __tablename__ = 'contract'
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, nullable=False)
    tx_hash = Column(String(128), nullable=False)
    admin_address = Column(String(64), nullable=True)
    contract_address = Column(String(64), nullable=True)

    def __repr__(self):
        return "<Contract(admin_address='%s',template_id='%i'," + \
            "'tx_hash'='%s')>" % \
            (self.admin_address, self.template_id, self.tx_hash, self.contract_address)

    @classmethod
    def get_id(cls):
        return Contract.id

    FIELDS = {
        'admin_address': str,
        'template_id': int,
        'tx_hash': str,
        'contract_address': str,
        }

    FIELDS.update(Base.FIELDS)
