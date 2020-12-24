"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

from enum import Enum

from sqlalchemy import Column
from sqlalchemy import String, Integer, BigInteger, DateTime

from app.model import Base
from app.utils import alchemy


# 約定情報
class Agreement(Base):
    __tablename__ = 'agreement'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    transaction_hash = Column(String(66))
    exchange_address = Column(String(42), primary_key=True)
    order_id = Column(BigInteger, primary_key=True)
    agreement_id = Column(BigInteger, primary_key=True)
    unique_order_id = Column(String(256), index=True)  # NOTE: exchange_address + '_' + str(order_id)
    buyer_address = Column(String(42), index=True)
    seller_address = Column(String(42), index=True)
    counterpart_address = Column(String(42))
    amount = Column(BigInteger)
    status = Column(Integer)
    agreement_timestamp = Column(DateTime, default=None)
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
