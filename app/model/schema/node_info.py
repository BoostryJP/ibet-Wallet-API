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
from typing import Optional
from pydantic import (
    BaseModel,
    Field
)
from web3 import Web3

from app.model.schema.base import SuccessResponse

############################
# COMMON
############################


############################
# REQUEST
############################


############################
# RESPONSE
############################

class GetNodeInfoResponse(BaseModel):
    payment_gateway_address: Optional[str]
    payment_gateway_abi: Optional[object]
    personal_info_address: Optional[str]
    personal_info_abi: Optional[object]
    ibet_straightbond_exchange_address: Optional[str]
    ibet_straightbond_exchange_abi: Optional[object]
    ibet_membership_exchange_address: Optional[str]
    ibet_membership_exchange_abi: Optional[object]
    ibet_coupon_exchange_address: Optional[str]
    ibet_coupon_exchange_abi: Optional[object]
    ibet_share_exchange_address: Optional[str]
    ibet_share_exchange_abi: Optional[object]
    ibet_escrow_address: Optional[str]
    ibet_escrow_abi: Optional[object]
    ibet_security_token_escrow_address: Optional[str]
    ibet_security_token_escrow_abi: Optional[object]
    e2e_messaging_address: Optional[str]
    e2e_messaging_abi: Optional[object]
    agent_address: Optional[str]


class GetBlockSyncStatusResponse(BaseModel):
    is_synced: bool = Field(..., description="block sync status")
    latest_block_number: Optional[int] = Field(..., description="latest block number (returns null if is_synced is "
                                                                "false)")
