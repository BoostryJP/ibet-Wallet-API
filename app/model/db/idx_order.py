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
    DateTime,
    String,
    BigInteger,
    Boolean
)

from app.model.db import Base
from app.utils import alchemy


class IDXOrder(Base):
    """DEX Order Events (INDEX)"""
    __tablename__ = "order"

    # Sequence Id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Transaction Hash
    transaction_hash = Column(String(66))
    # Token Address
    token_address = Column(String(42), index=True)
    # Exchange(DEX) Address
    exchange_address = Column(String(42), index=True)
    # Order Id
    order_id = Column(BigInteger, index=True)
    # Unique Order Id: exchange_address + "_" + str(order_id)
    unique_order_id = Column(String(256), index=True)
    # Account Address
    account_address = Column(String(42))
    # Counterpart Address
    counterpart_address = Column(String(42))
    # Buy/Sell
    is_buy = Column(Boolean)
    # Order Price
    price = Column(BigInteger)
    # Order Amount (quantity)
    amount = Column(BigInteger)
    # Paying Agent Address
    agent_address = Column(String(42))
    # Cancellation Status
    is_cancelled = Column(Boolean)
    # Order Timestamp (datetime)
    order_timestamp = Column(DateTime, default=None)

    FIELDS = {
        "id": int,
        "transaction_hash": str,
        "token_address": str,
        "exchange_address": str,
        "order_id": int,
        "account_address": str,
        "counterpart_address": str,
        "is_buy": bool,
        "price": int,
        "amount": int,
        "agent_address": str,
        "is_cancelled": bool,
        "order_timestamp": alchemy.datetime_to_timestamp,
    }

    FIELDS.update(Base.FIELDS)
