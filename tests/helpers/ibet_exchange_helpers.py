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

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from tests.helpers.contract import Contract
from tests.types import DeployedContract, UnitTestAccount

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


def withdraw_from_exchange(
    invoker: UnitTestAccount,
    exchange: DeployedContract,
    token: DeployedContract,
):
    web3.eth.default_account = invoker["account_address"]
    exchange_contract = Contract.get_contract(
        contract_name="IbetExchangeInterface", address=exchange["address"]
    )
    exchange_contract.functions.withdraw(token["address"]).transact(
        {"from": invoker["account_address"]}
    )


###############################################################
# IbetSecurityTokenEscrow
###############################################################
# エスクローの作成
def create_security_token_escrow(
    invoker: UnitTestAccount,
    exchange: DeployedContract,
    token: DeployedContract,
    recipient_address: str,
    agent_address: str,
    amount: int,
    transfer_application_data: str = "{}",
    data: str = "{}",
):
    web3.eth.default_account = invoker["account_address"]
    security_token_escrow_contract = Contract.get_contract(
        "IbetSecurityTokenEscrow", exchange["address"]
    )
    security_token_escrow_contract.functions.createEscrow(
        token["address"],
        recipient_address,
        amount,
        agent_address,
        transfer_application_data,
        data,
    ).transact({"from": invoker["account_address"]})


def get_latest_security_escrow_id(exchange: DeployedContract) -> int:
    security_token_escrow_contract = Contract.get_contract(
        "IbetSecurityTokenEscrow", exchange["address"]
    )
    latest_escrow_id = security_token_escrow_contract.functions.latestEscrowId().call()
    return latest_escrow_id


# エスクローのキャンセル
def cancel_security_token_escrow(
    invoker: UnitTestAccount, exchange: DeployedContract, escrow_id: int
):
    web3.eth.default_account = invoker["account_address"]
    security_token_escrow_contract = Contract.get_contract(
        "IbetSecurityTokenEscrow", exchange["address"]
    )
    security_token_escrow_contract.functions.cancelEscrow(escrow_id).transact(
        {"from": invoker["account_address"]}
    )


# エスクローの完了
def finish_security_token_escrow(
    invoker: UnitTestAccount, exchange: DeployedContract, escrow_id: int
):
    web3.eth.default_account = invoker["account_address"]
    security_token_escrow_contract = Contract.get_contract(
        "IbetSecurityTokenEscrow", exchange["address"]
    )
    security_token_escrow_contract.functions.finishEscrow(escrow_id).transact(
        {"from": invoker["account_address"]}
    )


# 移転の承認
def approve_transfer_security_token_escrow(
    invoker: UnitTestAccount,
    exchange: DeployedContract,
    escrow_id: int,
    transfer_approval_data: str,
):
    web3.eth.default_account = invoker["account_address"]
    security_token_escrow_contract = Contract.get_contract(
        "IbetSecurityTokenEscrow", exchange["address"]
    )
    security_token_escrow_contract.functions.approveTransfer(
        escrow_id, transfer_approval_data
    ).transact({"from": invoker["account_address"]})


###############################################################
# IbetEscrow
###############################################################
# エスクローの作成
def create_token_escrow(
    invoker: UnitTestAccount,
    exchange: DeployedContract,
    token: DeployedContract,
    recipient_address: str,
    agent_address: str,
    amount: int,
):
    web3.eth.default_account = invoker["account_address"]
    ibet_escrow = Contract.get_contract("IbetEscrow", exchange["address"])
    ibet_escrow.functions.createEscrow(
        token["address"], recipient_address, amount, agent_address, "{}"
    ).transact({"from": invoker["account_address"]})


def get_latest_escrow_id(exchange: DeployedContract) -> int:
    ibet_escrow = Contract.get_contract("IbetEscrow", exchange["address"])
    latest_escrow_id = ibet_escrow.functions.latestEscrowId().call()
    return latest_escrow_id


# エスクローの完了
def finish_token_escrow(
    invoker: UnitTestAccount, exchange: DeployedContract, escrow_id: int
):
    web3.eth.default_account = invoker["account_address"]
    ibet_escrow = Contract.get_contract("IbetEscrow", exchange["address"])
    ibet_escrow.functions.finishEscrow(escrow_id).transact(
        {"from": invoker["account_address"]}
    )


###############################################################
# IbetSecurityTokenDVP
###############################################################
# DVP決済の作成
def create_security_token_delivery(
    invoker: UnitTestAccount,
    exchange: DeployedContract,
    token: DeployedContract,
    recipient_address: str,
    agent_address: str,
    amount: int,
):
    web3.eth.default_account = invoker["account_address"]
    security_token_dvp_contract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    security_token_dvp_contract.functions.createDelivery(
        token["address"],
        recipient_address,
        amount,
        agent_address,
        "{}",
    ).transact({"from": invoker["account_address"]})


def get_latest_security_delivery_id(exchange: DeployedContract) -> int:
    security_token_dvp_contract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    latest_delivery_id = security_token_dvp_contract.functions.latestDeliveryId().call()
    return latest_delivery_id


# DVP決済の取消
def cancel_security_token_delivery(
    invoker: UnitTestAccount, exchange: DeployedContract, delivery_id: int
):
    web3.eth.default_account = invoker["account_address"]
    security_token_dvp_contract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    security_token_dvp_contract.functions.cancelDelivery(delivery_id).transact(
        {"from": invoker["account_address"]}
    )


# DVP決済の確認
def confirm_security_token_delivery(
    invoker: UnitTestAccount, exchange: DeployedContract, delivery_id: int
):
    web3.eth.default_account = invoker["account_address"]
    security_token_dvp_contract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    security_token_dvp_contract.functions.confirmDelivery(delivery_id).transact(
        {"from": invoker["account_address"]}
    )


# DVP決済の完了
def finish_security_token_dvlivery(
    invoker: UnitTestAccount, exchange: DeployedContract, delivery_id: int
):
    web3.eth.default_account = invoker["account_address"]
    security_token_dvp_contract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    security_token_dvp_contract.functions.finishDelivery(delivery_id).transact(
        {"from": invoker["account_address"]}
    )


# DVP決済の中断
def abort_security_token_delivery(
    invoker: UnitTestAccount, exchange: DeployedContract, delivery_id: int
):
    web3.eth.default_account = invoker["account_address"]
    security_token_dvp_contract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    security_token_dvp_contract.functions.abortDelivery(delivery_id).transact(
        {"from": invoker["account_address"]}
    )
