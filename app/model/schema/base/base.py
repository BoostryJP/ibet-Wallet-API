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

from fastapi import Query
from pydantic import BaseModel, Field, WrapValidator, constr
from pydantic.dataclasses import dataclass
from pydantic_core.core_schema import ValidatorFunctionWrapHandler

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


def datetime_string_validator(
    value: Any, handler: ValidatorFunctionWrapHandler, *args, **kwargs
) -> str | None:
    """Validate string datetime format

    - %Y-%m-%dT%H:%M:%S.%f
    """
    if value is not None:
        if not isinstance(value, str):
            raise ValueError("Value must be a string")
        try:
            dt = datetime.fromisoformat(value)

            # Ensure the datetime has timezone info
            if dt.tzinfo is None:
                raise ValueError("Timezone information is required")

            # Convert JST to UTC
            dt_utc = dt.astimezone(timezone.utc)

            # Strip timezone info and return as iso format string
            return dt_utc.replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S.%f")
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {str(e)}")
    return value


ValidatedDatetimeStr = Annotated[str, WrapValidator(datetime_string_validator)]


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
