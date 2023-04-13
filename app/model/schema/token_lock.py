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
from typing import Optional

from fastapi import Query
from pydantic import BaseModel, StrictStr
from pydantic.dataclasses import dataclass

from app.model.schema.base import ResultSet, SortOrder

############################
# COMMON
############################


class Locked(BaseModel):
    token_address: str
    lock_address: str
    account_address: str
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
    lock_address: Optional[str] = Query(default=None, description="lock address")
    account_address: Optional[str] = Query(default=None, description="account address")
    offset: Optional[int] = Query(default=None, description="start position", ge=0)
    limit: Optional[int] = Query(default=None, description="number of set", ge=0)
    sort_item: ListAllLockSortItem = Query(
        default=ListAllLockSortItem.token_address, description="sort item"
    )
    sort_order: SortOrder = Query(
        default=SortOrder.ASC, description="sort order(0: ASC, 1: DESC)"
    )
    token_address_list: list[StrictStr] = Query(
        default=[], description="list of token address (**this affects total number**)"
    )


@dataclass
class RetrieveTokenLockCountQuery:
    lock_address: Optional[str] = Query(default=None, description="lock address")
    account_address: Optional[str] = Query(default=None, description="account address")
    token_address_list: list[StrictStr] = Query(
        default=[], description="list of token address"
    )


############################
# RESPONSE
############################


class ListAllTokenLockResponse(BaseModel):
    result_set: ResultSet
    locked_list: list[Locked]


class RetrieveTokenLockCountResponse(BaseModel):
    count: int
