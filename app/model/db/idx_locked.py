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
from sqlalchemy import (
    Column,
    String,
    BigInteger
)

from app.model.db import Base


class IDXLocked(Base):
    """Token Locked Amount (INDEX)"""
    __tablename__ = "locked"

    # Token Address
    token_address = Column(String(42), primary_key=True)
    # Lock Address
    lock_address = Column(String(42), primary_key=True)
    # Account Address
    account_address = Column(String(42), primary_key=True)
    # Locked Amount
    value = Column(BigInteger, nullable=False)

    FIELDS = {
        "token_address": str,
        "lock_address": str,
        "account_address": str,
        "value": int
    }
    FIELDS.update(Base.FIELDS)

    def json(self):
        return {
            "token_address": self.token_address,
            "lock_address": self.lock_address,
            "account_address": self.account_address,
            "value": self.value
        }
