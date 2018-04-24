# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer, BigInteger, Boolean

from app.model import Base

class Agreement(Base):
    __tablename__ = 'agreement'
    orderId = Column(BigInteger, primary_key=True)
    agreementId = Column(BigInteger, primary_key=True)
    counterpart_address = Column(String(256))
    amount = Column(BigInteger)
    status = Column(Integer)
