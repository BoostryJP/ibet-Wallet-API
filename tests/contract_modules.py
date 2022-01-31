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

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

from app import config
from app.contracts import Contract
from tests.account_config import eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


# 名簿用個人情報登録
# NOTE: issuer address に対する情報の公開を行う
def register_personalinfo(invoker, personal_info):
    web3.eth.defaultAccount = invoker['account_address']

    PersonalInfoContract = Contract.get_contract(
        'PersonalInfo', personal_info['address'])

    issuer = eth_account['issuer']
    encrypted_info = 'some_encrypted_info'
    tx_hash = PersonalInfoContract.functions.register(
        issuer['account_address'], encrypted_info). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# 決済用銀行口座情報登録
def register_payment_gateway(invoker, payment_gateway):
    PaymentGatewayContract = Contract.get_contract(
        'PaymentGateway', payment_gateway['address'])

    # 1) 登録 from Invoker
    web3.eth.defaultAccount = invoker['account_address']

    agent = eth_account['agent']
    encrypted_info = 'some_encrypted_info'
    tx_hash = PaymentGatewayContract.functions.register(
        agent['account_address'], encrypted_info). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)

    # 2) 認可 from Agent
    web3.eth.defaultAccount = agent['account_address']

    tx_hash = PaymentGatewayContract.functions.approve(invoker['account_address']). \
        transact({'from': agent['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


'''
Straight Bond Token （普通社債）
'''


# 債券トークンの発行
def issue_bond_token(invoker, attribute):
    web3.eth.defaultAccount = invoker['account_address']

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
        invoker['account_address']
    )

    # その他項目の更新
    TokenContract = Contract.get_contract('IbetStraightBond', contract_address)
    TokenContract.functions.setTradableExchange(attribute['tradableExchange']). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    TokenContract.functions.setInterestRate(attribute['interestRate']). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    TokenContract.functions.setInterestPaymentDate(interestPaymentDate). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    TokenContract.functions.setMemo(attribute['memo']). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    TokenContract.functions.setContactInformation(attribute['contactInformation']). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    TokenContract.functions.setPrivacyPolicy(attribute['privacyPolicy']). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    TokenContract.functions.setPersonalInfoAddress(attribute['personalInfoAddress']). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    TokenContract.functions.setMemo(attribute['memo']). \
        transact({'from': invoker['account_address'], 'gas': 4000000})

    return {'address': contract_address, 'abi': abi}


# 債券トークンのリスト登録
def register_bond_list(invoker, bond_token, token_list):
    TokenListContract = Contract.get_contract(
        'TokenList', token_list['address'])

    web3.eth.defaultAccount = invoker['account_address']

    tx_hash = TokenListContract.functions.register(
        bond_token['address'], 'IbetStraightBond'). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# 債券トークンの募集
def offer_bond_token(invoker, bond_exchange, bond_token, amount, price):
    bond_transfer_to_exchange(invoker, bond_exchange, bond_token, amount)
    make_sell(invoker, bond_exchange, bond_token, amount, price)


# DEXコントラクトにトークンをチャージ
def bond_transfer_to_exchange(invoker, bond_exchange, bond_token, amount):
    web3.eth.defaultAccount = invoker['account_address']

    token_contract = Contract.get_contract(
        'IbetStraightBond',
        bond_token['address']
    )

    token_contract.functions.transfer(
        bond_exchange['address'],
        amount
    ).transact({
        'from': invoker['account_address'],
        'gas': 4000000
    })

# DEXコントラクトからトークンを引き出し
def bond_withdraw_from_exchange(invoker, bond_exchange, bond_token, amount):
    web3.eth.defaultAccount = invoker['account_address']

    exchange_contract = Contract.get_contract(
        contract_name='IbetExchange',
        address=bond_exchange['address']
    )
    exchange_contract.functions.withdraw(
        bond_token['address']
    ).transact({
        'from': invoker['account_address'],
        'gas': 4000000
    })


# 債券の償還
def bond_redeem(invoker, token):
    web3.eth.defaultAccount = invoker['account_address']

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])

    tx_hash = TokenContract.functions.redeem(). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# 債券の譲渡可否変更
