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
import time
from eth_typing import ChecksumAddress

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

from app import config
from app.contracts import Contract
from tests.account_config import eth_account
from tests.conftest import DeployedContract

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


# 名簿用個人情報登録
# NOTE: issuer address に対する情報の公開を行う
def register_personalinfo(invoker: ChecksumAddress, personal_info):
    web3.eth.default_account = invoker

    PersonalInfoContract = Contract.get_contract(
        'PersonalInfo', personal_info['address'])

    issuer = eth_account['issuer']
    encrypted_info = 'some_encrypted_info'
    tx_hash = PersonalInfoContract.functions.register(
        issuer, encrypted_info). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# 決済用銀行口座情報登録
def register_payment_gateway(invoker: ChecksumAddress, payment_gateway):
    PaymentGatewayContract = Contract.get_contract(
        'PaymentGateway', payment_gateway['address'])

    # 1) 登録 from Invoker
    web3.eth.default_account = invoker

    agent = eth_account['agent']
    encrypted_info = 'some_encrypted_info'
    tx_hash = PaymentGatewayContract.functions.register(
        agent, encrypted_info). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)

    # 2) 認可 from Agent
    web3.eth.default_account = agent

    tx_hash = PaymentGatewayContract.functions.approve(invoker). \
        transact({'from': agent, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# トークン移転
def transfer_token(token_contract, from_address, to_address, amount):
    tx_hash = token_contract.functions.transfer(
        to_address,
        amount
    ).transact({
        'from': from_address
    })
    web3.eth.wait_for_transaction_receipt(tx_hash)


'''
Straight Bond Token （普通社債）
'''


# 債券トークンの発行
def issue_bond_token(invoker: ChecksumAddress, attribute):
    web3.eth.default_account = invoker

    interestPaymentDate = json.dumps(
        {
            'interestPaymentDate1': attribute['interestPaymentDate1'],
            'interestPaymentDate2': attribute['interestPaymentDate2'],
            'interestPaymentDate3': attribute['interestPaymentDate3'],
            'interestPaymentDate4': attribute['interestPaymentDate4'],
            'interestPaymentDate5': attribute['interestPaymentDate5'],
            'interestPaymentDate6': attribute['interestPaymentDate6'],
            'interestPaymentDate7': attribute['interestPaymentDate7'],
            'interestPaymentDate8': attribute['interestPaymentDate8'],
            'interestPaymentDate9': attribute['interestPaymentDate9'],
            'interestPaymentDate10': attribute['interestPaymentDate10'],
            'interestPaymentDate11': attribute['interestPaymentDate11'],
            'interestPaymentDate12': attribute['interestPaymentDate12'],
        }
    )

    arguments = [
        attribute['name'], attribute['symbol'], attribute['totalSupply'],
        attribute['faceValue'],
        attribute['redemptionDate'], attribute['redemptionValue'],
        attribute['returnDate'], attribute['returnAmount'],
        attribute['purpose']
    ]

    contract_address, abi = Contract.deploy_contract(
        'IbetStraightBond',
        arguments,
        invoker
    )

    # その他項目の更新
    TokenContract = Contract.get_contract('IbetStraightBond', contract_address)
    if 'tradableExchange' in attribute:
        tx_hash = TokenContract.functions.setTradableExchange(attribute['tradableExchange']). \
            transact({'from': invoker, 'gas': 4000000})
        web3.eth.wait_for_transaction_receipt(tx_hash)
    if 'interestRate' in attribute:
        tx_hash = TokenContract.functions.setInterestRate(attribute['interestRate']). \
            transact({'from': invoker, 'gas': 4000000})
        web3.eth.wait_for_transaction_receipt(tx_hash)
    tx_hash = TokenContract.functions.setInterestPaymentDate(interestPaymentDate). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    if "memo" in attribute:
        tx_hash = TokenContract.functions.setMemo(attribute['memo']). \
            transact({'from': invoker, 'gas': 4000000})
        web3.eth.wait_for_transaction_receipt(tx_hash)
    if 'contactInformation' in attribute:
        tx_hash = TokenContract.functions.setContactInformation(attribute['contactInformation']). \
            transact({'from': invoker, 'gas': 4000000})
        web3.eth.wait_for_transaction_receipt(tx_hash)
    if 'privacyPolicy' in attribute:
        tx_hash = TokenContract.functions.setPrivacyPolicy(attribute['privacyPolicy']). \
            transact({'from': invoker, 'gas': 4000000})
        web3.eth.wait_for_transaction_receipt(tx_hash)
    if 'personalInfoAddress' in attribute:
        tx_hash = TokenContract.functions.setPersonalInfoAddress(attribute['personalInfoAddress']). \
            transact({'from': invoker, 'gas': 4000000})
        web3.eth.wait_for_transaction_receipt(tx_hash)
    tx_hash = TokenContract.functions.setTransferable(True). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)

    return {'address': contract_address, 'abi': abi}


# 債券トークンのリスト登録
def register_bond_list(invoker: ChecksumAddress, bond_token, token_list):
    TokenListContract = Contract.get_contract(
        'TokenList', token_list['address'])

    web3.eth.default_account = invoker

    tx_hash = TokenListContract.functions.register(
        bond_token['address'], 'IbetStraightBond'). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# 債券トークンの募集
def offer_bond_token(invoker: ChecksumAddress, bond_exchange, bond_token, amount, price):
    bond_transfer_to_exchange(invoker, bond_exchange, bond_token, amount)
    make_sell(invoker, bond_exchange, bond_token, amount, price)


# 取引コントラクトに債券トークンをチャージ
def bond_transfer_to_exchange(invoker: ChecksumAddress, bond_exchange, bond_token, amount):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract(
        'IbetStraightBond', bond_token['address'])

    tx_hash = TokenContract.functions.transfer(bond_exchange['address'], amount). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# 債券トークンの移転
def transfer_bond_token(invoker: ChecksumAddress, to: ChecksumAddress, token: DeployedContract, amount: int):
    web3.eth.default_account = invoker
    TokenContract = Contract. \
        get_contract('IbetStraightBond', token['address'])
    tx_hash = TokenContract.functions. \
        transfer(to, amount). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# 債券の償還
def bond_redeem(invoker: ChecksumAddress, token):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])

    tx_hash = TokenContract.functions.changeToRedeemed(). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# 債券の譲渡可否変更
