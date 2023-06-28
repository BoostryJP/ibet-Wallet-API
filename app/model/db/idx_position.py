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
from typing import Optional

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

    @staticmethod
    def bond(position: Optional["IDXPosition"]):
        return {
            "balance": position.balance if position and position.balance else 0,
            "pending_transfer": position.pending_transfer
            if position and position.pending_transfer
            else 0,
            "exchange_balance": position.exchange_balance
            if position and position.exchange_balance
            else 0,
            "exchange_commitment": position.exchange_commitment
            if position and position.exchange_commitment
            else 0,
        }

    @staticmethod
    def share(share: Optional["IDXPosition"]):
        return {
            "balance": share.balance if share and share.balance else 0,
            "pending_transfer": share.pending_transfer
            if share and share.pending_transfer
            else 0,
            "exchange_balance": share.exchange_balance
            if share and share.exchange_balance
            else 0,
            "exchange_commitment": share.exchange_commitment
            if share and share.exchange_commitment
            else 0,
        }

    @staticmethod
    def coupon(coupon: Optional["IDXPosition"]):
        return {
            "balance": coupon.balance if coupon and coupon.balance else 0,
            "exchange_balance": coupon.exchange_balance
            if coupon and coupon.exchange_balance
            else 0,
            "exchange_commitment": coupon.exchange_commitment
            if coupon and coupon.exchange_commitment
            else 0,
        }

    @staticmethod
    def membership(membership: Optional["IDXPosition"]):
        return {
            "balance": membership.balance if membership and membership.balance else 0,
            "exchange_balance": membership.exchange_balance
            if membership and membership.exchange_balance
            else 0,
            "exchange_commitment": membership.exchange_commitment
            if membership and membership.exchange_commitment
            else 0,
        }


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
