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
from typing import TypedDict

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session
from web3 import Web3
from web3.eth import Contract as Web3Contract
from web3.middleware import geth_poa_middleware
from web3.types import ChecksumAddress, RPCEndpoint

from app import config
from app.contracts import Contract
from app.database import (
    AsyncSessionLocal,
    SessionLocal,
    async_engine,
    db_async_session,
    db_session,
    engine,
)
from app.main import app
from app.model.db import Notification
from app.model.db.base import Base
from app.utils.web3_utils import AsyncFailOverHTTPProvider
from tests.account_config import eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class DeployedContract(TypedDict):
    address: str
    abi: dict


class SharedContract(TypedDict):
    PaymentGateway: DeployedContract
    PersonalInfo: DeployedContract
    IbetShareExchange: DeployedContract
    IbetStraightBondExchange: DeployedContract
    IbetMembershipExchange: DeployedContract
    IbetCouponExchange: DeployedContract
    TokenList: DeployedContract
    E2EMessaging: Web3Contract
    IbetEscrow: Web3Contract
    IbetSecurityTokenEscrow: Web3Contract


class UnitTestAccount(TypedDict):
    account_address: ChecksumAddress
    password: str


@pytest.fixture(scope="session")
def client() -> TestClient:
    AsyncFailOverHTTPProvider.is_default = None

    client = TestClient(app)
    return client


@pytest.fixture(scope="session")
def payment_gateway_contract() -> DeployedContract:
    deployer = eth_account["deployer"]
    agent = eth_account["agent"]

    web3.eth.default_account = deployer["account_address"]

    contract_address, abi = Contract.deploy_contract(
        "PaymentGateway", [], deployer["account_address"]
    )
    contract = Contract.get_contract("PaymentGateway", contract_address)
    contract.functions.addAgent(agent["account_address"]).transact(
        {"from": deployer["account_address"]}
    )

    return {"address": contract_address, "abi": abi}


@pytest.fixture(scope="session")
def personalinfo_contract() -> DeployedContract:
    deployer = eth_account["deployer"]
    web3.eth.default_account = deployer["account_address"]

    contract_address, abi = Contract.deploy_contract(
        "PersonalInfo", [], deployer["account_address"]
    )

    return {"address": contract_address, "abi": abi}


@pytest.fixture(scope="session")
def tokenlist_contract() -> DeployedContract:
    deployer = eth_account["deployer"]

    web3.eth.default_account = deployer["account_address"]

    contract_address, abi = Contract.deploy_contract(
        "TokenList", [], deployer["account_address"]
    )

    return {"address": contract_address, "abi": abi}


@pytest.fixture(scope="session")
def e2e_messaging_contract() -> Web3Contract:
    deployer = eth_account["deployer"]
    web3.eth.default_account = deployer["account_address"]
    contract_address, abi = Contract.deploy_contract(
        contract_name="E2EMessaging", args=[], deployer=deployer["account_address"]
    )
    _e2e_messaging_contract: Web3Contract = Contract.get_contract(
        contract_name="E2EMessaging", address=contract_address
    )
    return _e2e_messaging_contract


@pytest.fixture(scope="session")
def ibet_escrow_contract() -> Web3Contract:
    deployer = eth_account["deployer"]["account_address"]

    web3.eth.default_account = deployer

    storage_address, _ = Contract.deploy_contract(
        contract_name="EscrowStorage", args=[], deployer=deployer
    )

    contract_address, abi = Contract.deploy_contract(
        contract_name="IbetEscrow", args=[storage_address], deployer=deployer
    )

    storage = Contract.get_contract(
        contract_name="EscrowStorage", address=storage_address
    )
    storage.functions.upgradeVersion(contract_address).transact({"from": deployer})

    _ibet_escrow_contract: Web3Contract = Contract.get_contract(
        contract_name="IbetEscrow", address=contract_address
    )
    return _ibet_escrow_contract


