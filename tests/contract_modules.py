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
from eth_utils.address import to_checksum_address
from web3 import Web3
from web3.contract import Contract as Web3Contract
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import TxParams, Wei

from app import config
from tests.account_config import eth_account
from tests.types import DeployedContract, UnitTestAccount
from tests.utils.contract import Contract

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


# 名簿用個人情報登録
# NOTE: issuer address に対する情報の公開を行う
def register_personalinfo(invoker: UnitTestAccount, personal_info: DeployedContract):
    web3.eth.default_account = invoker["account_address"]

    personal_info_contract = Contract.get_contract(
        "PersonalInfo", personal_info["address"]
    )

    issuer = eth_account["issuer"]
    encrypted_info = "some_encrypted_info"
    personal_info_contract.functions.register(
        issuer["account_address"], encrypted_info
    ).transact({"from": invoker["account_address"]})


# トークン移転
def transfer_token(
    token_contract: Web3Contract,
    from_address: str,
    to_address: str,
    amount: int,
):
    token_contract.functions.transfer(to_address, amount).transact(
        {"from": from_address}
    )


###############################################################
# Bond Token
###############################################################
# BONDトークン：発行
def bond_issue_token(
    invoker: UnitTestAccount, attribute: dict[str, Any]
) -> DeployedContract:
    web3.eth.default_account = invoker["account_address"]

    interest_payment_date = json.dumps(
        {
            "interestPaymentDate1": attribute["interestPaymentDate1"],
            "interestPaymentDate2": attribute["interestPaymentDate2"],
            "interestPaymentDate3": attribute["interestPaymentDate3"],
            "interestPaymentDate4": attribute["interestPaymentDate4"],
            "interestPaymentDate5": attribute["interestPaymentDate5"],
            "interestPaymentDate6": attribute["interestPaymentDate6"],
            "interestPaymentDate7": attribute["interestPaymentDate7"],
            "interestPaymentDate8": attribute["interestPaymentDate8"],
            "interestPaymentDate9": attribute["interestPaymentDate9"],
            "interestPaymentDate10": attribute["interestPaymentDate10"],
            "interestPaymentDate11": attribute["interestPaymentDate11"],
            "interestPaymentDate12": attribute["interestPaymentDate12"],
        }
    )

    arguments = [
        attribute["name"],
        attribute["symbol"],
        attribute["totalSupply"],
        attribute["faceValue"],
        attribute["faceValueCurrency"],
        attribute["redemptionDate"],
        attribute["redemptionValue"],
        attribute["redemptionValueCurrency"],
        attribute["returnDate"],
        attribute["returnAmount"],
        attribute["purpose"],
    ]

    contract_address, abi = Contract.deploy_contract(
        "IbetStraightBond", arguments, invoker["account_address"]
    )

    # その他項目の更新
    token_contract = Contract.get_contract("IbetStraightBond", contract_address)
    if "tradableExchange" in attribute:
        token_contract.functions.setTradableExchange(
            attribute["tradableExchange"]
        ).transact({"from": invoker["account_address"]})
    if "interestRate" in attribute:
        token_contract.functions.setInterestRate(attribute["interestRate"]).transact(
            {"from": invoker["account_address"]}
        )
    token_contract.functions.setInterestPaymentDate(interest_payment_date).transact(
        {"from": invoker["account_address"]}
    )
    if "memo" in attribute:
        token_contract.functions.setMemo(attribute["memo"]).transact(
            {"from": invoker["account_address"]}
        )
    if "contactInformation" in attribute:
        token_contract.functions.setContactInformation(
            attribute["contactInformation"]
        ).transact({"from": invoker["account_address"]})
    if "privacyPolicy" in attribute:
        token_contract.functions.setPrivacyPolicy(attribute["privacyPolicy"]).transact(
            {"from": invoker["account_address"]}
        )
    if "personalInfoAddress" in attribute:
        token_contract.functions.setPersonalInfoAddress(
            attribute["personalInfoAddress"]
        ).transact({"from": invoker["account_address"]})
    if "requirePersonalInfoRegistered" in attribute:
        token_contract.functions.setRequirePersonalInfoRegistered(
            attribute["requirePersonalInfoRegistered"]
        ).transact({"from": invoker["account_address"]})
    token_contract.functions.setTransferable(True).transact(
        {"from": invoker["account_address"]}
    )
    if "interestPaymentCurrency" in attribute:
        token_contract.functions.setInterestPaymentCurrency(
            attribute["interestPaymentCurrency"]
        ).transact({"from": invoker["account_address"]})
    if "baseFxRate" in attribute:
        token_contract.functions.setBaseFXRate(str(attribute["baseFxRate"])).transact(
            {"from": invoker["account_address"]}
        )

    return {"address": contract_address, "abi": abi}


