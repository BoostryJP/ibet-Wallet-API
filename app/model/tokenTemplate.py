# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer

from app.model import Base

class TokenTemplate(Base):
    __tablename__ = 'token_template'
    id = Column(Integer, primary_key=True)
    template_name = Column(String(64), unique=True)
    solidity_code = Column(String(5024), nullable=True)
    abi = Column(String(5024), nullable=True)
    bytecode = Column(String(5024), nullable=False)
    bytecode_runtime = Column(String(5024), nullable=False)

    def __repr__(self):
        return "<TokenTemplate(template_name='%s',solidity_code='%s'," + \
            "abi='%s',bytecode='%s',bytecode_runtime='%s'," + \
            "eth_address='%s')>" % \
            (self.template_name, self.solidity_code, self.abi,
                self.bytecode, self.bytecode_runtime)

    @classmethod
    def get_id(cls):
        return TokenTemplate.id

    FIELDS = {
        'template_name': str,
        'solidity_code': str,
        'abi': str,
        'bytecode': str,
        'bytecode_runtime': str,
        }

    FIELDS.update(Base.FIELDS)