def bond_change_transferable(invoker, token, transferable):
    web3.eth.defaultAccount = invoker['account_address']

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])

    tx_hash = TokenContract.functions.setTransferable(transferable). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# 債券の無効化
def bond_invalidate(invoker, token):
    web3.eth.defaultAccount = invoker['account_address']

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])
    tx_hash = TokenContract.functions.setStatus(False). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# 債券の譲渡不可
def bond_untransferable(invoker, token):
    web3.eth.defaultAccount = invoker['account_address']

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])
    tx_hash = TokenContract.functions.setTransferable(False). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


'''
Share Token （株式）
'''


# 株式トークンの発行
def issue_share_token(invoker, attribute):
    web3.eth.defaultAccount = invoker['account_address']

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
        deployer=invoker['account_address']
    )

    TokenContract = Contract.get_contract('IbetShare', contract_address)
    if 'tradableExchange' in attribute:
        TokenContract.functions.setTradableExchange(to_checksum_address(attribute['tradableExchange'])). \
            transact({'from': invoker['account_address'], 'gas': 4000000})
    if 'personalInfoAddress' in attribute:
        TokenContract.functions.setPersonalInfoAddress(to_checksum_address(attribute['personalInfoAddress'])). \
            transact({'from': invoker['account_address'], 'gas': 4000000})
    if 'contactInformation' in attribute:
        TokenContract.functions.setContactInformation(attribute['contactInformation']). \
            transact({'from': invoker['account_address'], 'gas': 4000000})
    if 'privacyPolicy' in attribute:
        TokenContract.functions.setPrivacyPolicy(attribute['privacyPolicy']). \
            transact({'from': invoker['account_address'], 'gas': 4000000})
    if 'memo' in attribute:
        TokenContract.functions.setMemo(attribute['memo']). \
            transact({'from': invoker['account_address'], 'gas': 4000000})
    if 'transferable' in attribute:
        TokenContract.functions.setTransferable(attribute['transferable']). \
            transact({'from': invoker['account_address'], 'gas': 4000000})

    time.sleep(3)

    return {'address': contract_address, 'abi': abi}


# 株式トークンのリスト登録
def register_share_list(invoker, share_token, token_list):
    TokenListContract = Contract.get_contract(
        'TokenList', token_list['address'])

    web3.eth.defaultAccount = invoker['account_address']

    tx_hash = TokenListContract.functions.register(
        share_token['address'], 'IbetShare'). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# 株式トークンの関連URL追加
def register_share_reference_url(invoker, token, url_list):
    web3.eth.defaultAccount = invoker['account_address']

    TokenContract = Contract.get_contract('IbetShare', token['address'])
    i = 0
    for url in url_list:
        tx_hash = TokenContract.functions.setReferenceUrls(i, url). \
            transact({'from': invoker['account_address'], 'gas': 4000000})
        web3.eth.waitForTransactionReceipt(tx_hash)
        i = i + 1


# 株式Tokenの募集（売出）
def share_offer(invoker, exchange, token, amount, price):
    share_transfer_to_exchange(invoker, exchange, token, amount)
    make_sell(invoker, exchange, token, amount, price)


# DEXコントラクトにトークンをデポジット
def share_transfer_to_exchange(invoker, exchange, token, amount):
    web3.eth.defaultAccount = invoker['account_address']
    token_contract = Contract.get_contract(
        contract_name='IbetShare',
        address=token['address']
    )
    token_contract.functions.transfer(
        exchange['address'],
        amount
    ).transact({
        'from': invoker['account_address'],
        'gas': 4000000
    })


# DEXコントラクトからトークンを引き出し
def share_withdraw_from_exchange(invoker, exchange, token, amount):
    web3.eth.defaultAccount = invoker['account_address']
    exchange_contract = Contract.get_contract(
        contract_name='IbetExchange',
        address=exchange['address']
    )
    exchange_contract.functions.withdraw(
        token['address']
    ).transact({
        'from': invoker['account_address'],
        'gas': 4000000
    })


