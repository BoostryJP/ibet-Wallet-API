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
import pytest
from unittest import mock
from unittest.mock import MagicMock
from importlib import reload

from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.model.db import (
    Notification,
    NotificationType
)
from app.contracts import Contract
from tests.account_config import eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="function")
def watcher_factory(session, shared_contract):
    def _watcher(cls_name):
        # Create PaymentGateway contract for each test method.
        deployer = eth_account["deployer"]
        payment_gateway_contract_address, _ = Contract.deploy_contract(
            "PaymentGateway",
            [],
            deployer["account_address"]
        )
        config.PAYMENT_GATEWAY_CONTRACT_ADDRESS = payment_gateway_contract_address

        from batch import processor_Notifications_PaymentGateway
        test_module = reload(processor_Notifications_PaymentGateway)
        cls = getattr(test_module, cls_name)
        watcher = cls()
        watcher.from_block = web3.eth.blockNumber
        return watcher, payment_gateway_contract_address

    return _watcher


class TestWatchPaymentAccountRegister:
    agent = eth_account["agent"]
    trader = eth_account["trader"]
    trader2 = eth_account["issuer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, watcher_factory, session, shared_contract):
        watcher, payment_gateway_contract_address = watcher_factory("WatchPaymentAccountRegister")

        # Register Agent Info
        payment_gateway_contract = Contract.get_contract("PaymentGateway", payment_gateway_contract_address)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.PAYMENT_ACCOUNT_REGISTER.value
        assert _notification.priority == 2
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "account_address": self.trader["account_address"],
            "agent_address": self.agent["account_address"],
        }
        assert _notification.metainfo == {}

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract):
        watcher, payment_gateway_contract_address = watcher_factory("WatchPaymentAccountRegister")

        # Register Agent Info
        payment_gateway_contract = Contract.get_contract("PaymentGateway", payment_gateway_contract_address)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader2["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
        assert _notification.notification_type == NotificationType.PAYMENT_ACCOUNT_REGISTER.value
        assert _notification.priority == 2
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "account_address": self.trader["account_address"],
            "agent_address": self.agent["account_address"],
        }
        assert _notification.metainfo == {}
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.PAYMENT_ACCOUNT_REGISTER.value
        assert _notification.priority == 2
        assert _notification.address == self.trader2["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "account_address": self.trader2["account_address"],
            "agent_address": self.agent["account_address"],
        }
        assert _notification.metainfo == {}

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract):
        watcher, _ = watcher_factory("WatchPaymentAccountRegister")

        # Not Register Agent Info
        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, _ = watcher_factory("WatchPaymentAccountRegister")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchPaymentAccountApprove:
    agent = eth_account["agent"]
    trader = eth_account["trader"]
    trader2 = eth_account["issuer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, watcher_factory, session, shared_contract):
        watcher, payment_gateway_contract_address = watcher_factory("WatchPaymentAccountApprove")

        # Register Agent Info
        payment_gateway_contract = Contract.get_contract("PaymentGateway", payment_gateway_contract_address)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Approve
        tx_hash = payment_gateway_contract.functions.approve(self.trader["account_address"]).transact(
            {"from": self.agent["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.PAYMENT_ACCOUNT_APPROVE.value
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "account_address": self.trader["account_address"],
            "agent_address": self.agent["account_address"],
        }
        assert _notification.metainfo == {}

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract):
        watcher, payment_gateway_contract_address = watcher_factory("WatchPaymentAccountApprove")

        # Register Agent Info
        payment_gateway_contract = Contract.get_contract("PaymentGateway", payment_gateway_contract_address)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader2["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Approve
        tx_hash = payment_gateway_contract.functions.approve(self.trader["account_address"]).transact(
            {"from": self.agent["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        tx_hash = payment_gateway_contract.functions.approve(self.trader2["account_address"]).transact(
            {"from": self.agent["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
        assert _notification.notification_type == NotificationType.PAYMENT_ACCOUNT_APPROVE.value
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "account_address": self.trader["account_address"],
            "agent_address": self.agent["account_address"],
        }
        assert _notification.metainfo == {}
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.PAYMENT_ACCOUNT_APPROVE.value
        assert _notification.priority == 0
        assert _notification.address == self.trader2["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "account_address": self.trader2["account_address"],
            "agent_address": self.agent["account_address"],
        }
        assert _notification.metainfo == {}

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract):
        watcher, payment_gateway_contract_address = watcher_factory("WatchPaymentAccountApprove")

        # Register Agent Info
        payment_gateway_contract = Contract.get_contract("PaymentGateway", payment_gateway_contract_address)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Not Approve
        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, _ = watcher_factory("WatchPaymentAccountApprove")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchPaymentAccountWarn:
    agent = eth_account["agent"]
    trader = eth_account["trader"]
    trader2 = eth_account["issuer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, watcher_factory, session, shared_contract):
        watcher, payment_gateway_contract_address = watcher_factory("WatchPaymentAccountWarn")

        # Register Agent Info
        payment_gateway_contract = Contract.get_contract("PaymentGateway", payment_gateway_contract_address)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Warn
        tx_hash = payment_gateway_contract.functions.warn(self.trader["account_address"]).transact(
            {"from": self.agent["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.PAYMENT_ACCOUNT_WARN.value
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "account_address": self.trader["account_address"],
            "agent_address": self.agent["account_address"],
        }
        assert _notification.metainfo == {}

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract):
        watcher, payment_gateway_contract_address = watcher_factory("WatchPaymentAccountWarn")

        # Register Agent Info
        payment_gateway_contract = Contract.get_contract("PaymentGateway", payment_gateway_contract_address)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader2["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Warn
        tx_hash = payment_gateway_contract.functions.warn(self.trader["account_address"]).transact(
            {"from": self.agent["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        tx_hash = payment_gateway_contract.functions.warn(self.trader2["account_address"]).transact(
            {"from": self.agent["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
        assert _notification.notification_type == NotificationType.PAYMENT_ACCOUNT_WARN.value
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "account_address": self.trader["account_address"],
            "agent_address": self.agent["account_address"],
        }
        assert _notification.metainfo == {}
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.PAYMENT_ACCOUNT_WARN.value
        assert _notification.priority == 0
        assert _notification.address == self.trader2["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "account_address": self.trader2["account_address"],
            "agent_address": self.agent["account_address"],
        }
        assert _notification.metainfo == {}

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract):
        watcher, payment_gateway_contract_address = watcher_factory("WatchPaymentAccountWarn")

        # Register Agent Info
        payment_gateway_contract = Contract.get_contract("PaymentGateway", payment_gateway_contract_address)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Not Warn
        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, _ = watcher_factory("WatchPaymentAccountWarn")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchPaymentAccountDisapprove:
    agent = eth_account["agent"]
    trader = eth_account["trader"]
    trader2 = eth_account["issuer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, watcher_factory, session, shared_contract):
        watcher, payment_gateway_contract_address = watcher_factory("WatchPaymentAccountDisapprove")

        # Register Agent Info
        payment_gateway_contract = Contract.get_contract("PaymentGateway", payment_gateway_contract_address)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Disapprove
        tx_hash = payment_gateway_contract.functions.disapprove(self.trader["account_address"]).transact(
            {"from": self.agent["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.PAYMENT_ACCOUNT_UNAPPROVE.value
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "account_address": self.trader["account_address"],
            "agent_address": self.agent["account_address"],
        }
        assert _notification.metainfo == {}

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract):
        watcher, payment_gateway_contract_address = watcher_factory("WatchPaymentAccountDisapprove")

        # Register Agent Info
        payment_gateway_contract = Contract.get_contract("PaymentGateway", payment_gateway_contract_address)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader2["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Disapprove
        tx_hash = payment_gateway_contract.functions.disapprove(self.trader["account_address"]).transact(
            {"from": self.agent["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        tx_hash = payment_gateway_contract.functions.disapprove(self.trader2["account_address"]).transact(
            {"from": self.agent["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
        assert _notification.notification_type == NotificationType.PAYMENT_ACCOUNT_UNAPPROVE.value
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "account_address": self.trader["account_address"],
            "agent_address": self.agent["account_address"],
        }
        assert _notification.metainfo == {}
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.PAYMENT_ACCOUNT_UNAPPROVE.value
        assert _notification.priority == 0
        assert _notification.address == self.trader2["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "account_address": self.trader2["account_address"],
            "agent_address": self.agent["account_address"],
        }
        assert _notification.metainfo == {}

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract):
        watcher, payment_gateway_contract_address = watcher_factory("WatchPaymentAccountDisapprove")

        # Register Agent Info
        payment_gateway_contract = Contract.get_contract("PaymentGateway", payment_gateway_contract_address)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Not Disapprove
        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, _ = watcher_factory("WatchPaymentAccountDisapprove")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchPaymentAccountBan:
    agent = eth_account["agent"]
    trader = eth_account["trader"]
    trader2 = eth_account["issuer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, watcher_factory, session, shared_contract):
        watcher, payment_gateway_contract_address = watcher_factory("WatchPaymentAccountBan")

        # Register Agent Info
        payment_gateway_contract = Contract.get_contract("PaymentGateway", payment_gateway_contract_address)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Disapprove
        tx_hash = payment_gateway_contract.functions.ban(self.trader["account_address"]).transact(
            {"from": self.agent["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.PAYMENT_ACCOUNT_BAN.value
        assert _notification.priority == 2
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "account_address": self.trader["account_address"],
            "agent_address": self.agent["account_address"],
        }
        assert _notification.metainfo == {}

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract):
        watcher, payment_gateway_contract_address = watcher_factory("WatchPaymentAccountBan")

        # Register Agent Info
        payment_gateway_contract = Contract.get_contract("PaymentGateway", payment_gateway_contract_address)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader2["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Ban
        tx_hash = payment_gateway_contract.functions.ban(self.trader["account_address"]).transact(
            {"from": self.agent["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        tx_hash = payment_gateway_contract.functions.ban(self.trader2["account_address"]).transact(
            {"from": self.agent["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
        assert _notification.notification_type == NotificationType.PAYMENT_ACCOUNT_BAN.value
        assert _notification.priority == 2
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "account_address": self.trader["account_address"],
            "agent_address": self.agent["account_address"],
        }
        assert _notification.metainfo == {}
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.PAYMENT_ACCOUNT_BAN.value
        assert _notification.priority == 2
        assert _notification.address == self.trader2["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "account_address": self.trader2["account_address"],
            "agent_address": self.agent["account_address"],
        }
        assert _notification.metainfo == {}

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract):
        watcher, payment_gateway_contract_address = watcher_factory("WatchPaymentAccountBan")

        # Register Agent Info
        payment_gateway_contract = Contract.get_contract("PaymentGateway", payment_gateway_contract_address)
        tx_hash = payment_gateway_contract.functions.register(self.agent["account_address"], "encrypt_data").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Not Ban
        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, _ = watcher_factory("WatchPaymentAccountBan")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None
