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
class StraightBondTokensSortItem(StrEnum):
    token_address = "token_address"
    owner_address = "owner_address"
    name = "name"
    symbol = "symbol"
    company_name = "company_name"
    tradable_exchange = "tradable_exchange"
    status = "status"
    personal_info_address = "personal_info_address"
    require_personal_info_registered = "require_personal_info_registered"
    transferable = "transferable"
    is_offering = "is_offering"
    transfer_approval_required = "transfer_approval_required"
    is_redeemed = "is_redeemed"
    created = "created"


class StraightBondTokensQuery(BasePaginationQuery):
    owner_address: Optional[EthereumAddress] = Field(None, description="issuer address")
    name: Optional[str] = Field(None, description="token name")
    symbol: Optional[str] = Field(None, description="token symbol")
    company_name: Optional[str] = Field(None, description="company name")
    tradable_exchange: Optional[EthereumAddress] = Field(
        None, description="tradable exchange"
    )
    status: Optional[bool] = Field(None, description="token status")
    personal_info_address: Optional[EthereumAddress] = Field(
        None, description="personal information address"
    )
    require_personal_info_registered: Optional[bool] = Field(
        None, description="whether personal information registration is required"
    )
    transferable: Optional[bool] = Field(None, description="transferable status")
    is_offering: Optional[bool] = Field(None, description="offering status")
    transfer_approval_required: Optional[bool] = Field(
        None, description="transfer approval required status"
    )
    is_redeemed: Optional[bool] = Field(None, description="redeem status")

    sort_item: Optional[StraightBondTokensSortItem] = Field(
        StraightBondTokensSortItem.created, description="sort item"
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.ASC, description=SortOrder.__doc__
    )


class ListAllStraightBondTokensQuery(StraightBondTokensQuery):
    address_list: list[EthereumAddress] = Field(
        default_factory=list,
        description="list of token address (**this affects total number**)",
    )


############################
# RESPONSE
############################
class RetrieveStraightBondTokenResponse(BaseModel):
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


class ListAllStraightBondTokensResponse(BaseModel):
    result_set: ResultSet
    tokens: list[RetrieveStraightBondTokenResponse]


class ListAllStraightBondTokenAddressesResponse(BaseModel):
    result_set: ResultSet
    address_list: list[EthereumAddress]
