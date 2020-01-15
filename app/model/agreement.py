# -*- coding: utf-8 -*-
from enum import Enum

from sqlalchemy import Column
from sqlalchemy import String, Integer, BigInteger, DateTime

from app.model import Base
from app.utils import alchemy


# 約定情報
class Agreement(Base):
    __tablename__ = 'agreement'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    exchange_address = Column(String(256), primary_key=True)
    order_id = Column(BigInteger, primary_key=True)
    agreement_id = Column(BigInteger, primary_key=True)
    unique_order_id = Column(String(256), index=True)  # NOTE: exchange_address + '_' + str(order_id)
    buyer_address = Column(String(256), index=True)
    seller_address = Column(String(256), index=True)
    counterpart_address = Column(String(256))
    amount = Column(BigInteger)
    status = Column(Integer)
    settlement_timestamp = Column(DateTime, default=None)

    def __repr__(self):
        return "<Agreement(exchange_address='%s', order_id='%d', agreement_id='%d')>" % \
               (self.exchange_address, self.order_id, self.agreement_id)

    FIELDS = {
        'id': int,
        'exchange_address': str,
        'order_id': int,
        'agreement_id': int,
        'unique_order_id': str,
        'buyer_address': str,
        'seller_address': str,
        'counterpart_address': str,
        'amount': int,
        'status': int,
        'settlement_timestamp': alchemy.datetime_to_timestamp,
    }

    FIELDS.update(Base.FIELDS)


class AgreementStatus(Enum):
    PENDING = 0
    DONE = 1
    CANCELED = 2
