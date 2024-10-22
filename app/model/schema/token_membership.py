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

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field

from app.model.schema.base import (
    BasePaginationQuery,
    EthereumAddress,
    ResultSet,
    SortOrder,
)

############################
# COMMON
############################


############################
# REQUEST
############################
class MembershipTokensSortItem(StrEnum):
    token_address = "token_address"
    owner_address = "owner_address"
    name = "name"
    symbol = "symbol"
    company_name = "company_name"
    tradable_exchange = "tradable_exchange"
    status = "status"
    transferable = "transferable"
    initial_offering_status = "initial_offering_status"
    created = "created"


class MembershipTokensQuery(BasePaginationQuery):
    owner_address: Optional[EthereumAddress] = Field(None, description="issuer address")
    name: Optional[str] = Field(None, description="token name")
    symbol: Optional[str] = Field(None, description="token symbol")
    company_name: Optional[str] = Field(None, description="company name")
    tradable_exchange: Optional[EthereumAddress] = Field(
        None, description="tradable exchange"
    )
    status: Optional[bool] = Field(None, description="token status")
    transferable: Optional[bool] = Field(None, description="transferable status")
    initial_offering_status: Optional[bool] = Field(None, description="offering status")

    sort_item: Optional[MembershipTokensSortItem] = Field(
        MembershipTokensSortItem.created, description="sort item"
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.ASC, description=SortOrder.__doc__
    )


class ListAllMembershipTokensQuery(MembershipTokensQuery):
    address_list: list[EthereumAddress] = Field(
        default_factory=list,
        description="list of token address (**this affects total number**)",
    )


############################
# RESPONSE
############################
class MembershipImage(BaseModel):
    id: int
    url: str


class RetrieveMembershipTokenResponse(BaseModel):
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
    image_url: list[MembershipImage]


class ListAllMembershipTokensResponse(BaseModel):
    result_set: ResultSet
    tokens: list[RetrieveMembershipTokenResponse]


class ListAllMembershipTokenAddressesResponse(BaseModel):
    result_set: ResultSet
    address_list: list[EthereumAddress]
