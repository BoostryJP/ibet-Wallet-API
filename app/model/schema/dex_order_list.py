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
from typing import Optional, Generic, TypeVar
from pydantic import (
    BaseModel,
    Field,
    validator
)
from pydantic.generics import GenericModel
from web3 import Web3
from app.model.schema import (
    StraightBondToken,
    ShareToken,
    MembershipToken,
    CouponToken
)

############################
# COMMON
############################


############################
# REQUEST
############################

class OrderListRequest(BaseModel):
    account_address_list: list[str] = Field(description="Account address list")
    include_canceled_items: Optional[bool] = Field(
        description="Whether to include canceled orders or canceled agreements."
    )

    @validator("account_address_list")
    def account_address_list_is_valid_address(cls, v):
        for address in v:
            if address is not None:
                if not Web3.isAddress(address):
                    raise ValueError("account_address_list has not a valid address")
        return v


############################
# RESPONSE
############################

class TokenAddress(BaseModel):
    token_address: str


class Order(BaseModel):
    order_id: int
    counterpart_address: str
    amount: int
    price: int
    is_buy: bool
    canceled: bool
    order_timestamp: str


TokenModel = TypeVar("TokenModel", StraightBondToken, ShareToken, MembershipToken, CouponToken, TokenAddress)


class OrderSet(GenericModel, Generic[TokenModel]):
    token: TokenModel
    order: Order
    sort_id: int


class Agreement(BaseModel):
    # id: int
    exchange_address: str = Field(description="exchange address")
    order_id: int
    agreement_id: int
    amount: int
    price: int
    is_buy: bool
    canceled: bool
    agreement_timestamp: str


class AgreementSet(GenericModel, Generic[TokenModel]):
    token: TokenModel
    agreement: Agreement
    sort_id: int


class CompleteAgreementSet(AgreementSet, Generic[TokenModel]):
    settlement_timestamp: str = Field(description="settlement timestamp")


class OrderListResponse(BaseModel, Generic[TokenModel]):
    order_list: list[OrderSet[TokenModel]]
    settlement_list: list[AgreementSet[TokenModel]]
    complete_list: list[CompleteAgreementSet[TokenModel]]
