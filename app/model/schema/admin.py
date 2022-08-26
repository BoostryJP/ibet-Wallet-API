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


class RegisterAdminTokensRequest(BaseModel):
    contract_address: str = Field(..., description="Token Address")
    is_public: bool = Field(..., description="Public and private listings")
    max_holding_quantity: int | None = Field(None, ge=0, description="Maximum holding quantity limit")
    max_sell_amount: int | None = Field(None, ge=0, description="Maximum sell amount limit")

    @validator("contract_address")
    def contract_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("token_address is not a valid address")
        return v


class UpdateAdminTokenRequest(BaseModel):
    is_public: bool | None
    max_holding_quantity: int | None = Field(None, ge=0)
    max_sell_amount: int | None = Field(None, ge=0)
    owner_address: str | None = Field(None)

    @validator("owner_address")
    def owner_address_is_valid_address(cls, v):
        if v is not None:
            if not Web3.isAddress(v):
                raise ValueError("owner_address is not a valid address")
        return v

############################
# RESPONSE
############################


class AdminToken(BaseModel):
    id: str = Field(...)
    token_address: str = Field(...)
    is_public: bool = Field(...)
    max_holding_quantity: int = Field(...)
    max_sell_amount: int = Field(...)
    owner_address: str = Field(...)
    created: str = Field(..., description="Create Datetime (JST)")


class AdminTokensType(BaseModel):
    IbetStraightBond: bool = Field(...)
    IbetShare: bool = Field(...)
    IbetMembership: bool = Field(...)
    IbetCoupon: bool = Field(...)
