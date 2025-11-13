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

from datetime import datetime, timezone
from enum import IntEnum, StrEnum
from typing import Annotated, Any, Generic, Optional, TypeVar

from annotated_types import Timezone
from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    NonNegativeInt,
    constr,
)

from app.model.type.base import EthereumAddress

############################
# COMMON
############################
EmailStr = constr(
    pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+.[a-zA-Z0-9-.]+$", max_length=100
)

NaiveUTCDatetime = Annotated[datetime, Timezone(None)]


class TokenType(StrEnum):
    IbetStraightBond = "IbetStraightBond"
    IbetShare = "IbetShare"
    IbetMembership = "IbetMembership"
    IbetCoupon = "IbetCoupon"


class TokenImage(BaseModel):
    id: int
    url: str


class BondToken(BaseModel):
    token_address: EthereumAddress
    token_template: str = Field(examples=["IbetStraightBond"])
    owner_address: EthereumAddress = Field(description="issuer address")
    company_name: str
    rsa_publickey: str
    name: str = Field(description="token name")
    symbol: str = Field(description="token symbol")
    total_supply: int
    tradable_exchange: EthereumAddress
    contact_information: str
    privacy_policy: str
    status: bool
    max_holding_quantity: Optional[int]
    max_sell_amount: Optional[int]
    personal_info_address: EthereumAddress
    require_personal_info_registered: bool
    transferable: bool
    is_offering: bool
    transfer_approval_required: bool
    face_value: int
    face_value_currency: str
    interest_rate: float
    interest_payment_date1: Optional[str]
    interest_payment_date2: Optional[str]
    interest_payment_date3: Optional[str]
    interest_payment_date4: Optional[str]
    interest_payment_date5: Optional[str]
    interest_payment_date6: Optional[str]
    interest_payment_date7: Optional[str]
    interest_payment_date8: Optional[str]
    interest_payment_date9: Optional[str]
    interest_payment_date10: Optional[str]
    interest_payment_date11: Optional[str]
    interest_payment_date12: Optional[str]
    interest_payment_currency: str
    redemption_date: str
    redemption_value: int
    redemption_value_currency: str
    base_fx_rate: float
    return_date: str
    return_amount: str
    purpose: str
    memo: str
    is_redeemed: bool


class ShareDividendInformation(BaseModel):
    dividends: float = Field(examples=[999.9999999999999])
    dividend_record_date: str = Field(examples=["20200909"])
    dividend_payment_date: str = Field(examples=["20201001"])


class ShareToken(BaseModel):
    token_address: EthereumAddress
    token_template: str = Field(examples=["IbetShare"])
    owner_address: EthereumAddress = Field(description="issuer address")
    company_name: str
    rsa_publickey: str
    name: str = Field(description="token name")
    symbol: str = Field(description="token symbol")
    total_supply: int
    tradable_exchange: EthereumAddress
    contact_information: str
    privacy_policy: str
    status: bool
    max_holding_quantity: Optional[int]
    max_sell_amount: Optional[int]
    personal_info_address: str
    require_personal_info_registered: bool
    transferable: bool
    is_offering: bool
    transfer_approval_required: bool
    issue_price: int
    cancellation_date: str
    memo: str
    principal_value: int
    is_canceled: bool
    dividend_information: ShareDividendInformation


class MembershipToken(BaseModel):
    token_address: EthereumAddress
    token_template: str = Field(examples=["IbetMembership"])
    owner_address: EthereumAddress = Field(description="issuer address")
    company_name: str
    rsa_publickey: str
    name: str = Field(description="token name")
    symbol: str = Field(description="token symbol")
    total_supply: int
    tradable_exchange: EthereumAddress
    contact_information: str
    privacy_policy: str
    status: bool
    max_holding_quantity: Optional[int]
    max_sell_amount: Optional[int]
    details: str
    return_details: str
    expiration_date: str
    memo: str
    transferable: bool
    initial_offering_status: bool
    image_url: list[TokenImage]


class CouponToken(BaseModel):
    token_address: EthereumAddress
    token_template: str = Field(examples=["IbetCoupon"])
    owner_address: EthereumAddress = Field(description="issuer address")
    company_name: str
    rsa_publickey: str
    name: str = Field(description="token name")
    symbol: str = Field(description="token symbol")
    total_supply: int
    tradable_exchange: EthereumAddress
    contact_information: str
    privacy_policy: str
    status: bool
    max_holding_quantity: Optional[int]
    max_sell_amount: Optional[int]
    details: str
    return_details: str
    expiration_date: str
    memo: str
    transferable: bool
    initial_offering_status: bool
    image_url: list[TokenImage]


class ValueOperator(IntEnum):
    EQUAL = 0
    GTE = 1
    LTE = 2


def naive_utc_datetime_validator(value: Any) -> NaiveUTCDatetime | None:
    """Validate datetime"""
    if value is not None:
        try:
            if value.tzinfo is None:
                # Return the datetime as is if it has no timezone info
                return value
            # Convert timezone to UTC
            dt_utc = value.astimezone(timezone.utc)

            # Return naive UTC datetime
            return dt_utc.replace(tzinfo=None)
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {str(e)}")
    return value


ValidatedNaiveUTCDatetime = Annotated[
    datetime, AfterValidator(naive_utc_datetime_validator)
]


############################
# REQUEST
############################
class SortOrder(IntEnum):
    """sort order(0: ASC, 1: DESC)"""

    ASC = 0
    DESC = 1


class BasePaginationQuery(BaseModel):
    offset: Optional[NonNegativeInt] = Field(None, description="Offset for pagination")
    limit: Optional[NonNegativeInt] = Field(None, description="Limit for pagination")


############################
# RESPONSE
############################
class ResultSet(BaseModel):
    """result set for pagination"""

    count: Optional[int] = None
    offset: Optional[int] = Field(..., description="start position")
    limit: Optional[int] = Field(..., description="number of set")
    total: Optional[int] = None


class Success200MetaModel(BaseModel):
    code: int = Field(..., examples=[200])
    message: str = Field(..., examples=["OK"])


Data = TypeVar("Data")


class SuccessResponse(BaseModel):
    meta: Success200MetaModel = Field(
        ..., examples=[Success200MetaModel(code=200, message="OK").model_dump()]
    )
    data: dict = {}

    @staticmethod
    def default():
        return SuccessResponse(
            meta=Success200MetaModel(code=200, message="OK")
        ).model_dump()


class GenericSuccessResponse(BaseModel, Generic[Data]):
    meta: Success200MetaModel = Field(
        ..., examples=[Success200MetaModel(code=200, message="OK").model_dump()]
    )
    data: Data
