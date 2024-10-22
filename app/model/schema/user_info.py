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

from pydantic import BaseModel, Field

from app.model.schema.base import EthereumAddress

############################
# COMMON
############################


############################
# REQUEST
############################
class TaggingAccountAddressRequest(BaseModel):
    account_address: EthereumAddress = Field(..., description="Account address")
    account_tag: str | None = Field(..., description="Account tag", max_length=50)


class RetrievePaymentAccountQuery(BaseModel):
    account_address: EthereumAddress = Field(..., description="Account Address")
    agent_address: EthereumAddress = Field(..., description="Agent Address")


class RetrievePersonalInfoQuery(BaseModel):
    account_address: EthereumAddress = Field(..., description="Account Address")
    owner_address: EthereumAddress = Field(..., description="Owner(issuer) address")
    personal_info_address: Optional[EthereumAddress] = Field(
        None, description="PersonalInfo contract address"
    )


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
    account_address: EthereumAddress
    agent_address: EthereumAddress
    approval_status: ApprovalStatus = Field(
        description="approval status (NONE(0)/NG(1)/OK(2)/WARN(3)/BAN(4))"
    )


class RetrievePersonalInfoRegistrationStatusResponse(BaseModel):
    account_address: EthereumAddress
    owner_address: EthereumAddress = Field(description="link address")
    registered: bool
