# -*- coding: utf-8 -*-
import json

from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.contracts import Contract

from .account_config import eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


# 名簿用個人情報登録
# NOTE: issuer address に対する情報の公開を行う
def register_personalinfo(invoker, personal_info):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

    PersonalInfoContract = Contract.get_contract(
        'PersonalInfo', personal_info['address'])

    issuer = eth_account['issuer']
    encrypted_info = 'some_encrypted_info'
    tx_hash = PersonalInfoContract.functions.register(
        issuer['account_address'], encrypted_info). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# 決済用銀行口座情報登録
def register_payment_gateway(invoker, payment_gateway):
    PaymentGatewayContract = Contract.get_contract(
        'PaymentGateway', payment_gateway['address'])

    # 1) 登録 from Invoker
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

    agent = eth_account['agent']
    encrypted_info = 'some_encrypted_info'
    tx_hash = PaymentGatewayContract.functions.register(
        agent['account_address'], encrypted_info). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)

    # 2) 認可 from Agent
    web3.eth.defaultAccount = agent['account_address']
    web3.personal.unlockAccount(agent['account_address'], agent['password'])

    tx_hash = PaymentGatewayContract.functions.approve(invoker['account_address']). \
        transact({'from': agent['account_address'], 'gas': 4000000})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# 取引参加者登録
def register_exchange_regulator(invoker, exchange_regulator_service, account_address):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

    ExchangeRegulatorService = \
        Contract.get_contract('ExchangeRegulatorService', exchange_regulator_service['address'])

    tx_hash = ExchangeRegulatorService.functions.register(account_address, False). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


'''
Straight Bond Token （普通社債）
'''


# 債券トークンの発行
def issue_bond_token(invoker, attribute):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

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
        attribute['tradableExchange'],
        attribute['faceValue'], attribute['interestRate'], interestPaymentDate,
        attribute['redemptionDate'], attribute['redemptionValue'],
        attribute['returnDate'], attribute['returnAmount'],
        attribute['purpose'], attribute['memo'],
        attribute['contactInformation'], attribute['privacyPolicy'],
        attribute['personalInfoAddress']
    ]

    contract_address, abi = Contract.deploy_contract(
        'IbetStraightBond', arguments, invoker['account_address'])

    return {'address': contract_address, 'abi': abi}


# 債券トークンのリスト登録
def register_bond_list(invoker, bond_token, token_list):
    TokenListContract = Contract.get_contract(
        'TokenList', token_list['address'])

    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

    tx_hash = TokenListContract.functions.register(
        bond_token['address'], 'IbetStraightBond'). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# 債券トークンの募集
def offer_bond_token(invoker, bond_exchange, bond_token, amount, price):
    bond_transfer_to_exchange(invoker, bond_exchange, bond_token, amount)
    make_sell_bond_token(invoker, bond_exchange, bond_token, amount, price)


# 取引コントラクトに債券トークンをチャージ
def bond_transfer_to_exchange(invoker, bond_exchange, bond_token, amount):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

    TokenContract = Contract.get_contract(
        'IbetStraightBond', bond_token['address'])

    tx_hash = TokenContract.functions.transfer(bond_exchange['address'], amount). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# 債券トークンの売りMake注文
def make_sell_bond_token(invoker, bond_exchange, bond_token, amount, price):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

    ExchangeContract = Contract.get_contract(
        'IbetStraightBondExchange', bond_exchange['address'])

    agent = eth_account['agent']

    gas = ExchangeContract.estimateGas(). \
        createOrder(bond_token['address'], amount, price, False, agent['account_address'])
    tx_hash = ExchangeContract.functions. \
        createOrder(bond_token['address'], amount, price, False, agent['account_address']). \
        transact({'from': invoker['account_address'], 'gas': gas})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# 債券トークンの買いTake注文
def take_buy_bond_token(invoker, bond_exchange, order_id, amount):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

    ExchangeContract = Contract.get_contract(
        'IbetStraightBondExchange', bond_exchange['address'])

    tx_hash = ExchangeContract.functions. \
        executeOrder(order_id, amount, True). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# 直近注文IDを取得
