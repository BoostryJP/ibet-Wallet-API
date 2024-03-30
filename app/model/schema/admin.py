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

from typing import Optional

from pydantic import BaseModel, Field, RootModel

from app.model.schema.base import ValidatedEthereumAddress

############################
# COMMON
############################


############################
# REQUEST
############################
class RegisterAdminTokenRequest(BaseModel):
    contract_address: ValidatedEthereumAddress = Field(..., description="Token Address")
    is_public: bool = Field(..., description="Public and private listings")
    max_holding_quantity: int | None = Field(
        None, ge=0, description="Maximum holding quantity limit"
    )
    max_sell_amount: int | None = Field(
        None, ge=0, description="Maximum sell amount limit"
    )


class UpdateAdminTokenRequest(BaseModel):
    is_public: bool | None = None
    max_holding_quantity: int | None = Field(None, ge=0)
    max_sell_amount: int | None = Field(None, ge=0)
    owner_address: ValidatedEthereumAddress | None = Field(None)


############################
# RESPONSE
############################
class RetrieveAdminTokenResponse(BaseModel):
    id: int = Field(...)
    token_address: ValidatedEthereumAddress = Field(..., description="Token address")
    is_public: bool = Field(...)
    max_holding_quantity: Optional[int]
    max_sell_amount: Optional[int]
    owner_address: ValidatedEthereumAddress = Field(..., description="Issuer address")
    created: str = Field(..., description="Create Datetime (local timezone)")


class ListAllAdminTokensResponse(RootModel[list[RetrieveAdminTokenResponse]]):
    pass


class GetAdminTokenTypeResponse(BaseModel):
    IbetStraightBond: bool = Field(...)
    IbetShare: bool = Field(...)
    IbetMembership: bool = Field(...)
    IbetCoupon: bool = Field(...)
