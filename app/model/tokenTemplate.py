# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer

from app.model import Base

class TokenTemplate(Base):
    __tablename__ = 'token_template'
    id = Column(Integer, primary_key=True)
    template_name = Column(String(64), unique=True)
    abi = Column(String(15360), nullable=True)

    def __repr__(self):
        return "<TokenTemplate(template_name='%s',abi='%s')>" % \
            (self.template_name, self.abi)

    @classmethod
    def get_id(cls):
        return TokenTemplate.id

    FIELDS = {
        'template_name': str,
        'abi': str,
        }

    FIELDS.update(Base.FIELDS)
