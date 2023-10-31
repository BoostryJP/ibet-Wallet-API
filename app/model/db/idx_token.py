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
import datetime
from typing import Type, Union

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import engine
from app.model.db.base import Base


class TokenBase(Base):
    """Token Base Attribute"""

    __abstract__ = True

    # Token Address
    token_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # Token Template
    token_template: Mapped[str | None] = mapped_column(String(40))
    # Owner Address
    owner_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # Company Name(Corporate)
    # NOTE: Short-term cache required
    company_name: Mapped[str | None] = mapped_column(Text)
    # RSA Public Key(Corporate)
    # NOTE: Short-term cache required
    rsa_publickey: Mapped[str | None] = mapped_column(String(2000))
    # Name
    name: Mapped[str | None] = mapped_column(String(200))
    # Symbol
    symbol: Mapped[str | None] = mapped_column(String(200))
    # Total Supply
    # NOTE: Short-term cache required
    total_supply: Mapped[int | None] = mapped_column(BigInteger)
    # Tradable Exchange
    tradable_exchange: Mapped[str | None] = mapped_column(String(42), index=True)
    # Contact Information
    contact_information: Mapped[str | None] = mapped_column(String(2000))
    # Privacy Policy
    privacy_policy: Mapped[str | None] = mapped_column(String(5000))
    # Status
    # NOTE: Short-term cache required
    status: Mapped[bool | None] = mapped_column(Boolean)
    # Max Holding Quantity
    max_holding_quantity: Mapped[int | None] = mapped_column(BigInteger)
    # Max Sell Amount
    max_sell_amount: Mapped[int | None] = mapped_column(BigInteger)
    # Cached time of short-term cache
    short_term_cache_created: Mapped[datetime.datetime | None] = mapped_column(DateTime)

    FIELDS = {
        "token_address": str,
        "token_template": str,
        "owner_address": str,
        "company_name": str,
        "rsa_publickey": str,
        "name": str,
        "symbol": str,
        "total_supply": int,
        "tradable_exchange": str,
        "contact_information": str,
        "privacy_policy": str,
        "status": bool,
        "max_holding_quantity": int,
        "max_sell_amount": int,
    }

    FIELDS.update(Base.FIELDS)

    def json(self):
        return {
            "token_address": self.token_address,
            "token_template": self.token_template,
            "owner_address": self.owner_address,
            "company_name": self.company_name,
            "rsa_publickey": self.rsa_publickey,
            "name": self.name,
            "symbol": self.symbol,
            "total_supply": self.total_supply,
            "tradable_exchange": self.tradable_exchange,
            "contact_information": self.contact_information,
            "privacy_policy": self.privacy_policy,
            "status": self.status,
            "max_holding_quantity": self.max_holding_quantity,
            "max_sell_amount": self.max_sell_amount,
        }


class IDXBondToken(TokenBase):
    """BondToken (INDEX)"""

    __tablename__ = "bond_token"

    # Personal Info Address
    personal_info_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # Transferable
    # NOTE: Short-term cache required
    transferable: Mapped[bool | None] = mapped_column(Boolean)
    # Is Offering
    # NOTE: Short-term cache required
    is_offering: Mapped[bool | None] = mapped_column(Boolean)
    # Transfer Approval Required
    # NOTE: Short-term cache required
    transfer_approval_required: Mapped[bool | None] = mapped_column(Boolean)
    # Face Value
    face_value: Mapped[int | None] = mapped_column(BigInteger)
    # Face Value Currency
    face_value_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    # Interest Rate
    interest_rate: Mapped[float | None] = mapped_column(Float)
    # Interest Payment Date(JSON)
    interest_payment_date: Mapped[dict | None] = mapped_column(JSON)
    # Interest Payment Currency
    interest_payment_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    # Redemption Date
    redemption_date: Mapped[str | None] = mapped_column(String(8))
    # Redemption Value
    redemption_value: Mapped[int | None] = mapped_column(BigInteger)
    # Redemption Value Currency
    redemption_value_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    # Base FX Rate
    base_fx_rate: Mapped[float] = mapped_column(Numeric(16, 6), nullable=False)
    # Return Date
    return_date: Mapped[str | None] = mapped_column(String(8))
    # Return Amount
    return_amount: Mapped[str | None] = mapped_column(String(2000))
    # Purpose
    purpose: Mapped[str | None] = mapped_column(String(2000))
    # Memo
    if engine.name == "mysql":
        memo: Mapped[str | None] = mapped_column(Text)
    else:
        memo: Mapped[str | None] = mapped_column(String(10000))
    # Is Redeemed
    # NOTE: Short-term cache required
    is_redeemed: Mapped[bool | None] = mapped_column(Boolean)

    FIELDS = {
        "personal_info_address": str,
        "transferable": bool,
        "is_offering": bool,
        "transfer_approval_required": bool,
        "face_value": int,
        "face_value_currency": str,
        "interest_rate": float,
        "interest_payment_date": list,
        "interest_payment_currency": str,
        "redemption_date": str,
        "redemption_value": int,
        "redemption_value_currency": str,
        "base_fx_rate": float,
        "return_date": str,
        "return_amount": str,
        "purpose": str,
        "memo": str,
        "is_redeemed": bool,
    }

    FIELDS.update(TokenBase.FIELDS)

    def json(self):
        return {
            **super().json(),
            "personal_info_address": self.personal_info_address,
            "transferable": self.transferable,
            "is_offering": self.is_offering,
            "transfer_approval_required": self.transfer_approval_required,
            "face_value": self.face_value,
            "face_value_currency": self.face_value_currency,
            "interest_rate": self.interest_rate,
            "interest_payment_date": self.interest_payment_date,
            "interest_payment_currency": self.interest_payment_currency,
            "redemption_date": self.redemption_date,
            "redemption_value": self.redemption_value,
            "redemption_value_currency": self.redemption_value_currency,
            "base_fx_rate": float(self.base_fx_rate),
            "return_date": self.return_date,
            "return_amount": self.return_amount,
            "purpose": self.purpose,
            "memo": self.memo,
            "is_redeemed": self.is_redeemed,
        }


