# -*- coding: utf-8 -*-
import time
import json

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

from app import config
from app.contracts import Contract

from .account_config import eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)

# 株主名簿用個人情報登録
def register_personalinfo(invoker, personal_info):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'],invoker['password'])

    PersonalInfoContract = Contract.get_contract(
        'PersonalInfo', personal_info['address'])

    issuer = eth_account['issuer']
    encrypted_info = 'some_encrypted_info'
    tx_hash = PersonalInfoContract.functions.register(
        issuer['account_address'], encrypted_info).\
        transact({'from':invoker['account_address'], 'gas':4000000})
    tx = wait_transaction_receipt(tx_hash)


# 決済用銀行口座情報登録
def register_whitelist(invoker, white_list):
    WhiteListContract = Contract.get_contract(
        'WhiteList', white_list['address'])

    # 1) 登録 from Invoker
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'],invoker['password'])

    agent = eth_account['agent']
    encrypted_info = 'some_encrypted_info'
    tx_hash = WhiteListContract.functions.register(
        agent['account_address'], encrypted_info).\
        transact({'from':invoker['account_address'], 'gas':4000000})
    tx = wait_transaction_receipt(tx_hash)

    # 2) 認可 from Agent
    web3.eth.defaultAccount = agent['account_address']
    web3.personal.unlockAccount(agent['account_address'], agent['password'])

    tx_hash = WhiteListContract.functions.approve(invoker['account_address']).\
        transact({'from':agent['account_address'], 'gas':4000000})
    tx = wait_transaction_receipt(tx_hash)


# 債券トークンの発行
def issue_bond_token(invoker, attribute):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'],invoker['password'])

    interestPaymentDate = json.dumps({
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
    })

    arguments = [
    attribute['name'], attribute['symbol'], attribute['totalSupply'],
    attribute['faceValue'], attribute['interestRate'], interestPaymentDate,
    attribute['redemptionDate'], attribute['redemptionAmount'],
    attribute['returnDate'], attribute['returnAmount'],
    attribute['purpose'], attribute['memo']
    ]

    contract_address, abi = Contract.deploy_contract(
        'IbetStraightBond', arguments, invoker['account_address'])

    return {'address': contract_address, 'abi': abi}


# 債券トークンのリスト登録
def register_bond_list(invoker, bond_token, token_list):
    TokenListContract = Contract.get_contract(
        'TokenList', token_list['address'])

    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'],invoker['password'])

    tx_hash = TokenListContract.functions.register(
        bond_token['address'], 'IbetStraightBond').\
        transact({'from':invoker['account_address'], 'gas':4000000})
    tx = wait_transaction_receipt(tx_hash)


# 債券トークンの募集
def offer_bond_token(invoker, bond_exchange, bond_token, amount, price):
    bond_transfer_to_exchange(invoker, bond_exchange, bond_token, amount)
    make_sell_bond_token(invoker, bond_exchange, bond_token, amount, price)


# 取引コントラクトに債券トークンをチャージ
def bond_transfer_to_exchange(invoker, bond_exchange, bond_token, amount):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'],invoker['password'])

    TokenContract = Contract.get_contract(
        'IbetStraightBond', bond_token['address'])

    tx_hash = TokenContract.functions.transfer(bond_exchange['address'], amount).\
        transact({'from':invoker['account_address'], 'gas':4000000})
    tx = wait_transaction_receipt(tx_hash)


# 債券トークンの売りMake注文
def make_sell_bond_token(invoker, bond_exchange, bond_token, amount, price):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'],invoker['password'])

    ExchangeContract = Contract.get_contract(
        'IbetStraightBondExchange', bond_exchange['address'])

    agent = eth_account['agent']

    gas = ExchangeContract.estimateGas().\
        createOrder(bond_token['address'], amount, price, False, agent['account_address'])
    tx_hash = ExchangeContract.functions.\
        createOrder(bond_token['address'], amount, price, False, agent['account_address']).\
        transact({'from':invoker['account_address'], 'gas':gas})
    tx = wait_transaction_receipt(tx_hash)


# 債券トークンの買いTake注文
def take_buy_bond_token(invoker, bond_exchange, order_id, amount):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'],invoker['password'])

    ExchangeContract = Contract.get_contract(
        'IbetStraightBondExchange', bond_exchange['address'])

    tx_hash = ExchangeContract.functions.\
        executeOrder(order_id, amount, True).\
        transact({'from':invoker['account_address'], 'gas':4000000})
    tx = wait_transaction_receipt(tx_hash)


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

    latest_agreementid = ExchangeContract.functions.latestAgreementIds(order_id).call()
    return latest_agreementid


# 債券約定の資金決済
def bond_confirm_agreement(invoker, bond_exchange, order_id, agreement_id):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'],invoker['password'])

    ExchangeContract = Contract.get_contract(
        'IbetStraightBondExchange', bond_exchange['address'])

    tx_hash = ExchangeContract.functions.\
        confirmAgreement(order_id, agreement_id).\
        transact({'from':invoker['account_address'], 'gas':4000000})
    tx = wait_transaction_receipt(tx_hash)


# トランザクションがブロックに取り込まれるまで待つ
# インターバルで10回以上経過した場合は失敗とみなす（Falseを返す）
def wait_transaction_receipt(tx_hash):
    count = 0
    tx = None
    while True:
        time.sleep(float(config.TEST_INTARVAL))
        try:
            tx = web3.eth.getTransactionReceipt(tx_hash)
        except:
            continue
        count += 1
        if tx is not None:
            break
        elif count > 120:
            raise Exception

    return tx