# 株式トークンの無効化
def invalidate_share_token(invoker, token):
    web3.eth.defaultAccount = invoker['account_address']
    ShareTokenContract = Contract.get_contract('IbetShare', token['address'])
    tx_hash = ShareTokenContract.functions.setStatus(False). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# 株式トークンの譲渡不可
def untransferable_share_token(invoker, token):
    web3.eth.defaultAccount = invoker['account_address']
    ShareTokenContract = Contract.get_contract('IbetShare', token['address'])
    tx_hash = ShareTokenContract.functions.setTransferable(False). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


'''
Coupon Token （クーポン）
'''


# クーポントークンの発行
def issue_coupon_token(invoker, attribute):
    web3.eth.defaultAccount = invoker['account_address']

    arguments = [
        attribute['name'], attribute['symbol'], attribute['totalSupply'],
        attribute['tradableExchange'],
        attribute['details'], attribute['returnDetails'], attribute['memo'],
        attribute['expirationDate'], attribute['transferable'],
        attribute['contactInformation'], attribute['privacyPolicy']
    ]
    contract_address, abi = Contract.deploy_contract(
        'IbetCoupon', arguments, invoker['account_address'])

    return {'address': contract_address, 'abi': abi}


# クーポンTokenの公開リスト登録
def coupon_register_list(invoker, token, token_list):
    web3.eth.defaultAccount = invoker['account_address']
    TokenListContract = Contract. \
        get_contract('TokenList', token_list['address'])
    tx_hash = TokenListContract.functions. \
        register(token['address'], 'IbetCoupon'). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# クーポントークンの割当
def transfer_coupon_token(invoker, coupon_token, to, value):
    web3.eth.defaultAccount = invoker['account_address']
    coupon_contract = Contract.get_contract('IbetCoupon', coupon_token['address'])
    tx_hash = coupon_contract.functions.transfer(to, value). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# クーポントークンの無効化
def invalidate_coupon_token(invoker, coupon_token):
    web3.eth.defaultAccount = invoker['account_address']
    CouponTokenContract = Contract.get_contract(
        'IbetCoupon', coupon_token['address'])

    tx_hash = CouponTokenContract.functions. \
        setStatus(False). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# クーポントークンの譲渡不可
def untransferable_coupon_token(invoker, coupon_token):
    web3.eth.defaultAccount = invoker['account_address']
    CouponTokenContract = Contract.get_contract(
        'IbetCoupon', coupon_token['address'])

    tx_hash = CouponTokenContract.functions. \
        setTransferable(False). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# クーポントークンの消費
def consume_coupon_token(invoker, coupon_token, value):
    web3.eth.defaultAccount = invoker['account_address']
    CouponTokenContract = Contract.get_contract(
        'IbetCoupon', coupon_token['address'])

    tx_hash = CouponTokenContract.functions. \
        consume(value). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# クーポントークンの売出
def coupon_offer(invoker, exchange, token, amount, price):
    coupon_transfer_to_exchange(invoker, exchange, token, amount)
    make_sell(invoker, exchange, token, amount, price)


# クーポンDEXコントラクトにクーポントークンをデポジット
def coupon_transfer_to_exchange(invoker, exchange, token, amount):
    web3.eth.defaultAccount = invoker['account_address']
    token_contract = Contract.get_contract(
        contract_name='IbetCoupon',
        address=token['address']
    )
    token_contract.functions.transfer(
        exchange['address'],
        amount
    ).transact({
        'from': invoker['account_address'],
        'gas': 4000000
    })


# クーポンDEXコントラクトからクーポントークンを引き出し
def coupon_withdraw_from_exchange(invoker, exchange, token, amount):
    web3.eth.defaultAccount = invoker['account_address']
    exchange_contract = Contract.get_contract(
        contract_name='IbetExchange',
        address=exchange['address']
    )
    exchange_contract.functions.withdraw(
        token['address']
    ).transact({
        'from': invoker['account_address'],
        'gas': 4000000
    })


'''
Membership Token （会員権）
'''


