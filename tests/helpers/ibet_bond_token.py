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

from web3 import Web3
from web3.contract import Contract as Web3Contract
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from tests.helpers.contract import Contract

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class IbetStraightBondTestHelper:
    @staticmethod
    def issue(tx_from: str, args: dict[str, Any]) -> Web3Contract:
        """
        Issue IbetStraightBond token

        :param tx_from: Transaction sender address
        :param args: IbetStraightBond issue arguments
        :return: IbetStraightBond contract instance
        """
        # issue
        interest_payment_date = json.dumps(
            {
                "interestPaymentDate1": args["interestPaymentDate1"],
                "interestPaymentDate2": args["interestPaymentDate2"],
                "interestPaymentDate3": args["interestPaymentDate3"],
                "interestPaymentDate4": args["interestPaymentDate4"],
                "interestPaymentDate5": args["interestPaymentDate5"],
                "interestPaymentDate6": args["interestPaymentDate6"],
                "interestPaymentDate7": args["interestPaymentDate7"],
                "interestPaymentDate8": args["interestPaymentDate8"],
                "interestPaymentDate9": args["interestPaymentDate9"],
                "interestPaymentDate10": args["interestPaymentDate10"],
                "interestPaymentDate11": args["interestPaymentDate11"],
                "interestPaymentDate12": args["interestPaymentDate12"],
            }
        )
        arguments = [
            args["name"],
            args["symbol"],
            args["totalSupply"],
            args["faceValue"],
            args["faceValueCurrency"],
            args["redemptionDate"],
            args["redemptionValue"],
            args["redemptionValueCurrency"],
            args["returnDate"],
            args["returnAmount"],
            args["purpose"],
        ]
        contract_address, _ = Contract.deploy_contract(
            "IbetStraightBond", arguments, tx_from
        )

        # update
        bond_contract = Contract.get_contract("IbetStraightBond", contract_address)
        if "tradableExchange" in args:
            bond_contract.functions.setTradableExchange(
                args["tradableExchange"]
            ).transact({"from": tx_from})
        if "interestRate" in args:
            bond_contract.functions.setInterestRate(args["interestRate"]).transact(
                {"from": tx_from}
            )
        bond_contract.functions.setInterestPaymentDate(interest_payment_date).transact(
            {"from": tx_from}
        )
        if "memo" in args:
            bond_contract.functions.setMemo(args["memo"]).transact({"from": tx_from})
        if "contactInformation" in args:
            bond_contract.functions.setContactInformation(
                args["contactInformation"]
            ).transact({"from": tx_from})
        if "privacyPolicy" in args:
            bond_contract.functions.setPrivacyPolicy(args["privacyPolicy"]).transact(
                {"from": tx_from}
            )
        if "personalInfoAddress" in args:
            bond_contract.functions.setPersonalInfoAddress(
                args["personalInfoAddress"]
            ).transact({"from": tx_from})
        if "requirePersonalInfoRegistered" in args:
            bond_contract.functions.setRequirePersonalInfoRegistered(
                args["requirePersonalInfoRegistered"]
            ).transact({"from": tx_from})
        bond_contract.functions.setTransferable(True).transact({"from": tx_from})
        if "interestPaymentCurrency" in args:
            bond_contract.functions.setInterestPaymentCurrency(
                args["interestPaymentCurrency"]
            ).transact({"from": tx_from})
        if "baseFxRate" in args:
            bond_contract.functions.setBaseFXRate(str(args["baseFxRate"])).transact(
                {"from": tx_from}
            )

        return bond_contract

    @staticmethod
    def mint(
        tx_from: str,
        token_address: str,
        target_address: str,
        amount: int,
        lock_address: str = config.ZERO_ADDRESS,
    ) -> None:
        """
        Mint IbetStraightBond token

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetStraightBond contract address
        :param target_address: Mint destination address
        :param amount: Mint amount
        :param lock_address: Lock address (default: ZERO_ADDRESS)
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStraightBond", address=token_address
        )
        token_contract.functions.issueFrom(
            target_address, lock_address, amount
        ).transact({"from": tx_from})

    @staticmethod
    def burn(
        tx_from: str,
        token_address: str,
        target_address: str,
        amount: int,
        lock_address: str = config.ZERO_ADDRESS,
    ) -> None:
        """
        Burn IbetStraightBond token

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetStraightBond contract address
        :param target_address: Burn source address
        :param amount: Burn amount
        :param lock_address: Lock address (default: ZERO_ADDRESS)
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStraightBond", address=token_address
        )
        token_contract.functions.redeemFrom(
            target_address, lock_address, amount
        ).transact({"from": tx_from})

    @staticmethod
    def register_token_list(
        tx_from: str,
        token_address: str,
        token_list_contract_address: str,
        token_template_name: str = "IbetStraightBond",
    ) -> None:
        """
        Register IbetStraightBond token to TokenList contract

        :param tx_from: Transaction sender address
        :param token_address: IbetStraightBond contract address
        :param token_list_contract_address: TokenList contract address
        :param token_template_name: Token template name (default: "IbetStraightBond")
        """
        token_list_contract = Contract.get_contract(
            contract_name="TokenList", address=token_list_contract_address
        )
        token_list_contract.functions.register(
            token_address, token_template_name
        ).transact({"from": tx_from})

    @staticmethod
    def transfer_token(tx_from: str, token_address: str, to: str, amount: int) -> None:
        """
        Transfer IbetStraightBond token

        :param tx_from: Transaction sender address
        :param token_address: IbetStraightBond contract address
        :param to: Transfer destination address
        :param amount: Transfer amount
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStraightBond", address=token_address
        )
        token_contract.functions.transfer(to, amount).transact({"from": tx_from})

    @staticmethod
    def force_transfer_token(
        tx_from: str, token_address: str, _from: str, _to: str, amount: int
    ) -> None:
        """
        Force transfer IbetStraightBond token

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetStraightBond token contract address
        :param _from: Transfer source address
        :param _to: Transfer destination address
        :param amount: Transfer amount
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStraightBond", address=token_address
        )
        token_contract.functions.transferFrom(_from, _to, amount).transact(
            {"from": tx_from}
        )

    @staticmethod
    def apply_for_token_transfer(
        tx_from: str, token_address: str, to: str, value: int
    ) -> None:
        """
        Apply for transfer on IbetStraightBond contract

        :param tx_from: Transaction sender address
        :param token_address: IbetStraightBond contract address
        :param to: Transfer destination address
        :param value: Transfer amount
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStraightBond", address=token_address
        )
        token_contract.functions.applyForTransfer(to, value, "").transact(
            {"from": tx_from}
        )

    @staticmethod
    def cancel_token_transfer_application(
        tx_from: str, token_address: str, application_id: int, application_data: str
    ) -> None:
        """
        Cancel transfer application on IbetStraightBond contract

        :param tx_from: Transaction sender address
        :param token_address: IbetStraightBond contract address
        :param application_id: Transfer application ID
        :param application_data: Transfer application data
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStraightBond", address=token_address
        )
        token_contract.functions.cancelTransfer(
            application_id, application_data
        ).transact({"from": tx_from})

    @staticmethod
    def approve_token_transfer(
        tx_from: str, token_address: str, application_id: int, application_data: str
    ) -> None:
        """
        Approve transfer application on IbetStraightBond contract

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetStraightBond contract address
        :param application_id: Transfer application ID
        :param application_data: Transfer application data
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStraightBond", address=token_address
        )
        token_contract.functions.approveTransfer(
            application_id, application_data
        ).transact({"from": tx_from})

    @staticmethod
    def lock_token(
        tx_from: str, token_address: str, lock_address: str, amount: int, lock_data: str
    ) -> None:
        """
        Lock IbetStraightBond token

        :param tx_from: Transaction sender address
        :param token_address: IbetStraightBond contract address
        :param lock_address: Lock destination address
        :param amount: Lock amount
        :param lock_data: Lock data
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStraightBond", address=token_address
        )
        token_contract.functions.lock(lock_address, amount, lock_data).transact(
            {"from": tx_from}
        )

    @staticmethod
    def force_lock_token(
        tx_from: str,
        token_address: str,
        lock_address: str,
        account_address: str,
        amount: int,
        lock_data: str,
    ) -> None:
        """
        Force lock IbetStraightBond token

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetStraightBond contract address
        :param lock_address: Lock destination address
        :param account_address: Account address to be locked
        :param amount: Lock amount
        :param lock_data: Lock data
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStraightBond", address=token_address
        )
        token_contract.functions.forceLock(
            lock_address, account_address, amount, lock_data
        ).transact({"from": tx_from})

    @staticmethod
    def force_change_locked_account(
        tx_from: str,
        token_address: str,
        lock_address: str,
        current_account_address: str,
        new_account_address: str,
        amount: int,
        change_data: str,
    ) -> None:
        """
        Force change locked account on IbetStraightBond token

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetStraightBond contract address
        :param lock_address: Lock address
        :param current_account_address: Current locked account address
        :param new_account_address: New locked account address
        :param amount: Amount to be changed
        :param change_data: Change data
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStraightBond", address=token_address
        )
        token_contract.functions.forceChangeLockedAccount(
            lock_address,
            current_account_address,
            new_account_address,
            amount,
            change_data,
        ).transact({"from": tx_from})

    @staticmethod
    def unlock_token(
        tx_from: str,
        token_address: str,
        account_address: str,
        recipient_address: str,
        amount: int,
        unlock_data: str,
    ) -> None:
        """
        Unlock IbetStraightBond token

        :param tx_from: Transaction sender address (lock address)
        :param token_address: IbetStraightBond contract address
        :param account_address: Account address to be unlocked
        :param recipient_address: Unlock destination address
        :param amount: Unlock amount
        :param unlock_data: Unlock data
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStraightBond", address=token_address
        )
        token_contract.functions.unlock(
            account_address, recipient_address, amount, unlock_data
        ).transact({"from": tx_from})

    @staticmethod
    def force_unlock_token(
        tx_from: str,
        token_address: str,
        lock_address: str,
        account_address: str,
        recipient_address: str,
        amount: int,
        unlock_data: str,
    ) -> None:
        """
        Force unlock IbetStraightBond token

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetStraightBond contract address
        :param lock_address: Lock address
        :param account_address: Account address to be unlocked
        :param recipient_address: Unlock destination address
        :param amount: Unlock amount
        :param unlock_data: Unlock data
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStraightBond", address=token_address
        )
        token_contract.functions.forceUnlock(
            lock_address, account_address, recipient_address, amount, unlock_data
        ).transact({"from": tx_from})

    @staticmethod
    def create_escrow(
        escrow_address: str,
        tx_from: str,
        token_address: str,
        recipient_address: str,
        amount: int,
        agent_address: str,
    ) -> None:
        """
        Create escrow on IbetSecurityTokenEscrow contract

        :param escrow_address: IbetSecurityTokenEscrow contract address
        :param tx_from: Transaction sender address
        :param token_address: IbetStraightBond contract address
        :param recipient_address: Escrow recipient address
        :param amount: Escrow amount
        :param agent_address: Escrow agent address
        """
        IbetStraightBondTestHelper.transfer_token(
            tx_from=tx_from,
            to=escrow_address,
            token_address=token_address,
            amount=amount,
        )
        escrow_contract = Contract.get_contract(
            contract_name="IbetSecurityTokenEscrow", address=escrow_address
        )
        escrow_contract.functions.createEscrow(
            token_address,
            recipient_address,
            amount,
            agent_address,
            "test_data",
            "test_data",
        ).transact({"from": tx_from})

    @staticmethod
    def set_transferable(tx_from: str, token_address: str, transferable: bool) -> None:
        """
        Set transferable on IbetStraightBond contract

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetStraightBond contract address
        :param transferable: Whether the token is transferable
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStraightBond", address=token_address
        )
        token_contract.functions.setTransferable(transferable).transact(
            {"from": tx_from}
        )

    @staticmethod
    def set_transfer_approval_required(
        tx_from: str, token_address: str, required: bool
    ) -> None:
        """
        Set transfer approval required on IbetStraightBond contract

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetStraightBond contract address
        :param required: Whether transfer approval is required
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStraightBond", address=token_address
        )
        token_contract.functions.setTransferApprovalRequired(required).transact(
            {"from": tx_from}
        )

    @staticmethod
    def set_token_status(tx_from: str, token_address: str, status: int) -> None:
        """
        Set token status on IbetStraightBond contract

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetStraightBond contract address
        :param status: Token status
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStraightBond", address=token_address
        )
        token_contract.functions.setStatus(status).transact({"from": tx_from})

    @staticmethod
    def change_to_redeemed(tx_from: str, token_address: str) -> None:
        """
        Change to redeemed status on IbetStraightBond contract

        :param tx_from: Transaction sender address (issuer)
        :param token_address: IbetStraightBond contract address
        """
        token_contract = Contract.get_contract(
            contract_name="IbetStraightBond", address=token_address
        )
        token_contract.functions.changeToRedeemed().transact({"from": tx_from})