class IDXShareToken(TokenBase):
    """ShareToken (INDEX)"""

    __tablename__ = "share_token"

    # Personal Info Address
    personal_info_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # Transferable
    # NOTE: Short-term cache required
    transferable: Mapped[bool | None] = mapped_column(Boolean)
    # Is Offering
    # NOTE: Short-term cache required
    is_offering: Mapped[bool | None] = mapped_column(Boolean)
    # Transfer Approval Required
    # NOTE: Short-term cache required
    transfer_approval_required: Mapped[bool | None] = mapped_column(Boolean)
    # Issue Price
    issue_price: Mapped[int | None] = mapped_column(BigInteger)
    # Cancellation Date
    cancellation_date: Mapped[str | None] = mapped_column(String(8))
    # Memo
    if engine.name == "mysql":
        memo: Mapped[str | None] = mapped_column(Text)
    else:
        memo: Mapped[str | None] = mapped_column(String(10000))
    # Principal Value
    # NOTE: Short-term cache required
    principal_value: Mapped[int | None] = mapped_column(BigInteger)
    # Is Canceled
    # NOTE: Short-term cache required
    is_canceled: Mapped[int | None] = mapped_column(Boolean)
    # Dividend Information(JSON)
    # NOTE: Short-term cache required
    dividend_information: Mapped[dict | None] = mapped_column(JSON)

    FIELDS = {
        "personal_info_address": str,
        "transferable": bool,
        "is_offering": bool,
        "transfer_approval_required": bool,
        "issue_price": int,
        "cancellation_date": str,
        "memo": str,
        "principal_value": int,
        "is_canceled": bool,
        "dividend_information": slice,
    }

    FIELDS.update(TokenBase.FIELDS)

    def json(self):
        return {
            **super().json(),
            "personal_info_address": self.personal_info_address,
            "transferable": self.transferable,
            "is_offering": self.is_offering,
            "transfer_approval_required": self.transfer_approval_required,
            "issue_price": self.issue_price,
            "cancellation_date": self.cancellation_date,
            "memo": self.memo,
            "principal_value": self.principal_value,
            "is_canceled": self.is_canceled,
            "dividend_information": self.dividend_information,
        }


class IDXMembershipToken(TokenBase):
    """MembershipToken (INDEX)"""

    __tablename__ = "membership_token"

    # Details
    details: Mapped[str | None] = mapped_column(String(2000))
    # Return Details
    return_details: Mapped[str | None] = mapped_column(String(2000))
    # Expiration Date
    expiration_date: Mapped[str | None] = mapped_column(String(8))
    # Memo
    memo: Mapped[str | None] = mapped_column(String(2000))
    # Transferable
    # NOTE: Short-term cache required
    transferable: Mapped[bool | None] = mapped_column(Boolean)
    # Initial Offering Status
    # NOTE: Short-term cache required
    initial_offering_status: Mapped[bool | None] = mapped_column(Boolean)
    # Image URL(JSON)
    image_url: Mapped[dict | None] = mapped_column(JSON)

    FIELDS = {
        "details": str,
        "return_details": str,
        "expiration_date": str,
        "memo": str,
        "transferable": bool,
        "initial_offering_status": bool,
        "image_url": list,
    }

    FIELDS.update(TokenBase.FIELDS)

    def json(self):
        return {
            **super().json(),
            "details": self.details,
            "return_details": self.return_details,
            "expiration_date": self.expiration_date,
            "memo": self.memo,
            "transferable": self.transferable,
            "initial_offering_status": self.initial_offering_status,
            "image_url": self.image_url,
        }


class IDXCouponToken(TokenBase):
    """CouponToken (INDEX)"""

    __tablename__ = "coupon_token"

    # Details
    details: Mapped[str | None] = mapped_column(String(2000))
    # Return Details
    return_details: Mapped[str | None] = mapped_column(String(2000))
    # Expiration Date
    expiration_date: Mapped[str | None] = mapped_column(String(8))
    # Memo
    memo: Mapped[str | None] = mapped_column(String(2000))
    # Transferable
    # NOTE: Short-term cache required
    transferable: Mapped[bool | None] = mapped_column(Boolean)
    # Initial Offering Status
    # NOTE: Short-term cache required
    initial_offering_status: Mapped[bool | None] = mapped_column(Boolean)
    # Image URL(JSON)
    image_url: Mapped[dict | None] = mapped_column(JSON)

    FIELDS = {
        "details": str,
        "return_details": str,
        "expiration_date": str,
        "memo": str,
        "transferable": bool,
        "initial_offering_status": bool,
        "image_url": list,
    }

    FIELDS.update(TokenBase.FIELDS)

    def json(self):
        return {
            **super().json(),
            "details": self.details,
            "return_details": self.return_details,
            "expiration_date": self.expiration_date,
            "memo": self.memo,
            "transferable": self.transferable,
            "initial_offering_status": self.initial_offering_status,
            "image_url": self.image_url,
        }


IDXTokenModel = Union[
    Type[IDXShareToken],
    Type[IDXBondToken],
    Type[IDXMembershipToken],
    Type[IDXCouponToken],
]
IDXTokenInstance = Union[
    IDXBondToken, IDXShareToken, IDXMembershipToken, IDXCouponToken
]
