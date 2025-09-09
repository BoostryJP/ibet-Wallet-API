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
from typing import Literal, Optional, Union

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
class TokenBase(BaseModel):
    token_address: EthereumAddress
    key_manager: list[str]


class IbetBondToken(TokenBase):
    token_template: Literal["ibetBond"]
    product_type: Literal[1]


class IbetShareToken(TokenBase):
    token_template: Literal["ibetShare"]
    product_type: Literal[1, 2, 3, 4, 5]


class IbetMembershipToken(TokenBase):
    token_template: Literal["ibetMembership"]
    product_type: Literal[1]


class IbetCouponToken(TokenBase):
    token_template: Literal["ibetCoupon"]
    product_type: Literal[1]


class PublicAccount(BaseModel):
    key_manager: str
    key_manager_name: str
    account_type: Literal[1, 2, 3, 4]
    account_address: EthereumAddress
    modified: str = Field(..., description="Updated Datetime (local timezone)")


############################
# REQUEST
############################
class ListAllPublicListedTokensSortItem(StrEnum):
    token_address = "token_address"


class ListAllPublicListedTokensQuery(BasePaginationQuery):
    token_template: Literal["ibetBond", "ibetShare", "ibetMembership", "ibetCoupon"] = (
        Field(None, description="Token template")
    )
    sort_item: ListAllPublicListedTokensSortItem = Field(
        default=ListAllPublicListedTokensSortItem.token_address, description="sort item"
    )
    sort_order: Optional[SortOrder] = Field(
        default=SortOrder.ASC, description="sort order"
    )


class ListAllPublicAccountsSortItem(StrEnum):
    key_manager = "key_manager"
    key_manager_name = "key_manager_name"
    account_address = "account_address"


class ListAllPublicAccountsQuery(BasePaginationQuery):
    key_manager: Optional[str] = Field(None, description="Key manager")
    key_manager_name: Optional[str] = Field(None, description="Key manager name")
    sort_item: ListAllPublicAccountsSortItem = Field(
        default=ListAllPublicAccountsSortItem.key_manager, description="sort item"
    )
    sort_order: Optional[SortOrder] = Field(
        default=SortOrder.ASC, description="sort order"
    )


############################
# RESPONSE
############################
class ListAllPublicListedTokensResponse(BaseModel):
    result_set: ResultSet
    tokens: list[
        Union[IbetBondToken, IbetShareToken, IbetMembershipToken, IbetCouponToken]
    ]


class ListAllPublicAccountsResponse(BaseModel):
    result_set: ResultSet
    accounts: list[PublicAccount]