def bond_change_transferable(invoker: ChecksumAddress, token, transferable):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])

    tx_hash = TokenContract.functions.setTransferable(transferable). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# 債券の無効化
def bond_invalidate(invoker: ChecksumAddress, token):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])
    tx_hash = TokenContract.functions.setStatus(False). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# 債券の譲渡不可
def bond_untransferable(invoker: ChecksumAddress, token):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])
    tx_hash = TokenContract.functions.setTransferable(False). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# 移転承諾要否フラグの更新
def bond_set_transfer_approval_required(invoker: ChecksumAddress, token, required: bool):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])
    tx_hash = TokenContract.functions.setTransferApprovalRequired(required).transact({
        'from': invoker
    })
    web3.eth.wait_for_transaction_receipt(tx_hash)


# トークン移転申請
def bond_apply_for_transfer(invoker: ChecksumAddress, token, recipient, amount, application_data):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])
    tx_hash = TokenContract.functions.applyForTransfer(recipient, amount, application_data). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# トークン移転申請取消
def bond_cancel_transfer(invoker: ChecksumAddress, token, application_id, application_data):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])
    tx_hash = TokenContract.functions.cancelTransfer(application_id, application_data). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# トークン移転申請承認
def bond_approve_transfer(invoker: ChecksumAddress, token, application_id, application_data):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])
    tx_hash = TokenContract.functions.approveTransfer(application_id, application_data). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# トークン資産ロック
def bond_lock(invoker: ChecksumAddress, token, lock_address: str, amount: int):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])
    tx_hash = TokenContract.functions.lock(lock_address, amount, ""). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# トークン資産アンロック
def bond_unlock(invoker: ChecksumAddress, token, target: str, recipient: str, amount: int, data_str: str = ""):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])
    tx_hash = TokenContract.functions.unlock(target, recipient, amount, data_str). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# トークン追加発行
def bond_issue_from(invoker: ChecksumAddress, token, target: str, amount: int, lock_address: str = config.ZERO_ADDRESS):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])
    tx_hash = TokenContract.functions.issueFrom(target, lock_address, amount). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# トークン発行数量の削減
def bond_redeem_from(invoker: ChecksumAddress, token, target_address: str, amount: int, lock_address: str = config.ZERO_ADDRESS):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])
    tx_hash = TokenContract.functions.redeemFrom(target_address, lock_address, amount). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# 取引コントラクトの更新
def bond_set_tradable_exchange(invoker: ChecksumAddress, token, exchange_address: str):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])
    tx_hash = TokenContract.functions.setTradableExchange(exchange_address). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