def get_latest_orderid(bond_exchange):
    ExchangeContract = Contract.get_contract(
        'IbetStraightBondExchange', bond_exchange['address'])

    latest_orderid = ExchangeContract.functions.latestOrderId().call()
    return latest_orderid


# 直近約定IDを取得
def get_latest_agreementid(bond_exchange, order_id):
    ExchangeContract = Contract.get_contract(
        'IbetStraightBondExchange', bond_exchange['address'])

    latest_agreementid = ExchangeContract.functions.latestAgreementId(order_id).call()
    return latest_agreementid


# 債券約定の資金決済
def bond_confirm_agreement(invoker, bond_exchange, order_id, agreement_id):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

    ExchangeContract = Contract.get_contract(
        'IbetStraightBondExchange', bond_exchange['address'])

    tx_hash = ExchangeContract.functions. \
        confirmAgreement(order_id, agreement_id). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# 債券の償還
def bond_redeem(invoker, token):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])

    tx_hash = TokenContract.functions.redeem(). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)

# 債券の譲渡可否変更
def bond_change_transferable(invoker, token, transferable):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

    TokenContract = Contract.get_contract('IbetStraightBond', token['address'])

    tx_hash = TokenContract.functions.setTransferable(transferable). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    web3.eth.waitForTransactionReceipt(tx_hash)


'''
Coupon Token （クーポン）
'''


# クーポントークンの発行
def issue_coupon_token(invoker, attribute):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

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
    TokenListContract = Contract. \
        get_contract('TokenList', token_list['address'])

    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

    tx_hash = TokenListContract.functions. \
        register(token['address'], 'IbetCoupon'). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# クーポントークンの割当
def transfer_coupon_token(invoker, coupon_token, to, value):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])
    coupon_contract = Contract.get_contract('IbetCoupon', coupon_token['address'])
    gas = coupon_contract.estimateGas().transfer(to, value)
    tx_hash = coupon_contract.functions.transfer(to, value). \
        transact({'from': invoker['account_address'], 'gas': gas})
    web3.eth.waitForTransactionReceipt(tx_hash)


# クーポントークンの無効化
def invalidate_coupon_token(invoker, coupon_token):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

    CouponTokenContract = Contract.get_contract(
        'IbetCoupon', coupon_token['address'])

    tx_hash = CouponTokenContract.functions. \
        setStatus(False). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# クーポントークンの消費
def consume_coupon_token(invoker, coupon_token, value):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

    CouponTokenContract = Contract.get_contract(
        'IbetCoupon', coupon_token['address'])

    tx_hash = CouponTokenContract.functions. \
        consume(value). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# クーポントークンの売出
def coupon_offer(invoker, exchange, token, amount, price):
    coupon_transfer_to_exchange(invoker, exchange, token, amount)
    coupon_make_sell(invoker, exchange, token, amount, price)


# クーポンDEXコントラクトにクーポントークンをデポジット
def coupon_transfer_to_exchange(invoker, exchange, token, amount):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])
    TokenContract = Contract. \
        get_contract('IbetCoupon', token['address'])
    tx_hash = TokenContract.functions. \
        transfer(exchange['address'], amount). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# クーポントークンの売りMake注文
def coupon_make_sell(invoker, exchange, token, amount, price):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])
    ExchangeContract = Contract. \
        get_contract('IbetCouponExchange', exchange['address'])
    agent = eth_account['agent']
    gas = ExchangeContract.estimateGas(). \
        createOrder(token['address'], amount, price, False, agent['account_address'])
    tx_hash = ExchangeContract.functions. \
        createOrder(token['address'], amount, price, False, agent['account_address']). \
        transact({'from': invoker['account_address'], 'gas': gas})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# クーポントークンの買いTake注文
def coupon_take_buy(invoker, exchange, order_id, amount):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])
    ExchangeContract = Contract. \
        get_contract('IbetCouponExchange', exchange['address'])
    gas = ExchangeContract.estimateGas(). \
        executeOrder(order_id, amount, True)
    tx_hash = ExchangeContract.functions. \
        executeOrder(order_id, amount, True). \
        transact({'from': invoker['account_address'], 'gas': gas})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# 直近注文IDを取得
def coupon_get_latest_orderid(exchange):
    ExchangeContract = Contract. \
        get_contract('IbetCouponExchange', exchange['address'])
    latest_orderid = ExchangeContract.functions.latestOrderId().call()
    return latest_orderid


