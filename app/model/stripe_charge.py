# -*- coding: utf-8 -*-
from enum import Enum
from sqlalchemy import Column
from sqlalchemy import String, Integer, BigInteger
from sqlalchemy import UniqueConstraint

from app.model import Base

class StripeCharge(Base):
    __tablename__ = 'stripe_charge'
    __table_args__ = (UniqueConstraint('exchange_address','order_id','agreement_id'),{})
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    exchange_address = Column(String(256))
    account_id = Column(BigInteger)
    customer_id = Column(BigInteger)
    order_id = Column(BigInteger)
    agreement_id = Column(BigInteger)
    status = Column(Integer)

    def __repr__(self):
        return "<StripeCharge(exchange_address='%s', order_id='%d', agreement_id='%d')>" % \
            (self.exchange_address, self.order_id, self.agreement_id)

    FIELDS = {
        'id': int,
        'exchange_address': str,
        'account_id': int,
        'customer_id': int,
        'order_id': int,
        'agreement_id': int,
        'status': int,
    }

    FIELDS.update(Base.FIELDS)

class StripeChargeStatus(Enum):
    PROCESSIN = 0
    SUCCESS = 1
    ERROR = 2

class StripeKYCStatus(Enum):
    Pending = 0     # 本人確認書類提出済みでStripe側で確認中。
    Unverified = 1  # 本人確認書類が提出されていない、またはStripe側で確認できない
    Verified = 2    # 本人確認（審査）が完了


