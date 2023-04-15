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
from sqlalchemy import BigInteger, Column, String

from app.model.db.base import Base


class IDXPosition(Base):
    """Token Positions (INDEX)"""

    __tablename__ = "position"

    # Token Address
    token_address = Column(String(42), primary_key=True)
    # Account Address
    account_address = Column(String(42), primary_key=True)
    # Balance
    balance = Column(BigInteger)
    # Exchange Balance
    exchange_balance = Column(BigInteger)
    # Commitment Volume on Exchange
    exchange_commitment = Column(BigInteger)
    # Pending Transfer
    pending_transfer = Column(BigInteger)

    FIELDS = {
        "token_address": str,
        "account_address": str,
        "balance": int,
        "exchange_balance": int,
        "exchange_commitment": int,
        "pending_transfer": int,
    }
    FIELDS.update(Base.FIELDS)


class IDXPositionBondBlockNumber(Base):
    """Synchronized blockNumber of IDXPosition(Bond token)"""

    __tablename__ = "idx_position_bond_block_number"

    # target token address
    token_address = Column(String(42), primary_key=True)
    # target exchange address
    exchange_address = Column(String(42), primary_key=True)
    # latest blockNumber
    latest_block_number = Column(BigInteger)

    FIELDS = {
        "token_address": str,
        "exchange_address": str,
        "latest_block_number": int,
    }

    FIELDS.update(Base.FIELDS)


class IDXPositionShareBlockNumber(Base):
    """Synchronized blockNumber of IDXPosition(Share token)"""

    __tablename__ = "idx_position_share_block_number"

    # target token address
    token_address = Column(String(42), primary_key=True)
    # target exchange address
    exchange_address = Column(String(42), primary_key=True)
    # latest blockNumber
    latest_block_number = Column(BigInteger)

    FIELDS = {
        "token_address": str,
        "exchange_address": str,
        "latest_block_number": int,
    }

    FIELDS.update(Base.FIELDS)


class IDXPositionCouponBlockNumber(Base):
    """Synchronized blockNumber of IDXPosition(Coupon token)"""

    __tablename__ = "idx_position_coupon_block_number"

    # target token address
    token_address = Column(String(42), primary_key=True)
    # target exchange address
    exchange_address = Column(String(42), primary_key=True)
    # latest blockNumber
    latest_block_number = Column(BigInteger)

    FIELDS = {
        "token_address": str,
        "exchange_address": str,
        "latest_block_number": int,
    }

    FIELDS.update(Base.FIELDS)


class IDXPositionMembershipBlockNumber(Base):
    """Synchronized blockNumber of IDXPosition(Membership token)"""

    __tablename__ = "idx_position_membership_block_number"

    # target token address
    token_address = Column(String(42), primary_key=True)
    # target exchange address
    exchange_address = Column(String(42), primary_key=True)
    # latest blockNumber
    latest_block_number = Column(BigInteger)

    FIELDS = {
        "token_address": str,
        "exchange_address": str,
        "latest_block_number": int,
    }

    FIELDS.update(Base.FIELDS)


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
            "value": self.value,
        }
