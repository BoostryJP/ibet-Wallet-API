# -*- coding: utf-8 -*-
import time
import json

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

from app import config
from .account_config import eth_account
from .contract_config import IbetStraightBond, PersonalInfo, TokenList

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)

# 株主名簿用個人情報登録
def register_personalinfo(invoker, personal_info):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'],invoker['password'])

    PersonalInfoContract = web3.eth.contract(
        address=personal_info['address'], abi=personal_info['abi'])

    issuer = eth_account['issuer']
    encrypted_info = 'some_encrypted_info'
    tx_hash = PersonalInfoContract.functions.register(issuer['account_address'], encrypted_info).\
        transact({'from':invoker['account_address'], 'gas':4000000})
    tx = wait_transaction_receipt(tx_hash)


# 決済用銀行口座情報登録
def register_whitelist(invoker, white_list):
    WhiteListContract = web3.eth.contract(
        address=white_list['address'], abi=white_list['abi'])

    # 1) 登録 from Invoker
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'],invoker['password'])

    agent = eth_account['agent']
    encrypted_info = 'some_encrypted_info'
    tx_hash = WhiteListContract.functions.register(agent['account_address'], encrypted_info).\
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

    abi = IbetStraightBond['abi']
    bytecode = IbetStraightBond['bytecode']
    bytecode_runtime = IbetStraightBond['bytecode_runtime']

    TokenContract = web3.eth.contract(
        abi=abi,
        bytecode=bytecode,
        bytecode_runtime=bytecode_runtime,
    )

    interestPaymentDate = json.dumps({
        'interestPaymentDate1': attribute['interestPaymentDate1'],
        'interestPaymentDate2': attribute['interestPaymentDate2']
    })

    arguments = [
        attribute['name'], attribute['symbol'], attribute['totalSupply'],
        attribute['faceValue'], attribute['interestRate'], interestPaymentDate,
        attribute['redemptionDate'], attribute['redemptionAmount'],
        attribute['returnDate'], attribute['returnAmount'],
        attribute['purpose'], attribute['memo']
    ]

    tx_hash = TokenContract.deploy(
        transaction={
            'from': invoker['account_address'],
            'gas': 4000000
        },
        args=arguments).hex()

    print('------ token issued ------')

    tx = wait_transaction_receipt(tx_hash)

    contract_address = ''
    if tx is not None:
        # ブロックの状態を確認して、コントラクトアドレスが登録されているかを確認する。
        if 'contractAddress' in tx.keys():
            contract_address = tx['contractAddress']

    return {'address': contract_address, 'abi': IbetStraightBond['abi']}


# 債券トークンのリスト登録
def register_bond_list(invoker, bond_token, token_list):
    TokenListContract = web3.eth.contract(
        address=token_list['address'], abi=token_list['abi'])

    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'],invoker['password'])

    tx_hash = TokenListContract.functions.register(bond_token['address'], 'IbetStraightBond').\
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

    TokenContract = web3.eth.contract(
        address=bond_token['address'], abi=bond_token['abi'])

    tx_hash = TokenContract.functions.transfer(bond_exchange['address'], amount).\
        transact({'from':invoker['account_address'], 'gas':4000000})
    tx = wait_transaction_receipt(tx_hash)


# 債券トークンの売りMake注文
def make_sell_bond_token(invoker, bond_exchange, bond_token, amount, price):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'],invoker['password'])

    ExchangeContract = web3.eth.contract(
        address=bond_exchange['address'], abi=bond_exchange['abi'])

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

    ExchangeContract = web3.eth.contract(
        address=bond_exchange['address'], abi=bond_exchange['abi'])

    tx_hash = ExchangeContract.functions.\
        executeOrder(order_id, amount, True).\
        transact({'from':invoker['account_address'], 'gas':4000000})
    tx = wait_transaction_receipt(tx_hash)


# 直近注文IDを取得
def get_latest_orderid(bond_exchange):
    ExchangeContract = web3.eth.contract(
        address=bond_exchange['address'], abi=bond_exchange['abi'])
    latest_orderid = ExchangeContract.functions.latestOrderId().call()
    return latest_orderid


# 直近約定IDを取得
def get_latest_agreementid(bond_exchange, order_id):
    ExchangeContract = web3.eth.contract(
        address=bond_exchange['address'], abi=bond_exchange['abi'])
    latest_agreementid = ExchangeContract.functions.latestAgreementIds(order_id).call()
    return latest_agreementid


# 債券約定の資金決済
def bond_confirm_agreement(invoker, bond_exchange, order_id, agreement_id):
    web3.eth.defaultAccount = invoker['account_address']
    web3.personal.unlockAccount(invoker['account_address'],invoker['password'])

    ExchangeContract = web3.eth.contract(
        address=bond_exchange['address'], abi=bond_exchange['abi'])

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
        elif count > 10:
            raise Exception

    return tx
