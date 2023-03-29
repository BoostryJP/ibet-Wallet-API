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

from app.contracts import Contract


class TokenFactory:
    def __init__(self, web3):
        self.web3 = web3

    def get_straight_bond(self, address):
        contract = Contract.get_contract("IbetStraightBond", address)
        return Token(contract)

    def get_share(self, address):
        contract = Contract.get_contract("IbetShare", address)
        return Token(contract)

    def get_membership(self, address):
        contract = Contract.get_contract("IbetMembership", address)
        return Token(contract)

    def get_coupon(self, address):
        contract = Contract.get_contract("IbetCoupon", address)
        return Token(contract)


class Token:
    def __init__(self, contract):
        self.contract = contract

    @property
    def name(self):
        return Contract.call_function(
            contract=self.contract, function_name="name", args=(), default_returns=""
        )

    @property
    def owner_address(self):
        return Contract.call_function(
            contract=self.contract, function_name="owner", args=(), default_returns=""
        )
