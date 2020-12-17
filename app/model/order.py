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

from sqlalchemy import Column, DateTime
from sqlalchemy import String, BigInteger, Boolean

from app.model import Base
from app.utils import alchemy


class Order(Base):
    __tablename__ = 'order'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    transaction_hash = Column(String(66))
    token_address = Column(String(42), index=True)
    exchange_address = Column(String(42), index=True)
    order_id = Column(BigInteger, index=True)
    unique_order_id = Column(String(256), index=True)
    account_address = Column(String(42))
    counterpart_address = Column(String(42))
    is_buy = Column(Boolean)
    price = Column(BigInteger)
    amount = Column(BigInteger)
    agent_address = Column(String(42))
    is_cancelled = Column(Boolean)
    order_timestamp = Column(DateTime, default=None)

    def __repr__(self):
        return "<Order(exchange_address='%s', order_id='%d')>" % \
               (self.exchange_address, self.order_id)

    FIELDS = {
        'id': int,
        'transaction_hash': str,
        'token_address': str,
        'exchange_address': str,
        'order_id': int,
        'account_address': str,
        'counterpart_address': str,
        'is_buy': bool,
        'price': int,
        'amount': int,
        'agent_address': str,
        'is_cancelled': bool,
        'order_timestamp': alchemy.datetime_to_timestamp,
    }

    FIELDS.update(Base.FIELDS)