# 直近約定IDを取得
def coupon_get_latest_agreementid(exchange, order_id):
    ExchangeContract = Contract. \
        get_contract('IbetCouponExchange', exchange['address'])
    latest_agreementid = \
        ExchangeContract.functions.latestAgreementId(order_id).call()
    return latest_agreementid


# 決済承認
def coupon_confirm_agreement(invoker, exchange, order_id, agreement_id):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])
    ExchangeContract = Contract. \
        get_contract('IbetCouponExchange', exchange['address'])
    gas = ExchangeContract.estimateGas(). \
        confirmAgreement(order_id, agreement_id)
    tx_hash = ExchangeContract.functions. \
        confirmAgreement(order_id, agreement_id). \
        transact({'from': invoker['account_address'], 'gas': gas})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


'''
Membership Token （会員権）
'''


# 会員権Tokenの発行
def membership_issue(invoker, attribute):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

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
    TokenListContract = Contract. \
        get_contract('TokenList', token_list['address'])

    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])

    tx_hash = TokenListContract.functions. \
        register(token['address'], 'IbetMembership'). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# 会員権Tokenの無効化
def membership_invalidate(invoker, token):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])
    TokenContract = Contract. \
        get_contract('IbetMembership', token['address'])

    tx_hash = TokenContract.functions. \
        setStatus(False). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# 会員権Tokenの募集（売出）
def membership_offer(invoker, exchange, token, amount, price):
    membership_transfer_to_exchange(invoker, exchange, token, amount)
    membership_make_sell(invoker, exchange, token, amount, price)


# 会員権DEXコントラクトに会員権Tokenをデポジット
def membership_transfer_to_exchange(invoker, exchange, token, amount):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])
    TokenContract = Contract. \
        get_contract('IbetMembership', token['address'])
    tx_hash = TokenContract.functions. \
        transfer(exchange['address'], amount). \
        transact({'from': invoker['account_address'], 'gas': 4000000})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# 会員権Tokenの売りMake注文
def membership_make_sell(invoker, exchange, token, amount, price):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])
    ExchangeContract = Contract. \
        get_contract('IbetMembershipExchange', exchange['address'])
    agent = eth_account['agent']
    gas = ExchangeContract.estimateGas(). \
        createOrder(token['address'], amount, price, False, agent['account_address'])
    tx_hash = ExchangeContract.functions. \
        createOrder(token['address'], amount, price, False, agent['account_address']). \
        transact({'from': invoker['account_address'], 'gas': gas})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# 会員権Tokenの買いTake注文
def membership_take_buy(invoker, exchange, order_id, amount):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])
    ExchangeContract = Contract. \
        get_contract('IbetMembershipExchange', exchange['address'])
    gas = ExchangeContract.estimateGas(). \
        executeOrder(order_id, amount, True)
    tx_hash = ExchangeContract.functions. \
        executeOrder(order_id, amount, True). \
        transact({'from': invoker['account_address'], 'gas': gas})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)


# 直近注文IDを取得
def membership_get_latest_orderid(exchange):
    ExchangeContract = Contract. \
        get_contract('IbetMembershipExchange', exchange['address'])
    latest_orderid = ExchangeContract.functions.latestOrderId().call()
    return latest_orderid


# 直近約定IDを取得
def membership_get_latest_agreementid(exchange, order_id):
    ExchangeContract = Contract. \
        get_contract('IbetMembershipExchange', exchange['address'])
    latest_agreementid = \
        ExchangeContract.functions.latestAgreementId(order_id).call()
    return latest_agreementid


# 会員権約定の資金決済
def membership_confirm_agreement(invoker, exchange, order_id, agreement_id):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'], invoker['password'])
    ExchangeContract = Contract. \
        get_contract('IbetMembershipExchange', exchange['address'])
    gas = ExchangeContract.estimateGas(). \
        confirmAgreement(order_id, agreement_id)
    tx_hash = ExchangeContract.functions. \
        confirmAgreement(order_id, agreement_id). \
        transact({'from': invoker['account_address'], 'gas': gas})
    tx = web3.eth.waitForTransactionReceipt(tx_hash)
