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

from sqlalchemy import (
    Column,
    String,
    BigInteger,
)

from app.model.db import Base


class TokenHoldersList(Base):
    """Token Holder List"""
    __tablename__ = "token_holders_list"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Token Address
    token_address = Column(String(42))
    # Block Number
    block_number = Column(BigInteger)
    # List id (UUID)
    list_id = Column(String(36), index=False)
    # batch processing status
    batch_status = Column(String(256))


class TokenHolderBatchStatus(Enum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class TokenHolder(Base):
    """Token Holder"""
    __tablename__ = "token_holder"

    # Related to TokenHoldersList primary key
    holder_list_id = Column(BigInteger, primary_key=True)

    # Account Address
    account_address = Column(String(42), primary_key=True)

    # Amounts
    balance = Column(BigInteger)
    pending_transfer = Column(BigInteger)
    exchange_balance = Column(BigInteger)
    exchange_commitment = Column(BigInteger)

    def json(self):
        return {
            "account_address": self.account_address,
            "balance": self.balance,
            "pending_transfer": self.pending_transfer,
            "exchange_balance": self.exchange_balance,
            "exchange_commitment": self.exchange_commitment,
        }

    FIELDS = {
        "holder_list_id": int,
        "account_address": str,
        "balance": int,
        "pending_transfer": int,
        "exchange_balance": int,
        "exchange_commitment": int,
    }

    FIELDS.update(Base.FIELDS)

