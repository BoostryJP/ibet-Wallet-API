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

from sqlalchemy import Column
from sqlalchemy import String, BigInteger, DateTime

from app.model import Base

class ConsumeCoupon(Base):
    __tablename__ = 'consume_coupon'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    transaction_hash = Column(String(66), index=True)
    token_address = Column(String(42), index=True)
    account_address = Column(String(42), index=True)
    amount = Column(BigInteger)
    block_timestamp = Column(DateTime, default=None)

    def __repr__(self):
        return "<ConsumeCoupon id='%d'>" % \
            (self.id)

    FIELDS = {
        'id': int,
        'transaction_hash': str,
        'token_address': str,
        'account_address': str,
        'amount': int,
        'block_timestamp': str
    }

    FIELDS.update(Base.FIELDS)
