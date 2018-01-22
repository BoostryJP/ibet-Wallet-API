# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer

from app.model import Base

class Issuer(Base):
    __tablename__ = 'issuers'
    id = Column(Integer, primary_key=True)
    eth_address = Column(String(64), unique=True, index=True)
    user_name = Column(String(64), unique=False, index=True)
    token = Column(String(255), nullable=True)

    def __repr__(self):
        return "<Issuer(eth_address='%s',user_name='%s')>" % \
            (self.eth_address, self.user_name)

    @classmethod
    def get_id(cls):
        return User.id

    FIELDS = {
        'eth_address': str,
        'user_name': str,
        'token': str
    }

    FIELDS.update(Base.FIELDS)
