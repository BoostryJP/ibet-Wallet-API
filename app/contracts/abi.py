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
import json
import os
from enum import Enum
from functools import lru_cache
from typing import Any, List, Literal, Optional, Type, Union

import eth_utils.abi
from hexbytes import HexBytes
from pydantic import BaseModel, ConfigDict, RootModel, create_model
from web3 import Web3


class ABIInputType(str, Enum):
    address = "address"
    uint256 = "uint256"
    string = "string"
    bool = "bool"

    def to_python_type(self) -> Type:
        match self:
            case ABIInputType.address | ABIInputType.string:
                return str
            case ABIInputType.uint256:
                return int
            case ABIInputType.bool:
                return bool
            case _:
                return Any


class ABIDescriptionType(str, Enum):
    function = "function"
    constructor = "constructor"
    fallback = "fallback"
    event = "event"
    receive = "receive"


GENERIC_DESCRIPTION_TYPES = Union[
    Literal[ABIDescriptionType.constructor],
    Literal[ABIDescriptionType.fallback],
    Literal[ABIDescriptionType.receive],
]


class ABIDescriptionFunctionInput(BaseModel):
    name: str
    type: str
    components: Optional[List["ABIDescriptionFunctionInput"]] = None


ABIDescriptionFunctionInput.update_forward_refs()


class ABIDescriptionEventInput(BaseModel):
    indexed: bool
    name: str
    type: ABIInputType


class ABIGenericDescription(BaseModel):
    type: GENERIC_DESCRIPTION_TYPES


class ABIFunctionDescription(BaseModel):
    type: Literal[ABIDescriptionType.function]
    name: str
    inputs: List[ABIDescriptionFunctionInput]

    def get_selector(self) -> HexBytes:
        signature = self.get_signature()
        return Web3.keccak(text=signature)[0:4]

    def get_signature(self) -> str:
        joined_input_types = ",".join(
            input.type
            if input.type != "tuple"
            else eth_utils.abi.collapse_if_tuple(input.model_dump())
            for input in self.inputs
        )
        return f"{self.name}({joined_input_types})"


class ABIEventDescription(BaseModel):
    type: Literal[ABIDescriptionType.event]
    name: str
    inputs: List[ABIDescriptionEventInput]
    anonymous: bool


ABIDescription = Union[
    ABIEventDescription, ABIFunctionDescription, ABIGenericDescription
]


class ABI(RootModel[List[ABIDescription]]):
    pass


@lru_cache(None)
def create_abi_event_argument_models(contract_name: str) -> tuple[Type[BaseModel]]:
    contract_file = (
        f"{os.path.dirname(os.path.abspath(__file__))}/json/{contract_name}.json"
    )

    with open(contract_file, "r") as file:
        contract_json = json.load(file)
        abi_list = ABI.model_validate(contract_json.get("abi"))

        models = []
        for abi in abi_list.root:
            if abi.type != ABIDescriptionType.event:
                continue

            fields = {}
            for i in abi.inputs:
                if i.indexed is True:
                    fields[i.name] = (Optional[i.type.to_python_type()], None)

            if len(fields.values()) == 0:
                continue

            model = create_model(
                f"{abi.name.capitalize()}{abi.type.capitalize()}Argument",
                **fields,
                __config__=ConfigDict(extra="forbid"),
            )

            models.append(model)

        parent_model = Union[tuple(models)]
    return parent_model
