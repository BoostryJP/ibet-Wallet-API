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

from datetime import datetime, timezone
from enum import IntEnum, StrEnum
from typing import Annotated, Any, Generic, Optional, TypeVar

from annotated_types import Timezone
from fastapi import Query
from pydantic import AfterValidator, BaseModel, Field, WrapValidator, constr
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


EmailStr = constr(
    pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+.[a-zA-Z0-9-.]+$", max_length=100
)

ValidatedEthereumAddress = Annotated[str, WrapValidator(ethereum_address_validator)]

NaiveUTCDatetime = Annotated[datetime, Timezone(None)]


def naive_utc_datetime_validator(value: Any) -> NaiveUTCDatetime | None:
    """Validate datetime"""
    if value is not None:
        try:
            if value.tzinfo is None:
                # Return the datetime as is if it has no timezone info
                return value
            # Convert timezone to UTC
            dt_utc = value.astimezone(timezone.utc)

            # Return naive UTC datetime
            return dt_utc.replace(tzinfo=None)
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {str(e)}")
    return value


ValidatedNaiveUTCDatetime = Annotated[
    datetime, AfterValidator(naive_utc_datetime_validator)
]


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
