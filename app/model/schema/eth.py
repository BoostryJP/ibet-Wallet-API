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
from fastapi import Query
from typing import Optional
from pydantic import (
    BaseModel,
    Field,
    StrictStr
)
from pydantic.dataclasses import dataclass

############################
# COMMON
############################


############################
# REQUEST
############################

class BlockIdentifier(str, Enum):
    latest = "latest"
    earliest = "earliest"
    pending = "pending"


@dataclass
class GetTransactionCountQuery:
    block_identifier: Optional[BlockIdentifier] = Query(default=None)


class SendRawTransactionRequest(BaseModel):
    raw_tx_hex_list: list[StrictStr] = Field(description="Signed transaction list", min_items=1)


class WaitForTransactionReceiptRequest(BaseModel):
    transaction_hash: StrictStr = Field(description="transaction hash")
    timeout: Optional[int] = Field(default=5, description="Timeout value", ge=1, le=30)


############################
# RESPONSE
############################

class TransactionCountResponse(BaseModel):
    nonce: int = Field(..., example=34)
    gasprice: int = Field(..., example=0)
    chainid: str = Field(..., example="2017")


class SendRawTransactionResponse(BaseModel):
    id: int = Field(..., example=1, description="transaction send order")
    status: int = Field(..., example=1, description="execution failure:0, execution success:1, execution success("
                                                    "pending transaction):2")
    transaction_hash: Optional[str] = Field(description="transaction hash")
    error_code: Optional[int] = Field(example=240202, description="error code thrown from contract")
    error_msg: Optional[str] = Field(example="Message sender is not token owner.", description="error msg")


class SendRawTransactionsResponse(BaseModel):
    __root__: list[SendRawTransactionResponse]


class SendRawTransactionNoWaitResponse(BaseModel):
    id: int = Field(..., example=1, description="transaction send order")
    status: int = Field(..., example=1, description="execution failure:0, execution success:1")
    transaction_hash: Optional[str] = Field(description="transaction hash")


class SendRawTransactionsNoWaitResponse(BaseModel):
    __root__: list[SendRawTransactionNoWaitResponse]


class WaitForTransactionReceiptResponse(BaseModel):
    status: int = Field(..., example=1, description="transaction revert:0, transaction success:1")
    error_code: Optional[int] = Field(example=240202, description="error code thrown from contract")
    error_msg: Optional[str] = Field(example="Message sender is not token owner.", description="error msg")
