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
from app.config import ZERO_ADDRESS
from app.contracts import AsyncContract


class TokenList:
    def __init__(self, contract, token_template=None):
        self.contract = contract
        self.token_template = token_template

    async def is_registered(self, address):
        token_info = await AsyncContract.call_function(
            contract=self.contract,
            function_name="getTokenByAddress",
            args=(address,),
            default_returns=(ZERO_ADDRESS, "", ZERO_ADDRESS),
        )
        if token_info[0] == ZERO_ADDRESS:
            return False
        if self.token_template is not None and token_info[1] != self.token_template:
            return False
        return True

    async def get_token(self, address):
        token_info = await AsyncContract.call_function(
            contract=self.contract,
            function_name="getTokenByAddress",
            args=(address,),
            default_returns=(ZERO_ADDRESS, "", ZERO_ADDRESS),
        )
        return token_info
