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
from sqlalchemy import String, BigInteger

from app.model import Base


class Position(Base):
    """
    トークン保有残高
    """
    __tablename__ = 'position'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    token_address = Column(String(42), index=True)
    account_address = Column(String(42))
    balance = Column(BigInteger)

    def __repr__(self):
        return "<Position(token_address='%s', account_address='%s', balance='%d')>" % \
               (self.token_address, self.account_address, self.balance)

    FIELDS = {
        'id': int,
        'token_address': str,
        'account_address': str,
        'balance': int,
    }

    FIELDS.update(Base.FIELDS)
