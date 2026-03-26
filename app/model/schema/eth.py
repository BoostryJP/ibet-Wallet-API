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

from enum import IntEnum, StrEnum
from typing import Annotated, Literal, Optional, TypeAlias, TypedDict

from pydantic import BaseModel, Field, RootModel, StrictStr, field_validator

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
# DTO
############################


class SendRawTransactionResultBaseDict(TypedDict):
    id: int
    status: Literal[0, 1, 2, 3, 4]
    transaction_hash: str | None


class SendRawTransactionResultWithErrorDict(TypedDict):
    id: int
    status: Literal[0]
    transaction_hash: str | None
    error_code: int | None
    error_msg: str | None


SendRawTransactionResultDict: TypeAlias = (
    SendRawTransactionResultBaseDict | SendRawTransactionResultWithErrorDict
)


class SendRawTransactionNoWaitResultWithoutHashDict(TypedDict):
    id: int
    status: Literal[0]


class SendRawTransactionNoWaitResultWithHashDict(TypedDict):
    id: int
    status: Literal[0, 1, 3, 4]
    transaction_hash: str | None


SendRawTransactionNoWaitResultDict: TypeAlias = (
    SendRawTransactionNoWaitResultWithoutHashDict
    | SendRawTransactionNoWaitResultWithHashDict
)


class WaitForTransactionReceiptSuccessResultDict(TypedDict):
    status: Literal[1]


class WaitForTransactionReceiptFailureResultDict(TypedDict):
    status: Literal[0]
    error_code: int | None
    error_msg: str | None


WaitForTransactionReceiptResultDict: TypeAlias = (
    WaitForTransactionReceiptSuccessResultDict
    | WaitForTransactionReceiptFailureResultDict
)


############################
# REQUEST
############################


class JsonRPCRequest(BaseModel):
    method: str = Field(description="method: eth_xxx")
    params: list[object] = Field(description="parameters")

    @field_validator("method")
    @classmethod
    def method_is_available(cls, v: str) -> str:
        if v[: v.index("_")] not in ["eth"]:
            raise ValueError(f"The method {v} is not available")
        return v


class BlockIdentifier(StrEnum):
    latest = "latest"
    earliest = "earliest"
    pending = "pending"


class GetTransactionCountQuery(BaseModel):
    block_identifier: Optional[BlockIdentifier] = Field(None)


class SendRawTransactionRequest(BaseModel):
    raw_tx_hex_list: list[StrictStr] = Field(
        description="Signed transaction list", min_length=1
    )


class WaitForTransactionReceiptQuery(BaseModel):
    transaction_hash: StrictStr = Field(..., description="transaction hash")
    timeout: Optional[int] = Field(5, description="timeout value", ge=1, le=30)


############################
# RESPONSE
############################


class TransactionCountResponse(BaseModel):
    nonce: int = Field(..., examples=[34])
    gasprice: int = Field(..., examples=[0])
    chainid: str = Field(..., examples=["2017"])


class SendRawTransactionFailureResponse(BaseModel):
    id: int = Field(..., examples=[1], description="transaction send order")
    status: Literal[0] = Field(
        ...,
        examples=[0],
        description="execution failure",
    )
    transaction_hash: str | None = Field(..., description="transaction hash")
    error_code: int | None = Field(
        default=None, examples=[240202], description="error code thrown from contract"
    )
    error_msg: str | None = Field(
        default=None,
        examples=["Message sender is not token owner."],
        description="error msg",
    )


class SendRawTransactionSuccessResponse(BaseModel):
    id: int = Field(..., examples=[1], description="transaction send order")
    status: Literal[1, 2, 3, 4] = Field(
        ...,
        examples=[1],
        description="execution success:1, pending:2, nonce too low:3, already known:4",
    )
    transaction_hash: str | None = Field(..., description="transaction hash")


SendRawTransactionResponse: TypeAlias = Annotated[
    SendRawTransactionFailureResponse | SendRawTransactionSuccessResponse,
    Field(discriminator="status"),
]


class SendRawTransactionsResponse(RootModel[list[SendRawTransactionResponse]]):
    pass


class SendRawTransactionNoWaitFailureResponse(BaseModel):
    id: int = Field(..., examples=[1], description="transaction send order")
    status: Literal[0] = Field(..., examples=[0], description="execution failure")
    transaction_hash: str | None = Field(default=None, description="transaction hash")


class SendRawTransactionNoWaitSuccessResponse(BaseModel):
    id: int = Field(..., examples=[1], description="transaction send order")
    status: Literal[1, 3, 4] = Field(
        ...,
        examples=[1],
        description="execution success:1, nonce too low:3, already known:4",
    )
    transaction_hash: str | None = Field(default=None, description="transaction hash")


SendRawTransactionNoWaitResponse: TypeAlias = Annotated[
    SendRawTransactionNoWaitFailureResponse | SendRawTransactionNoWaitSuccessResponse,
    Field(discriminator="status"),
]


class SendRawTransactionsNoWaitResponse(
    RootModel[list[SendRawTransactionNoWaitResponse]]
):
    pass


class WaitForTransactionReceiptFailureResponse(BaseModel):
    status: Literal[0] = Field(..., examples=[0], description="transaction revert")
    error_code: int | None = Field(
        default=None, examples=[240202], description="error code thrown from contract"
    )
    error_msg: str | None = Field(
        default=None,
        examples=["Message sender is not token owner."],
        description="error msg",
    )


class WaitForTransactionReceiptSuccessResponse(BaseModel):
    status: Literal[1] = Field(..., examples=[1], description="transaction success")


WaitForTransactionReceiptResponse: TypeAlias = Annotated[
    WaitForTransactionReceiptFailureResponse | WaitForTransactionReceiptSuccessResponse,
    Field(discriminator="status"),
]