# 会員権Tokenの発行
def membership_issue(invoker, attribute):
    web3.eth.defaultAccount = invoker['account_address']
    arguments = [
        attribute['name'], attribute['symbol'], attribute['initialSupply'],
        attribute['tradableExchange'],
        attribute['details'], attribute['returnDetails'],
        attribute['expirationDate'], attribute['memo'],
        attribute['transferable'],
        attribute['contactInformation'], attribute['privacyPolicy']
    ]
    contract_address, abi = Contract. \
        deploy_contract('IbetMembership', arguments, invoker['account_address'])
    return {'address': contract_address, 'abi': abi}


# 会員権Tokenの公開リスト登録
def membership_register_list(invoker, token, token_list):
    web3.eth.defaultAccount = invoker['account_address']
    TokenListContract = Contract. \
        get_contract('TokenList', token_list['address'])
    tx_hash = TokenListContract.functions. \
        register(token['address'], 'IbetMembership'). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# 会員権Tokenの無効化
def membership_invalidate(invoker, token):
    web3.eth.defaultAccount = invoker['account_address']
    TokenContract = Contract. \
        get_contract('IbetMembership', token['address'])

    tx_hash = TokenContract.functions. \
        setStatus(False). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# 会員権Tokenの譲渡不可
def membership_untransferable(invoker, token):
    web3.eth.defaultAccount = invoker['account_address']
    TokenContract = Contract. \
        get_contract('IbetMembership', token['address'])

    tx_hash = TokenContract.functions. \
        setTransferable(False). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# 会員権Tokenの募集（売出）
def membership_offer(invoker, exchange, token, amount, price):
    membership_transfer_to_exchange(invoker, exchange, token, amount)
    make_sell(invoker, exchange, token, amount, price)


# 会員権DEXコントラクトに会員権Tokenをデポジット
def membership_transfer_to_exchange(invoker, exchange, token, amount):
    web3.eth.defaultAccount = invoker['account_address']
    TokenContract = Contract. \
        get_contract('IbetMembership', token['address'])
    tx_hash = TokenContract.functions. \
        transfer(exchange['address'], amount). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


'''
DEX
'''


# Tokenの売りMake注文
def make_sell(invoker, exchange, token, amount, price):
    web3.eth.defaultAccount = invoker['account_address']
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    agent = eth_account['agent']
    tx_hash = ExchangeContract.functions. \
        createOrder(token['address'], amount, price, False, agent['account_address']). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# Tokenの買いTake注文
def take_buy(invoker, exchange, order_id, amount):
    web3.eth.defaultAccount = invoker['account_address']
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    tx_hash = ExchangeContract.functions. \
        executeOrder(order_id, amount, True). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# Tokenの買いMake注文
def make_buy(invoker, exchange, token, amount, price):
    web3.eth.defaultAccount = invoker['account_address']
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    agent = eth_account['agent']
    tx_hash = ExchangeContract.functions. \
        createOrder(token['address'], amount, price, True, agent['account_address']). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# Tokenの売りTake注文
def take_sell(invoker, exchange, order_id, amount):
    web3.eth.defaultAccount = invoker['account_address']
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    tx_hash = ExchangeContract.functions. \
        executeOrder(order_id, amount, False). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# 直近注文IDを取得
def get_latest_orderid(exchange):
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    latest_orderid = ExchangeContract.functions.latestOrderId().call()
    return latest_orderid


# 注文の取消
def cancel_order(invoker, exchange, order_id):
    web3.eth.defaultAccount = invoker['account_address']
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    tx_hash = ExchangeContract.functions. \
        cancelOrder(order_id). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# 直近約定IDを取得
def get_latest_agreementid(exchange, order_id):
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    latest_agreementid = \
        ExchangeContract.functions.latestAgreementId(order_id).call()
    return latest_agreementid


# 約定の資金決済
def confirm_agreement(invoker, exchange, order_id, agreement_id):
    web3.eth.defaultAccount = invoker['account_address']
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    tx_hash = ExchangeContract.functions. \
        confirmAgreement(order_id, agreement_id). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


# 約定の取消
def cancel_agreement(invoker, exchange, order_id, agreement_id):
    web3.eth.defaultAccount = invoker['account_address']
    ExchangeContract = Contract. \
        get_contract('IbetExchange', exchange['address'])
    tx_hash = ExchangeContract.functions. \
        cancelAgreement(order_id, agreement_id). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)
