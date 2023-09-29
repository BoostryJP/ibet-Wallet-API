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
from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass

from app.model.schema.base import ValidatedEthereumAddress

############################
# COMMON
############################


############################
# REQUEST
############################
@dataclass
class RetrievePaymentAccountQuery:
    account_address: Annotated[
        ValidatedEthereumAddress, Query(..., description="Account Address")
    ]
    agent_address: Annotated[
        ValidatedEthereumAddress, Query(..., description="Agent Address")
    ]


@dataclass
class RetrievePersonalInfoQuery:
    account_address: Annotated[
        ValidatedEthereumAddress, Query(..., description="Account Address")
    ]
    owner_address: Annotated[
        ValidatedEthereumAddress, Query(..., description="owner(issuer) address")
    ]
    personal_info_address: Annotated[
        Optional[ValidatedEthereumAddress],
        Query(description="PersonalInfo contract address"),
    ] = None


############################
# RESPONSE
############################
class ApprovalStatus(int, Enum):
    NONE = 0
    NG = 1
    OK = 2
    WARN = 3
    BAN = 4


class RetrievePaymentAccountRegistrationStatusResponse(BaseModel):
    account_address: ValidatedEthereumAddress
    agent_address: ValidatedEthereumAddress
    approval_status: ApprovalStatus = Field(
        description="approval status (NONE(0)/NG(1)/OK(2)/WARN(3)/BAN(4))"
    )


class RetrievePersonalInfoRegistrationStatusResponse(BaseModel):
    account_address: ValidatedEthereumAddress
    owner_address: ValidatedEthereumAddress = Field(description="link address")
    registered: bool