'''
Share Token （株式）
'''


# 株式トークンの発行
def issue_share_token(invoker: ChecksumAddress, attribute):
    web3.eth.default_account = invoker

    arguments = [
        attribute['name'],
        attribute['symbol'],
        attribute['issuePrice'],
        attribute['totalSupply'],
        attribute['dividends'],
        attribute['dividendRecordDate'],
        attribute['dividendPaymentDate'],
        attribute['cancellationDate'],
        attribute['principalValue']
    ]
    contract_address, abi = Contract.deploy_contract(
        contract_name='IbetShare',
        args=arguments,
        deployer=invoker
    )

    TokenContract = Contract.get_contract('IbetShare', contract_address)
    if 'tradableExchange' in attribute:
        TokenContract.functions.setTradableExchange(to_checksum_address(attribute['tradableExchange'])). \
            transact({'from': invoker, 'gas': 4000000})
    if 'personalInfoAddress' in attribute:
        TokenContract.functions.setPersonalInfoAddress(to_checksum_address(attribute['personalInfoAddress'])). \
            transact({'from': invoker, 'gas': 4000000})
    if 'contactInformation' in attribute:
        TokenContract.functions.setContactInformation(attribute['contactInformation']). \
            transact({'from': invoker, 'gas': 4000000})
    if 'privacyPolicy' in attribute:
        TokenContract.functions.setPrivacyPolicy(attribute['privacyPolicy']). \
            transact({'from': invoker, 'gas': 4000000})
    if 'memo' in attribute:
        TokenContract.functions.setMemo(attribute['memo']). \
            transact({'from': invoker, 'gas': 4000000})
    if 'transferable' in attribute:
        TokenContract.functions.setTransferable(attribute['transferable']). \
            transact({'from': invoker, 'gas': 4000000})

    time.sleep(3)

    return {'address': contract_address, 'abi': abi}


# 株式トークンのリスト登録
def register_share_list(invoker: ChecksumAddress, share_token, token_list):
    TokenListContract = Contract.get_contract(
        'TokenList', token_list['address'])

    web3.eth.default_account = invoker

    tx_hash = TokenListContract.functions.register(
        share_token['address'], 'IbetShare'). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# 株式Tokenの募集（売出）
def share_offer(invoker: ChecksumAddress, exchange, token, amount, price):
    share_transfer_to_exchange(invoker, exchange, token, amount)
    make_sell(invoker, exchange, token, amount, price)


# 取引コントラクトに株式トークンをチャージ
def share_transfer_to_exchange(invoker: ChecksumAddress, exchange, token, amount):
    web3.eth.default_account = invoker
    TokenContract = Contract. \
        get_contract('IbetShare', token['address'])
    tx_hash = TokenContract.functions. \
        transfer(exchange['address'], amount). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# 株式トークンの移転
def transfer_share_token(invoker: ChecksumAddress, to: ChecksumAddress, token, amount: int):
    web3.eth.default_account = invoker
    TokenContract = Contract. \
        get_contract('IbetShare', token['address'])
    tx_hash = TokenContract.functions. \
        transfer(to, amount). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# 株式トークンの無効化
def invalidate_share_token(invoker: ChecksumAddress, token):
    web3.eth.default_account = invoker
    ShareTokenContract = Contract.get_contract('IbetShare', token['address'])
    tx_hash = ShareTokenContract.functions.setStatus(False). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# 株式トークンの譲渡不可
def untransferable_share_token(invoker: ChecksumAddress, token):
    web3.eth.default_account = invoker
    ShareTokenContract = Contract.get_contract('IbetShare', token['address'])
    tx_hash = ShareTokenContract.functions.setTransferable(False). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# 移転承諾要否フラグの更新
def share_set_transfer_approval_required(invoker: ChecksumAddress, token, required: bool):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetShare', token['address'])
    tx_hash = TokenContract.functions.setTransferApprovalRequired(required).transact({
        'from': invoker
    })
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# トークン移転申請
def share_apply_for_transfer(invoker: ChecksumAddress, token, recipient, amount, application_data):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetShare', token['address'])
    tx_hash = TokenContract.functions.applyForTransfer(recipient, amount, application_data). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# トークン移転申請取消
def share_cancel_transfer(invoker: ChecksumAddress, token, application_id, application_data):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetShare', token['address'])
    tx_hash = TokenContract.functions.cancelTransfer(application_id, application_data). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# トークン移転申請承認