# BONDトークン：公開リスト登録
def bond_register_token_list(
    invoker: UnitTestAccount, bond_token: DeployedContract, token_list: DeployedContract
):
    token_list_contract = Contract.get_contract("TokenList", token_list["address"])

    web3.eth.default_account = invoker["account_address"]

    token_list_contract.functions.register(
        bond_token["address"], "IbetStraightBond"
    ).transact({"from": invoker["account_address"]})


# BONDトークン：取引コントラクトにデポジット
def bond_transfer_to_exchange(
    invoker: UnitTestAccount,
    bond_exchange: DeployedContract,
    bond_token: DeployedContract,
    amount: int,
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", bond_token["address"])
    token_contract.functions.transfer(bond_exchange["address"], amount).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：移転
def bond_transfer_token(
    invoker: UnitTestAccount, to: UnitTestAccount, token: DeployedContract, amount: int
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.transfer(to["account_address"], amount).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：償還
def bond_redeem(invoker: UnitTestAccount, token: DeployedContract):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.changeToRedeemed().transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：譲渡可否変更
def bond_set_transferable(
    invoker: UnitTestAccount, token: DeployedContract, transferable: bool
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.setTransferable(transferable).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：無効化
def bond_set_status(invoker: UnitTestAccount, token: DeployedContract):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.setStatus(False).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：譲渡不可設定
def bond_untransferable(invoker: UnitTestAccount, token: DeployedContract):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.setTransferable(False).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：移転承諾要否フラグの更新
def bond_set_transfer_approval_required(
    invoker: UnitTestAccount, token: DeployedContract, required: bool
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.setTransferApprovalRequired(required).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：移転申請
def bond_apply_for_transfer(
    invoker: UnitTestAccount,
    token: DeployedContract,
    recipient: UnitTestAccount,
    amount: int,
    application_data: str,
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.applyForTransfer(
        recipient["account_address"], amount, application_data
    ).transact({"from": invoker["account_address"]})


# BONDトークン：移転申請取消
def bond_cancel_transfer(
    invoker: UnitTestAccount,
    token: DeployedContract,
    application_id: int,
    application_data: str,
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.cancelTransfer(application_id, application_data).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：移転申請承認
def bond_approve_transfer(
    invoker: UnitTestAccount,
    token: DeployedContract,
    application_id: int,
    application_data: str,
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.approveTransfer(application_id, application_data).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：資産ロック
def bond_lock(
    invoker: UnitTestAccount,
    token: DeployedContract,
    lock_address: str,
    amount: int,
    data_str: str = "",
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.lock(lock_address, amount, data_str).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：資産強制ロック
def bond_force_lock(
    invoker: UnitTestAccount,
    token: DeployedContract,
    lock_address: str,
    account_address: str,
    amount: int,
    data_str: str = "",
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.forceLock(
        lock_address, account_address, amount, data_str
    ).transact({"from": invoker["account_address"]})


# BONDトークン：資産アンロック
def bond_unlock(
    invoker: UnitTestAccount,
    token: DeployedContract,
    target: str,
    recipient: str,
    amount: int,
    data_str: str = "",
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.unlock(target, recipient, amount, data_str).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：資産強制アンロック
def bond_force_unlock(
    invoker: UnitTestAccount,
    token: DeployedContract,
    lock_address: str,
    target: str,
    recipient: str,
    amount: int,
    data_str: str = "",
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.forceUnlock(
        lock_address, target, recipient, amount, data_str
    ).transact({"from": invoker["account_address"]})


# BONDトークン：資産ロック元強制変更
def bond_force_change_locked_account(
    invoker: UnitTestAccount,
    token: DeployedContract,
    lock_address: str,
    before_account_address: str,
    after_account_address: str,
    amount: int,
    data_str: str = "",
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.forceChangeLockedAccount(
        lock_address, before_account_address, after_account_address, amount, data_str
    ).transact({"from": invoker["account_address"]})


# BONDトークン：追加発行
def bond_issue_from(
    invoker: UnitTestAccount,
    token: DeployedContract,
    target: str,
    amount: int,
    lock_address: str = config.ZERO_ADDRESS,
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.issueFrom(target, lock_address, amount).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：発行数量の削減
def bond_redeem_from(
    invoker: UnitTestAccount,
    token: DeployedContract,
    target_address: str,
    amount: int,
    lock_address: str = config.ZERO_ADDRESS,
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.redeemFrom(target_address, lock_address, amount).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：取引コントラクトの更新
def bond_set_tradable_exchange(
    invoker: UnitTestAccount, token: DeployedContract, exchange_address: str
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.setTradableExchange(exchange_address).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：償還状態に変更
def bond_change_to_redeemed(invoker: UnitTestAccount, token: DeployedContract):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetStraightBond", token["address"])
    token_contract.functions.changeToRedeemed().transact(
        {"from": invoker["account_address"]}
    )


###############################################################
# Share Token
###############################################################
# SHAREトークン：発行
def share_issue_token(
    invoker: UnitTestAccount, attribute: dict[str, Any]
) -> DeployedContract:
    web3.eth.default_account = invoker["account_address"]

    arguments = [
        attribute["name"],
        attribute["symbol"],
        attribute["issuePrice"],
        attribute["totalSupply"],
        attribute["dividends"],
        attribute["dividendRecordDate"],
        attribute["dividendPaymentDate"],
        attribute["cancellationDate"],
        attribute["principalValue"],
    ]
    contract_address, abi = Contract.deploy_contract(
        contract_name="IbetShare", args=arguments, deployer=invoker["account_address"]
    )

    token_contract = Contract.get_contract("IbetShare", contract_address)
    if "tradableExchange" in attribute:
        token_contract.functions.setTradableExchange(
            to_checksum_address(attribute["tradableExchange"])
        ).transact({"from": invoker["account_address"]})
    if "personalInfoAddress" in attribute:
        token_contract.functions.setPersonalInfoAddress(
            to_checksum_address(attribute["personalInfoAddress"])
        ).transact({"from": invoker["account_address"]})
    if "requirePersonalInfoRegistered" in attribute:
        token_contract.functions.setRequirePersonalInfoRegistered(
            attribute["requirePersonalInfoRegistered"]
        ).transact({"from": invoker["account_address"]})
    if "contactInformation" in attribute:
        token_contract.functions.setContactInformation(
            attribute["contactInformation"]
        ).transact({"from": invoker["account_address"]})
    if "privacyPolicy" in attribute:
        token_contract.functions.setPrivacyPolicy(attribute["privacyPolicy"]).transact(
            {"from": invoker["account_address"]}
        )
    if "memo" in attribute:
        token_contract.functions.setMemo(attribute["memo"]).transact(
            {"from": invoker["account_address"]}
        )
    if "transferable" in attribute:
        token_contract.functions.setTransferable(attribute["transferable"]).transact(
            {"from": invoker["account_address"]}
        )

    return {"address": contract_address, "abi": abi}


# SHAREトークン：公開リスト登録
def share_register_token_list(
    invoker: UnitTestAccount,
    share_token: DeployedContract,
    token_list: DeployedContract,
):
    token_list_contract = Contract.get_contract("TokenList", token_list["address"])

    web3.eth.default_account = invoker["account_address"]

    token_list_contract.functions.register(
        share_token["address"], "IbetShare"
    ).transact({"from": invoker["account_address"]})


# SHAREトークン：取引コントラクトにデポジット
def share_transfer_to_exchange(
    invoker: UnitTestAccount,
    exchange: DeployedContract,
    token: DeployedContract,
    amount: int,
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetShare", token["address"])
    token_contract.functions.transfer(exchange["address"], amount).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：移転
def share_transfer_token(
    invoker: UnitTestAccount, to: UnitTestAccount, token: DeployedContract, amount: int
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetShare", token["address"])
    token_contract.functions.transfer(to["account_address"], amount).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：移管
def share_reallocate_token(
    invoker: UnitTestAccount, to: UnitTestAccount, token: DeployedContract, amount: int
):
    web3.eth.default_account = invoker["account_address"]
    token_contract: Any = Contract.get_contract("IbetShare", token["address"])
    tx_params: TxParams = {
        "from": invoker["account_address"],
        "gas": 6000000,
        "gasPrice": Wei(0),
    }
    tx: TxParams = token_contract.functions.transfer(
        to["account_address"], amount
    ).build_transaction(tx_params)
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
    web3.eth.send_transaction(tx)


# SHAREトークン：無効化
def share_set_status(invoker: UnitTestAccount, token: DeployedContract):
    web3.eth.default_account = invoker["account_address"]
    share_token_contract = Contract.get_contract("IbetShare", token["address"])
    share_token_contract.functions.setStatus(False).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：譲渡不可設定
def share_set_transferable(invoker: UnitTestAccount, token: DeployedContract):
    web3.eth.default_account = invoker["account_address"]
    share_token_contract = Contract.get_contract("IbetShare", token["address"])
    share_token_contract.functions.setTransferable(False).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：移転承諾要否フラグの更新
def share_set_transfer_approval_required(
    invoker: UnitTestAccount, token: DeployedContract, required: bool
):
    web3.eth.default_account = invoker["account_address"]

    token_contract = Contract.get_contract("IbetShare", token["address"])
    token_contract.functions.setTransferApprovalRequired(required).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：移転申請
def share_apply_for_transfer(
    invoker: UnitTestAccount,
    token: DeployedContract,
    recipient: UnitTestAccount,
    amount: int,
    application_data: str,
):
    web3.eth.default_account = invoker["account_address"]

    token_contract = Contract.get_contract("IbetShare", token["address"])
    token_contract.functions.applyForTransfer(
        recipient["account_address"], amount, application_data
    ).transact({"from": invoker["account_address"]})


# SHAREトークン：移転申請取消
def share_cancel_transfer(
    invoker: UnitTestAccount,
    token: DeployedContract,
    application_id: int,
    application_data: str,
):
    web3.eth.default_account = invoker["account_address"]

    token_contract = Contract.get_contract("IbetShare", token["address"])
    token_contract.functions.cancelTransfer(application_id, application_data).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：移転申請承認
def share_approve_transfer(
    invoker: UnitTestAccount,
    token: DeployedContract,
    application_id: int,
    application_data: str,
):
    web3.eth.default_account = invoker["account_address"]

    token_contract = Contract.get_contract("IbetShare", token["address"])
    token_contract.functions.approveTransfer(application_id, application_data).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：資産ロック
def share_lock(
    invoker: UnitTestAccount,
    token: DeployedContract,
    lock_address: str,
    amount: int,
    data_str: str = "",
):
    web3.eth.default_account = invoker["account_address"]

    token_contract = Contract.get_contract("IbetShare", token["address"])
    token_contract.functions.lock(lock_address, amount, data_str).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：資産強制ロック
def share_force_lock(
    invoker: UnitTestAccount,
    token: DeployedContract,
    lock_address: str,
    account_address: str,
    amount: int,
    data_str: str = "",
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetShare", token["address"])
    token_contract.functions.forceLock(
        lock_address, account_address, amount, data_str
    ).transact({"from": invoker["account_address"]})


# SHAREトークン：資産アンロック
def share_unlock(
    invoker: UnitTestAccount,
    token: DeployedContract,
    target: str,
    recipient: str,
    amount: int,
    data_str: str = "",
):
    web3.eth.default_account = invoker["account_address"]

    token_contract = Contract.get_contract("IbetShare", token["address"])
    token_contract.functions.unlock(target, recipient, amount, data_str).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：資産強制アンロック
def share_force_unlock(
    invoker: UnitTestAccount,
    token: DeployedContract,
    lock_address: str,
    target: str,
    recipient: str,
    amount: int,
    data_str: str = "",
):
    web3.eth.default_account = invoker["account_address"]

    token_contract = Contract.get_contract("IbetShare", token["address"])
    token_contract.functions.forceUnlock(
        lock_address, target, recipient, amount, data_str
    ).transact({"from": invoker["account_address"]})


# SHAREトークン：資産ロック元強制変更
def share_force_change_locked_account(
    invoker: UnitTestAccount,
    token: DeployedContract,
    lock_address: str,
    before_account_address: str,
    after_account_address: str,
    amount: int,
    data_str: str = "",
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetShare", token["address"])
    token_contract.functions.forceChangeLockedAccount(
        lock_address, before_account_address, after_account_address, amount, data_str
    ).transact({"from": invoker["account_address"]})


# SHAREトークン：追加発行
def share_issue_from(
    invoker: UnitTestAccount,
    token: DeployedContract,
    target: str,
    amount: int,
    lock_address: str = config.ZERO_ADDRESS,
):
    web3.eth.default_account = invoker["account_address"]

    token_contract = Contract.get_contract("IbetShare", token["address"])
    token_contract.functions.issueFrom(target, lock_address, amount).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：発行数量の削減
def share_redeem_from(
    invoker: UnitTestAccount,
    token: DeployedContract,
    target_address: str,
    amount: int,
    lock_address: str = config.ZERO_ADDRESS,
):
    web3.eth.default_account = invoker["account_address"]

    token_contract = Contract.get_contract("IbetShare", token["address"])
    token_contract.functions.redeemFrom(target_address, lock_address, amount).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：取引コントラクトの更新
def share_set_tradable_exchange(
    invoker: UnitTestAccount, token: DeployedContract, exchange_address: str
):
    web3.eth.default_account = invoker["account_address"]

    token_contract = Contract.get_contract("IbetShare", token["address"])
    token_contract.functions.setTradableExchange(exchange_address).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：消却状態に変更
def share_change_to_canceled(invoker: UnitTestAccount, token: DeployedContract):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetShare", token["address"])
    token_contract.functions.changeToCanceled().transact(
        {"from": invoker["account_address"]}
    )


###############################################################
# Coupon Token
###############################################################
# COUPONトークン：発行
def coupon_issue_token(
    invoker: UnitTestAccount, attribute: dict[str, Any]
) -> DeployedContract:
    web3.eth.default_account = invoker["account_address"]

    arguments = [
        attribute["name"],
        attribute["symbol"],
        attribute["totalSupply"],
        attribute["tradableExchange"],
        attribute["details"],
        attribute["returnDetails"],
        attribute["memo"],
        attribute["expirationDate"],
        attribute["transferable"],
        attribute["contactInformation"],
        attribute["privacyPolicy"],
    ]
    contract_address, abi = Contract.deploy_contract(
        "IbetCoupon", arguments, invoker["account_address"]
    )

    return {"address": contract_address, "abi": abi}


# COUPONトークン：公開リスト登録
def coupon_register_token_list(
    invoker: UnitTestAccount, token: DeployedContract, token_list: DeployedContract
):
    web3.eth.default_account = invoker["account_address"]
    token_list_contract = Contract.get_contract("TokenList", token_list["address"])
    token_list_contract.functions.register(token["address"], "IbetCoupon").transact(
        {"from": invoker["account_address"]}
    )


# COUPONトークン：トークンの移転
def coupon_transfer_token(
    invoker: UnitTestAccount, token: DeployedContract, to: UnitTestAccount, amount: int
):
    web3.eth.default_account = invoker["account_address"]
    coupon_contract = Contract.get_contract("IbetCoupon", token["address"])
    coupon_contract.functions.transfer(to["account_address"], amount).transact(
        {"from": invoker["account_address"]}
    )


# COUPONトークン：無効化
def coupon_set_status(invoker: UnitTestAccount, token: DeployedContract):
    web3.eth.default_account = invoker["account_address"]
    coupon_token_contract = Contract.get_contract("IbetCoupon", token["address"])
    coupon_token_contract.functions.setStatus(False).transact(
        {"from": invoker["account_address"]}
    )


# COUPONトークン：譲渡不可設定
def coupon_set_transferable(invoker: UnitTestAccount, token: DeployedContract):
    web3.eth.default_account = invoker["account_address"]
    coupon_token_contract = Contract.get_contract("IbetCoupon", token["address"])
    coupon_token_contract.functions.setTransferable(False).transact(
        {"from": invoker["account_address"]}
    )


# COUPONトークン：消費
def coupon_consume(
    invoker: UnitTestAccount, coupon_token: DeployedContract, amount: int
):
    web3.eth.default_account = invoker["account_address"]
    coupon_token_contract = Contract.get_contract("IbetCoupon", coupon_token["address"])
    coupon_token_contract.functions.consume(amount).transact(
        {"from": invoker["account_address"]}
    )


# COUPONトークン：取引コントラクトにデポジット
def coupon_transfer_to_exchange(
    invoker: UnitTestAccount,
    exchange: DeployedContract,
    token: DeployedContract,
    amount: int,
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract(
        contract_name="IbetCoupon", address=token["address"]
    )
    token_contract.functions.transfer(exchange["address"], amount).transact(
        {"from": invoker["account_address"]}
    )


# COUPONトークン：取引コントラクトから引き出し
def coupon_withdraw_from_exchange(
    invoker: UnitTestAccount,
    exchange: DeployedContract,
    token: DeployedContract,
    amount: int,
):
    web3.eth.default_account = invoker["account_address"]
    exchange_contract = Contract.get_contract(
        contract_name="IbetExchangeInterface", address=exchange["address"]
    )
    exchange_contract.functions.withdraw(token["address"]).transact(
        {"from": invoker["account_address"]}
    )


# COUPONトークン：取引コントラクトの更新
def coupon_set_tradable_exchange(
    invoker: UnitTestAccount, token: DeployedContract, exchange_address: str
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetCoupon", token["address"])
    token_contract.functions.setTradableExchange(exchange_address).transact(
        {"from": invoker["account_address"]}
    )


###############################################################
# Membership Token
###############################################################
# MEMBERSHIPトークン：発行
def membership_issue_token(
    invoker: UnitTestAccount, attribute: dict[str, Any]
) -> DeployedContract:
    web3.eth.default_account = invoker["account_address"]
    arguments = [
        attribute["name"],
        attribute["symbol"],
        attribute["initialSupply"],
        attribute["tradableExchange"],
        attribute["details"],
        attribute["returnDetails"],
        attribute["expirationDate"],
        attribute["memo"],
        attribute["transferable"],
        attribute["contactInformation"],
        attribute["privacyPolicy"],
    ]
    contract_address, abi = Contract.deploy_contract(
        "IbetMembership", arguments, invoker["account_address"]
    )
    return {"address": contract_address, "abi": abi}


# MEMBERSHIPトークン：公開リスト登録
def membership_register_token_list(
    invoker: UnitTestAccount, token: DeployedContract, token_list: DeployedContract
):
    web3.eth.default_account = invoker["account_address"]
    token_list_contract = Contract.get_contract("TokenList", token_list["address"])
    token_list_contract.functions.register(token["address"], "IbetMembership").transact(
        {"from": invoker["account_address"]}
    )


# MEMBERSHIPトークン：無効化
def membership_invalidate(invoker: UnitTestAccount, token: DeployedContract):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetMembership", token["address"])
    token_contract.functions.setStatus(False).transact(
        {"from": invoker["account_address"]}
    )


# MEMBERSHIPトークン：譲渡不可設定
def membership_untransferable(invoker: UnitTestAccount, token: DeployedContract):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetMembership", token["address"])
    token_contract.functions.setTransferable(False).transact(
        {"from": invoker["account_address"]}
    )


# MEMBERSHIPトークン：取引コントラクトにデポジット
def membership_transfer_to_exchange(
    invoker: UnitTestAccount,
    exchange: DeployedContract,
    token: DeployedContract,
    amount: int,
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetMembership", token["address"])
    token_contract.functions.transfer(exchange["address"], amount).transact(
        {"from": invoker["account_address"]}
    )


# MEMBERSHIPトークン：取引コントラクトの更新
def membership_set_tradable_exchange(
    invoker: UnitTestAccount, token: DeployedContract, exchange_address: str
):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract("IbetMembership", token["address"])
    token_contract.functions.setTradableExchange(exchange_address).transact(
        {"from": invoker["account_address"]}
    )


# MEMBERSHIPトークン：移転
def membership_transfer_token(
    invoker: UnitTestAccount, token: DeployedContract, to: UnitTestAccount, amount: int
):
    web3.eth.default_account = invoker["account_address"]
    coupon_contract = Contract.get_contract("IbetCoupon", token["address"])
    coupon_contract.functions.transfer(to["account_address"], amount).transact(
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
):
    web3.eth.default_account = invoker["account_address"]
    security_token_escrow_contract = Contract.get_contract(
        "IbetSecurityTokenEscrow", exchange["address"]
    )
    security_token_escrow_contract.functions.createEscrow(
        token["address"], recipient_address, amount, agent_address, "{}", "{}"
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
