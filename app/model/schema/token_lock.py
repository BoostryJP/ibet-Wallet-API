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
class Locked(BaseModel):
    token_address: EthereumAddress
    lock_address: EthereumAddress
    account_address: EthereumAddress
    value: int


############################
# REQUEST
############################
class ListAllLockSortItem(StrEnum):
    token_address = "token_address"
    lock_address = "lock_address"
    account_address = "account_address"
    value = "value"


class ListAllTokenLockQuery(BasePaginationQuery):
    token_address_list: list[EthereumAddress] = Field(
        default_factory=list,
        description="list of token address (**this affects total number**)",
    )
    lock_address: Optional[EthereumAddress] = Field(None, description="lock address")
    account_address: Optional[EthereumAddress] = Field(
        None, description="account address"
    )
    sort_item: ListAllLockSortItem = Field(
        ListAllLockSortItem.token_address, description="sort item"
    )
    sort_order: SortOrder = Field(SortOrder.ASC, description=SortOrder.__doc__)


class RetrieveTokenLockCountQuery(BaseModel):
    token_address_list: list[EthereumAddress] = Field(
        default_factory=list, description="list of token address"
    )
    lock_address: Optional[EthereumAddress] = Field(None, description="lock address")
    account_address: Optional[EthereumAddress] = Field(
        None, description="account address"
    )


############################
# RESPONSE
############################
class ListAllTokenLockResponse(BaseModel):
    result_set: ResultSet
    locked_list: list[Locked]


class RetrieveTokenLockCountResponse(BaseModel):
    count: int