def share_approve_transfer(invoker: ChecksumAddress, token, application_id, application_data):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetShare', token['address'])
    tx_hash = TokenContract.functions.approveTransfer(application_id, application_data). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# トークン資産ロック
def share_lock(invoker: ChecksumAddress, token, lock_address: str, amount: int):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetShare', token['address'])
    tx_hash = TokenContract.functions.lock(lock_address, amount, ""). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# トークン資産アンロック
def share_unlock(invoker: ChecksumAddress, token, target: str, recipient: str, amount: int, data_str: str = ""):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetShare', token['address'])
    tx_hash = TokenContract.functions.unlock(target, recipient, amount, data_str). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# トークン追加発行
def share_issue_from(invoker: ChecksumAddress, token, target: str, amount: int, lock_address: str = config.ZERO_ADDRESS):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetShare', token['address'])
    tx_hash = TokenContract.functions.issueFrom(target, lock_address, amount). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# トークン発行数量の削減
def share_redeem_from(invoker: ChecksumAddress, token, target_address: str, amount: int, lock_address: str = config.ZERO_ADDRESS):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetShare', token['address'])
    tx_hash = TokenContract.functions.redeemFrom(target_address, lock_address, amount). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# 取引コントラクトの更新
def share_set_tradable_exchange(invoker: ChecksumAddress, token, exchange_address: str):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetShare', token['address'])
    tx_hash = TokenContract.functions.setTradableExchange(exchange_address). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


'''
Coupon Token （クーポン）
'''


# クーポントークンの発行
def issue_coupon_token(invoker: ChecksumAddress, attribute):
    web3.eth.default_account = invoker

    arguments = [
        attribute['name'], attribute['symbol'], attribute['totalSupply'],
        attribute['tradableExchange'],
        attribute['details'], attribute['returnDetails'], attribute['memo'],
        attribute['expirationDate'], attribute['transferable'],
        attribute['contactInformation'], attribute['privacyPolicy']
    ]
    contract_address, abi = Contract.deploy_contract(
        'IbetCoupon', arguments, invoker)

    return {'address': contract_address, 'abi': abi}


# クーポンTokenの公開リスト登録
def coupon_register_list(invoker: ChecksumAddress, token, token_list):
    web3.eth.default_account = invoker
    TokenListContract = Contract. \
        get_contract('TokenList', token_list['address'])
    tx_hash = TokenListContract.functions. \
        register(token['address'], 'IbetCoupon'). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# クーポントークンの割当
def transfer_coupon_token(invoker: ChecksumAddress, coupon_token, to, value):
    web3.eth.default_account = invoker
    coupon_contract = Contract.get_contract(
        'IbetCoupon', coupon_token['address'])
    tx_hash = coupon_contract.functions.transfer(to, value). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# クーポントークンの無効化
def invalidate_coupon_token(invoker: ChecksumAddress, coupon_token):
    web3.eth.default_account = invoker
    CouponTokenContract = Contract.get_contract(
        'IbetCoupon', coupon_token['address'])

    tx_hash = CouponTokenContract.functions. \
        setStatus(False). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# クーポントークンの譲渡不可
def untransferable_coupon_token(invoker: ChecksumAddress, coupon_token):
    web3.eth.default_account = invoker
    CouponTokenContract = Contract.get_contract(
        'IbetCoupon', coupon_token['address'])

    tx_hash = CouponTokenContract.functions. \
        setTransferable(False). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# クーポントークンの消費
def consume_coupon_token(invoker: ChecksumAddress, coupon_token, value):
    web3.eth.default_account = invoker
    CouponTokenContract = Contract.get_contract(
        'IbetCoupon', coupon_token['address'])

    tx_hash = CouponTokenContract.functions. \
        consume(value). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# クーポントークンの売出
def coupon_offer(invoker: ChecksumAddress, exchange, token, amount, price):
    coupon_transfer_to_exchange(invoker, exchange, token, amount)
    make_sell(invoker, exchange, token, amount, price)


# クーポンDEXコントラクトにクーポントークンをデポジット
def coupon_transfer_to_exchange(invoker: ChecksumAddress, exchange, token, amount):
    web3.eth.default_account = invoker
    token_contract = Contract.get_contract(
        contract_name='IbetCoupon',
        address=token['address']
    )
    tx_hash = token_contract.functions.transfer(
        exchange['address'],
        amount
    ).transact({
        'from': invoker,
        'gas': 4000000
    })
    return tx_hash


