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

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field, RootModel

from app.model.schema.base import EthereumAddress

############################
# COMMON
############################


############################
# REQUEST
############################
class OrderType(StrEnum):
    buy = "buy"
    sell = "sell"


class ListAllOrderBookQuery(BaseModel):
    token_address: EthereumAddress = Field(..., description="Token address")
    exchange_agent_address: EthereumAddress = Field(
        ..., description="Settlement agent address on ibet exchange"
    )
    order_type: OrderType = Field(
        ...,
        description="Order type to be executed by the Orderer. If 'buy' is selected, the sell order book will be returned.",
    )
    account_address: Optional[EthereumAddress] = Field(
        None,
        description="Orderer's account address. Orders from the given address will not be included in the response.",
    )


class ListAllLastPriceQuery(BaseModel):
    address_list: list[EthereumAddress] = Field(
        default_factory=list, description="Token address list"
    )


class ListAllTickQuery(BaseModel):
    address_list: list[EthereumAddress] = Field(
        default_factory=list, description="Token address list"
    )


class RetrieveAgreementQuery(BaseModel):
    order_id: int = Field(..., description="order id")
    agreement_id: int = Field(..., description="agreement id")
    exchange_address: EthereumAddress = Field(..., description="exchange_address")


############################
# RESPONSE
############################
class OrderBookItem(BaseModel):
    exchange_address: EthereumAddress = Field(description="Exchange contract address")
    order_id: int = Field(description="Order id")
    price: int = Field(description="Order price")
    amount: int = Field(description="Order volume")
    account_address: EthereumAddress = Field(
        description="An orderrer of each order book"
    )


class ListAllOrderBookItemResponse(RootModel[list[OrderBookItem]]):
    pass


class LastPrice(BaseModel):
    token_address: EthereumAddress
    last_price: int


class ListAllLastPriceResponse(RootModel[list[LastPrice]]):
    pass


class Tick(BaseModel):
    block_timestamp: str = Field(description="block timestamp (UTC)")
    buy_address: EthereumAddress
    sell_address: EthereumAddress
    order_id: int
    agreement_id: int
    price: int
    amount: int


class Ticks(BaseModel):
    token_address: EthereumAddress
    tick: list[Tick]


class ListAllTicksResponse(RootModel[list[Ticks]]):
    pass


class RetrieveAgreementDetailResponse(BaseModel):
    token_address: EthereumAddress = Field(description="token address")
    counterpart: EthereumAddress = Field(description="taker account address")
    buyer_address: EthereumAddress = Field(description="buyer account address")
    seller_address: EthereumAddress = Field(description="seller account address")
    amount: int = Field(description="agreement token amount")
    price: int = Field(description="agreement price")
    canceled: bool = Field(description="agreement canceled status")
    paid: bool = Field(description="agreement payment status")
    expiry: int = Field(description="expiry (unixtime)")
