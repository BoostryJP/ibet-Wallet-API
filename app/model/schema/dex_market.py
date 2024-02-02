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
from pydantic import BaseModel, Field, RootModel
from pydantic.dataclasses import dataclass

from app.model.schema.base import ValidatedEthereumAddress

############################
# COMMON
############################


############################
# REQUEST
############################
class OrderType(str, Enum):
    buy = "buy"
    sell = "sell"


@dataclass
class ListAllOrderBookQuery:
    token_address: Annotated[
        ValidatedEthereumAddress, Query(default=..., description="Token address")
    ]
    exchange_agent_address: Annotated[
        ValidatedEthereumAddress,
        Query(default=..., description="Settlement agent address on ibet exchange"),
    ]
    order_type: Annotated[
        OrderType,
        Query(
            default=...,
            description="Order type to be executed by the Orderer. "
            'If "buy" is selected, the sell order book will be returned.',
        ),
    ]
    account_address: Annotated[
        Optional[ValidatedEthereumAddress],
        Query(
            description="Orderer's account address. Orders from the given address will not be included in the response.",
        ),
    ] = None


@dataclass
class ListAllLastPriceQuery:
    address_list: Annotated[
        list[ValidatedEthereumAddress],
        Query(default_factory=list, description="Token address list"),
    ]


@dataclass
class ListAllTickQuery:
    address_list: Annotated[
        list[ValidatedEthereumAddress],
        Query(default_factory=list, description="Token address list"),
    ]


@dataclass
class RetrieveAgreementQuery:
    order_id: Annotated[int, Query(default=..., description="order id")]
    agreement_id: Annotated[int, Query(default=..., description="agreement id")]
    exchange_address: Annotated[
        ValidatedEthereumAddress, Query(default=..., description="exchange_address")
    ]


############################
# RESPONSE
############################
class OrderBookItem(BaseModel):
    exchange_address: ValidatedEthereumAddress = Field(
        description="Exchange contract address"
    )
    order_id: int = Field(description="Order id")
    price: int = Field(description="Order price")
    amount: int = Field(description="Order volume")
    account_address: ValidatedEthereumAddress = Field(
        description="An orderrer of each order book"
    )


class ListAllOrderBookItemResponse(RootModel[list[OrderBookItem]]):
    pass


class LastPrice(BaseModel):
    token_address: ValidatedEthereumAddress
    last_price: int


class ListAllLastPriceResponse(RootModel[list[LastPrice]]):
    pass


class Tick(BaseModel):
    block_timestamp: str = Field(description="block timestamp (UTC)")
    buy_address: ValidatedEthereumAddress
    sell_address: ValidatedEthereumAddress
    order_id: int
    agreement_id: int
    price: int
    amount: int


class Ticks(BaseModel):
    token_address: ValidatedEthereumAddress
    tick: list[Tick]


class ListAllTicksResponse(RootModel[list[Ticks]]):
    pass


class RetrieveAgreementDetailResponse(BaseModel):
    token_address: ValidatedEthereumAddress = Field(description="token address")
    counterpart: ValidatedEthereumAddress = Field(description="taker account address")
    buyer_address: ValidatedEthereumAddress = Field(description="buyer account address")
    seller_address: ValidatedEthereumAddress = Field(
        description="seller account address"
    )
    amount: int = Field(description="agreement token amount")
    price: int = Field(description="agreement price")
    canceled: bool = Field(description="agreement canceled status")
    paid: bool = Field(description="agreement payment status")
    expiry: int = Field(description="expiry (unixtime)")
