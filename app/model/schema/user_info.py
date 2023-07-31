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
from pydantic import BaseModel, Field, field_validator
from pydantic.dataclasses import dataclass
from web3 import Web3

############################
# COMMON
############################


############################
# REQUEST
############################


@dataclass
class RetrievePaymentAccountQuery:
    account_address: Annotated[str, Query(..., description="Account Address")]
    agent_address: Annotated[str, Query(..., description="Agent Address")]

    @field_validator("account_address")
    @classmethod
    def account_address_is_valid_address(cls, v):
        if not Web3.is_address(v):
            raise ValueError("account_address is not a valid address")
        return v

    @field_validator("agent_address")
    @classmethod
    def agent_address_is_valid_address(cls, v):
        if not Web3.is_address(v):
            raise ValueError("agent_address is not a valid address")
        return v


@dataclass
class RetrievePersonalInfoQuery:
    account_address: Annotated[str, Query(..., description="Account Address")]
    owner_address: Annotated[str, Query(..., description="owner(issuer) address")]
    personal_info_address: Annotated[
        Optional[str], Query(description="PersonalInfo contract address")
    ] = None

    @field_validator("personal_info_address")
    @classmethod
    def personal_info_address_is_valid_address(cls, v):
        if v is not None:
            if not Web3.is_address(v):
                raise ValueError("personal_info_address is not a valid address")
        return v

    @field_validator("account_address")
    @classmethod
    def account_address_is_valid_address(cls, v):
        if not Web3.is_address(v):
            raise ValueError("account_address is not a valid address")
        return v

    @field_validator("owner_address")
    @classmethod
    def owner_address_is_valid_address(cls, v):
        if not Web3.is_address(v):
            raise ValueError("owner_address is not a valid address")
        return v


############################
# RESPONSE
############################


class ApprovalStatus(int, Enum):
    NONE = 0
    NG = 1
    OK = 2
    WARN = 3
    BAN = 4


class RetrievePaymentAccountRegistrationStatusResponse(BaseModel):
    account_address: str
    agent_address: str
    approval_status: ApprovalStatus = Field(
        description="approval status (NONE(0)/NG(1)/OK(2)/WARN(3)/BAN(4))"
    )


class RetrievePersonalInfoRegistrationStatusResponse(BaseModel):
    account_address: str
    owner_address: str = Field(description="link address")
    registered: bool
