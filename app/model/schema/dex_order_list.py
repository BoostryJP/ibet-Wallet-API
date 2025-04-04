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

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

from app.model.schema.base import EthereumAddress
from app.model.schema.token_coupon import RetrieveCouponTokenResponse
from app.model.schema.token_membership import RetrieveMembershipTokenResponse

############################
# COMMON
############################


############################
# REQUEST
############################
class ListAllOrderListQuery(BaseModel):
    account_address_list: list[EthereumAddress] = Field(
        default_factory=list, description="Account address list"
    )
    include_canceled_items: Optional[bool] = Field(
        None, description="Whether to include canceled orders or canceled agreements."
    )


############################
# RESPONSE
############################
class TokenAddress(BaseModel):
    token_address: EthereumAddress


class Order(BaseModel):
    order_id: int
    counterpart_address: str
    amount: int
    price: int
    is_buy: bool
    canceled: bool
    order_timestamp: str


TokenModel = TypeVar(
    "TokenModel",
    RetrieveMembershipTokenResponse,
    RetrieveCouponTokenResponse,
    TokenAddress,
)


class OrderSet(BaseModel, Generic[TokenModel]):
    token: TokenModel
    order: Order
    sort_id: int


class Agreement(BaseModel):
    exchange_address: EthereumAddress = Field(description="exchange address")
    order_id: int
    agreement_id: int
    amount: int
    price: int
    is_buy: bool
    canceled: bool
    agreement_timestamp: str


class AgreementSet(BaseModel, Generic[TokenModel]):
    token: TokenModel
    agreement: Agreement
    sort_id: int


class CompleteAgreementSet(AgreementSet, Generic[TokenModel]):
    settlement_timestamp: str = Field(description="settlement timestamp")


class ListAllOrderListResponse(BaseModel, Generic[TokenModel]):
    order_list: list[OrderSet[TokenModel]]
    settlement_list: list[AgreementSet[TokenModel]]
    complete_list: list[CompleteAgreementSet[TokenModel]]
