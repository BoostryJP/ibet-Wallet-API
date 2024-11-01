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

from eth_utils import to_checksum_address
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from app.contracts import Contract
from tests.account_config import eth_account
from tests.conftest import DeployedContract, UnitTestAccount

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


# 名簿用個人情報登録
# NOTE: issuer address に対する情報の公開を行う
def register_personalinfo(invoker, personal_info):
    web3.eth.default_account = invoker["account_address"]

    PersonalInfoContract = Contract.get_contract(
        "PersonalInfo", personal_info["address"]
    )

    issuer = eth_account["issuer"]
    encrypted_info = "some_encrypted_info"
    PersonalInfoContract.functions.register(
        issuer["account_address"], encrypted_info
    ).transact({"from": invoker["account_address"]})


# 決済用銀行口座情報登録
def register_payment_gateway(invoker, payment_gateway):
    PaymentGatewayContract = Contract.get_contract(
        "PaymentGateway", payment_gateway["address"]
    )

    # 1) 登録 from Invoker
    web3.eth.default_account = invoker["account_address"]

    agent = eth_account["agent"]
    encrypted_info = "some_encrypted_info"
    PaymentGatewayContract.functions.register(
        agent["account_address"], encrypted_info
    ).transact({"from": invoker["account_address"]})

    # 2) 認可 from Agent
    web3.eth.default_account = agent["account_address"]
    PaymentGatewayContract.functions.approve(invoker["account_address"]).transact(
        {"from": agent["account_address"]}
    )


# トークン移転
def transfer_token(token_contract, from_address, to_address, amount):
    token_contract.functions.transfer(to_address, amount).transact(
        {"from": from_address}
    )