@pytest.fixture(scope="session")
def ibet_st_escrow_contract() -> Web3Contract:
    deployer = eth_account["deployer"]["account_address"]

    storage_address, _ = Contract.deploy_contract(
        contract_name="EscrowStorage", args=[], deployer=deployer
    )
    contract_address, abi = Contract.deploy_contract(
        contract_name="IbetSecurityTokenEscrow",
        args=[storage_address],
        deployer=deployer,
    )

    storage = Contract.get_contract(
        contract_name="EscrowStorage", address=storage_address
    )
    storage.functions.upgradeVersion(contract_address).transact({"from": deployer})

    _ibet_st_escrow_contract: Web3Contract = Contract.get_contract(
        contract_name="IbetSecurityTokenEscrow", address=contract_address
    )
    return _ibet_st_escrow_contract


@pytest.fixture(scope="session")
def shared_contract(
    payment_gateway_contract,
    personalinfo_contract,
    tokenlist_contract,
    e2e_messaging_contract,
    ibet_escrow_contract,
    ibet_st_escrow_contract,
) -> SharedContract:
    return {
        "PaymentGateway": payment_gateway_contract,
        "PersonalInfo": personalinfo_contract,
        "IbetShareExchange": ibet_exchange_contract(
            payment_gateway_contract["address"]
        ),
        "IbetStraightBondExchange": ibet_exchange_contract(
            payment_gateway_contract["address"]
        ),
        "IbetMembershipExchange": ibet_exchange_contract(
            payment_gateway_contract["address"]
        ),
        "IbetCouponExchange": ibet_exchange_contract(
            payment_gateway_contract["address"]
        ),
        "TokenList": tokenlist_contract,
        "E2EMessaging": e2e_messaging_contract,
        "IbetEscrow": ibet_escrow_contract,
        "IbetSecurityTokenEscrow": ibet_st_escrow_contract,
    }


@pytest_asyncio.fixture(scope="session")
async def async_db_engine():
    if async_engine.name != "mysql":
        async with async_engine.begin() as conn:
            # NOTE:MySQLの場合はSEQ機能が利用できない
            await conn.run_sync(Notification.notification_id_seq.create)

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_engine

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# テーブルの自動作成・自動削除
@pytest.fixture(scope="session")
def db_engine():
    from app.model.db.base import Base

    if engine.name != "mysql":
        # NOTE:MySQLの場合はSEQ機能が利用できない
        Notification.notification_id_seq.create(bind=engine)

    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)


# テーブル上のレコード削除
@pytest_asyncio.fixture(scope="function")
async def async_db(async_db_engine):
    # Create DB session
    db = AsyncSessionLocal()

    def override_inject_db_session():
        return db

    # Replace target API's dependency DB session.
    app.dependency_overrides[db_async_session] = override_inject_db_session

    async with db as session:
        await session.begin()
        yield session
        await session.rollback()

        # Remove DB tables
        if engine.name == "mysql":
            await session.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            for table in Base.metadata.sorted_tables:
                await session.execute(text(f"TRUNCATE TABLE `{table.name}`;"))
                if table.autoincrement_column is not None:
                    await session.execute(
                        text(f"ALTER TABLE `{table.name}` auto_increment = 1;")
                    )
            await session.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        else:
            await session.begin()
            for table in Base.metadata.sorted_tables:
                await session.execute(
                    text(f'ALTER TABLE "{table.name}" DISABLE TRIGGER ALL;')
                )
                await session.execute(
                    text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE;')
                )
                if table.autoincrement_column is not None:
                    await session.execute(
                        text(
                            f"ALTER SEQUENCE {table.name}_{table.autoincrement_column.name}_seq RESTART WITH 1;"
                        )
                    )
                await session.execute(
                    text(f'ALTER TABLE "{table.name}" ENABLE TRIGGER ALL;')
                )
            await session.commit()
    await db.close()

    app.dependency_overrides[db_async_session] = db_async_session


