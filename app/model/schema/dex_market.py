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
from pydantic import (
    BaseModel,
    Field,
    validator
)
from web3 import Web3

from app.model.schema.base import QueryModel

############################
# COMMON
############################


############################
# REQUEST
############################

class OrderType(str, Enum):
    buy = "buy"
    sell = "sell"


class OrderBookRequest(BaseModel):
    account_address: Optional[str] = Field(description="Orderer's account address. Orders from the given address "
                                                       "will not be included in the response.")
    token_address: str = Field(description="Token address")
    order_type: OrderType = Field(description="Order type to be executed by the Orderer. "
                                              "If \"buy\" is selected, the sell order book will be returned.")

    @validator("token_address")
    def token_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("token_address is not a valid address")
        return v

    @validator("account_address")
    def account_address_is_valid_address(cls, v):
        if v is not None:
            if not Web3.isAddress(v):
                raise ValueError("account_address is not a valid address")
        return v


class LastPriceRequest(BaseModel):
    address_list: list[str] = Field(description="Token address list")

    @validator("address_list")
    def address_list_is_valid_address(cls, v):
        for address in v:
            if address is not None:
                if not Web3.isAddress(address):
                    raise ValueError("address_list has not a valid address")
        return v


class TickRequest(BaseModel):
    address_list: list[str] = Field(description="Token address list")

    @validator("address_list")
    def address_list_is_valid_address(cls, v):
        for address in v:
            if address is not None:
                if not Web3.isAddress(address):
                    raise ValueError("address_list has not a valid address")
        return v


class AgreementQuery(QueryModel):
    order_id: int = Field(description="order id")
    agreement_id: int = Field(description="agreement id")
    exchange_address: str = Field(description="exchange_address")

    @validator("exchange_address")
    def exchange_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
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


class OrderBookList(BaseModel):
    __root__: list[OrderBookItem]


class LastPrice(BaseModel):
    token_address: str
    last_price: int


class Tick(BaseModel):
    block_timestamp: str = Field(description="block timestamp (UTC)")
    buy_address: str
    sell_address: str
    order_id: int
    agreement_id: int
    price: int
    amount: int


class TicksResponse(BaseModel):
    token_address: str
    tick: list[Tick]


class AgreementDetail(BaseModel):
    token_address: str = Field(description="token address")
    counterpart: str = Field(description="taker account address")
    buyer_address: str = Field(description="buyer account address")
    seller_address: str = Field(description="seller account address")
    amount: int = Field(description="agreement token amount")
    price: int = Field(description="agreement price")
    canceled: bool = Field(description="agreement canceled status")
    paid: bool = Field(description="agreement payment status")
    expiry: str = Field(description="expiry (unixtime)")

