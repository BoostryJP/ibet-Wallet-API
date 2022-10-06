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
from pydantic.dataclasses import dataclass

from app.model.schema.base import (
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


@dataclass
class ListAllCouponTokensQuery:
    offset: Optional[int] = Query(default=None, description="start position", ge=0)
    limit: Optional[int] = Query(default=None, description="number of set", ge=0)
    owner_address: Optional[str] = Query(default=None, description="issuer address")
    name: Optional[str] = Query(default=None, description="token name")
    symbol: Optional[str] = Query(default=None, description="token symbol")
    company_name: Optional[str] = Query(default=None, description="company name")
    tradable_exchange: Optional[str] = Query(default=None, description="tradable exchange address")
    status: Optional[bool] = Query(default=None, description="token status")
    transferable: Optional[bool] = Query(default=None, description="transferable status")
    initial_offering_status: Optional[bool] = Query(default=None, description="offering status")

    sort_item: Optional[CouponTokensSortItem] = Query(
        default=CouponTokensSortItem.created,
        description="sort item"
    )
    sort_order: Optional[SortOrder] = Query(default=SortOrder.ASC, description="sort order(0: ASC, 1: DESC)")


############################
# RESPONSE
############################

class CouponImage(BaseModel):
    id: int
    url: str


class RetrieveCouponTokenResponse(BaseModel):
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
    max_holding_quantity: Optional[int]
    max_sell_amount: Optional[int]
    details: str
    return_details: str
    expiration_date: str
    memo: str
    transferable: bool
    initial_offering_status: bool
    image_url: list[CouponImage]


class ListAllCouponTokensResponse(BaseModel):
    result_set: ResultSet
    tokens: list[RetrieveCouponTokenResponse]


class ListAllCouponTokenAddressesResponse(BaseModel):
    result_set: ResultSet
    address_list: list[str]
