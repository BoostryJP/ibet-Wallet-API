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
from datetime import (
    datetime,
    timezone,
    timedelta
)
from sqlalchemy import (
    Column,
    String,
    BigInteger,
    JSON,
    DateTime
)

from app.model.db import Base

UTC = timezone(timedelta(hours=0), "UTC")
JST = timezone(timedelta(hours=+9), "JST")

class IDXLock(Base):
    """Token Lock Event (INDEX)"""
    __tablename__ = "lock"

    # Sequence Id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Transaction Hash
    transaction_hash = Column(String(66), index=True)
    # Block Number
    block_number = Column(BigInteger, nullable=False)
    # Token Address
    token_address = Column(String(42), index=True)
    # Lock Address
    lock_address = Column(String(42), index=True)
    # Account Address
    account_address = Column(String(42), index=True)
    # Locked Amount
    value = Column(BigInteger, nullable=False)
    # Data
    data = Column(JSON, nullable=False)
    # Lock Datetime
    block_timestamp = Column(DateTime)

    FIELDS = {
        "id": int,
        "transaction_hash": str,
        "block_number": int,
        "token_address": str,
        "lock_address": str,
        "account_address": str,
        "value": int,
        "data": dict,
        "block_timestamp": datetime
    }
    FIELDS.update(Base.FIELDS)

    @staticmethod
    def replace_to_JST(_datetime: datetime) -> datetime | None:
        if _datetime is None:
            return None
        datetime_jp = _datetime.replace(tzinfo=UTC).astimezone(JST)
        return datetime_jp

    def json(self):
        return {
            "id": self.id,
            "transaction_hash": self.transaction_hash,
            "block_number": self.block_number,
            "token_address": self.token_address,
            "lock_address": self.lock_address,
            "account_address": self.account_address,
            "value": self.value,
            "data": self.data,
            "block_timestamp": self.replace_to_JST(self.block_timestamp)
        }


class IDXUnlock(Base):
    """Token Unlock Event (INDEX)"""
    __tablename__ = "unlock"

    # Sequence Id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Transaction Hash
    transaction_hash = Column(String(66), index=True)
    # Block Number
    block_number = Column(BigInteger, nullable=False)
    # Token Address
    token_address = Column(String(42), index=True)
    # Lock Address
    lock_address = Column(String(42), index=True)
    # Account Address
    account_address = Column(String(42), index=True)
    # Account Address
    recipient_address = Column(String(42), index=True)
    # Locked Amount
    value = Column(BigInteger, nullable=False)
    # Data
    data = Column(JSON, nullable=False)
    # Lock Datetime
    block_timestamp = Column(DateTime)

    FIELDS = {
        "id": int,
        "transaction_hash": str,
        "block_number": int,
        "token_address": str,
        "lock_address": str,
        "account_address": str,
        "recipient_address": str,
        "value": int,
        "data": dict,
        "block_timestamp": datetime
    }
    FIELDS.update(Base.FIELDS)

    @staticmethod
    def replace_to_JST(_datetime: datetime) -> datetime | None:
        if _datetime is None:
            return None
        datetime_jp = _datetime.replace(tzinfo=UTC).astimezone(JST)
        return datetime_jp

    def json(self):
        return {
            "id": self.id,
            "transaction_hash": self.transaction_hash,
            "block_number": self.block_number,
            "token_address": self.token_address,
            "lock_address": self.lock_address,
            "account_address": self.account_address,
            "recipient_address": self.recipient_address,
            "value": self.value,
            "data": self.data,
            "block_timestamp": self.replace_to_JST(self.block_timestamp)
        }


class IDXLockedPosition(Base):
    """Token Locked Amount (INDEX)"""
    __tablename__ = "locked_position"

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
        "value": int,
    }
    FIELDS.update(Base.FIELDS)

    def json(self):
        return {
            "token_address": self.token_address,
            "lock_address": self.lock_address,
            "account_address": self.account_address,
            "value": self.value
        }
