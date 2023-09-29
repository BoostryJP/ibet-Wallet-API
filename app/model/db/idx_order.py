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
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.model.db.base import Base
from app.utils import alchemy


class IDXOrder(Base):
    """DEX Order Events (INDEX)"""

    __tablename__ = "order"

    # Sequence Id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Transaction Hash
    transaction_hash: Mapped[str | None] = mapped_column(String(66))
    # Token Address
    token_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # Exchange(DEX) Address
    exchange_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # Order Id
    order_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    # Unique Order Id: exchange_address + "_" + str(order_id)
    unique_order_id: Mapped[str | None] = mapped_column(String(256), index=True)
    # Account Address
    account_address: Mapped[str | None] = mapped_column(String(42))
    # Counterpart Address
    counterpart_address: Mapped[str | None] = mapped_column(String(42))
    # Buy/Sell
    is_buy: Mapped[bool | None] = mapped_column(Boolean)
    # Order Price
    price: Mapped[int | None] = mapped_column(BigInteger)
    # Order Amount (quantity)
    amount: Mapped[int | None] = mapped_column(BigInteger)
    # Paying Agent Address
    agent_address: Mapped[str | None] = mapped_column(String(42))
    # Cancellation Status
    is_cancelled: Mapped[bool | None] = mapped_column(Boolean)
    # Order Timestamp (datetime)
    # NOTE:
    #  Postgres: Stored as UTC datetime.
    #  MySQL: Before 23.3, stored as JST datetime.
    #         From 23.3, stored as UTC datetime.
    order_timestamp: Mapped[datetime | None] = mapped_column(DateTime, default=None)

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
