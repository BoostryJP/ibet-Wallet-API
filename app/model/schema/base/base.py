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
from typing import TYPE_CHECKING, Annotated, Any, Generic, Optional, TypeVar

from annotated_types import Timezone
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    StringConstraints,
)

from app.model.type.base import EthereumAddress

if TYPE_CHECKING:
    from app.model.blockchain import (
        BondToken as BlockchainBondToken,
        CouponToken as BlockchainCouponToken,
        MembershipToken as BlockchainMembershipToken,
        ShareToken as BlockchainShareToken,
    )
    from app.model.schema.token_bond import BondTokenDict
    from app.model.schema.token_coupon import CouponTokenDict
    from app.model.schema.token_membership import MembershipTokenDict
    from app.model.schema.token_share import ShareTokenDict

############################
# COMMON
############################
EmailStr = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+.[a-zA-Z0-9-.]+$",
        max_length=100,
    ),
]

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

    @classmethod
    def from_token_dict(cls, token_data: "BondTokenDict") -> "BondToken":
        return cls(
            token_address=token_data["token_address"],
            token_template=token_data["token_template"],
            owner_address=token_data["owner_address"],
            company_name=token_data["company_name"],
            rsa_publickey=token_data["rsa_publickey"],
            name=token_data["name"],
            symbol=token_data["symbol"],
            total_supply=token_data["total_supply"],
            tradable_exchange=token_data["tradable_exchange"],
            contact_information=token_data["contact_information"],
            privacy_policy=token_data["privacy_policy"],
            status=token_data["status"],
            max_holding_quantity=token_data["max_holding_quantity"],
            max_sell_amount=token_data["max_sell_amount"],
            personal_info_address=token_data["personal_info_address"],
            require_personal_info_registered=token_data[
                "require_personal_info_registered"
            ],
            transferable=token_data["transferable"],
            is_offering=token_data["is_offering"],
            transfer_approval_required=token_data["transfer_approval_required"],
            face_value=token_data["face_value"],
            face_value_currency=token_data["face_value_currency"],
            interest_rate=token_data["interest_rate"],
            interest_payment_date1=token_data["interest_payment_date1"],
            interest_payment_date2=token_data["interest_payment_date2"],
            interest_payment_date3=token_data["interest_payment_date3"],
            interest_payment_date4=token_data["interest_payment_date4"],
            interest_payment_date5=token_data["interest_payment_date5"],
            interest_payment_date6=token_data["interest_payment_date6"],
            interest_payment_date7=token_data["interest_payment_date7"],
            interest_payment_date8=token_data["interest_payment_date8"],
            interest_payment_date9=token_data["interest_payment_date9"],
            interest_payment_date10=token_data["interest_payment_date10"],
            interest_payment_date11=token_data["interest_payment_date11"],
            interest_payment_date12=token_data["interest_payment_date12"],
            interest_payment_currency=token_data["interest_payment_currency"],
            redemption_date=token_data["redemption_date"],
            redemption_value=token_data["redemption_value"],
            redemption_value_currency=token_data["redemption_value_currency"],
            base_fx_rate=token_data["base_fx_rate"],
            return_date=token_data["return_date"],
            return_amount=token_data["return_amount"],
            purpose=token_data["purpose"],
            memo=token_data["memo"],
            is_redeemed=token_data["is_redeemed"],
        )

    @classmethod
    def from_blockchain_token(cls, token: "BlockchainBondToken") -> "BondToken":
        return cls.from_token_dict(token.to_dict())


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

    @classmethod
    def from_token_dict(cls, token_data: "ShareTokenDict") -> "ShareToken":
        dividend_information = token_data["dividend_information"]
        return cls(
            token_address=token_data["token_address"],
            token_template=token_data["token_template"],
            owner_address=token_data["owner_address"],
            company_name=token_data["company_name"],
            rsa_publickey=token_data["rsa_publickey"],
            name=token_data["name"],
            symbol=token_data["symbol"],
            total_supply=token_data["total_supply"],
            tradable_exchange=token_data["tradable_exchange"],
            contact_information=token_data["contact_information"],
            privacy_policy=token_data["privacy_policy"],
            status=token_data["status"],
            max_holding_quantity=token_data["max_holding_quantity"],
            max_sell_amount=token_data["max_sell_amount"],
            personal_info_address=token_data["personal_info_address"],
            require_personal_info_registered=token_data[
                "require_personal_info_registered"
            ],
            transferable=token_data["transferable"],
            is_offering=token_data["is_offering"],
            transfer_approval_required=token_data["transfer_approval_required"],
            issue_price=token_data["issue_price"],
            cancellation_date=token_data["cancellation_date"],
            memo=token_data["memo"],
            principal_value=token_data["principal_value"],
            is_canceled=token_data["is_canceled"],
            dividend_information=ShareDividendInformation(
                dividends=dividend_information["dividends"],
                dividend_record_date=dividend_information["dividend_record_date"],
                dividend_payment_date=dividend_information["dividend_payment_date"],
            ),
        )

    @classmethod
    def from_blockchain_token(cls, token: "BlockchainShareToken") -> "ShareToken":
        return cls.from_token_dict(token.to_dict())


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

    @classmethod
    def from_token_dict(cls, token_data: "MembershipTokenDict") -> "MembershipToken":
        return cls(
            token_address=token_data["token_address"],
            token_template=token_data["token_template"],
            owner_address=token_data["owner_address"],
            company_name=token_data["company_name"],
            rsa_publickey=token_data["rsa_publickey"],
            name=token_data["name"],
            symbol=token_data["symbol"],
            total_supply=token_data["total_supply"],
            tradable_exchange=token_data["tradable_exchange"],
            contact_information=token_data["contact_information"],
            privacy_policy=token_data["privacy_policy"],
            status=token_data["status"],
            max_holding_quantity=token_data["max_holding_quantity"],
            max_sell_amount=token_data["max_sell_amount"],
            details=token_data["details"],
            return_details=token_data["return_details"],
            expiration_date=token_data["expiration_date"],
            memo=token_data["memo"],
            transferable=token_data["transferable"],
            initial_offering_status=token_data["initial_offering_status"],
            image_url=[
                TokenImage(id=image["id"], url=image["url"])
                for image in token_data["image_url"]
            ],
        )

    @classmethod
    def from_blockchain_token(
        cls, token: "BlockchainMembershipToken"
    ) -> "MembershipToken":
        return cls.from_token_dict(token.to_dict())


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

    @classmethod
    def from_token_dict(cls, token_data: "CouponTokenDict") -> "CouponToken":
        return cls(
            token_address=token_data["token_address"],
            token_template=token_data["token_template"],
            owner_address=token_data["owner_address"],
            company_name=token_data["company_name"],
            rsa_publickey=token_data["rsa_publickey"],
            name=token_data["name"],
            symbol=token_data["symbol"],
            total_supply=token_data["total_supply"],
            tradable_exchange=token_data["tradable_exchange"],
            contact_information=token_data["contact_information"],
            privacy_policy=token_data["privacy_policy"],
            status=token_data["status"],
            max_holding_quantity=token_data["max_holding_quantity"],
            max_sell_amount=token_data["max_sell_amount"],
            details=token_data["details"],
            return_details=token_data["return_details"],
            expiration_date=token_data["expiration_date"],
            memo=token_data["memo"],
            transferable=token_data["transferable"],
            initial_offering_status=token_data["initial_offering_status"],
            image_url=[
                TokenImage(id=image["id"], url=image["url"])
                for image in token_data["image_url"]
            ],
        )

    @classmethod
    def from_blockchain_token(cls, token: "BlockchainCouponToken") -> "CouponToken":
        return cls.from_token_dict(token.to_dict())


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

    count: Optional[int] = Field(..., description="number of returned items")
    offset: Optional[int] = Field(..., description="start position")
    limit: Optional[int] = Field(..., description="number of set")
    total: Optional[int] = Field(..., description="total number of available items")


class Success200MetaModel(BaseModel):
    code: int = Field(..., examples=[200])
    message: str = Field(..., examples=["OK"])


Data = TypeVar("Data")


class EmptyData(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SuccessResponse(BaseModel):
    meta: Success200MetaModel = Field(
        ..., examples=[Success200MetaModel(code=200, message="OK").model_dump()]
    )
    data: EmptyData = Field(default_factory=EmptyData)

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
