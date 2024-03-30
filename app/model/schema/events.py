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
from typing import Annotated, Optional, Self

from fastapi import Query
from pydantic import BaseModel, Field, RootModel, StrictStr, model_validator
from pydantic.dataclasses import dataclass

from app.contracts import create_abi_event_argument_models

############################
# COMMON
############################


############################
# REQUEST
############################


class E2EMessagingEventType(str, Enum):
    PublicKeyUpdated = "PublicKeyUpdated"
    Message = "Message"


class E2EMessagingEventArguments(BaseModel):
    sender: Optional[StrictStr] = None
    receiver: Optional[StrictStr] = None
    who: Optional[StrictStr] = None


@dataclass
class E2EMessagingEventsQuery:
    from_block: Annotated[
        int, Query(default=..., description="from block number", ge=1)
    ]
    to_block: Annotated[int, Query(default=..., description="to block number", ge=1)]
    event: Annotated[
        Optional[E2EMessagingEventType], Query(description="events to get")
    ] = None
    argument_filters: Annotated[
        Optional[str],
        Query(
            description="filter argument. serialize obj to a JSON formatted str required."
            "eg."
            "```"
            '{"sender": "0x0000000000000000000000000000000000000000"}'
            "```",
        ),
    ] = None

    @model_validator(mode="after")
    @classmethod
    def validate_block_number(cls, values: Self):
        if values.to_block < values.from_block:
            raise ValueError("to_block must be greater than or equal to the from_block")
        return values


class IbetEscrowEventType(str, Enum):
    Deposited = "Deposited"
    Withdrawn = "Withdrawn"
    EscrowCreated = "EscrowCreated"
    EscrowCanceled = "EscrowCanceled"
    EscrowFinished = "EscrowFinished"


class EscrowEventArguments(BaseModel):
    token: Optional[str] = None
    account: Optional[str] = None
    escrowId: Optional[int] = None


@dataclass
class IbetEscrowEventsQuery:
    from_block: Annotated[
        int, Query(default=..., description="from block number", ge=1)
    ]
    to_block: Annotated[int, Query(default=..., description="to block number", ge=1)]
    event: Annotated[
        Optional[IbetEscrowEventType], Query(description="events to get")
    ] = None
    argument_filters: Annotated[
        Optional[str],
        Query(
            description="filter argument. serialize obj to a JSON formatted str required."
            "eg."
            "```"
            "{"
            '    "escrowId": 0'
            '    "token": "0x0000000000000000000000000000000000000000"'
            "}"
            "```",
        ),
    ] = None

    @model_validator(mode="after")
    @classmethod
    def validate_block_number(cls, values: Self):
        if values.to_block < values.from_block:
            raise ValueError("to_block must be greater than or equal to the from_block")
        return values


class IbetSecurityTokenEscrowEventType(str, Enum):
    Deposited = "Deposited"
    Withdrawn = "Withdrawn"
    EscrowCreated = "EscrowCreated"
    EscrowCanceled = "EscrowCanceled"
    EscrowFinished = "EscrowFinished"

    ApplyForTransfer = "ApplyForTransfer"
    CancelTransfer = "CancelTransfer"
    ApproveTransfer = "ApproveTransfer"
    FinishTransfer = "FinishTransfer"


@dataclass
class IbetSecurityTokenEscrowEventsQuery:
    from_block: Annotated[
        int, Query(default=..., description="from block number", ge=1)
    ]
    to_block: Annotated[int, Query(default=..., description="to block number", ge=1)]
    event: Annotated[
        Optional[IbetSecurityTokenEscrowEventType], Query(description="events to get")
    ] = None
    argument_filters: Annotated[
        Optional[str],
        Query(
            description="filter argument. serialize obj to a JSON formatted str required."
            "eg."
            "```"
            "{"
            '    "escrowId": 0'
            '    "token": "0x0000000000000000000000000000000000000000"'
            "}"
            "```",
        ),
    ] = None

    @model_validator(mode="after")
    @classmethod
    def validate_block_number(cls, values: Self):
        if values.to_block < values.from_block:
            raise ValueError("to_block must be greater than or equal to the from_block")
        return values


class SecurityTokenEventArguments(
    RootModel[create_abi_event_argument_models("IbetSecurityTokenInterface")]
):
    pass


class IbetSecurityTokenInterfaceEventType(str, Enum):
    Allot = "Allot"
    ApplyForOffering = "ApplyForOffering"
    ApplyForTransfer = "ApplyForTransfer"
    ApproveTransfer = "ApproveTransfer"
    CancelTransfer = "CancelTransfer"
    ChangeOfferingStatus = "ChangeOfferingStatus"
    ChangeStatus = "ChangeStatus"
    ChangeTransferApprovalRequired = "ChangeTransferApprovalRequired"
    Issue = "Issue"
    Lock = "Lock"
    Redeem = "Redeem"
    Transfer = "Transfer"
    Unlock = "Unlock"


@dataclass
class IbetSecurityTokenInterfaceEventsQuery:
    from_block: Annotated[
        int, Query(default=..., description="from block number", ge=1)
    ]
    to_block: Annotated[int, Query(default=..., description="to block number", ge=1)]
    event: Annotated[
        Optional[IbetSecurityTokenInterfaceEventType],
        Query(description="events to get"),
    ] = None
    argument_filters: Annotated[
        Optional[str],
        Query(
            description="filter argument. serialize obj to a JSON formatted str required."
            "eg."
            "```"
            "{"
            '    "from": "0x0000000000000000000000000000000000000000"'
            '    "to": "0x0000000000000000000000000000000000000000"'
            "}"
            "```",
        ),
    ] = None

    @model_validator(mode="after")
    @classmethod
    def validate_block_number(cls, values: Self):
        if values.to_block < values.from_block:
            raise ValueError("to_block must be greater than or equal to the from_block")
        return values


############################
# RESPONSE
############################


class Event(BaseModel):
    event: str = Field(description="the event name")
    args: object = Field(description="event args")
    transaction_hash: str = Field(description="transaction hash")
    block_number: int = Field(description="the block number where this log was in")
    block_timestamp: int = Field(description="timestamp where this log was in")
    log_index: int = Field(description="integer of the log index position in the block")


class ListAllEventsResponse(RootModel[list[Event]]):
    pass
