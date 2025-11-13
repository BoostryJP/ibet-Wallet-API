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

from typing import Optional, Union

from pydantic import BaseModel, Field, RootModel

from app.model.schema.base import EthereumAddress
from app.model.schema.token_bond import RetrieveStraightBondTokenResponse
from app.model.schema.token_coupon import RetrieveCouponTokenResponse
from app.model.schema.token_membership import RetrieveMembershipTokenResponse
from app.model.schema.token_share import RetrieveShareTokenResponse
from app.model.type.company_list import Trustee


############################
# COMMON
############################
class CompanyInfo(BaseModel):
    address: EthereumAddress
    corporate_name: str
    trustee: Trustee | None = None
    rsa_publickey: str
    homepage: str


############################
# REQUEST
############################
class ListAllCompaniesQuery(BaseModel):
    include_private_listing: Optional[bool] = Field(
        False, description="include private listing token issuers"
    )


class ListAllCompanyTokensQuery(BaseModel):
    include_private_listing: Optional[bool] = Field(
        False, description="include private listing token issuers"
    )


############################
# RESPONSE
############################
class RetrieveCompanyInfoResponse(CompanyInfo):
    in_use_personal_info_addresses: list[str]


class ListAllCompaniesResponse(RootModel[list[CompanyInfo]]):
    pass


class ListAllCompanyTokensResponse(
    RootModel[
        list[
            Union[
                RetrieveStraightBondTokenResponse,
                RetrieveShareTokenResponse,
                RetrieveMembershipTokenResponse,
                RetrieveCouponTokenResponse,
            ]
        ]
    ]
):
    pass


class CompanyToken(BaseModel):
    token_address: EthereumAddress
    token_template: str
    owner_address: EthereumAddress
    rsa_publickey: str
    name: str
    symbol: str
    total_supply: int
    contact_information: str
    privacy_policy: str
    status: bool
    max_holding_quantity: Optional[int]
    max_sell_amount: Optional[int]
