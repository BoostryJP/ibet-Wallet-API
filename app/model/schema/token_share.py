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
from typing import Optional

from fastapi import Query
from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass
from typing_extensions import Annotated

from app.model.schema.base import ResultSet, SortOrder, ValidatedEthereumAddress

############################
# COMMON
############################


############################
# REQUEST
############################
class ShareTokensSortItem(str, Enum):
    token_address = "token_address"
    owner_address = "owner_address"
    name = "name"
    symbol = "symbol"
    company_name = "company_name"
    tradable_exchange = "tradable_exchange"
    status = "status"
    personal_info_address = "personal_info_address"
    transferable = "transferable"
    is_offering = "is_offering"
    transfer_approval_required = "transfer_approval_required"
    is_canceled = "is_canceled"
    created = "created"


@dataclass
class ListAllShareTokensQuery:
    offset: Annotated[Optional[int], Query(description="start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="number of set", ge=0)] = None

    owner_address: Annotated[
        Optional[ValidatedEthereumAddress], Query(description="issuer address")
    ] = None
    name: Annotated[Optional[str], Query(description="token name")] = None
    symbol: Annotated[Optional[str], Query(description="token symbol")] = None
    company_name: Annotated[Optional[str], Query(description="company name")] = None
    tradable_exchange: Annotated[
        Optional[ValidatedEthereumAddress], Query(description="tradable exchange")
    ] = None
    status: Annotated[Optional[bool], Query(description="token status")] = None
    personal_info_address: Annotated[
        Optional[ValidatedEthereumAddress],
        Query(description="personal information address"),
    ] = None
    transferable: Annotated[
        Optional[bool], Query(description="transferable status")
    ] = None
    is_offering: Annotated[Optional[bool], Query(description="offering status")] = None
    transfer_approval_required: Annotated[
        Optional[bool], Query(description="transfer approval required status")
    ] = None
    is_canceled: Annotated[Optional[bool], Query(description="cancellation status")] = (
        None
    )

    sort_item: Annotated[
        Optional[ShareTokensSortItem], Query(description="sort item")
    ] = ShareTokensSortItem.created
    sort_order: Annotated[
        Optional[SortOrder], Query(description="sort order(0: ASC, 1: DESC)")
    ] = SortOrder.ASC


############################
# RESPONSE
############################
class DividendInformation(BaseModel):
    dividends: float = Field(examples=[999.9999999999999])
    dividend_record_date: str = Field(examples=["20200909"])
    dividend_payment_date: str = Field(examples=["20201001"])


class RetrieveShareTokenResponse(BaseModel):
    token_address: ValidatedEthereumAddress
    token_template: str = Field(examples=["IbetShare"])
    owner_address: ValidatedEthereumAddress = Field(description="issuer address")
    company_name: str
    rsa_publickey: str
    name: str = Field(description="token name")
    symbol: str = Field(description="token symbol")
    total_supply: int
    tradable_exchange: ValidatedEthereumAddress
    contact_information: str
    privacy_policy: str
    status: bool
    max_holding_quantity: Optional[int]
    max_sell_amount: Optional[int]
    personal_info_address: str
    transferable: bool
    is_offering: bool
    transfer_approval_required: bool
    issue_price: int
    cancellation_date: str
    memo: str
    principal_value: int
    is_canceled: bool
    dividend_information: DividendInformation


class ListAllShareTokensResponse(BaseModel):
    result_set: ResultSet
    tokens: list[RetrieveShareTokenResponse]


class ListAllShareTokenAddressesResponse(BaseModel):
    result_set: ResultSet
    address_list: list[ValidatedEthereumAddress]
