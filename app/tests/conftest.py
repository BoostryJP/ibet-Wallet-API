# -*- coding: utf-8 -*-
import pytest
from falcon import testing

import time
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

from app.main import App
from app.middleware import JSONTranslator, DatabaseSessionManager
from app.database import db_session, init_session, engine
from app import config
from app.testutil.auth_client import TestAuthClient

from .account_config import eth_account
from .contract_config import WhiteList, PersonalInfo, IbetStraightBondExchange,\
    TokenList

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)

@pytest.fixture(scope = 'session')
def client():
    config.DB_AUTOCOMMIT = False

    init_session()
    middleware = [JSONTranslator(), DatabaseSessionManager(db_session)]
    return TestAuthClient(App(middleware=middleware))

def whitelist_contract():
    deployer = eth_account['deployer']
    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'],deployer['password'])
    WhiteListContract = web3.eth.contract(
        abi = WhiteList['abi'],
        bytecode = WhiteList['bytecode'],
        bytecode_runtime = WhiteList['bytecode_runtime'],
    )

    tx_hash = WhiteListContract.deploy(
        transaction={'from':deployer['account_address'], 'gas':4000000}
    ).hex()

    count = 0
    tx = None
    while True:
        time.sleep(float(config.TEST_INTARVAL))
        try:
            tx = web3.eth.getTransactionReceipt(tx_hash)
        except:
            continue
        count += 1
        if tx is not None or count > 120:
            break

    contract_address = ''
    if tx is not None :
        # ブロックの状態を確認して、コントラクトアドレスが登録されているかを確認する。
        if 'contractAddress' in tx.keys():
            contract_address = tx['contractAddress']

    return {'address':contract_address, 'abi':WhiteList['abi']}

def personalinfo_contract():
    deployer = eth_account['deployer']
    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'],deployer['password'])
    PersonalInfoContract = web3.eth.contract(
        abi = PersonalInfo['abi'],
        bytecode = PersonalInfo['bytecode'],
        bytecode_runtime = PersonalInfo['bytecode_runtime'],
    )

    tx_hash = PersonalInfoContract.deploy(
        transaction={'from':deployer['account_address'], 'gas':4000000}
    ).hex()

    count = 0
    tx = None
    while True:
        time.sleep(float(config.TEST_INTARVAL))
        try:
            tx = web3.eth.getTransactionReceipt(tx_hash)
        except:
            continue
        count += 1
        if tx is not None or count > 120:
            break

    contract_address = ''
    if tx is not None :
        # ブロックの状態を確認して、コントラクトアドレスが登録されているかを確認する。
        if 'contractAddress' in tx.keys():
            contract_address = tx['contractAddress']

    return {'address':contract_address, 'abi':PersonalInfo['abi']}

def bond_exchange_contract(whitelist_address, personalinfo_address):
    deployer = eth_account['deployer']
    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'],deployer['password'])
    BondExchangeContract = web3.eth.contract(
        abi = IbetStraightBondExchange['abi'],
        bytecode = IbetStraightBondExchange['bytecode'],
        bytecode_runtime = IbetStraightBondExchange['bytecode_runtime'],
    )

    arguments = [
        whitelist_address,
        personalinfo_address
    ]

    tx_hash = BondExchangeContract.deploy(
        transaction={'from':deployer['account_address'], 'gas':5500000},
        args=arguments
    ).hex()

    count = 0
    tx = None
    while True:
        time.sleep(float(config.TEST_INTARVAL))
        try:
            tx = web3.eth.getTransactionReceipt(tx_hash)
        except:
            continue
        count += 1
        if tx is not None or count > 120:
            break

    contract_address = ''
    if tx is not None :
        # ブロックの状態を確認して、コントラクトアドレスが登録されているかを確認する。
        if 'contractAddress' in tx.keys():
            contract_address = tx['contractAddress']

    return {'address':contract_address, 'abi':IbetStraightBondExchange['abi']}

def tokenlist_contract():
    deployer = eth_account['deployer']
    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'],deployer['password'])
    TokenListContract = web3.eth.contract(
        abi = TokenList['abi'],
        bytecode = TokenList['bytecode'],
        bytecode_runtime = TokenList['bytecode_runtime'],
    )

    tx_hash = TokenListContract.deploy(
        transaction={'from':deployer['account_address'], 'gas':4000000}
    ).hex()

    count = 0
    tx = None
    while True:
        time.sleep(float(config.TEST_INTARVAL))
        try:
            tx = web3.eth.getTransactionReceipt(tx_hash)
        except:
            continue
        count += 1
        if tx is not None or count > 120:
            break

    contract_address = ''
    if tx is not None :
        # ブロックの状態を確認して、コントラクトアドレスが登録されているかを確認する。
        if 'contractAddress' in tx.keys():
            contract_address = tx['contractAddress']

    return {'address':contract_address, 'abi':TokenList['abi']}

@pytest.fixture(scope = 'session')
def shared_contract():
    white_list = whitelist_contract()
    personal_info = personalinfo_contract()
    bond_exchange = bond_exchange_contract(white_list['address'], personal_info['address'])
    token_list = tokenlist_contract()
    contracts = {
        'WhiteList': white_list,
        'PersonalInfo': personal_info,
        'IbetStraightBondExchange': bond_exchange,
        'TokenList': token_list
    }
    return contracts

# テーブルの自動作成・自動削除
@pytest.fixture(scope = 'session')
def db(request):
    from app.model import Base
    Base.metadata.create_all(engine)

    def teardown():
        Base.metadata.drop_all(engine)
        return

    request.addfinalizer(teardown)
    return db_session

# セッションの作成・自動ロールバック
@pytest.fixture(scope = 'function')
def session(request, db):
    session = db_session()

    def teardown():
        session.rollback()

    request.addfinalizer(teardown)
    return session
