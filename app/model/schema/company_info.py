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
from optparse import Option
from typing import Optional
from pydantic import (
    BaseModel,
    Field,
    validator
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

class CompanyInfo(BaseModel):
    address: str
    corporate_name: str
    rsa_publickey: str
    homepage: str


class CompanyToken(BaseModel):
    token_address: str
    token_template: str
    owner_address: str
    rsa_publickey: str
    name: str
    symbol: str
    total_supply: int
    contract_information: str
    privacy_policy: str
    status: bool
    max_holding_quantity: int
    max_sell_amount: int
