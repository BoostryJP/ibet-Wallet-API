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
from fastapi import Query
from pydantic.dataclasses import dataclass
from typing import Optional
from pydantic import (
    BaseModel,
    Field,
    validator
)
from web3 import Web3

############################
# COMMON
############################


############################
# REQUEST
############################

@dataclass
class RetrievePaymentAccountQuery:
    account_address: str = Query(..., description="Account Address")
    agent_address: str = Query(..., description="Agent Address")

    @validator("account_address")
    def account_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("account_address is not a valid address")
        return v

    @validator("agent_address")
    def agent_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("agent_address is not a valid address")
        return v


@dataclass
class RetrievePersonalInfoQuery:
    personal_info_address: Optional[str] = Query(default=None, description="PersonalInfo contract address")
    account_address: str = Query(..., description="account address")
    owner_address: str = Query(..., description="owner(issuer) address")

    @validator("personal_info_address")
    def personal_info_address_is_valid_address(cls, v):
        if v is not None:
            if not Web3.isAddress(v):
                raise ValueError("personal_info_address is not a valid address")
        return v

    @validator("account_address")
    def account_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("account_address is not a valid address")
        return v

    @validator("owner_address")
    def owner_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
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
    approval_status: ApprovalStatus = Field(description="approval status (NONE(0)/NG(1)/OK(2)/WARN(3)/BAN(4))")


class RetrievePersonalInfoRegistrationStatusResponse(BaseModel):
    account_address: str
    owner_address: str = Field(description="link address")
    registered: bool