# クーポンDEXコントラクトからクーポントークンを引き出し
def coupon_withdraw_from_exchange(invoker: ChecksumAddress, exchange, token, amount):
    web3.eth.default_account = invoker
    exchange_contract = Contract.get_contract(
        contract_name='IbetExchange',
        address=exchange['address']
    )
    tx_hash = exchange_contract.functions.withdraw(
        token['address']
    ).transact({
        'from': invoker,
        'gas': 4000000
    })
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# 取引コントラクトの更新
def coupon_set_tradable_exchange(invoker: ChecksumAddress, token, exchange_address: str):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetCoupon', token['address'])
    tx_hash = TokenContract.functions.setTradableExchange(exchange_address). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


'''
Membership Token （会員権）
'''


# 会員権Tokenの発行
def membership_issue(invoker: ChecksumAddress, attribute):
    web3.eth.default_account = invoker
    arguments = [
        attribute['name'], attribute['symbol'], attribute['initialSupply'],
        attribute['tradableExchange'],
        attribute['details'], attribute['returnDetails'],
        attribute['expirationDate'], attribute['memo'],
        attribute['transferable'],
        attribute['contactInformation'], attribute['privacyPolicy']
    ]
    contract_address, abi = Contract.deploy_contract('IbetMembership', arguments, invoker)
    return {'address': contract_address, 'abi': abi}


# 会員権Tokenの公開リスト登録
def membership_register_list(invoker: ChecksumAddress, token, token_list):
    web3.eth.default_account = invoker
    TokenListContract = Contract. \
        get_contract('TokenList', token_list['address'])
    tx_hash = TokenListContract.functions. \
        register(token['address'], 'IbetMembership'). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# 会員権Tokenの無効化
def membership_invalidate(invoker: ChecksumAddress, token):
    web3.eth.default_account = invoker
    TokenContract = Contract. \
        get_contract('IbetMembership', token['address'])

    tx_hash = TokenContract.functions. \
        setStatus(False). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# 会員権Tokenの譲渡不可
def membership_untransferable(invoker: ChecksumAddress, token):
    web3.eth.default_account = invoker
    TokenContract = Contract. \
        get_contract('IbetMembership', token['address'])

    tx_hash = TokenContract.functions. \
        setTransferable(False). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# 会員権Tokenの募集（売出）
def membership_offer(invoker: ChecksumAddress, exchange, token, amount, price):
    membership_transfer_to_exchange(invoker, exchange, token, amount)
    make_sell(invoker, exchange, token, amount, price)


# 会員権DEXコントラクトに会員権Tokenをデポジット
def membership_transfer_to_exchange(invoker: ChecksumAddress, exchange, token, amount):
    web3.eth.default_account = invoker
    TokenContract = Contract. \
        get_contract('IbetMembership', token['address'])
    tx_hash = TokenContract.functions. \
        transfer(exchange['address'], amount). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# 取引コントラクトの更新
def membership_set_tradable_exchange(invoker: ChecksumAddress, token, exchange_address: str):
    web3.eth.default_account = invoker

    TokenContract = Contract.get_contract('IbetMembership', token['address'])
    tx_hash = TokenContract.functions.setTradableExchange(exchange_address). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


'''
DEX
'''


# Tokenの売りMake注文
def make_sell(invoker: ChecksumAddress, exchange, token, amount, price):
    web3.eth.default_account = invoker
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    agent = eth_account['agent']
    tx_hash = ExchangeContract.functions. \
        createOrder(token['address'], amount, price, False, agent). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# Tokenの買いTake注文
def take_buy(invoker: ChecksumAddress, exchange, order_id, amount):
    web3.eth.default_account = invoker
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    tx_hash = ExchangeContract.functions. \
        executeOrder(order_id, amount, True). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# Tokenの買いMake注文
def make_buy(invoker: ChecksumAddress, exchange, token, amount, price):
    web3.eth.default_account = invoker
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    agent = eth_account['agent']
    tx_hash = ExchangeContract.functions. \
        createOrder(token['address'], amount, price, True, agent). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# Tokenの売りTake注文
def take_sell(invoker: ChecksumAddress, exchange, order_id, amount):
    web3.eth.default_account = invoker
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    tx_hash = ExchangeContract.functions. \
        executeOrder(order_id, amount, False). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# 直近注文IDを取得
