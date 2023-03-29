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
from typing import Generic, Optional, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass
from pydantic.generics import GenericModel

############################
# REQUEST
############################


class SortOrder(IntEnum):
    ASC = 0
    DESC = 1


@dataclass
class ResultSetQuery:
    offset: Optional[int] = Query(default=None, description="start position", ge=0)
    limit: Optional[int] = Query(default=None, description="number of set", ge=0)


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
    meta: Success200MetaModel = Field(
        ..., example=Success200MetaModel(code=200, message="OK")
    )
    data: dict = {}

    @staticmethod
    def default():
        return SuccessResponse(meta=Success200MetaModel(code=200, message="OK")).dict()


class GenericSuccessResponse(GenericModel, Generic[Data]):
    meta: Success200MetaModel = Field(
        ..., example=Success200MetaModel(code=200, message="OK")
    )
    data: Data
