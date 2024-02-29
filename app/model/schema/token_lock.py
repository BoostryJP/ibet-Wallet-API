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
from typing import Annotated, Optional

from fastapi import Query
from pydantic import BaseModel
from pydantic.dataclasses import dataclass

from app.model.schema.base import ResultSet, SortOrder, ValidatedEthereumAddress


############################
# COMMON
############################
class Locked(BaseModel):
    token_address: ValidatedEthereumAddress
    lock_address: ValidatedEthereumAddress
    account_address: ValidatedEthereumAddress
    value: int


############################
# REQUEST
############################
class ListAllLockSortItem(str, Enum):
    token_address = "token_address"
    lock_address = "lock_address"
    account_address = "account_address"
    value = "value"


@dataclass
class ListAllTokenLockQuery:
    token_address_list: Annotated[
        list[ValidatedEthereumAddress],
        Query(
            default_factory=list,
            description="list of token address (**this affects total number**)",
        ),
    ]
    lock_address: Annotated[
        Optional[ValidatedEthereumAddress], Query(description="lock address")
    ] = None
    account_address: Annotated[
        Optional[ValidatedEthereumAddress], Query(description="account address")
    ] = None
    offset: Annotated[Optional[int], Query(description="start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="number of set", ge=0)] = None
    sort_item: Annotated[ListAllLockSortItem, Query(description="sort item")] = (
        ListAllLockSortItem.token_address
    )
    sort_order: Annotated[
        SortOrder, Query(description="sort order(0: ASC, 1: DESC)")
    ] = SortOrder.ASC


@dataclass
class RetrieveTokenLockCountQuery:
    token_address_list: Annotated[
        list[ValidatedEthereumAddress],
        Query(default_factory=list, description="list of token address"),
    ]
    lock_address: Annotated[
        Optional[ValidatedEthereumAddress], Query(description="lock address")
    ] = None
    account_address: Annotated[
        Optional[ValidatedEthereumAddress], Query(description="account address")
    ] = None


############################
# RESPONSE
############################
class ListAllTokenLockResponse(BaseModel):
    result_set: ResultSet
    locked_list: list[Locked]


class RetrieveTokenLockCountResponse(BaseModel):
    count: int