def get_latest_orderid(exchange):
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    latest_orderid = ExchangeContract.functions.latestOrderId().call()
    return latest_orderid


# 注文の取消
def cancel_order(invoker: ChecksumAddress, exchange, order_id):
    web3.eth.default_account = invoker
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    tx_hash = ExchangeContract.functions. \
        cancelOrder(order_id). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# 注文の強制取消
def force_cancel_order(invoker: ChecksumAddress, exchange, order_id):
    web3.eth.default_account = invoker
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    tx_hash = ExchangeContract.functions. \
        forceCancelOrder(order_id). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# 直近約定IDを取得
def get_latest_agreementid(exchange, order_id):
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    latest_agreementid = \
        ExchangeContract.functions.latestAgreementId(order_id).call()
    return latest_agreementid


# 約定の資金決済
def confirm_agreement(invoker, exchange, order_id, agreement_id):
    web3.eth.default_account = invoker
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    tx_hash = ExchangeContract.functions. \
        confirmAgreement(order_id, agreement_id). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# 約定の取消
def cancel_agreement(invoker: ChecksumAddress, exchange, order_id, agreement_id):
    web3.eth.default_account = invoker
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    tx_hash = ExchangeContract.functions. \
        cancelAgreement(order_id, agreement_id). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


# エスクローの作成
def create_security_token_escrow(invoker: ChecksumAddress, exchange, token, recipient_address, agent_address, amount):
    web3.eth.default_account = invoker
    IbetSecurityTokenEscrowContract = Contract. \
        get_contract('IbetSecurityTokenEscrow', exchange['address'])
    tx_hash = IbetSecurityTokenEscrowContract.functions. \
        createEscrow(token['address'], recipient_address, amount, agent_address, "{}", "{}"). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


def get_latest_security_escrow_id(exchange):
    IbetSecurityTokenEscrowContract = Contract. \
        get_contract('IbetSecurityTokenEscrow', exchange['address'])
    latest_escrow_id = \
        IbetSecurityTokenEscrowContract.functions.latestEscrowId().call()
    return latest_escrow_id


# エスクローのキャンセル
def cancel_security_token_escrow(invoker: ChecksumAddress, exchange, escrow_id):
    web3.eth.default_account = invoker
    IbetSecurityTokenEscrowContract = Contract. \
        get_contract('IbetSecurityTokenEscrow', exchange['address'])
    tx_hash = IbetSecurityTokenEscrowContract.functions. \
        cancelEscrow(escrow_id).transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# 移転の承認
def approve_transfer_security_token_escrow(invoker: ChecksumAddress, exchange, escrow_id, transfer_approval_data: str):
    web3.eth.default_account = invoker
    IbetSecurityTokenEscrowContract = Contract. \
        get_contract('IbetSecurityTokenEscrow', exchange['address'])
    tx_hash = IbetSecurityTokenEscrowContract.functions. \
        approveTransfer(escrow_id, transfer_approval_data).transact(
            {'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# エスクローの完了
def finish_security_token_escrow(invoker: ChecksumAddress, exchange, escrow_id):
    web3.eth.default_account = invoker
    IbetSecurityTokenEscrowContract = Contract. \
        get_contract('IbetSecurityTokenEscrow', exchange['address'])
    tx_hash = IbetSecurityTokenEscrowContract.functions. \
        finishEscrow(escrow_id).transact(
            {'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)


# エスクローの作成
def create_token_escrow(invoker: ChecksumAddress, exchange, token, recipient_address, agent_address, amount):
    web3.eth.default_account = invoker
    IbetEscrow = Contract. \
        get_contract('IbetEscrow', exchange['address'])
    tx_hash = IbetEscrow.functions. \
        createEscrow(token['address'], recipient_address, amount, agent_address, "{}"). \
        transact({'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


def get_latest_escrow_id(exchange):
    IbetEscrow = Contract. \
        get_contract('IbetEscrow', exchange['address'])
    latest_escrow_id = \
        IbetEscrow.functions.latestEscrowId().call()
    return latest_escrow_id


# エスクローの完了
def finish_token_escrow(invoker: ChecksumAddress, exchange, escrow_id):
    web3.eth.default_account = invoker
    IbetEscrow = Contract. \
        get_contract('IbetEscrow', exchange['address'])
    tx_hash = IbetEscrow.functions. \
        finishEscrow(escrow_id).transact(
            {'from': invoker, 'gas': 4000000})
    web3.eth.wait_for_transaction_receipt(tx_hash)
