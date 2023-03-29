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

from sqlalchemy import BigInteger, Column, DateTime, Integer, String

from app.model.db.base import Base
from app.utils import alchemy


class IDXAgreement(Base):
    """DEX Agreement Events (INDEX)"""

    __tablename__ = "agreement"

    # Sequence Id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Transaction Hash
    transaction_hash = Column(String(66))
    # Exchange(DEX) Address
    exchange_address = Column(String(42), primary_key=True)
    # Order Id
    order_id = Column(BigInteger, primary_key=True)
    # Agreement Id
    agreement_id = Column(BigInteger, primary_key=True)
    # Unique Order Id: exchange_address + "_" + str(order_id)
    unique_order_id = Column(String(256), index=True)
    # Buyer Address
    buyer_address = Column(String(42), index=True)
    # Seller Address
    seller_address = Column(String(42), index=True)
    # Counterpart Address
    counterpart_address = Column(String(42))
    # Agreement Amount
    amount = Column(BigInteger)
    # Agreement Status
    status = Column(Integer)
    # Agreement Timestamp (datetime)
    # NOTE:
    #  Postgres: Stored as UTC datetime.
    #  MySQL: Before 23.3, stored as JST datetime.
    #         From 23.3, stored as UTC datetime.
    agreement_timestamp = Column(DateTime, default=None)
    # Settlement Timestamp (datetime)
    # NOTE:
    #  Postgres: Stored as UTC datetime.
    #  MySQL: Before 23.3, stored as JST datetime.
    #         From 23.3, stored as UTC datetime.
    settlement_timestamp = Column(DateTime, default=None)

    FIELDS = {
        "id": int,
        "exchange_address": str,
        "order_id": int,
        "agreement_id": int,
        "unique_order_id": str,
        "buyer_address": str,
        "seller_address": str,
        "counterpart_address": str,
        "amount": int,
        "status": int,
        "settlement_timestamp": alchemy.datetime_to_timestamp,
    }

    FIELDS.update(Base.FIELDS)


class AgreementStatus(Enum):
    PENDING = 0
    DONE = 1
    CANCELED = 2
