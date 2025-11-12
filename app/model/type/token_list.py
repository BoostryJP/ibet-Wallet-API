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

from typing import Literal

from eth_utils.address import to_checksum_address
from pydantic import BaseModel, field_validator

from app.model.schema.base import EthereumAddress


############################
# COMMON
############################
class TokenListItem(BaseModel):
    token_template: Literal["ibetBond", "ibetShare", "ibetMembership", "ibetCoupon"]
    product_type: int
    token_address: EthereumAddress
    key_manager: list[str]

    @field_validator("token_address")
    @classmethod
    def convert_to_checksum(cls, value: EthereumAddress) -> EthereumAddress:
        if value is None:
            return value
        return to_checksum_address(value)
