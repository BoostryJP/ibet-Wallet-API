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
from sqlalchemy import BigInteger, Column, DateTime, String

from app.model.db.base import Base


class IDXConsumeCoupon(Base):
    """Coupon Consume Events (INDEX)"""

    __tablename__ = "consume_coupon"

    # Sequence Id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Transaction Hash
    transaction_hash = Column(String(66), index=True)
    # Token Address
    token_address = Column(String(42), index=True)
    # Account Address
    account_address = Column(String(42), index=True)
    # Consume Amount
    amount = Column(BigInteger)
    # Block Timestamp (datetime)
    # NOTE:
    #  Postgres: Stored as UTC datetime.
    #  MySQL: Before 23.3, stored as JST datetime.
    #         From 23.3, stored as UTC datetime.
    block_timestamp = Column(DateTime, default=None)

    FIELDS = {
        "id": int,
        "transaction_hash": str,
        "token_address": str,
        "account_address": str,
        "amount": int,
        "block_timestamp": str,
    }

    FIELDS.update(Base.FIELDS)
