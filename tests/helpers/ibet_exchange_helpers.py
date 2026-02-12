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

from hexbytes import HexBytes

from tests.helpers.contract import Contract
from tests.types import DeployedContract, UnitTestAccount


def withdraw_from_exchange(
    invoker: UnitTestAccount,
    exchange: DeployedContract,
    token: DeployedContract,
) -> HexBytes:
    exchange_contract = Contract.get_contract(
        contract_name="IbetExchangeInterface", address=exchange["address"]
    )
    tx = exchange_contract.functions.withdraw(token["address"]).transact(
        {"from": invoker["account_address"]}  # type: ignore
    )
    return tx


###############################################################
# IbetSecurityTokenEscrow
###############################################################
# Create escrow
def create_security_token_escrow(
    invoker: UnitTestAccount,
    exchange: DeployedContract,
    token: DeployedContract,
    recipient_address: str,
    agent_address: str,
    amount: int,
    transfer_application_data: str = "{}",
    data: str = "{}",
) -> HexBytes:
    security_token_escrow_contract = Contract.get_contract(
        "IbetSecurityTokenEscrow", exchange["address"]
    )
    tx = security_token_escrow_contract.functions.createEscrow(
        token["address"],
        recipient_address,
        amount,
        agent_address,
        transfer_application_data,
        data,
    ).transact({"from": invoker["account_address"]})  # type: ignore
    return tx


def get_latest_security_escrow_id(exchange: DeployedContract) -> int:
    security_token_escrow_contract = Contract.get_contract(
        "IbetSecurityTokenEscrow", exchange["address"]
    )
    latest_escrow_id = security_token_escrow_contract.functions.latestEscrowId().call()
    return latest_escrow_id


# Cancel escrow
def cancel_security_token_escrow(
    invoker: UnitTestAccount, exchange: DeployedContract, escrow_id: int
) -> HexBytes:
    security_token_escrow_contract = Contract.get_contract(
        "IbetSecurityTokenEscrow", exchange["address"]
    )
    tx = security_token_escrow_contract.functions.cancelEscrow(escrow_id).transact(
        {"from": invoker["account_address"]}  # type: ignore
    )
    return tx


# Finish escrow
def finish_security_token_escrow(
    invoker: UnitTestAccount, exchange: DeployedContract, escrow_id: int
) -> HexBytes:
    security_token_escrow_contract = Contract.get_contract(
        "IbetSecurityTokenEscrow", exchange["address"]
    )
    tx = security_token_escrow_contract.functions.finishEscrow(escrow_id).transact(
        {"from": invoker["account_address"]}  # type: ignore
    )
    return tx


# Approve transfer
def approve_transfer_security_token_escrow(
    invoker: UnitTestAccount,
    exchange: DeployedContract,
    escrow_id: int,
    transfer_approval_data: str,
) -> HexBytes:
    security_token_escrow_contract = Contract.get_contract(
        "IbetSecurityTokenEscrow", exchange["address"]
    )
    tx = security_token_escrow_contract.functions.approveTransfer(
        escrow_id, transfer_approval_data
    ).transact({"from": invoker["account_address"]})  # type: ignore
    return tx


###############################################################
# IbetEscrow
###############################################################
# Create escrow
def create_token_escrow(
    invoker: UnitTestAccount,
    exchange: DeployedContract,
    token: DeployedContract,
    recipient_address: str,
    agent_address: str,
    amount: int,
) -> HexBytes:
    ibet_escrow = Contract.get_contract("IbetEscrow", exchange["address"])
    tx = ibet_escrow.functions.createEscrow(
        token["address"], recipient_address, amount, agent_address, "{}"
    ).transact({"from": invoker["account_address"]})  # type: ignore
    return tx


# Get latest escrow ID
def get_latest_escrow_id(exchange: DeployedContract) -> int:
    ibet_escrow = Contract.get_contract("IbetEscrow", exchange["address"])
    latest_escrow_id = ibet_escrow.functions.latestEscrowId().call()
    return latest_escrow_id


# Cancel escrow
def cancel_token_escrow(
    invoker: UnitTestAccount, exchange: DeployedContract, escrow_id: int
) -> HexBytes:
    ibet_escrow = Contract.get_contract("IbetEscrow", exchange["address"])
    tx = ibet_escrow.functions.cancelEscrow(escrow_id).transact(
        {"from": invoker["account_address"]}  # type: ignore
    )
    return tx


# Finish escrow
def finish_token_escrow(
    invoker: UnitTestAccount, exchange: DeployedContract, escrow_id: int
) -> HexBytes:
    ibet_escrow = Contract.get_contract("IbetEscrow", exchange["address"])
    tx = ibet_escrow.functions.finishEscrow(escrow_id).transact(
        {"from": invoker["account_address"]}  # type: ignore
    )
    return tx


###############################################################
# IbetSecurityTokenDVP
###############################################################
# Create DVP settlement
def create_security_token_delivery(
    invoker: UnitTestAccount,
    exchange: DeployedContract,
    token: DeployedContract,
    recipient_address: str,
    agent_address: str,
    amount: int,
) -> HexBytes:
    security_token_dvp_contract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    tx = security_token_dvp_contract.functions.createDelivery(
        token["address"],
        recipient_address,
        amount,
        agent_address,
        "{}",
    ).transact({"from": invoker["account_address"]})  # type: ignore
    return tx


def get_latest_security_delivery_id(exchange: DeployedContract) -> int:
    security_token_dvp_contract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    latest_delivery_id = security_token_dvp_contract.functions.latestDeliveryId().call()
    return latest_delivery_id


# Cancel DVP settlement
def cancel_security_token_delivery(
    invoker: UnitTestAccount, exchange: DeployedContract, delivery_id: int
) -> HexBytes:
    security_token_dvp_contract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    tx = security_token_dvp_contract.functions.cancelDelivery(delivery_id).transact(
        {"from": invoker["account_address"]}  # type: ignore
    )
    return tx


# Confirm DVP settlement
def confirm_security_token_delivery(
    invoker: UnitTestAccount, exchange: DeployedContract, delivery_id: int
) -> HexBytes:
    security_token_dvp_contract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    tx = security_token_dvp_contract.functions.confirmDelivery(delivery_id).transact(
        {"from": invoker["account_address"]}  # type: ignore
    )
    return tx


# Finish DVP settlement
def finish_security_token_delivery(
    invoker: UnitTestAccount, exchange: DeployedContract, delivery_id: int
) -> HexBytes:
    security_token_dvp_contract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    tx = security_token_dvp_contract.functions.finishDelivery(delivery_id).transact(
        {"from": invoker["account_address"]}  # type: ignore
    )
    return tx


# Abort DVP settlement
def abort_security_token_delivery(
    invoker: UnitTestAccount, exchange: DeployedContract, delivery_id: int
) -> HexBytes:
    security_token_dvp_contract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    tx = security_token_dvp_contract.functions.abortDelivery(delivery_id).transact(
        {"from": invoker["account_address"]}  # type: ignore
    )
    return tx