# テーブルの自動作成・自動削除
@pytest.fixture(scope="function")
def db(db_engine):
    # Create DB session
    db = SessionLocal()

    def override_inject_db_session():
        return db

    # Replace target API's dependency DB session.
    app.dependency_overrides[db_session] = override_inject_db_session

    yield db

    # Remove DB tables
    db.rollback()
    if engine.name == "mysql":
        db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        for table in Base.metadata.sorted_tables:
            db.execute(text(f"TRUNCATE TABLE `{table.name}`;"))
            if table.autoincrement_column is not None:
                db.execute(text(f"ALTER TABLE `{table.name}` auto_increment = 1;"))
        db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    else:
        db.begin()
        for table in Base.metadata.sorted_tables:
            db.execute(text(f'ALTER TABLE "{table.name}" DISABLE TRIGGER ALL;'))
            db.execute(text(f'TRUNCATE TABLE "{table.name}";'))
            if table.autoincrement_column is not None:
                db.execute(
                    text(
                        f"ALTER SEQUENCE {table.name}_{table.autoincrement_column.name}_seq RESTART WITH 1;"
                    )
                )
            db.execute(text(f'ALTER TABLE "{table.name}" ENABLE TRIGGER ALL;'))
        db.commit()
    db.close()

    app.dependency_overrides[db_session] = db_session


# ブロックナンバーの保存・復元
@pytest.fixture(scope="function")
def block_number(request):
    evm_snapshot = web3.provider.make_request(RPCEndpoint("evm_snapshot"), [])

    def teardown():
        web3.provider.make_request(
            RPCEndpoint("evm_revert"),
            [
                int(evm_snapshot["result"], 16),
            ],
        )

    request.addfinalizer(teardown)


# セッションの作成・自動ロールバック
@pytest.fixture(scope="function")
def session(db: Session):
    yield db


@pytest_asyncio.fixture(scope="function")
async def async_session(async_db):
    yield async_db


