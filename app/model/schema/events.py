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

from pydantic import BaseModel, Field, RootModel, StrictStr, model_validator

from app.contracts import create_abi_event_argument_models

############################
# COMMON
############################


############################
# REQUEST
############################
class E2EMessagingEventType(StrEnum):
    PublicKeyUpdated = "PublicKeyUpdated"
    Message = "Message"


class E2EMessagingEventArguments(BaseModel):
    sender: Optional[StrictStr] = None
    receiver: Optional[StrictStr] = None
    who: Optional[StrictStr] = None


class E2EMessagingEventsQuery(BaseModel):
    from_block: int = Field(..., description="from block number", ge=1)
    to_block: int = Field(..., description="to block number", ge=1)
    event: Optional[E2EMessagingEventType] = Field(None, description="events to get")
    argument_filters: Optional[str] = Field(
        None,
        description="filter argument. serialize obj to a JSON formatted str required."
        "eg."
        "```"
        '{"sender": "0x0000000000000000000000000000000000000000"}'
        "```",
    )

    @model_validator(mode="after")
    def validate_block_number(self):
        if self.to_block < self.from_block:
            raise ValueError("to_block must be greater than or equal to the from_block")
        return self


class IbetEscrowEventType(StrEnum):
    Deposited = "Deposited"
    Withdrawn = "Withdrawn"
    EscrowCreated = "EscrowCreated"
    EscrowCanceled = "EscrowCanceled"
    EscrowFinished = "EscrowFinished"


class EscrowEventArguments(BaseModel):
    token: Optional[str] = None
    account: Optional[str] = None
    escrowId: Optional[int] = None


class IbetEscrowEventsQuery(BaseModel):
    from_block: int = Field(..., description="from block number", ge=1)
    to_block: int = Field(..., description="to block number", ge=1)
    event: Optional[IbetEscrowEventType] = Field(None, description="events to get")
    argument_filters: Optional[str] = Field(
        None,
        description="filter argument. serialize obj to a JSON formatted str required."
        "eg."
        "```"
        "{"
        '    "escrowId": 0'
        '    "token": "0x0000000000000000000000000000000000000000"'
        "}"
        "```",
    )

    @model_validator(mode="after")
    def validate_block_number(self):
        if self.to_block < self.from_block:
            raise ValueError("to_block must be greater than or equal to the from_block")
        return self


class IbetSecurityTokenEscrowEventType(StrEnum):
    Deposited = "Deposited"
    Withdrawn = "Withdrawn"
    EscrowCreated = "EscrowCreated"
    EscrowCanceled = "EscrowCanceled"
    EscrowFinished = "EscrowFinished"

    ApplyForTransfer = "ApplyForTransfer"
    CancelTransfer = "CancelTransfer"
    ApproveTransfer = "ApproveTransfer"
    FinishTransfer = "FinishTransfer"


class IbetSecurityTokenEscrowEventsQuery(BaseModel):
    from_block: int = Field(..., description="from block number", ge=1)
    to_block: int = Field(..., description="to block number", ge=1)
    event: Optional[IbetSecurityTokenEscrowEventType] = Field(
        None, description="events to get"
    )
    argument_filters: Optional[str] = Field(
        None,
        description="filter argument. serialize obj to a JSON formatted str required."
        "eg."
        "```"
        "{"
        '    "escrowId": 0'
        '    "token": "0x0000000000000000000000000000000000000000"'
        "}"
        "```",
    )

    @model_validator(mode="after")
    def validate_block_number(self):
        if self.to_block < self.from_block:
            raise ValueError("to_block must be greater than or equal to the from_block")
        return self


class IbetSecurityTokenDVPEventType(StrEnum):
    Deposited = "Deposited"
    Withdrawn = "Withdrawn"
    DeliveryCreated = "DeliveryCreated"
    DeliveryCanceled = "DeliveryCanceled"
    DeliveryConfirmed = "DeliveryConfirmed"
    DeliveryFinished = "DeliveryFinished"
    DeliveryAborted = "DeliveryAborted"


class IbetSecurityTokenDVPEventArguments(BaseModel):
    token: Optional[str] = None
    account: Optional[str] = None
    deliveryId: Optional[int] = None


class IbetSecurityTokenDVPEventsQuery(BaseModel):
    from_block: int = Field(..., description="from block number", ge=1)
    to_block: int = Field(..., description="to block number", ge=1)
    event: Optional[IbetSecurityTokenDVPEventType] = Field(
        None, description="events to get"
    )
    argument_filters: Optional[str] = Field(
        None,
        description="filter argument. serialize obj to a JSON formatted str required."
        "eg."
        "```"
        "{"
        '    "deliveryId": 0'
        '    "token": "0x0000000000000000000000000000000000000000"'
        "}"
        "```",
    )

    @model_validator(mode="after")
    def validate_block_number(self):
        if self.to_block < self.from_block:
            raise ValueError("to_block must be greater than or equal to the from_block")
        return self


class SecurityTokenEventArguments(
    RootModel[create_abi_event_argument_models("IbetSecurityTokenInterface")]
):
    pass


class IbetSecurityTokenInterfaceEventType(StrEnum):
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


class IbetSecurityTokenInterfaceEventsQuery(BaseModel):
    from_block: int = Field(..., description="from block number", ge=1)
    to_block: int = Field(..., description="to block number", ge=1)
    event: Optional[IbetSecurityTokenInterfaceEventType] = Field(
        None, description="events to get"
    )
    argument_filters: Optional[str] = Field(
        None,
        description="filter argument. serialize obj to a JSON formatted str required."
        "eg."
        "```"
        "{"
        '    "from": "0x0000000000000000000000000000000000000000"'
        '    "to": "0x0000000000000000000000000000000000000000"'
        "}"
        "```",
    )

    @model_validator(mode="after")
    def validate_block_number(self):
        if self.to_block < self.from_block:
            raise ValueError("to_block must be greater than or equal to the from_block")
        return self


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
