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
from enum import IntEnum
from fastapi.exceptions import RequestValidationError
from typing import TypeVar, Generic, Optional
from pydantic import (
    BaseModel,
    Field,
    ValidationError
)
from pydantic.generics import GenericModel
from pydantic.error_wrappers import ErrorWrapper


############################
# REQUEST
############################

class SortOrder(IntEnum):
    ASC = 0
    DESC = 1


class QueryModel(BaseModel):
    def __init__(self, **kwargs):
        try:
            super().__init__(**kwargs)
        except ValidationError as e:
            errors: list[ErrorWrapper] = []
            for error in e.raw_errors:
                raw_error = ErrorWrapper(exc=error.exc, loc=("query",) + error.loc_tuple())
                errors.append(raw_error)
            raise RequestValidationError(errors=errors) from None


class ResultSetQuery(QueryModel):
    offset: Optional[int] = Field(description="start position", ge=0)
    limit: Optional[int] = Field(description="number of set", ge=0)


############################
# RESPONSE
############################

class ResultSet(BaseModel):
    """result set for pagination"""
    count: Optional[int]
    offset: Optional[int] = Field(..., description="start position")
    limit: Optional[int] = Field(..., description="number of set")
    total: Optional[int]


class Success200MetaModel(BaseModel):
    code: int = Field(..., example=200)
    message: str = Field(..., example="OK")


Data = TypeVar("Data")


class SuccessResponse(BaseModel):
    meta: Success200MetaModel = Field(..., example=Success200MetaModel(code=200, message="OK"))
    data: dict = {}

    @staticmethod
    def use():
        return SuccessResponse(meta=Success200MetaModel(code=200, message="OK"))


class GenericSuccessResponse(GenericModel, Generic[Data]):
    meta: Success200MetaModel = Field(..., example=Success200MetaModel(code=200, message="OK"))
    data: Data
