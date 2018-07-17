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
from app.contracts import Contract
from app.testutil.auth_client import TestAuthClient

from .account_config import eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)

@pytest.fixture(scope = 'session')
def client():
    config.DB_AUTOCOMMIT = False

    init_session()
    middleware = [JSONTranslator(), DatabaseSessionManager(db_session)]
    return TestAuthClient(App(middleware=middleware))

@pytest.fixture(scope = 'session')
def whitelist_contract():
    deployer = eth_account['deployer']
    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'],deployer['password'])

    contract_address, abi = Contract.deploy_contract(
        'WhiteList', [], deployer['account_address'])

    agent = eth_account['agent']
    web3.eth.defaultAccount = agent['account_address']
    web3.personal.unlockAccount(agent['account_address'],agent['password'])

    contract = Contract.get_contract('WhiteList', contract_address)
    tx_hash = contract.functions.register_terms('書面サンプル').transact(
        {'from':agent['account_address'], 'gas':4000000}
    )
    tx = wait_transaction_receipt(tx_hash)

    return {'address':contract_address, 'abi':abi}

@pytest.fixture(scope = 'session')
def personalinfo_contract():
    deployer = eth_account['deployer']
    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'],deployer['password'])

    contract_address, abi = Contract.deploy_contract(
        'PersonalInfo', [], deployer['account_address'])

    return {'address':contract_address, 'abi':abi}

@pytest.fixture(scope = 'session')
def bond_exchange_contract(whitelist_address, personalinfo_address):
    deployer = eth_account['deployer']
    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'],deployer['password'])

    args = [whitelist_address, personalinfo_address]

    contract_address, abi = Contract.deploy_contract(
        'IbetStraightBondExchange', args, deployer['account_address'])

    return {'address':contract_address, 'abi':abi}

@pytest.fixture(scope = 'session')
def tokenlist_contract():
    deployer = eth_account['deployer']
    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'],deployer['password'])

    contract_address, abi = Contract.deploy_contract(
        'TokenList', [], deployer['account_address'])

    return {'address':contract_address, 'abi':abi}

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
