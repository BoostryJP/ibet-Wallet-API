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

from enum import Enum, IntEnum
from typing import Annotated, Optional

from fastapi import Query
from pydantic import BaseModel, Field, RootModel, StrictStr, field_validator
from pydantic.dataclasses import dataclass

############################
# COMMON
############################


class SendRawTransactionStatus(IntEnum):
    Failure = 0
    Success = 1
    Pending = 2
    NonceTooLow = 3
    AlreadyKnown = 4


############################
# REQUEST
############################


class JsonRPCRequest(BaseModel):
    method: str = Field(description="method: eth_xxx")
    params: list = Field(description="parameters")

    @field_validator("method")
    @classmethod
    def method_is_available(cls, v):
        if v[: v.index("_")] not in ["eth"]:
            raise ValueError(f"The method {v} is not available")
        return v


class BlockIdentifier(str, Enum):
    latest = "latest"
    earliest = "earliest"
    pending = "pending"


@dataclass
class GetTransactionCountQuery:
    block_identifier: Annotated[Optional[BlockIdentifier], Query()] = None


class SendRawTransactionRequest(BaseModel):
    raw_tx_hex_list: list[StrictStr] = Field(
        description="Signed transaction list", min_length=1
    )


@dataclass
class WaitForTransactionReceiptQuery:
    transaction_hash: Annotated[
        StrictStr, Query(default=..., description="transaction hash")
    ]
    timeout: Annotated[
        Optional[int], Query(description="Timeout value", ge=1, le=30)
    ] = 5


############################
# RESPONSE
############################


class TransactionCountResponse(BaseModel):
    nonce: int = Field(..., examples=[34])
    gasprice: int = Field(..., examples=[0])
    chainid: str = Field(..., examples=["2017"])


class SendRawTransactionResponse(BaseModel):
    id: int = Field(..., examples=[1], description="transaction send order")
    status: SendRawTransactionStatus = Field(
        ...,
        examples=[1],
        description="execution failure:0, execution success:1, execution success("
        "pending transaction):2",
    )
    transaction_hash: Optional[str] = Field(
        default=None, description="transaction hash"
    )
    error_code: Optional[int] = Field(
        default=None, examples=[240202], description="error code thrown from contract"
    )
    error_msg: Optional[str] = Field(
        default=None,
        examples=["Message sender is not token owner."],
        description="error msg",
    )


class SendRawTransactionsResponse(RootModel[list[SendRawTransactionResponse]]):
    pass


class SendRawTransactionNoWaitResponse(BaseModel):
    id: int = Field(..., examples=[1], description="transaction send order")
    status: SendRawTransactionStatus = Field(
        ..., examples=[1], description="execution failure:0, execution success:1"
    )
    transaction_hash: Optional[str] = Field(
        default=None, description="transaction hash"
    )


class SendRawTransactionsNoWaitResponse(
    RootModel[list[SendRawTransactionNoWaitResponse]]
):
    pass


class WaitForTransactionReceiptResponse(BaseModel):
    status: int = Field(
        ..., examples=[1], description="transaction revert:0, transaction success:1"
    )
    error_code: Optional[int] = Field(
        default=None, examples=[240202], description="error code thrown from contract"
    )
    error_msg: Optional[str] = Field(
        default=None,
        examples=["Message sender is not token owner."],
        description="error msg",
    )
