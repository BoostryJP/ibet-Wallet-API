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
from typing import Union, Type
from sqlalchemy import (
    Column,
    String,
    BigInteger,
    Boolean,
    Float,
    Text,
    JSON,
    DateTime
)
from app.model.db import Base


class TokenBase(Base):
    """Token Base Attribute"""
    __abstract__ = True

    # Token Address
    token_address = Column(String(42), primary_key=True)
    # Token Template
    token_template = Column(String(40))
    # Owner Address
    owner_address = Column(String(42), index=True)
    # Company Name(Corporate)
    # NOTE: Short-term cache required
    company_name = Column(Text)
    # RSA Public Key(Corporate)
    # NOTE: Short-term cache required
    rsa_publickey = Column(String(2000))
    # Name
    name = Column(String(200))
    # Symbol
    symbol = Column(String(200))
    # Total Supply
    # NOTE: Short-term cache required
    total_supply = Column(BigInteger)
    # Tradable Exchange
    tradable_exchange = Column(String(42), index=True)
    # Contact Information
    contact_information = Column(String(2000))
    # Privacy Policy
    privacy_policy = Column(String(5000))
    # Status
    # NOTE: Short-term cache required
    status = Column(Boolean)
    # Max Holding Quantity
    max_holding_quantity = Column(BigInteger)
    # Max Sell Amount
    max_sell_amount = Column(BigInteger)
    # Cached time of short-term cache
    short_term_cache_created = Column(DateTime)

    FIELDS = {
        "id": int,
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
    personal_info_address = Column(String(42), index=True)
    # Transferable
    # NOTE: Short-term cache required
    transferable = Column(Boolean)
    # Is Offering
    # NOTE: Short-term cache required
    is_offering = Column(Boolean)
    # Transfer Approval Required
    # NOTE: Short-term cache required
    transfer_approval_required = Column(Boolean)
    # Face Value
    face_value = Column(BigInteger)
    # Interest Rate
    interest_rate = Column(Float)
    # Interest Payment Date(JSON)
    interest_payment_date = Column(JSON)
    # Redemption Date
    redemption_date = Column(String(8))
    # Redemption Value
    redemption_value = Column(BigInteger)
    # Return Date
    return_date = Column(String(8))
    # Return Amount
    return_amount = Column(String(2000))
    # Purpose
    purpose = Column(String(2000))
    # Memo
    memo = Column(String(2000))
    # Is Redeemed
    # NOTE: Short-term cache required
    is_redeemed = Column(Boolean)

    FIELDS = {
        "personal_info_address": str,
        "transferable": bool,
        "is_offering": bool,
        "transfer_approval_required": bool,
        "face_value": int,
        "interest_rate": float,
        "interest_payment_date": list,
        "redemption_date": str,
        "redemption_value": int,
        "return_date": str,
        "return_amount": str,
        "purpose": str,
        "memo": str,
        "is_redeemed": bool
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
            "interest_rate": self.interest_rate,
            "interest_payment_date": self.interest_payment_date,
            "redemption_date": self.redemption_date,
            "redemption_value": self.redemption_value,
            "return_date": self.return_date,
            "return_amount": self.return_amount,
            "purpose": self.purpose,
            "memo": self.memo,
            "is_redeemed": self.is_redeemed
        }


class IDXShareToken(TokenBase):
    """ShareToken (INDEX)"""
    __tablename__ = "share_token"

    # Personal Info Address
    personal_info_address = Column(String(42), index=True)
    # Transferable
    # NOTE: Short-term cache required
    transferable = Column(Boolean)
    # Is Offering
    # NOTE: Short-term cache required
    is_offering = Column(Boolean)
    # Transfer Approval Required
    # NOTE: Short-term cache required
    transfer_approval_required = Column(Boolean)
    # Issue Price
    issue_price = Column(BigInteger)
    # Cancellation Date
    cancellation_date = Column(String(8))
    # Memo
    memo = Column(String(2000))
    # Principal Value
    # NOTE: Short-term cache required
    principal_value = Column(BigInteger)
    # Is Canceled
    # NOTE: Short-term cache required
    is_canceled = Column(Boolean)
    # Dividend Information(JSON)
    # NOTE: Short-term cache required
    dividend_information = Column(JSON)

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
        "dividend_information": slice
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
            "dividend_information": self.dividend_information
        }


class IDXMembershipToken(TokenBase):
    """MembershipToken (INDEX)"""
    __tablename__ = "membership_token"

    # Details
    details = Column(String(2000))
    # Return Details
    return_details = Column(String(2000))
    # Expiration Date
    expiration_date = Column(String(8))
    # Memo
    memo = Column(String(2000))
    # Transferable
    # NOTE: Short-term cache required
    transferable = Column(Boolean)
    # Initial Offering Status
    # NOTE: Short-term cache required
    initial_offering_status = Column(Boolean)
    # Image URL(JSON)
    image_url = Column(JSON)

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
            "image_url": self.image_url
        }


class IDXCouponToken(TokenBase):
    """CouponToken (INDEX)"""
    __tablename__ = "coupon_token"

    # Details
    details = Column(String(2000))
    # Return Details
    return_details = Column(String(2000))
    # Expiration Date
    expiration_date = Column(String(8))
    # Memo
    memo = Column(String(2000))
    # Transferable
    # NOTE: Short-term cache required
    transferable = Column(Boolean)
    # Initial Offering Status
    # NOTE: Short-term cache required
    initial_offering_status = Column(Boolean)
    # Image URL(JSON)
    image_url = Column(JSON)

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
            "image_url": self.image_url
        }


TokenModelClassTypes = Union[
    Type[IDXShareToken],
    Type[IDXBondToken],
    Type[IDXMembershipToken],
    Type[IDXCouponToken]
]
TokenModelInstanceTypes = Union[
    IDXBondToken,
    IDXShareToken,
    IDXMembershipToken,
    IDXCouponToken
]
