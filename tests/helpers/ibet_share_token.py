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
from typing import Any

from eth_typing import HexStr
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract as Web3Contract
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import TxParams, Wei

from app import config
from tests.helpers.contract import Contract

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class IbetShareTestHelper:
    @staticmethod
    def issue(tx_from: str, args: dict[str, Any]) -> Web3Contract:
        """
        Issue IbetShare token

        :param tx_from: Transaction sender address
        :param args: IbetShare issue arguments
        :return: IbetShare contract instance
        """
        # issue
        arguments = [
            args["name"],
            args["symbol"],
            args["issuePrice"],
            args["totalSupply"],
            args["dividends"],
            args["dividendRecordDate"],
            args["dividendPaymentDate"],
            args["cancellationDate"],
            args["principalValue"],
        ]
        contract_address, _ = Contract.deploy_contract(
            contract_name="IbetShare", args=arguments, deployer=tx_from
        )

        # update
        share_contract = Contract.get_contract(
            contract_name="IbetShare", address=contract_address
        )
        if "tradableExchange" in args:
            share_contract.functions.setTradableExchange(
                args["tradableExchange"]
            ).transact({"from": tx_from})  # type: ignore
        if "personalInfoAddress" in args:
            share_contract.functions.setPersonalInfoAddress(
                args["personalInfoAddress"]
            ).transact({"from": tx_from})  # type: ignore
        if "requirePersonalInfoRegistered" in args:
            share_contract.functions.setRequirePersonalInfoRegistered(
                args["requirePersonalInfoRegistered"]
            ).transact({"from": tx_from})  # type: ignore
        if "contactInformation" in args:
            share_contract.functions.setContactInformation(
                args["contactInformation"]
            ).transact({"from": tx_from})  # type: ignore
        if "privacyPolicy" in args:
            share_contract.functions.setPrivacyPolicy(args["privacyPolicy"]).transact(
                {"from": tx_from}  # type: ignore
            )
        if "memo" in args:
            share_contract.functions.setMemo(args["memo"]).transact(
                {"from": tx_from}  # type: ignore
            )
        if "transferable" in args:
            share_contract.functions.setTransferable(args["transferable"]).transact(
                {"from": tx_from}  # type: ignore
            )
        if "transferApprovalRequired" in args:
            share_contract.functions.setTransferApprovalRequired(
                args["transferApprovalRequired"]
            ).transact({"from": tx_from})  # type: ignore

        return share_contract

    @staticmethod
    def mint(
        tx_from: str,
        token_address: str,
        target_address: str,
        amount: int,
        lock_address: str = config.ZERO_ADDRESS,
    ) -> HexBytes:
        """
        Mint IbetShare token

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetShare contract address
        :param target_address: Mint destination address
        :param amount: Mint amount
        :param lock_address: Lock address (default: ZERO_ADDRESS)
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        tx = token_contract.functions.issueFrom(
            target_address, lock_address, amount
        ).transact({"from": tx_from})  # type: ignore
        return tx

    @staticmethod
    def burn(
        tx_from: str,
        token_address: str,
        target_address: str,
        amount: int,
        lock_address: str = config.ZERO_ADDRESS,
    ) -> HexBytes:
        """
        Burn IbetShare token

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetShare contract address
        :param target_address: Burn source address
        :param amount: Burn amount
        :param lock_address: Lock address (default: ZERO_ADDRESS)
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        tx = token_contract.functions.redeemFrom(
            target_address, lock_address, amount
        ).transact({"from": tx_from})  # type: ignore
        return tx

    @staticmethod
    def register_token_list(
        tx_from: str,
        token_address: str,
        token_list_contract_address: str,
        token_template_name: str = "IbetShare",
    ) -> HexBytes:
        """
        Register IbetShare token to TokenList contract

        :param tx_from: Transaction sender address
        :param token_address: IbetShare token contract address
        :param token_list_contract_address: TokenList contract address
        :param token_template_name: Token template name (default: "IbetShare")
        """
        token_list_contract = Contract.get_contract(
            contract_name="TokenList", address=token_list_contract_address
        )
        tx = token_list_contract.functions.register(
            token_address, token_template_name
        ).transact({"from": tx_from})  # type: ignore
        return tx

    @staticmethod
    def transfer_token(
        tx_from: str, token_address: str, to: str, amount: int
    ) -> HexBytes:
        """
        Transfer IbetShare token

        :param tx_from: Transaction sender address
        :param token_address: IbetShare token contract address
        :param to: Recipient address
        :param amount: Transfer amount
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        tx = token_contract.functions.transfer(to, amount).transact({"from": tx_from})  # type: ignore
        return tx

    @staticmethod
    def reallocate_token(
        tx_from: str, token_address: str, to: str, amount: int
    ) -> HexBytes:
        """
        Reallocate IbetShare token

        :param tx_from: Transaction sender address
        :param token_address: IbetShare token contract address
        :param to: Reallocation destination address
        :param amount: Reallocation amount
        :return: Transaction object
        """
        token_contract: Any = Contract.get_contract("IbetShare", token_address)
        tx_params: TxParams = {
            "from": tx_from,
            "gas": 6000000,
            "gasPrice": Wei(0),
        }
        tx: TxParams = token_contract.functions.transfer(to, amount).build_transaction(
            tx_params
        )
        marker = b"\xc0\xff\xee\x00"
        annotation_data = json.dumps(
            {"purpose": "Reallocation"}, separators=(",", ":")
        ).encode("utf-8")
        tx_data = tx.get("data", "")
        if isinstance(tx_data, bytes):
            tx_data = tx_data.hex()
        else:
            tx_data = str(tx_data)
        tx["data"] = HexStr(tx_data + marker.hex() + annotation_data.hex())
        tx_hash = web3.eth.send_transaction(tx)
        # reallocate_token only needs a mined receipt because the batch indexer
        # reads the transaction input to classify the transfer as a reallocation.
        web3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_hash

    @staticmethod
    def force_transfer_token(
        tx_from: str, token_address: str, _from: str, _to: str, amount: int
    ) -> HexBytes:
        """
        Force transfer IbetShare token

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetShare token contract address
        :param _from: Transfer source address
        :param _to: Transfer destination address
        :param amount: Transfer amount
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        tx = token_contract.functions.transferFrom(_from, _to, amount).transact(
            {"from": tx_from}  # type: ignore
        )
        return tx

    @staticmethod
    def apply_for_token_transfer(
        tx_from: str,
        token_address: str,
        to: str,
        value: int,
        application_data: str = "",
    ) -> HexBytes:
        """
        Apply for transfer on IbetShare contract

        :param tx_from: Transaction sender address
        :param token_address: IbetShare contract address
        :param to: Transfer destination address
        :param value: Transfer amount
        :param application_data: Transfer application data
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        tx = token_contract.functions.applyForTransfer(
            to, value, application_data
        ).transact({"from": tx_from})  # type: ignore
        return tx

    @staticmethod
    def cancel_token_transfer_application(
        tx_from: str, token_address: str, application_id: int, application_data: str
    ) -> HexBytes:
        """
        Cancel transfer application on IbetShare contract

        :param tx_from: Transaction sender address
        :param token_address: IbetShare contract address
        :param application_id: Transfer application ID
        :param application_data: Transfer application data
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        tx = token_contract.functions.cancelTransfer(
            application_id, application_data
        ).transact({"from": tx_from})  # type: ignore
        return tx

    @staticmethod
    def approve_token_transfer(
        tx_from: str, token_address: str, application_id: int, application_data: str
    ) -> HexBytes:
        """
        Approve transfer application on IbetShare contract

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetShare contract address
        :param application_id: Transfer application ID
        :param application_data: Transfer application data
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        tx = token_contract.functions.approveTransfer(
            application_id, application_data
        ).transact({"from": tx_from})  # type: ignore
        return tx

    @staticmethod
    def lock_token(
        tx_from: str, token_address: str, lock_address: str, amount: int, lock_data: str
    ) -> HexBytes:
        """
        Lock IbetShare token

        :param tx_from: Transaction sender address
        :param token_address: IbetShare contract address
        :param lock_address: Lock destination address
        :param amount: Lock amount
        :param lock_data: Lock data
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        tx = token_contract.functions.lock(lock_address, amount, lock_data).transact(
            {"from": tx_from}  # type: ignore
        )
        return tx

    @staticmethod
    def force_lock_token(
        tx_from: str,
        token_address: str,
        lock_address: str,
        account_address: str,
        amount: int,
        lock_data: str,
    ) -> HexBytes:
        """
        Force lock IbetShare token

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetShare contract address
        :param lock_address: Lock destination address
        :param account_address: Account address to be locked
        :param amount: Lock amount
        :param lock_data: Lock data
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        tx = token_contract.functions.forceLock(
            lock_address, account_address, amount, lock_data
        ).transact({"from": tx_from})  # type: ignore
        return tx

    @staticmethod
    def unlock_token(
        tx_from: str,
        token_address: str,
        account_address: str,
        recipient_address: str,
        amount: int,
        unlock_data: str,
    ) -> HexBytes:
        """
        Unlock IbetShare token

        :param tx_from: Transaction sender address (lock address)
        :param token_address: IbetShare contract address
        :param account_address: Account address to be unlocked
        :param recipient_address: Unlock destination address
        :param amount: Unlock amount
        :param unlock_data: Unlock data
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        tx = token_contract.functions.unlock(
            account_address, recipient_address, amount, unlock_data
        ).transact({"from": tx_from})  # type: ignore
        return tx

    @staticmethod
    def force_unlock_token(
        tx_from: str,
        token_address: str,
        lock_address: str,
        account_address: str,
        recipient_address: str,
        amount: int,
        unlock_data: str,
    ) -> HexBytes:
        """
        Force unlock IbetShare token

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetShare contract address
        :param lock_address: Lock address
        :param account_address: Account address to be unlocked
        :param recipient_address: Unlock destination address
        :param amount: Unlock amount
        :param unlock_data: Unlock data
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        tx = token_contract.functions.forceUnlock(
            lock_address, account_address, recipient_address, amount, unlock_data
        ).transact({"from": tx_from})  # type: ignore
        return tx

    @staticmethod
    def force_change_locked_account(
        tx_from: str,
        token_address: str,
        lock_address: str,
        current_account_address: str,
        new_account_address: str,
        amount: int,
        change_data: str,
    ) -> HexBytes:
        """
        Force change locked account on IbetShare token

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetShare contract address
        :param lock_address: Lock address
        :param current_account_address: Current locked account address
        :param new_account_address: New locked account address
        :param amount: Amount to be changed
        :param change_data: Change data
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        tx = token_contract.functions.forceChangeLockedAccount(
            lock_address,
            current_account_address,
            new_account_address,
            amount,
            change_data,
        ).transact({"from": tx_from})  # type: ignore
        return tx

    @staticmethod
    def create_escrow(
        escrow_address: str,
        tx_from: str,
        token_address: str,
        recipient_address: str,
        amount: int,
        agent_address: str,
    ) -> HexBytes:
        """
        Create escrow on IbetSecurityTokenEscrow contract

        :param escrow_address: IbetSecurityTokenEscrow contract address
        :param tx_from: Transaction sender address
        :param token_address: IbetShare token contract address
        :param recipient_address: Escrow recipient address
        :param amount: Escrow amount
        :param agent_address: Escrow agent address
        :return: Transaction object
        """
        IbetShareTestHelper.transfer_token(
            tx_from=tx_from,
            to=escrow_address,
            token_address=token_address,
            amount=amount,
        )
        escrow_contract = Contract.get_contract(
            contract_name="IbetSecurityTokenEscrow", address=escrow_address
        )
        tx = escrow_contract.functions.createEscrow(
            token_address,
            recipient_address,
            amount,
            agent_address,
            "test_data",
            "test_data",
        ).transact({"from": tx_from})  # type: ignore
        return tx

    @staticmethod
    def set_transferable(
        tx_from: str, token_address: str, transferable: bool
    ) -> HexBytes:
        """
        Set transferable on IbetShare contract

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetShare contract address
        :param transferable: Whether the token is transferable
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        tx = token_contract.functions.setTransferable(transferable).transact(
            {"from": tx_from}  # type: ignore
        )
        return tx

    @staticmethod
    def set_transfer_approval_required(
        tx_from: str, token_address: str, required: bool
    ) -> HexBytes:
        """
        Set transfer approval required on IbetShare contract

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetShare contract address
        :param required: Whether transfer approval is required
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        tx = token_contract.functions.setTransferApprovalRequired(required).transact(
            {"from": tx_from}  # type: ignore
        )
        return tx

    @staticmethod
    def set_token_status(tx_from: str, token_address: str, status: int) -> HexBytes:
        """
        Set token status on IbetShare contract

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetShare contract address
        :param status: Token status
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        tx = token_contract.functions.setStatus(status).transact({"from": tx_from})  # type: ignore
        return tx

    @staticmethod
    def change_to_canceled(tx_from: str, token_address: str) -> HexBytes:
        """
        Change IbetShare token status to canceled

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetShare contract address
        :return: Transaction object
        """
        token_contract = Contract.get_contract(
            contract_name="IbetShare", address=token_address
        )
        tx = token_contract.functions.changeToCanceled().transact(
            {"from": tx_from}  # type: ignore
        )
        return tx