###############################################################
# Bond Token
###############################################################
# BONDトークン：発行
def issue_bond_token(invoker, attribute):
    web3.eth.default_account = invoker["account_address"]

    interestPaymentDate = json.dumps(
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
    TokenContract = Contract.get_contract("IbetStraightBond", contract_address)
    if "tradableExchange" in attribute:
        TokenContract.functions.setTradableExchange(
            attribute["tradableExchange"]
        ).transact({"from": invoker["account_address"]})
    if "interestRate" in attribute:
        TokenContract.functions.setInterestRate(attribute["interestRate"]).transact(
            {"from": invoker["account_address"]}
        )
    TokenContract.functions.setInterestPaymentDate(interestPaymentDate).transact(
        {"from": invoker["account_address"]}
    )
    if "memo" in attribute:
        TokenContract.functions.setMemo(attribute["memo"]).transact(
            {"from": invoker["account_address"]}
        )
    if "contactInformation" in attribute:
        TokenContract.functions.setContactInformation(
            attribute["contactInformation"]
        ).transact({"from": invoker["account_address"]})
    if "privacyPolicy" in attribute:
        TokenContract.functions.setPrivacyPolicy(attribute["privacyPolicy"]).transact(
            {"from": invoker["account_address"]}
        )
    if "personalInfoAddress" in attribute:
        TokenContract.functions.setPersonalInfoAddress(
            attribute["personalInfoAddress"]
        ).transact({"from": invoker["account_address"]})
    if "requirePersonalInfoRegistered" in attribute:
        TokenContract.functions.setRequirePersonalInfoRegistered(
            attribute["requirePersonalInfoRegistered"]
        ).transact({"from": invoker["account_address"]})
    TokenContract.functions.setTransferable(True).transact(
        {"from": invoker["account_address"]}
    )
    if "interestPaymentCurrency" in attribute:
        TokenContract.functions.setInterestPaymentCurrency(
            attribute["interestPaymentCurrency"]
        ).transact({"from": invoker["account_address"]})
    if "baseFxRate" in attribute:
        TokenContract.functions.setBaseFXRate(str(attribute["baseFxRate"])).transact(
            {"from": invoker["account_address"]}
        )

    return {"address": contract_address, "abi": abi}


# BONDトークン：公開リスト登録
def register_bond_list(invoker, bond_token, token_list):
    TokenListContract = Contract.get_contract("TokenList", token_list["address"])

    web3.eth.default_account = invoker["account_address"]

    TokenListContract.functions.register(
        bond_token["address"], "IbetStraightBond"
    ).transact({"from": invoker["account_address"]})


# BONDトークン：募集
def offer_bond_token(invoker, bond_exchange, bond_token, amount, price):
    bond_transfer_to_exchange(invoker, bond_exchange, bond_token, amount)
    make_sell(invoker, bond_exchange, bond_token, amount, price)


# BONDトークン：取引コントラクトにデポジット
def bond_transfer_to_exchange(invoker, bond_exchange, bond_token, amount):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetStraightBond", bond_token["address"])
    TokenContract.functions.transfer(bond_exchange["address"], amount).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：移転
def transfer_bond_token(
    invoker: UnitTestAccount, to: UnitTestAccount, token: DeployedContract, amount: int
):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetStraightBond", token["address"])
    TokenContract.functions.transfer(to["account_address"], amount).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：償還
def bond_redeem(invoker, token):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetStraightBond", token["address"])
    TokenContract.functions.changeToRedeemed().transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：譲渡可否変更
def bond_change_transferable(invoker, token, transferable):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetStraightBond", token["address"])
    TokenContract.functions.setTransferable(transferable).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：無効化
def bond_invalidate(invoker, token):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetStraightBond", token["address"])
    TokenContract.functions.setStatus(False).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：譲渡不可設定
def bond_untransferable(invoker, token):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetStraightBond", token["address"])
    TokenContract.functions.setTransferable(False).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：移転承諾要否フラグの更新
def bond_set_transfer_approval_required(invoker, token, required: bool):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetStraightBond", token["address"])
    TokenContract.functions.setTransferApprovalRequired(required).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：移転申請
def bond_apply_for_transfer(invoker, token, recipient, amount, application_data):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetStraightBond", token["address"])
    TokenContract.functions.applyForTransfer(
        recipient["account_address"], amount, application_data
    ).transact({"from": invoker["account_address"]})


# BONDトークン：移転申請取消
def bond_cancel_transfer(invoker, token, application_id, application_data):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetStraightBond", token["address"])
    TokenContract.functions.cancelTransfer(application_id, application_data).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：移転申請承認
def bond_approve_transfer(invoker, token, application_id, application_data):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetStraightBond", token["address"])
    TokenContract.functions.approveTransfer(application_id, application_data).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：資産ロック
def bond_lock(invoker, token, lock_address: str, amount: int):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetStraightBond", token["address"])
    TokenContract.functions.lock(lock_address, amount, "").transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：資産アンロック
def bond_unlock(
    invoker, token, target: str, recipient: str, amount: int, data_str: str = ""
):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetStraightBond", token["address"])
    TokenContract.functions.unlock(target, recipient, amount, data_str).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：追加発行
def bond_issue_from(
    invoker, token, target: str, amount: int, lock_address: str = config.ZERO_ADDRESS
):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetStraightBond", token["address"])
    TokenContract.functions.issueFrom(target, lock_address, amount).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：発行数量の削減
def bond_redeem_from(
    invoker,
    token,
    target_address: str,
    amount: int,
    lock_address: str = config.ZERO_ADDRESS,
):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetStraightBond", token["address"])
    TokenContract.functions.redeemFrom(target_address, lock_address, amount).transact(
        {"from": invoker["account_address"]}
    )


# BONDトークン：取引コントラクトの更新
def bond_set_tradable_exchange(invoker, token, exchange_address: str):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetStraightBond", token["address"])
    TokenContract.functions.setTradableExchange(exchange_address).transact(
        {"from": invoker["account_address"]}
    )


###############################################################
# Share Token
###############################################################
# SHAREトークン：発行
def issue_share_token(invoker, attribute):
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

    TokenContract = Contract.get_contract("IbetShare", contract_address)
    if "tradableExchange" in attribute:
        TokenContract.functions.setTradableExchange(
            to_checksum_address(attribute["tradableExchange"])
        ).transact({"from": invoker["account_address"]})
    if "personalInfoAddress" in attribute:
        TokenContract.functions.setPersonalInfoAddress(
            to_checksum_address(attribute["personalInfoAddress"])
        ).transact({"from": invoker["account_address"]})
    if "requirePersonalInfoRegistered" in attribute:
        TokenContract.functions.setRequirePersonalInfoRegistered(
            attribute["requirePersonalInfoRegistered"]
        ).transact({"from": invoker["account_address"]})
    if "contactInformation" in attribute:
        TokenContract.functions.setContactInformation(
            attribute["contactInformation"]
        ).transact({"from": invoker["account_address"]})
    if "privacyPolicy" in attribute:
        TokenContract.functions.setPrivacyPolicy(attribute["privacyPolicy"]).transact(
            {"from": invoker["account_address"]}
        )
    if "memo" in attribute:
        TokenContract.functions.setMemo(attribute["memo"]).transact(
            {"from": invoker["account_address"]}
        )
    if "transferable" in attribute:
        TokenContract.functions.setTransferable(attribute["transferable"]).transact(
            {"from": invoker["account_address"]}
        )

    return {"address": contract_address, "abi": abi}


# SHAREトークン：公開リスト登録
def register_share_list(invoker, share_token, token_list):
    TokenListContract = Contract.get_contract("TokenList", token_list["address"])

    web3.eth.default_account = invoker["account_address"]

    TokenListContract.functions.register(share_token["address"], "IbetShare").transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：募集（売出）
def share_offer(invoker, exchange, token, amount, price):
    share_transfer_to_exchange(invoker, exchange, token, amount)
    make_sell(invoker, exchange, token, amount, price)


# SHAREトークン：取引コントラクトにデポジット
def share_transfer_to_exchange(invoker, exchange, token, amount):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetShare", token["address"])
    TokenContract.functions.transfer(exchange["address"], amount).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：移転
def transfer_share_token(
    invoker: UnitTestAccount, to: UnitTestAccount, token: DeployedContract, amount: int
):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetShare", token["address"])
    TokenContract.functions.transfer(to["account_address"], amount).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：無効化
def invalidate_share_token(invoker, token):
    web3.eth.default_account = invoker["account_address"]
    ShareTokenContract = Contract.get_contract("IbetShare", token["address"])
    ShareTokenContract.functions.setStatus(False).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：譲渡不可設定
def untransferable_share_token(invoker, token):
    web3.eth.default_account = invoker["account_address"]
    ShareTokenContract = Contract.get_contract("IbetShare", token["address"])
    ShareTokenContract.functions.setTransferable(False).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：移転承諾要否フラグの更新
def share_set_transfer_approval_required(invoker, token, required: bool):
    web3.eth.default_account = invoker["account_address"]

    TokenContract = Contract.get_contract("IbetShare", token["address"])
    TokenContract.functions.setTransferApprovalRequired(required).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：移転申請
def share_apply_for_transfer(invoker, token, recipient, amount, application_data):
    web3.eth.default_account = invoker["account_address"]

    TokenContract = Contract.get_contract("IbetShare", token["address"])
    TokenContract.functions.applyForTransfer(
        recipient["account_address"], amount, application_data
    ).transact({"from": invoker["account_address"]})


# SHAREトークン：移転申請取消
def share_cancel_transfer(invoker, token, application_id, application_data):
    web3.eth.default_account = invoker["account_address"]

    TokenContract = Contract.get_contract("IbetShare", token["address"])
    TokenContract.functions.cancelTransfer(application_id, application_data).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：移転申請承認
def share_approve_transfer(invoker, token, application_id, application_data):
    web3.eth.default_account = invoker["account_address"]

    TokenContract = Contract.get_contract("IbetShare", token["address"])
    TokenContract.functions.approveTransfer(application_id, application_data).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：資産ロック
def share_lock(invoker, token, lock_address: str, amount: int, data_str: str = ""):
    web3.eth.default_account = invoker["account_address"]

    TokenContract = Contract.get_contract("IbetShare", token["address"])
    TokenContract.functions.lock(lock_address, amount, data_str).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：資産アンロック
def share_unlock(
    invoker, token, target: str, recipient: str, amount: int, data_str: str = ""
):
    web3.eth.default_account = invoker["account_address"]

    TokenContract = Contract.get_contract("IbetShare", token["address"])
    TokenContract.functions.unlock(target, recipient, amount, data_str).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：追加発行
def share_issue_from(
    invoker, token, target: str, amount: int, lock_address: str = config.ZERO_ADDRESS
):
    web3.eth.default_account = invoker["account_address"]

    TokenContract = Contract.get_contract("IbetShare", token["address"])
    TokenContract.functions.issueFrom(target, lock_address, amount).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：発行数量の削減
def share_redeem_from(
    invoker,
    token,
    target_address: str,
    amount: int,
    lock_address: str = config.ZERO_ADDRESS,
):
    web3.eth.default_account = invoker["account_address"]

    TokenContract = Contract.get_contract("IbetShare", token["address"])
    TokenContract.functions.redeemFrom(target_address, lock_address, amount).transact(
        {"from": invoker["account_address"]}
    )


# SHAREトークン：取引コントラクトの更新
def share_set_tradable_exchange(invoker, token, exchange_address: str):
    web3.eth.default_account = invoker["account_address"]

    TokenContract = Contract.get_contract("IbetShare", token["address"])
    TokenContract.functions.setTradableExchange(exchange_address).transact(
        {"from": invoker["account_address"]}
    )


###############################################################
# Coupon Token
###############################################################
# COUPONトークン：発行
def issue_coupon_token(invoker, attribute):
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
def coupon_register_list(invoker, token, token_list):
    web3.eth.default_account = invoker["account_address"]
    TokenListContract = Contract.get_contract("TokenList", token_list["address"])
    TokenListContract.functions.register(token["address"], "IbetCoupon").transact(
        {"from": invoker["account_address"]}
    )


# COUPONトークン：トークンの移転
def transfer_coupon_token(
    invoker: UnitTestAccount, token: DeployedContract, to: UnitTestAccount, amount: int
):
    web3.eth.default_account = invoker["account_address"]
    coupon_contract = Contract.get_contract("IbetCoupon", token["address"])
    coupon_contract.functions.transfer(to["account_address"], amount).transact(
        {"from": invoker["account_address"]}
    )


# COUPONトークン：無効化
def invalidate_coupon_token(invoker, token):
    web3.eth.default_account = invoker["account_address"]
    CouponTokenContract = Contract.get_contract("IbetCoupon", token["address"])
    CouponTokenContract.functions.setStatus(False).transact(
        {"from": invoker["account_address"]}
    )


# COUPONトークン：譲渡不可設定
def untransferable_coupon_token(invoker, token):
    web3.eth.default_account = invoker["account_address"]
    CouponTokenContract = Contract.get_contract("IbetCoupon", token["address"])
    CouponTokenContract.functions.setTransferable(False).transact(
        {"from": invoker["account_address"]}
    )


# COUPONトークン：消費
def consume_coupon_token(invoker, coupon_token, amount):
    web3.eth.default_account = invoker["account_address"]
    CouponTokenContract = Contract.get_contract("IbetCoupon", coupon_token["address"])
    CouponTokenContract.functions.consume(amount).transact(
        {"from": invoker["account_address"]}
    )


# COUPONトークン：売出
def coupon_offer(invoker, exchange, token, amount, price):
    coupon_transfer_to_exchange(invoker, exchange, token, amount)
    make_sell(invoker, exchange, token, amount, price)


# COUPONトークン：取引コントラクトにデポジット
def coupon_transfer_to_exchange(invoker, exchange, token, amount):
    web3.eth.default_account = invoker["account_address"]
    token_contract = Contract.get_contract(
        contract_name="IbetCoupon", address=token["address"]
    )
    token_contract.functions.transfer(exchange["address"], amount).transact(
        {"from": invoker["account_address"]}
    )


# COUPONトークン：取引コントラクトから引き出し
def coupon_withdraw_from_exchange(invoker, exchange, token, amount):
    web3.eth.default_account = invoker["account_address"]
    exchange_contract = Contract.get_contract(
        contract_name="IbetExchange", address=exchange["address"]
    )
    exchange_contract.functions.withdraw(token["address"]).transact(
        {"from": invoker["account_address"]}
    )


# COUPONトークン：取引コントラクトの更新
def coupon_set_tradable_exchange(invoker, token, exchange_address: str):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetCoupon", token["address"])
    TokenContract.functions.setTradableExchange(exchange_address).transact(
        {"from": invoker["account_address"]}
    )


###############################################################
# Membership Token
###############################################################
# MEMBERSHIPトークン：発行
def membership_issue(invoker, attribute):
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


# MEMBERSHIPトークン：開リスト登録
def membership_register_list(invoker, token, token_list):
    web3.eth.default_account = invoker["account_address"]
    TokenListContract = Contract.get_contract("TokenList", token_list["address"])
    TokenListContract.functions.register(token["address"], "IbetMembership").transact(
        {"from": invoker["account_address"]}
    )


# MEMBERSHIPトークン：無効化
def membership_invalidate(invoker, token):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetMembership", token["address"])
    TokenContract.functions.setStatus(False).transact(
        {"from": invoker["account_address"]}
    )


# MEMBERSHIPトークン：譲渡不可設定
def membership_untransferable(invoker, token):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetMembership", token["address"])
    TokenContract.functions.setTransferable(False).transact(
        {"from": invoker["account_address"]}
    )


# MEMBERSHIPトークン：募集（売出）
def membership_offer(invoker, exchange, token, amount, price):
    membership_transfer_to_exchange(invoker, exchange, token, amount)
    make_sell(invoker, exchange, token, amount, price)


# MEMBERSHIPトークン：取引コントラクトにデポジット
def membership_transfer_to_exchange(invoker, exchange, token, amount):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetMembership", token["address"])
    TokenContract.functions.transfer(exchange["address"], amount).transact(
        {"from": invoker["account_address"]}
    )


# MEMBERSHIPトークン：取引コントラクトの更新
def membership_set_tradable_exchange(invoker, token, exchange_address: str):
    web3.eth.default_account = invoker["account_address"]
    TokenContract = Contract.get_contract("IbetMembership", token["address"])
    TokenContract.functions.setTradableExchange(exchange_address).transact(
        {"from": invoker["account_address"]}
    )


# MEMBERSHIPトークン：移転
def transfer_membership_token(
    invoker: UnitTestAccount, token: DeployedContract, to: UnitTestAccount, amount: int
):
    web3.eth.default_account = invoker["account_address"]
    coupon_contract = Contract.get_contract("IbetCoupon", token["address"])
    coupon_contract.functions.transfer(to["account_address"], amount).transact(
        {"from": invoker["account_address"]}
    )


###############################################################
# DEX
###############################################################
# Tokenの売りMake注文
def make_sell(invoker, exchange, token, amount, price):
    web3.eth.default_account = invoker["account_address"]
    ExchangeContract = Contract.get_contract("IbetExchange", exchange["address"])
    agent = eth_account["agent"]
    ExchangeContract.functions.createOrder(
        token["address"], amount, price, False, agent["account_address"]
    ).transact({"from": invoker["account_address"]})


# Tokenの買いTake注文
def take_buy(invoker, exchange, order_id, amount):
    web3.eth.default_account = invoker["account_address"]
    ExchangeContract = Contract.get_contract("IbetExchange", exchange["address"])
    ExchangeContract.functions.executeOrder(order_id, amount, True).transact(
        {"from": invoker["account_address"]}
    )


# Tokenの買いMake注文
def make_buy(invoker, exchange, token, amount, price):
    web3.eth.default_account = invoker["account_address"]
    ExchangeContract = Contract.get_contract("IbetExchange", exchange["address"])
    agent = eth_account["agent"]
    ExchangeContract.functions.createOrder(
        token["address"], amount, price, True, agent["account_address"]
    ).transact({"from": invoker["account_address"]})


# Tokenの売りTake注文
def take_sell(invoker, exchange, order_id, amount):
    web3.eth.default_account = invoker["account_address"]
    ExchangeContract = Contract.get_contract("IbetExchange", exchange["address"])
    ExchangeContract.functions.executeOrder(order_id, amount, False).transact(
        {"from": invoker["account_address"]}
    )


# 直近注文IDを取得
def get_latest_orderid(exchange):
    ExchangeContract = Contract.get_contract("IbetExchange", exchange["address"])
    latest_orderid = ExchangeContract.functions.latestOrderId().call()
    return latest_orderid


# 注文の取消
def cancel_order(invoker, exchange, order_id):
    web3.eth.default_account = invoker["account_address"]
    ExchangeContract = Contract.get_contract("IbetExchange", exchange["address"])
    ExchangeContract.functions.cancelOrder(order_id).transact(
        {"from": invoker["account_address"]}
    )


# 注文の強制取消
def force_cancel_order(invoker, exchange, order_id):
    web3.eth.default_account = invoker["account_address"]
    ExchangeContract = Contract.get_contract("IbetExchange", exchange["address"])
    ExchangeContract.functions.forceCancelOrder(order_id).transact(
        {"from": invoker["account_address"]}
    )


# 直近約定IDを取得
def get_latest_agreementid(exchange, order_id):
    ExchangeContract = Contract.get_contract("IbetExchange", exchange["address"])
    latest_agreementid = ExchangeContract.functions.latestAgreementId(order_id).call()
    return latest_agreementid


# 約定の資金決済
def confirm_agreement(invoker, exchange, order_id, agreement_id):
    web3.eth.default_account = invoker["account_address"]
    ExchangeContract = Contract.get_contract("IbetExchange", exchange["address"])
    ExchangeContract.functions.confirmAgreement(order_id, agreement_id).transact(
        {"from": invoker["account_address"]}
    )


# 約定の取消
def cancel_agreement(invoker, exchange, order_id, agreement_id):
    web3.eth.default_account = invoker["account_address"]
    ExchangeContract = Contract.get_contract("IbetExchange", exchange["address"])
    ExchangeContract.functions.cancelAgreement(order_id, agreement_id).transact(
        {"from": invoker["account_address"]}
    )


# エスクローの作成
def create_security_token_escrow(
    invoker, exchange, token, recipient_address, agent_address, amount
):
    web3.eth.default_account = invoker["account_address"]
    IbetSecurityTokenEscrowContract = Contract.get_contract(
        "IbetSecurityTokenEscrow", exchange["address"]
    )
    IbetSecurityTokenEscrowContract.functions.createEscrow(
        token["address"], recipient_address, amount, agent_address, "{}", "{}"
    ).transact({"from": invoker["account_address"]})


def get_latest_security_escrow_id(exchange):
    IbetSecurityTokenEscrowContract = Contract.get_contract(
        "IbetSecurityTokenEscrow", exchange["address"]
    )
    latest_escrow_id = IbetSecurityTokenEscrowContract.functions.latestEscrowId().call()
    return latest_escrow_id


# エスクローのキャンセル
def cancel_security_token_escrow(invoker, exchange, escrow_id):
    web3.eth.default_account = invoker["account_address"]
    IbetSecurityTokenEscrowContract = Contract.get_contract(
        "IbetSecurityTokenEscrow", exchange["address"]
    )
    IbetSecurityTokenEscrowContract.functions.cancelEscrow(escrow_id).transact(
        {"from": invoker["account_address"]}
    )


# 移転の承認
def approve_transfer_security_token_escrow(
    invoker, exchange, escrow_id, transfer_approval_data: str
):
    web3.eth.default_account = invoker["account_address"]
    IbetSecurityTokenEscrowContract = Contract.get_contract(
        "IbetSecurityTokenEscrow", exchange["address"]
    )
    IbetSecurityTokenEscrowContract.functions.approveTransfer(
        escrow_id, transfer_approval_data
    ).transact({"from": invoker["account_address"]})


# エスクローの完了
def finish_security_token_escrow(invoker, exchange, escrow_id):
    web3.eth.default_account = invoker["account_address"]
    IbetSecurityTokenEscrowContract = Contract.get_contract(
        "IbetSecurityTokenEscrow", exchange["address"]
    )
    IbetSecurityTokenEscrowContract.functions.finishEscrow(escrow_id).transact(
        {"from": invoker["account_address"]}
    )


# エスクローの作成
def create_token_escrow(
    invoker, exchange, token, recipient_address, agent_address, amount
):
    web3.eth.default_account = invoker["account_address"]
    IbetEscrow = Contract.get_contract("IbetEscrow", exchange["address"])
    IbetEscrow.functions.createEscrow(
        token["address"], recipient_address, amount, agent_address, "{}"
    ).transact({"from": invoker["account_address"]})


def get_latest_escrow_id(exchange):
    IbetEscrow = Contract.get_contract("IbetEscrow", exchange["address"])
    latest_escrow_id = IbetEscrow.functions.latestEscrowId().call()
    return latest_escrow_id


# エスクローの完了
def finish_token_escrow(invoker, exchange, escrow_id):
    web3.eth.default_account = invoker["account_address"]
    IbetEscrow = Contract.get_contract("IbetEscrow", exchange["address"])
    IbetEscrow.functions.finishEscrow(escrow_id).transact(
        {"from": invoker["account_address"]}
    )


# DVP決済の作成
def create_security_token_delivery(
    invoker, exchange, token, recipient_address, agent_address, amount
):
    web3.eth.default_account = invoker["account_address"]
    IbetSecurityTokenDVPContract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    IbetSecurityTokenDVPContract.functions.createDelivery(
        token["address"],
        recipient_address,
        amount,
        agent_address,
        "{}",
    ).transact({"from": invoker["account_address"]})


def get_latest_security_delivery_id(exchange):
    IbetSecurityTokenDVPContract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    latest_delivery_id = (
        IbetSecurityTokenDVPContract.functions.latestDeliveryId().call()
    )
    return latest_delivery_id


# DVP決済の取消
def cancel_security_token_delivery(invoker, exchange, delivery_id):
    web3.eth.default_account = invoker["account_address"]
    IbetSecurityTokenDVPContract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    IbetSecurityTokenDVPContract.functions.cancelDelivery(delivery_id).transact(
        {"from": invoker["account_address"]}
    )


# DVP決済の確認
def confirm_security_token_delivery(invoker, exchange, delivery_id):
    web3.eth.default_account = invoker["account_address"]
    IbetSecurityTokenDVPContract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    IbetSecurityTokenDVPContract.functions.confirmDelivery(delivery_id).transact(
        {"from": invoker["account_address"]}
    )


# DVP決済の完了
def finish_security_token_dvlivery(invoker, exchange, delivery_id):
    web3.eth.default_account = invoker["account_address"]
    IbetSecurityTokenDVPContract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    IbetSecurityTokenDVPContract.functions.finishDelivery(delivery_id).transact(
        {"from": invoker["account_address"]}
    )


# DVP決済の中断
def abort_security_token_delivery(invoker, exchange, delivery_id):
    web3.eth.default_account = invoker["account_address"]
    IbetSecurityTokenDVPContract = Contract.get_contract(
        "IbetSecurityTokenDVP", exchange["address"]
    )
    IbetSecurityTokenDVPContract.functions.abortDelivery(delivery_id).transact(
        {"from": invoker["account_address"]}
    )
