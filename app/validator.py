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

from typing import Any

from pydantic_core.core_schema import ValidatorFunctionWrapHandler
from web3 import Web3


def ethereum_address_validator(value: Any, handler: ValidatorFunctionWrapHandler):
    """Validator for ethereum address"""
    if value is not None:
        if not isinstance(value, str):
            raise ValueError("Value must be of string")
        if not Web3.is_address(value):
            raise ValueError("Invalid ethereum address")
    return handler(value)
