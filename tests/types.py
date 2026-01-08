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

from typing import Any, NotRequired, TypedDict

from eth_typing import ChecksumAddress
from web3.contract import Contract as Web3Contract


class DeployedContract(TypedDict):
    address: str
    abi: NotRequired[Any]


class SharedContract(TypedDict):
    PaymentGateway: DeployedContract
    PersonalInfo: DeployedContract
    IbetShareExchange: DeployedContract
    IbetStraightBondExchange: DeployedContract
    IbetMembershipExchange: DeployedContract
    IbetCouponExchange: DeployedContract
    TokenList: DeployedContract
    E2EMessaging: Web3Contract
    IbetEscrow: Web3Contract
    IbetSecurityTokenEscrow: Web3Contract
    IbetSecurityTokenDVP: Web3Contract


class UnitTestAccount(TypedDict):
    account_address: ChecksumAddress
    password: str
