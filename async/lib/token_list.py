"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed onan "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""


class TokenList:
    def __init__(self, contract):
        self.contract = contract

    def is_registered(self, address):
        res = self.contract.functions.getTokenByAddress(address).call()
        return not (res[0] == "0x0000000000000000000000000000000000000000")

    def get_token(self, address):
        res = self.contract.functions.getTokenByAddress(address).call()  # token_address, token_template, owner_address
        return res
