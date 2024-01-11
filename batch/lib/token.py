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
from app.contracts import AsyncContract
from app.model.schema.base import TokenType


class TokenFactory:
    def __init__(self):
        pass

    def get_straight_bond(self, address):
        contract = AsyncContract.get_contract(TokenType.IbetStraightBond, address)
        return Token(contract)

    def get_share(self, address):
        contract = AsyncContract.get_contract(TokenType.IbetShare, address)
        return Token(contract)

    def get_membership(self, address):
        contract = AsyncContract.get_contract(TokenType.IbetMembership, address)
        return Token(contract)

    def get_coupon(self, address):
        contract = AsyncContract.get_contract(TokenType.IbetCoupon, address)
        return Token(contract)


class Token:
    def __init__(self, contract):
        self.contract = contract

    @property
    async def name(self):
        return await AsyncContract.call_function(
            contract=self.contract, function_name="name", args=(), default_returns=""
        )

    @property
    async def owner_address(self):
        return await AsyncContract.call_function(
            contract=self.contract, function_name="owner", args=(), default_returns=""
        )
