# -*- coding: utf-8 -*-
import pytest
from falcon import testing

from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.main import App
from app.middleware import JSONTranslator, DatabaseSessionManager
from app.database import db_session, init_session, engine
from app import config
from app.contracts import Contract
from app.testutil.auth_client import TestAuthClient

from .account_config import eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope='session')
def client():
    config.DB_AUTOCOMMIT = False

    init_session()
    middleware = [JSONTranslator(), DatabaseSessionManager(db_session)]
    return TestAuthClient(App(middleware=middleware))


@pytest.fixture(scope='session')
def payment_gateway_contract():
    deployer = eth_account['deployer']
    agent = eth_account['agent']

    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'], deployer['password'])

    contract_address, abi = Contract.deploy_contract(
        'PaymentGateway', [], deployer['account_address'])

    contract = Contract.get_contract('PaymentGateway', contract_address)
    tx_hash = contract.functions.addAgent(0, agent['account_address']).transact(
        {'from': deployer['account_address'], 'gas': 4000000}
    )
    web3.eth.waitForTransactionReceipt(tx_hash)

    web3.eth.defaultAccount = agent['account_address']
    web3.personal.unlockAccount(agent['account_address'], agent['password'])

    return {'address': contract_address, 'abi': abi}


@pytest.fixture(scope='session')
def personalinfo_contract():
    deployer = eth_account['deployer']
    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'], deployer['password'])

    contract_address, abi = Contract.deploy_contract(
        'PersonalInfo', [], deployer['account_address'])

    return {'address': contract_address, 'abi': abi}


@pytest.fixture(scope='session')
def exchange_regulator_service_contract():
    deployer = eth_account['deployer']
    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'], deployer['password'])

    contract_address, abi = Contract.deploy_contract(
        'ExchangeRegulatorService', [], deployer['account_address'])

    exchange_regulator_service = Contract.get_contract('ExchangeRegulatorService', contract_address)

    web3.eth.defaultAccount = deployer['account_address']
    exchange_regulator_service.functions.register(eth_account['issuer']['account_address'], False).\
        transact({'from': deployer['account_address'], 'gas': 4000000})
    exchange_regulator_service.functions.register(eth_account['trader']['account_address'], False).\
        transact({'from': deployer['account_address'], 'gas': 4000000})

    return {'address': contract_address, 'abi': abi}


@pytest.fixture(scope='session')
def bond_exchange_contract(payment_gateway_address, personalinfo_address, exchange_regulator_service_address):
    deployer = eth_account['deployer']
    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'], deployer['password'])

    issuer = eth_account['issuer']
    web3.eth.defaultAccount = issuer['account_address']
    web3.personal.unlockAccount(issuer['account_address'], issuer['password'])

    trader = eth_account['trader']
    web3.eth.defaultAccount = trader['account_address']
    web3.personal.unlockAccount(trader['account_address'], trader['password'])

    web3.eth.defaultAccount = deployer['account_address']
    storage_address, _ = Contract.deploy_contract(
        'ExchangeStorage', [], deployer['account_address'])

    args = [
        payment_gateway_address,
        personalinfo_address,
        storage_address,
        exchange_regulator_service_address
    ]

    contract_address, abi = Contract.deploy_contract(
        'IbetStraightBondExchange', args, deployer['account_address'])

    storage = Contract.get_contract('ExchangeStorage', storage_address)
    storage.functions.upgradeVersion(contract_address).transact(
        {'from': deployer['account_address'], 'gas': 4000000}
    )

    # 取引参加者登録
    ExchangeRegulatorService = \
        Contract.get_contract('ExchangeRegulatorService', exchange_regulator_service_address)
    ExchangeRegulatorService.functions.register(issuer['account_address'], False). \
        transact({'from': deployer['account_address'], 'gas': 4000000})
    ExchangeRegulatorService.functions.register(trader['account_address'], False). \
        transact({'from': deployer['account_address'], 'gas': 4000000})

    return {'address': contract_address, 'abi': abi}


@pytest.fixture(scope='session')
def membership_exchange_contract(payment_gateway_address):
    deployer = eth_account['deployer']
    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'], deployer['password'])

    storage_address, _ = Contract.deploy_contract(
        'ExchangeStorage', [], deployer['account_address'])

    args = [
        payment_gateway_address,
        storage_address
    ]

    contract_address, abi = Contract.deploy_contract(
        'IbetMembershipExchange', args, deployer['account_address'])

    storage = Contract.get_contract('ExchangeStorage', storage_address)
    storage.functions.upgradeVersion(contract_address).transact(
        {'from': deployer['account_address'], 'gas': 4000000}
    )

    return {'address': contract_address, 'abi': abi}


@pytest.fixture(scope='session')
def coupon_exchange_contract(payment_gateway_address):
    deployer = eth_account['deployer']
    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'], deployer['password'])

    storage_address, _ = Contract.deploy_contract(
        'ExchangeStorage', [], deployer['account_address'])

    args = [
        payment_gateway_address,
        storage_address
    ]

    contract_address, abi = Contract.deploy_contract(
        'IbetCouponExchange', args, deployer['account_address'])

    storage = Contract.get_contract('ExchangeStorage', storage_address)
    storage.functions.upgradeVersion(contract_address).transact(
        {'from': deployer['account_address'], 'gas': 4000000}
    )

    return {'address': contract_address, 'abi': abi}


@pytest.fixture(scope='session')
def tokenlist_contract():
    deployer = eth_account['deployer']
    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'], deployer['password'])

    contract_address, abi = Contract.deploy_contract(
        'TokenList', [], deployer['account_address'])

    return {'address': contract_address, 'abi': abi}


@pytest.fixture(scope='session')
def shared_contract():
    payment_gateway = payment_gateway_contract()
    personal_info = personalinfo_contract()
    exchange_regulator_service = exchange_regulator_service_contract()
    bond_exchange = bond_exchange_contract(
        payment_gateway['address'],
        personal_info['address'],
        exchange_regulator_service['address']
    )
    membership_exchange = membership_exchange_contract(payment_gateway['address'])
    coupon_exchange = coupon_exchange_contract(payment_gateway['address'])
    token_list = tokenlist_contract()
    contracts = {
        'PaymentGateway': payment_gateway,
        'PersonalInfo': personal_info,
        'IbetStraightBondExchange': bond_exchange,
        'IbetMembershipExchange': membership_exchange,
        'IbetCouponExchange': coupon_exchange,
        'TokenList': token_list
    }
    return contracts


# テーブルの自動作成・自動削除
@pytest.fixture(scope='session')
def db(request):
    from app.model import Base
    Base.metadata.create_all(engine)

    def teardown():
        Base.metadata.drop_all(engine)
        return

    request.addfinalizer(teardown)
    return db_session


# セッションの作成・自動ロールバック
@pytest.fixture(scope='function')
def session(request, db):
    session = db_session()

    def teardown():
        session.rollback()

    request.addfinalizer(teardown)
    return session
