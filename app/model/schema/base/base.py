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

from enum import IntEnum, StrEnum
from typing import Annotated, Generic, Optional, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field, WrapValidator
from pydantic.dataclasses import dataclass

from app.validator import ethereum_address_validator


############################
# COMMON
############################
class TokenType(StrEnum):
    IbetStraightBond = "IbetStraightBond"
    IbetShare = "IbetShare"
    IbetMembership = "IbetMembership"
    IbetCoupon = "IbetCoupon"


class ValueOperator(IntEnum):
    EQUAL = 0
    GTE = 1
    LTE = 2


ValidatedEthereumAddress = Annotated[str, WrapValidator(ethereum_address_validator)]


############################
# REQUEST
############################
class SortOrder(IntEnum):
    ASC = 0
    DESC = 1


@dataclass
class ResultSetQuery:
    offset: Annotated[Optional[int], Query(description="start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="number of set", ge=0)] = None


############################
# RESPONSE
############################
class ResultSet(BaseModel):
    """result set for pagination"""

    count: Optional[int] = None
    offset: Optional[int] = Field(..., description="start position")
    limit: Optional[int] = Field(..., description="number of set")
    total: Optional[int] = None


class Success200MetaModel(BaseModel):
    code: int = Field(..., examples=[200])
    message: str = Field(..., examples=["OK"])


Data = TypeVar("Data")


class SuccessResponse(BaseModel):
    meta: Success200MetaModel = Field(
        ..., examples=[Success200MetaModel(code=200, message="OK").model_dump()]
    )
    data: dict = {}

    @staticmethod
    def default():
        return SuccessResponse(
            meta=Success200MetaModel(code=200, message="OK")
        ).model_dump()


class GenericSuccessResponse(BaseModel, Generic[Data]):
    meta: Success200MetaModel = Field(
        ..., examples=[Success200MetaModel(code=200, message="OK").model_dump()]
    )
    data: Data
