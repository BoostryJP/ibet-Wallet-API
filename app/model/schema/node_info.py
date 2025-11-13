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

from pydantic import BaseModel, Field

from app.model.type import EthereumAddress

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
    payment_gateway_address: Optional[EthereumAddress]
    payment_gateway_abi: Optional[object]
    personal_info_address: Optional[EthereumAddress]
    personal_info_abi: Optional[object]
    ibet_membership_exchange_address: Optional[EthereumAddress]
    ibet_membership_exchange_abi: Optional[object]
    ibet_coupon_exchange_address: Optional[EthereumAddress]
    ibet_coupon_exchange_abi: Optional[object]
    ibet_escrow_address: Optional[EthereumAddress]
    ibet_escrow_abi: Optional[object]
    ibet_security_token_escrow_address: Optional[EthereumAddress]
    ibet_security_token_escrow_abi: Optional[object]
    ibet_security_token_dvp_address: Optional[EthereumAddress]
    ibet_security_token_dvp_abi: Optional[object]
    e2e_messaging_address: Optional[EthereumAddress]
    e2e_messaging_abi: Optional[object]


class GetBlockSyncStatusResponse(BaseModel):
    is_synced: bool = Field(..., description="block sync status")
    latest_block_number: Optional[int] = Field(
        ..., description="latest block number (returns null if is_synced is false)"
    )
