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

from pydantic import BaseModel, Field, RootModel

from app.model.schema.base import (
    BasePaginationQuery,
    EthereumAddress,
    ResultSet,
    ShareToken,
    SortOrder,
)

############################
# COMMON
############################


############################
# REQUEST
############################
class ShareTokensSortItem(StrEnum):
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
    is_canceled = "is_canceled"
    created = "created"


class ShareTokensQuery(BasePaginationQuery):
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
    is_canceled: Optional[bool] = Field(None, description="cancellation status")

    sort_item: Optional[ShareTokensSortItem] = Field(
        ShareTokensSortItem.created, description="sort item"
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.ASC, description=SortOrder.__doc__
    )


class ListAllShareTokensQuery(ShareTokensQuery):
    address_list: list[EthereumAddress] = Field(
        default_factory=list,
        description="list of token address (**this affects total number**)",
    )


############################
# RESPONSE
############################
class RetrieveShareTokenResponse(RootModel[ShareToken]):
    pass


class ListAllShareTokensResponse(BaseModel):
    result_set: ResultSet
    tokens: list[ShareToken]


class ListAllShareTokenAddressesResponse(BaseModel):
    result_set: ResultSet
    address_list: list[EthereumAddress]
