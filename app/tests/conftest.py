# -*- coding: utf-8 -*-
import json

import pytest
from falcon import testing

from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.main import App
from app.middleware import JSONTranslator, DatabaseSessionManager
from app.database import db_session, init_session, engine
from app import config
from app.contracts import Contract

from .account_config import eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope='session')
def client():
    config.DB_AUTOCOMMIT = False

    init_session()
    middleware = [JSONTranslator(), DatabaseSessionManager(db_session)]
    return testing.TestClient(App(middleware=middleware))


@pytest.fixture(scope='session')
def payment_gateway_contract():
    deployer = eth_account['deployer']
    agent = eth_account['agent']

    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'], deployer['password'])

    contract_address, abi = Contract.deploy_contract(
        'PaymentGateway', [], deployer['account_address'])

    contract = Contract.get_contract('PaymentGateway', contract_address)
    tx_hash = contract.functions.addAgent(agent['account_address']).transact(
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
def otc_exchange_contract(payment_gateway_address, personalinfo_address, exchange_regulator_service_address):
    deployer = eth_account['deployer']
    web3.eth.defaultAccount = deployer['account_address']
    web3.personal.unlockAccount(deployer['account_address'], deployer['password'])

    storage_address, _ = Contract.deploy_contract(
        'OTCExchangeStorage', [], deployer['account_address'])

    args = [
        payment_gateway_address,
        personalinfo_address,
        storage_address,
        exchange_regulator_service_address
    ]

    contract_address, abi = Contract.deploy_contract(
        'IbetOTCExchange', args, deployer['account_address'])

    storage = Contract.get_contract('OTCExchangeStorage', storage_address)
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
    otc_exchange = otc_exchange_contract(
        payment_gateway['address'],
        personal_info['address'],
        exchange_regulator_service['address']
    )
    token_list = tokenlist_contract()
    contracts = {
        'PaymentGateway': payment_gateway,
        'PersonalInfo': personal_info,
        'IbetStraightBondExchange': bond_exchange,
        'IbetMembershipExchange': membership_exchange,
        'IbetCouponExchange': coupon_exchange,
        'TokenList': token_list,
        'IbetOTCExchange': otc_exchange
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


# 発行企業リストのモック
@pytest.fixture(scope='function')
def mocked_company_list(request):
    company_list = json.load(open('data/company_list.json', 'r'))

    mocked_company_list = [
        {
            "address": eth_account['issuer']['account_address'],
            "corporate_name": "株式会社DEMO",
            "rsa_publickey": "-----BEGIN PUBLIC KEY-----\nMIIFIjANBgkqhkiG9w0BAQEFAAOCBQ8AMIIFCgKCBQEAtiBUQ2vdYvIqnCdUzKIC\np7jIYVtJy8KGniy6ktE0DTcYG70pFYkGDyI043meSB6Lkk0rNWaKBn3wyz4lx2oX\n3JySFyXR4vE4DNTEKS0htImO4RuK4M50v7LOfB8VphXzu9JkdVuN8LuMx6L6dhsd\nTN/aUvXULvjOy9AJekl24s44w4BgEfGj/uBYNAmiNmpM3lnIdJOg1T+4aEShHyVN\n98dv1DZ1Hh0YhMmqHqRGIzAQ6pKoly2xSVEmwBV4l2O3XEZ8ErVNgHdi6BRQrIBl\n+zQn5TysSGv5TIO1ahztUIygrzX7aEa+QnF1ROBBJ8yBW0VjjKI2Oh3wDT8ROaWb\ntB7gYQlMX9St/HJvGKaDKPDGurMFsEZeeD9Y4GWlFFkQplKIC3Kr4u6TIxcAZyG3\ntIz1IZomm/Lh9eiFiAbOMLYPdPCzh1A6uCRoJuqrNXYbE2egpLsKSkEe4VAcdaPo\nVuOXLpbDaew0cvXQR5IklHGGPPGVqQV1cmJWIqF5b1bzqziu2No+TLZceUd3N9Eh\nQIYVG4rbX2I/x2/WFeG5RHl9Zc/iSUomUqpnGY3ved61smb7uklF/7ueyj8TIm7O\ncJxhYjj+szXxV2RJyxLvSPzloQ4GDI9wd0zlya2CoYgAONJ7wm82b1LrLLhfpns2\ndSsN8htFX83p0dNn6f8ssKgA3rFbFFnBTQyFxlHO/An4qZflXtk1GsEc56g3mJFp\nrFANLpyum5mkHo9TbkL3K4mRGM1DGcLXWJwFUjDxS/OvjzDXw2dNiyrPeClvTpAb\npFfw/zqVd7ZrnTFg26bpUmM8flc6IRji49veOOMM7jMJN7mmu/pLd/Pg22oez23G\n6QsPDvqqXgjyg1NGo7natX6gyAYMpWZWOHj+Y2lffzcJYUo+wPFt/xNkAuCcDZem\nAiicfsGfniE67G1nfmwkykVwk9rTFCO8SnFei8wMpEAMYETYOS4ldavLfhY6mrF1\nItA5mlkMI84v3ROqPSp3s6F9oGYzPi5zMcgc67wIFGgaPb6i8+puui6BUbj83qOU\nKuKoQAGe9+NRnAkWSpbX07cX6XkPieTkBHEYfGaQTQOnsSs++PIk3kH5Arfjk0R5\nu1ZluzVdOXUn8D5WPfh9UFzqyXzo1HOIHxDkPejpPlNzO1w6qVQC+UiR/R2iug/U\n7StoLz476tQOwbfmnzUA6AbOKjRgN5laRoBac4BbGPJisGysOBruL7lgrw0XVtnh\nknChXfSYezxz/EtiGmO40HKAGudHDkz4gmPDkF4wlIyfDbQZOnNohz4zuOjr9Yi/\nJQVpqKxug2LXyJp38UaxL1LIT6ZyJSsaSrKAB21tsYAbksyPCVS6L6jkz8lsnlYg\nLj7lj6HQcbN8WO72+Z8Ddj/cPXJwEq4OTbtkPiPdcvSZjcBR9f3TmrQjDG0ROspt\nI/m4KhWfm7ed+eZKA1IqygFRyi6i0w6p+VbeBNgXqAiQI5GkDHqAiqv4OVyZoQB8\neunu5qM49r6bw6DJCqlg6lZDCptdKWtNBo9zgEegrJ/3oVI7x0kE7KQ4gPo5uY7j\nvBqGwjw0fIGPjrP/JKIQqGvm/ETwlfPwVbmCsvEHbqEY+6f84TnmolgjPMnbar6Q\nSDuvqVApY7yNCEue5X0pLRAd+287VBVVvsOsZVOSj02w4PGIlsg2Y33BbcpwESzr\n4McG/dPyTRFv9mYtFPpyV50CAwEAAQ==\n-----END PUBLIC KEY-----",
            "homepage": "https://www.aaaa.com/jp/"
        },
        {
            "address": eth_account['deployer']['account_address'],
            "corporate_name": "株式会社DEMO",
            "rsa_publickey": "-----BEGIN PUBLIC KEY-----\nMIIFIjANBgkqhkiG9w0BAQEFAAOCBQ8AMIIFCgKCBQEAtiBUQ2vdYvIqnCdUzKIC\np7jIYVtJy8KGniy6ktE0DTcYG70pFYkGDyI043meSB6Lkk0rNWaKBn3wyz4lx2oX\n3JySFyXR4vE4DNTEKS0htImO4RuK4M50v7LOfB8VphXzu9JkdVuN8LuMx6L6dhsd\nTN/aUvXULvjOy9AJekl24s44w4BgEfGj/uBYNAmiNmpM3lnIdJOg1T+4aEShHyVN\n98dv1DZ1Hh0YhMmqHqRGIzAQ6pKoly2xSVEmwBV4l2O3XEZ8ErVNgHdi6BRQrIBl\n+zQn5TysSGv5TIO1ahztUIygrzX7aEa+QnF1ROBBJ8yBW0VjjKI2Oh3wDT8ROaWb\ntB7gYQlMX9St/HJvGKaDKPDGurMFsEZeeD9Y4GWlFFkQplKIC3Kr4u6TIxcAZyG3\ntIz1IZomm/Lh9eiFiAbOMLYPdPCzh1A6uCRoJuqrNXYbE2egpLsKSkEe4VAcdaPo\nVuOXLpbDaew0cvXQR5IklHGGPPGVqQV1cmJWIqF5b1bzqziu2No+TLZceUd3N9Eh\nQIYVG4rbX2I/x2/WFeG5RHl9Zc/iSUomUqpnGY3ved61smb7uklF/7ueyj8TIm7O\ncJxhYjj+szXxV2RJyxLvSPzloQ4GDI9wd0zlya2CoYgAONJ7wm82b1LrLLhfpns2\ndSsN8htFX83p0dNn6f8ssKgA3rFbFFnBTQyFxlHO/An4qZflXtk1GsEc56g3mJFp\nrFANLpyum5mkHo9TbkL3K4mRGM1DGcLXWJwFUjDxS/OvjzDXw2dNiyrPeClvTpAb\npFfw/zqVd7ZrnTFg26bpUmM8flc6IRji49veOOMM7jMJN7mmu/pLd/Pg22oez23G\n6QsPDvqqXgjyg1NGo7natX6gyAYMpWZWOHj+Y2lffzcJYUo+wPFt/xNkAuCcDZem\nAiicfsGfniE67G1nfmwkykVwk9rTFCO8SnFei8wMpEAMYETYOS4ldavLfhY6mrF1\nItA5mlkMI84v3ROqPSp3s6F9oGYzPi5zMcgc67wIFGgaPb6i8+puui6BUbj83qOU\nKuKoQAGe9+NRnAkWSpbX07cX6XkPieTkBHEYfGaQTQOnsSs++PIk3kH5Arfjk0R5\nu1ZluzVdOXUn8D5WPfh9UFzqyXzo1HOIHxDkPejpPlNzO1w6qVQC+UiR/R2iug/U\n7StoLz476tQOwbfmnzUA6AbOKjRgN5laRoBac4BbGPJisGysOBruL7lgrw0XVtnh\nknChXfSYezxz/EtiGmO40HKAGudHDkz4gmPDkF4wlIyfDbQZOnNohz4zuOjr9Yi/\nJQVpqKxug2LXyJp38UaxL1LIT6ZyJSsaSrKAB21tsYAbksyPCVS6L6jkz8lsnlYg\nLj7lj6HQcbN8WO72+Z8Ddj/cPXJwEq4OTbtkPiPdcvSZjcBR9f3TmrQjDG0ROspt\nI/m4KhWfm7ed+eZKA1IqygFRyi6i0w6p+VbeBNgXqAiQI5GkDHqAiqv4OVyZoQB8\neunu5qM49r6bw6DJCqlg6lZDCptdKWtNBo9zgEegrJ/3oVI7x0kE7KQ4gPo5uY7j\nvBqGwjw0fIGPjrP/JKIQqGvm/ETwlfPwVbmCsvEHbqEY+6f84TnmolgjPMnbar6Q\nSDuvqVApY7yNCEue5X0pLRAd+287VBVVvsOsZVOSj02w4PGIlsg2Y33BbcpwESzr\n4McG/dPyTRFv9mYtFPpyV50CAwEAAQ==\n-----END PUBLIC KEY-----",
            "homepage": "https://www.aaaa.com/jp/"
        }
    ]
    with open('data/company_list.json', 'w') as f:
        json.dump(mocked_company_list, f, ensure_ascii=False, indent=4)

    def teardown():
        with open('data/company_list.json', 'w') as f:
            json.dump(company_list, f, ensure_ascii=False, indent=4)

    request.addfinalizer(teardown)
    return mocked_company_list
