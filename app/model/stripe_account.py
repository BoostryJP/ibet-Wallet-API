# -*- coding: utf-8 -*-
from enum import Enum
from sqlalchemy import Column
from sqlalchemy import String, BigInteger
from sqlalchemy import UniqueConstraint

from app.model import Base


class StripeAccount(Base):
    __tablename__ = 'stripe_account'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    account_address = Column(String(256))
    account_id = Column(String(256))
    customer_id = Column(String(256))

    def __repr__(self):
        return "<StripeAccount(account_address='%s', account_id='%s', customer_id='%s')>" % \
            (self.account_address, self.account_id, self.customer_id)

    FIELDS = {
        'id': int,
        'account_address': str,
        'account_id': str,
        'customer_id': str
    }

    FIELDS.update(Base.FIELDS)

# https://stripe.com/docs/api/persons/object#person_object-verification-status
class StripeAccountStatus(Enum):
    UNVERIFIED = 'unverified'
    PENDING = 'pending'
    VERIFIED = 'verified'
