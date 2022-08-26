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
from fastapi import Query
from typing import Optional
from pydantic import (
    BaseModel,
    Field
)

from app.model.schema.base import (
    ResultSetQuery,
    ResultSet,
    SortOrder
)

############################
# COMMON
############################


############################
# REQUEST
############################

class CouponTokensSortItem(str, Enum):
    token_address = "token_address"
    owner_address = "owner_address"
    name = "name"
    symbol = "symbol"
    company_name = "company_name"
    tradable_exchange = "tradable_exchange"
    status = "status"
    personal_info_address = "personal_info_address"
    transferable = "transferable"
    initial_offering_status = "initial_offering_status"
    created = "created"


class CouponTokensQuery(ResultSetQuery):
    owner_address: Optional[str] = Field(description="issuer address")
    name: Optional[str] = Field(description="token name")
    symbol: Optional[str] = Field(description="token symbol")
    company_name: Optional[str] = Field(description="company name")
    tradable_exchange: Optional[str] = Field(description="tradable exchange address")
    status: Optional[bool] = Field(description="token status")
    transferable: Optional[bool] = Field(description="transferable status")
    initial_offering_status: Optional[bool] = Field(description="offering status")

    sort_item: Optional[CouponTokensSortItem] = Field(
        default=CouponTokensSortItem.created,
        description="sort item"
    )
    sort_order: Optional[SortOrder] = Field(default=SortOrder.ASC, description="sort order")


############################
# RESPONSE
############################

class CouponImage(BaseModel):
    id: int
    url: str


class CouponToken(BaseModel):
    token_address: str
    token_template: str = Field(example="IbetCoupon")
    owner_address: str = Field(description="issuer address")
    company_name: str
    rsa_publickey: str
    name: str = Field(description="token name")
    symbol: str = Field(description="token symbol")
    total_supply: int
    tradable_exchange: str
    contact_information: str
    privacy_policy: str
    status: bool
    max_holding_quantity: int
    max_sell_amount: int
    details: str
    return_details: str
    expiration_date: str
    memo: str
    transferable: bool
    initial_offering_status: bool
    image_url: list[CouponImage]


class CouponTokensResponse(BaseModel):
    result_set: ResultSet
    tokens: list[CouponToken]


class CouponTokenAddressesResponse(BaseModel):
    result_set: ResultSet
    address_list: list[str]