# 発行企業リストのモック
@pytest.fixture(scope="function")
def mocked_company_list(request):
    company_list = json.load(open("data/company_list.json", "r"))

    mocked_company_list = [
        {
            "address": eth_account["issuer"]["account_address"],
            "corporate_name": "株式会社DEMO",
            "rsa_publickey": "-----BEGIN PUBLIC KEY-----\nMIIFIjANBgkqhkiG9w0BAQEFAAOCBQ8AMIIFCgKCBQEAtiBUQ2vdYvIqnCdUzKIC\np7jIYVtJy8KGniy6ktE0DTcYG70pFYkGDyI043meSB6Lkk0rNWaKBn3wyz4lx2oX\n3JySFyXR4vE4DNTEKS0htImO4RuK4M50v7LOfB8VphXzu9JkdVuN8LuMx6L6dhsd\nTN/aUvXULvjOy9AJekl24s44w4BgEfGj/uBYNAmiNmpM3lnIdJOg1T+4aEShHyVN\n98dv1DZ1Hh0YhMmqHqRGIzAQ6pKoly2xSVEmwBV4l2O3XEZ8ErVNgHdi6BRQrIBl\n+zQn5TysSGv5TIO1ahztUIygrzX7aEa+QnF1ROBBJ8yBW0VjjKI2Oh3wDT8ROaWb\ntB7gYQlMX9St/HJvGKaDKPDGurMFsEZeeD9Y4GWlFFkQplKIC3Kr4u6TIxcAZyG3\ntIz1IZomm/Lh9eiFiAbOMLYPdPCzh1A6uCRoJuqrNXYbE2egpLsKSkEe4VAcdaPo\nVuOXLpbDaew0cvXQR5IklHGGPPGVqQV1cmJWIqF5b1bzqziu2No+TLZceUd3N9Eh\nQIYVG4rbX2I/x2/WFeG5RHl9Zc/iSUomUqpnGY3ved61smb7uklF/7ueyj8TIm7O\ncJxhYjj+szXxV2RJyxLvSPzloQ4GDI9wd0zlya2CoYgAONJ7wm82b1LrLLhfpns2\ndSsN8htFX83p0dNn6f8ssKgA3rFbFFnBTQyFxlHO/An4qZflXtk1GsEc56g3mJFp\nrFANLpyum5mkHo9TbkL3K4mRGM1DGcLXWJwFUjDxS/OvjzDXw2dNiyrPeClvTpAb\npFfw/zqVd7ZrnTFg26bpUmM8flc6IRji49veOOMM7jMJN7mmu/pLd/Pg22oez23G\n6QsPDvqqXgjyg1NGo7natX6gyAYMpWZWOHj+Y2lffzcJYUo+wPFt/xNkAuCcDZem\nAiicfsGfniE67G1nfmwkykVwk9rTFCO8SnFei8wMpEAMYETYOS4ldavLfhY6mrF1\nItA5mlkMI84v3ROqPSp3s6F9oGYzPi5zMcgc67wIFGgaPb6i8+puui6BUbj83qOU\nKuKoQAGe9+NRnAkWSpbX07cX6XkPieTkBHEYfGaQTQOnsSs++PIk3kH5Arfjk0R5\nu1ZluzVdOXUn8D5WPfh9UFzqyXzo1HOIHxDkPejpPlNzO1w6qVQC+UiR/R2iug/U\n7StoLz476tQOwbfmnzUA6AbOKjRgN5laRoBac4BbGPJisGysOBruL7lgrw0XVtnh\nknChXfSYezxz/EtiGmO40HKAGudHDkz4gmPDkF4wlIyfDbQZOnNohz4zuOjr9Yi/\nJQVpqKxug2LXyJp38UaxL1LIT6ZyJSsaSrKAB21tsYAbksyPCVS6L6jkz8lsnlYg\nLj7lj6HQcbN8WO72+Z8Ddj/cPXJwEq4OTbtkPiPdcvSZjcBR9f3TmrQjDG0ROspt\nI/m4KhWfm7ed+eZKA1IqygFRyi6i0w6p+VbeBNgXqAiQI5GkDHqAiqv4OVyZoQB8\neunu5qM49r6bw6DJCqlg6lZDCptdKWtNBo9zgEegrJ/3oVI7x0kE7KQ4gPo5uY7j\nvBqGwjw0fIGPjrP/JKIQqGvm/ETwlfPwVbmCsvEHbqEY+6f84TnmolgjPMnbar6Q\nSDuvqVApY7yNCEue5X0pLRAd+287VBVVvsOsZVOSj02w4PGIlsg2Y33BbcpwESzr\n4McG/dPyTRFv9mYtFPpyV50CAwEAAQ==\n-----END PUBLIC KEY-----",
            "homepage": "https://www.aaaa.com/jp/",
        },
        {
            "address": eth_account["deployer"]["account_address"],
            "corporate_name": "株式会社DEMO",
            "rsa_publickey": "-----BEGIN PUBLIC KEY-----\nMIIFIjANBgkqhkiG9w0BAQEFAAOCBQ8AMIIFCgKCBQEAtiBUQ2vdYvIqnCdUzKIC\np7jIYVtJy8KGniy6ktE0DTcYG70pFYkGDyI043meSB6Lkk0rNWaKBn3wyz4lx2oX\n3JySFyXR4vE4DNTEKS0htImO4RuK4M50v7LOfB8VphXzu9JkdVuN8LuMx6L6dhsd\nTN/aUvXULvjOy9AJekl24s44w4BgEfGj/uBYNAmiNmpM3lnIdJOg1T+4aEShHyVN\n98dv1DZ1Hh0YhMmqHqRGIzAQ6pKoly2xSVEmwBV4l2O3XEZ8ErVNgHdi6BRQrIBl\n+zQn5TysSGv5TIO1ahztUIygrzX7aEa+QnF1ROBBJ8yBW0VjjKI2Oh3wDT8ROaWb\ntB7gYQlMX9St/HJvGKaDKPDGurMFsEZeeD9Y4GWlFFkQplKIC3Kr4u6TIxcAZyG3\ntIz1IZomm/Lh9eiFiAbOMLYPdPCzh1A6uCRoJuqrNXYbE2egpLsKSkEe4VAcdaPo\nVuOXLpbDaew0cvXQR5IklHGGPPGVqQV1cmJWIqF5b1bzqziu2No+TLZceUd3N9Eh\nQIYVG4rbX2I/x2/WFeG5RHl9Zc/iSUomUqpnGY3ved61smb7uklF/7ueyj8TIm7O\ncJxhYjj+szXxV2RJyxLvSPzloQ4GDI9wd0zlya2CoYgAONJ7wm82b1LrLLhfpns2\ndSsN8htFX83p0dNn6f8ssKgA3rFbFFnBTQyFxlHO/An4qZflXtk1GsEc56g3mJFp\nrFANLpyum5mkHo9TbkL3K4mRGM1DGcLXWJwFUjDxS/OvjzDXw2dNiyrPeClvTpAb\npFfw/zqVd7ZrnTFg26bpUmM8flc6IRji49veOOMM7jMJN7mmu/pLd/Pg22oez23G\n6QsPDvqqXgjyg1NGo7natX6gyAYMpWZWOHj+Y2lffzcJYUo+wPFt/xNkAuCcDZem\nAiicfsGfniE67G1nfmwkykVwk9rTFCO8SnFei8wMpEAMYETYOS4ldavLfhY6mrF1\nItA5mlkMI84v3ROqPSp3s6F9oGYzPi5zMcgc67wIFGgaPb6i8+puui6BUbj83qOU\nKuKoQAGe9+NRnAkWSpbX07cX6XkPieTkBHEYfGaQTQOnsSs++PIk3kH5Arfjk0R5\nu1ZluzVdOXUn8D5WPfh9UFzqyXzo1HOIHxDkPejpPlNzO1w6qVQC+UiR/R2iug/U\n7StoLz476tQOwbfmnzUA6AbOKjRgN5laRoBac4BbGPJisGysOBruL7lgrw0XVtnh\nknChXfSYezxz/EtiGmO40HKAGudHDkz4gmPDkF4wlIyfDbQZOnNohz4zuOjr9Yi/\nJQVpqKxug2LXyJp38UaxL1LIT6ZyJSsaSrKAB21tsYAbksyPCVS6L6jkz8lsnlYg\nLj7lj6HQcbN8WO72+Z8Ddj/cPXJwEq4OTbtkPiPdcvSZjcBR9f3TmrQjDG0ROspt\nI/m4KhWfm7ed+eZKA1IqygFRyi6i0w6p+VbeBNgXqAiQI5GkDHqAiqv4OVyZoQB8\neunu5qM49r6bw6DJCqlg6lZDCptdKWtNBo9zgEegrJ/3oVI7x0kE7KQ4gPo5uY7j\nvBqGwjw0fIGPjrP/JKIQqGvm/ETwlfPwVbmCsvEHbqEY+6f84TnmolgjPMnbar6Q\nSDuvqVApY7yNCEue5X0pLRAd+287VBVVvsOsZVOSj02w4PGIlsg2Y33BbcpwESzr\n4McG/dPyTRFv9mYtFPpyV50CAwEAAQ==\n-----END PUBLIC KEY-----",
            "homepage": "https://www.aaaa.com/jp/",
        },
        {
            "address": eth_account["agent"]["account_address"],
            "corporate_name": "株式会社DEMO",
            "rsa_publickey": "-----BEGIN PUBLIC KEY-----\nMIIFIjANBgkqhkiG9w0BAQEFAAOCBQ8AMIIFCgKCBQEAtiBUQ2vdYvIqnCdUzKIC\np7jIYVtJy8KGniy6ktE0DTcYG70pFYkGDyI043meSB6Lkk0rNWaKBn3wyz4lx2oX\n3JySFyXR4vE4DNTEKS0htImO4RuK4M50v7LOfB8VphXzu9JkdVuN8LuMx6L6dhsd\nTN/aUvXULvjOy9AJekl24s44w4BgEfGj/uBYNAmiNmpM3lnIdJOg1T+4aEShHyVN\n98dv1DZ1Hh0YhMmqHqRGIzAQ6pKoly2xSVEmwBV4l2O3XEZ8ErVNgHdi6BRQrIBl\n+zQn5TysSGv5TIO1ahztUIygrzX7aEa+QnF1ROBBJ8yBW0VjjKI2Oh3wDT8ROaWb\ntB7gYQlMX9St/HJvGKaDKPDGurMFsEZeeD9Y4GWlFFkQplKIC3Kr4u6TIxcAZyG3\ntIz1IZomm/Lh9eiFiAbOMLYPdPCzh1A6uCRoJuqrNXYbE2egpLsKSkEe4VAcdaPo\nVuOXLpbDaew0cvXQR5IklHGGPPGVqQV1cmJWIqF5b1bzqziu2No+TLZceUd3N9Eh\nQIYVG4rbX2I/x2/WFeG5RHl9Zc/iSUomUqpnGY3ved61smb7uklF/7ueyj8TIm7O\ncJxhYjj+szXxV2RJyxLvSPzloQ4GDI9wd0zlya2CoYgAONJ7wm82b1LrLLhfpns2\ndSsN8htFX83p0dNn6f8ssKgA3rFbFFnBTQyFxlHO/An4qZflXtk1GsEc56g3mJFp\nrFANLpyum5mkHo9TbkL3K4mRGM1DGcLXWJwFUjDxS/OvjzDXw2dNiyrPeClvTpAb\npFfw/zqVd7ZrnTFg26bpUmM8flc6IRji49veOOMM7jMJN7mmu/pLd/Pg22oez23G\n6QsPDvqqXgjyg1NGo7natX6gyAYMpWZWOHj+Y2lffzcJYUo+wPFt/xNkAuCcDZem\nAiicfsGfniE67G1nfmwkykVwk9rTFCO8SnFei8wMpEAMYETYOS4ldavLfhY6mrF1\nItA5mlkMI84v3ROqPSp3s6F9oGYzPi5zMcgc67wIFGgaPb6i8+puui6BUbj83qOU\nKuKoQAGe9+NRnAkWSpbX07cX6XkPieTkBHEYfGaQTQOnsSs++PIk3kH5Arfjk0R5\nu1ZluzVdOXUn8D5WPfh9UFzqyXzo1HOIHxDkPejpPlNzO1w6qVQC+UiR/R2iug/U\n7StoLz476tQOwbfmnzUA6AbOKjRgN5laRoBac4BbGPJisGysOBruL7lgrw0XVtnh\nknChXfSYezxz/EtiGmO40HKAGudHDkz4gmPDkF4wlIyfDbQZOnNohz4zuOjr9Yi/\nJQVpqKxug2LXyJp38UaxL1LIT6ZyJSsaSrKAB21tsYAbksyPCVS6L6jkz8lsnlYg\nLj7lj6HQcbN8WO72+Z8Ddj/cPXJwEq4OTbtkPiPdcvSZjcBR9f3TmrQjDG0ROspt\nI/m4KhWfm7ed+eZKA1IqygFRyi6i0w6p+VbeBNgXqAiQI5GkDHqAiqv4OVyZoQB8\neunu5qM49r6bw6DJCqlg6lZDCptdKWtNBo9zgEegrJ/3oVI7x0kE7KQ4gPo5uY7j\nvBqGwjw0fIGPjrP/JKIQqGvm/ETwlfPwVbmCsvEHbqEY+6f84TnmolgjPMnbar6Q\nSDuvqVApY7yNCEue5X0pLRAd+287VBVVvsOsZVOSj02w4PGIlsg2Y33BbcpwESzr\n4McG/dPyTRFv9mYtFPpyV50CAwEAAQ==\n-----END PUBLIC KEY-----",
            "homepage": None,
        },
    ]
    with open("data/company_list.json", "w") as f:
        json.dump(mocked_company_list, f, ensure_ascii=False, indent=4)

    def teardown():
        with open("data/company_list.json", "w") as f:
            json.dump(company_list, f, ensure_ascii=False, indent=4)

    request.addfinalizer(teardown)
    return mocked_company_list


def ibet_exchange_contract(payment_gateway_address) -> DeployedContract:
    deployer = eth_account["deployer"]

    web3.eth.default_account = deployer["account_address"]

    storage_address, _ = Contract.deploy_contract(
        "ExchangeStorage", [], deployer["account_address"]
    )

    args = [
        payment_gateway_address,
        storage_address,
    ]

    contract_address, abi = Contract.deploy_contract(
        "IbetExchange", args, deployer["account_address"]
    )

    storage = Contract.get_contract("ExchangeStorage", storage_address)
    storage.functions.upgradeVersion(contract_address).transact(
        {"from": deployer["account_address"]}
    )

    return {"address": contract_address, "abi": abi}
