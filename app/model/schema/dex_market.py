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

from eth_utils import is_address
from fastapi import Query
from pydantic import BaseModel, Field, validator
from pydantic.dataclasses import dataclass

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
    account_address: Optional[str] = Query(
        default=None,
        description="Orderer's account address. Orders from the given address will not be included in the response.",
    )
    token_address: str = Query(description="Token address")
    exchange_agent_address: str = Query(
        description="Settlement agent address on ibet exchange"
    )
    order_type: OrderType = Query(
        description="Order type to be executed by the Orderer. "
        'If "buy" is selected, the sell order book will be returned.'
    )

    @validator("token_address")
    def token_address_is_valid_address(cls, v):
        if not is_address(v):
            raise ValueError("token_address is not a valid address")
        return v

    @validator("exchange_agent_address")
    def exchange_agent_address_is_valid_address(cls, v):
        if not is_address(v):
            raise ValueError("exchange_agent_address is not a valid address")
        return v

    @validator("account_address")
    def account_address_is_valid_address(cls, v):
        if v is not None:
            if not is_address(v):
                raise ValueError("account_address is not a valid address")
        return v


@dataclass
class ListAllLastPriceQuery:
    address_list: list[str] = Query(description="Token address list")

    @validator("address_list")
    def address_list_is_valid_address(cls, v):
        for address in v:
            if address is not None:
                if not is_address(address):
                    raise ValueError("address_list has not a valid address")
        return v


@dataclass
class ListAllTickQuery:
    address_list: list[str] = Query(description="Token address list")

    @validator("address_list")
    def address_list_is_valid_address(cls, v):
        for address in v:
            if address is not None:
                if not is_address(address):
                    raise ValueError("address_list has not a valid address")
        return v


@dataclass
class RetrieveAgreementQuery:
    order_id: int = Query(description="order id")
    agreement_id: int = Query(description="agreement id")
    exchange_address: str = Query(description="exchange_address")

    @validator("exchange_address")
    @classmethod
    def exchange_address_is_valid_address(cls, v):
        if not is_address(v):
            raise ValueError("owner_address is not a valid address")
        return v


############################
# RESPONSE
############################
class OrderBookItem(BaseModel):
    exchange_address: str = Field(description="Exchange contract address")
    order_id: int = Field(description="Order id")
    price: int = Field(description="Order price")
    amount: int = Field(description="Order volume")
    account_address: str = Field(description="An orderrer of each order book")


class ListAllOrderBookItemResponse(BaseModel):
    __root__: list[OrderBookItem]


class LastPrice(BaseModel):
    token_address: str
    last_price: int


class ListAllLastPriceResponse(BaseModel):
    __root__: list[LastPrice]


class Tick(BaseModel):
    block_timestamp: str = Field(description="block timestamp (UTC)")
    buy_address: str
    sell_address: str
    order_id: int
    agreement_id: int
    price: int
    amount: int


class Ticks(BaseModel):
    token_address: str
    tick: list[Tick]


class ListAllTicksResponse(BaseModel):
    __root__: list[Ticks]


class RetrieveAgreementDetailResponse(BaseModel):
    token_address: str = Field(description="token address")
    counterpart: str = Field(description="taker account address")
    buyer_address: str = Field(description="buyer account address")
    seller_address: str = Field(description="seller account address")
    amount: int = Field(description="agreement token amount")
    price: int = Field(description="agreement price")
    canceled: bool = Field(description="agreement canceled status")
    paid: bool = Field(description="agreement payment status")
    expiry: int = Field(description="expiry (unixtime)")
