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
    root_validator,
    StrictStr
)

from app.model.schema.base import QueryModel

############################
# COMMON
############################


############################
# REQUEST
############################

class EventsQuery(QueryModel):
    from_block: int = Field(description="from block number", ge=1)
    to_block: int = Field(description="to block number", ge=1)

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


class E2EMessagingEventsQuery(EventsQuery):
    event: Optional[E2EMessagingEventType] = Field(description="events to get")
    argument_filters: Optional[str] = Field(
        description="filter argument. serialize obj to a JSON formatted str required."
                    "eg."
                    "```"
                    "{\"sender\": \"0x0000000000000000000000000000000000000000\"}"
                    "```"
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


class IbetEscrowEventsQuery(EventsQuery):
    event: Optional[IbetEscrowEventType] = Field(description="events to get")
    argument_filters: Optional[str] = Field(
        description="filter argument. serialize obj to a JSON formatted str required."
                    "eg."
                    "```"
                    "{"
                    "    \"escrowId\": 0"
                    "    \"token\": \"0x0000000000000000000000000000000000000000\""
                    "}"
                    "```"
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


class IbetSecurityTokenEscrowEventsQuery(EventsQuery):
    event: Optional[IbetSecurityTokenEscrowEventType] = Field(description="events to get")
    argument_filters: Optional[str] = Field(
        description="filter argument. serialize obj to a JSON formatted str required."
                    "eg."
                    "```"
                    "{"
                    "    \"escrowId\": 0"
                    "    \"token\": \"0x0000000000000000000000000000000000000000\""
                    "}"
                    "```"
    )


############################
# RESPONSE
############################

class Event(BaseModel):
    event: str = Field(description="the event name")
    args: object = Field(description="event args")
    transaction_hash: str = Field(description="transaction hash")
    block_number: int = Field(description="the block number where this log was in")
    log_index: int = Field(description="integer of the log index position in the block")
