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
from pydantic import BaseModel, Field, StrictStr, root_validator
from pydantic.dataclasses import dataclass

from app.contracts import create_abi_event_argument_models

############################
# COMMON
############################


############################
# REQUEST
############################


@dataclass
class EventsQuery:
    from_block: int = Query(description="from block number", ge=1)
    to_block: int = Query(description="to block number", ge=1)

    @root_validator
    def validate_block_number(cls, values):
        if values["to_block"] < values["from_block"]:
            raise ValueError("to_block must be greater than or equal to the from_block")
        return values


class E2EMessagingEventType(str, Enum):
    PublicKeyUpdated = "PublicKeyUpdated"
    Message = "Message"


class E2EMessagingEventArguments(BaseModel):
    sender: Optional[StrictStr]
    receiver: Optional[StrictStr]
    who: Optional[StrictStr]


@dataclass
class E2EMessagingEventsQuery(EventsQuery):
    event: Optional[E2EMessagingEventType] = Query(
        default=None, description="events to get"
    )
    argument_filters: Optional[str] = Query(
        default=None,
        description="filter argument. serialize obj to a JSON formatted str required."
        "eg."
        "```"
        '{"sender": "0x0000000000000000000000000000000000000000"}'
        "```",
    )


class IbetEscrowEventType(str, Enum):
    Deposited = "Deposited"
    Withdrawn = "Withdrawn"
    EscrowCreated = "EscrowCreated"
    EscrowCanceled = "EscrowCanceled"
    EscrowFinished = "EscrowFinished"


class EscrowEventArguments(BaseModel):
    token: Optional[str]
    account: Optional[str]
    escrowId: Optional[int]


@dataclass
class IbetEscrowEventsQuery(EventsQuery):
    event: Optional[IbetEscrowEventType] = Query(
        default=None, description="events to get"
    )
    argument_filters: Optional[str] = Query(
        default=None,
        description="filter argument. serialize obj to a JSON formatted str required."
        "eg."
        "```"
        "{"
        '    "escrowId": 0'
        '    "token": "0x0000000000000000000000000000000000000000"'
        "}"
        "```",
    )


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
class IbetSecurityTokenEscrowEventsQuery(EventsQuery):
    event: Optional[IbetSecurityTokenEscrowEventType] = Query(
        default=None, description="events to get"
    )
    argument_filters: Optional[str] = Query(
        default=None,
        description="filter argument. serialize obj to a JSON formatted str required."
        "eg."
        "```"
        "{"
        '    "escrowId": 0'
        '    "token": "0x0000000000000000000000000000000000000000"'
        "}"
        "```",
    )


class SecurityTokenEventArguments(BaseModel):
    __root__: create_abi_event_argument_models("IbetSecurityTokenInterface")


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
class IbetSecurityTokenInterfaceEventsQuery(EventsQuery):
    event: Optional[IbetSecurityTokenInterfaceEventType] = Query(
        default=None, description="events to get"
    )
    argument_filters: Optional[str] = Query(
        default=None,
        description="filter argument. serialize obj to a JSON formatted str required."
        "eg."
        "```"
        "{"
        '    "from": "0x0000000000000000000000000000000000000000"'
        '    "to": "0x0000000000000000000000000000000000000000"'
        "}"
        "```",
    )


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


class ListAllEventsResponse(BaseModel):
    __root__: list[Event]
