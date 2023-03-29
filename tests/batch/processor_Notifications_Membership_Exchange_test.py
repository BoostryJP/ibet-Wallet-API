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
from importlib import reload
from unittest import mock
from unittest.mock import MagicMock

import pytest
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.types import RPCEndpoint

from app import config
from app.model.db import Notification, NotificationBlockNumber, NotificationType
from tests.account_config import eth_account
from tests.conftest import ibet_exchange_contract
from tests.contract_modules import (
    cancel_agreement,
    cancel_order,
    confirm_agreement,
    force_cancel_order,
    make_sell,
    membership_issue,
    membership_register_list,
    membership_transfer_to_exchange,
    take_buy,
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="function")
def watcher_factory(session, shared_contract):
    def _watcher(cls_name):
        # Create exchange contract for each test method.
        membership_exchange = ibet_exchange_contract(
            shared_contract["PaymentGateway"]["address"]
        )

        config.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = membership_exchange[
            "address"
        ]

        from batch import processor_Notifications_Membership_Exchange

        test_module = reload(processor_Notifications_Membership_Exchange)
        test_module.db_session = session

        cls = getattr(test_module, cls_name)
        watcher = cls()
        watcher.from_block = web3.eth.block_number
        return watcher, membership_exchange["address"]

    return _watcher


def issue_token(issuer, exchange_contract_address, token_list):
    # Issue token
    args = {
        "name": "テスト会員権",
        "symbol": "MEMBERSHIP",
        "initialSupply": 1000000,
        "tradableExchange": exchange_contract_address,
        "details": "詳細",
        "returnDetails": "リターン詳細",
        "expirationDate": "20191231",
        "memo": "メモ",
        "transferable": True,
        "contactInformation": "問い合わせ先",
        "privacyPolicy": "プライバシーポリシー",
    }
    token = membership_issue(issuer, args)
    membership_register_list(issuer, token, token_list)

    return token


class TestWatchMembershipNewOrder:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory("WatchMembershipNewOrder")

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 0, 0
        )
        assert _notification.notification_type == NotificationType.NEW_ORDER.value
        assert _notification.priority == 0
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "accountAddress": self.issuer["account_address"],
            "isBuy": False,
            "price": 100,
            "amount": 1000000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type == NotificationType.NEW_ORDER
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Multi event logs
    def test_normal_2(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory("WatchMembershipNewOrder")

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 5000
        )
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000, 100)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 4000, 10)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (
            session.query(Notification).order_by(Notification.created).all()
        )
        assert len(_notification_list) == 2

        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number - 1, 0, 0, 0
        )
        assert _notification.notification_type == NotificationType.NEW_ORDER.value
        assert _notification.priority == 0
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "accountAddress": self.issuer["account_address"],
            "isBuy": False,
            "price": 100,
            "amount": 1000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 0, 0
        )
        assert _notification.notification_type == NotificationType.NEW_ORDER.value
        assert _notification.priority == 0
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 2,
            "accountAddress": self.issuer["account_address"],
            "isBuy": False,
            "price": 10,
            "amount": 4000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type == NotificationType.NEW_ORDER
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # No event logs
    def test_normal_3(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory("WatchMembershipNewOrder")

        token_list_contract = shared_contract["TokenList"]
        issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Not Create Order
        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number.latest_block_number == block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_4>
    # Error occur
    @mock.patch(
        "web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception())
    )
    def test_error_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, _ = watcher_factory("WatchMembershipNewOrder")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number is None


class TestWatchMembershipCancelOrder:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipCancelOrder"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Cancel Order
        cancel_order(self.issuer, {"address": exchange_contract_address}, 1)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 1, 0
        )
        assert _notification.notification_type == NotificationType.CANCEL_ORDER.value
        assert _notification.priority == 0
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "accountAddress": self.issuer["account_address"],
            "isBuy": False,
            "price": 100,
            "amount": 1000000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type
                == NotificationType.CANCEL_ORDER
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Multi event logs
    def test_normal_2(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipCancelOrder"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 5000
        )
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000, 100)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 4000, 10)

        # Cancel Order
        cancel_order(self.issuer, {"address": exchange_contract_address}, 1)
        cancel_order(self.issuer, {"address": exchange_contract_address}, 2)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (
            session.query(Notification).order_by(Notification.created).all()
        )
        assert len(_notification_list) == 2

        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number - 1, 0, 1, 0
        )
        assert _notification.notification_type == NotificationType.CANCEL_ORDER.value
        assert _notification.priority == 0
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "accountAddress": self.issuer["account_address"],
            "isBuy": False,
            "price": 100,
            "amount": 1000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 1, 0
        )
        assert _notification.notification_type == NotificationType.CANCEL_ORDER.value
        assert _notification.priority == 0
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 2,
            "accountAddress": self.issuer["account_address"],
            "isBuy": False,
            "price": 10,
            "amount": 4000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type
                == NotificationType.CANCEL_ORDER
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # No event logs
    def test_normal_3(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipCancelOrder"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Not Cancel Order
        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number.latest_block_number == block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_4>
    # Error occur
    @mock.patch(
        "web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception())
    )
    def test_error_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, _ = watcher_factory("WatchMembershipCancelOrder")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number is None


class TestWatchMembershipForceCancelOrder:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipForceCancelOrder"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(
            issuer=self.issuer,
            exchange_contract_address=exchange_contract_address,
            token_list=token_list_contract,
        )

        # Create Order
        membership_transfer_to_exchange(
            invoker=self.issuer,
            exchange={"address": exchange_contract_address},
            token=token,
            amount=1000000,
        )
        make_sell(
            invoker=self.issuer,
            exchange={"address": exchange_contract_address},
            token=token,
            amount=1000000,
            price=100,
        )

        # Force Cancel Order
        force_cancel_order(
            invoker=eth_account["agent"],
            exchange={"address": exchange_contract_address},
            order_id=1,
        )

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 1, 0
        )
        assert (
            _notification.notification_type == NotificationType.FORCE_CANCEL_ORDER.value
        )
        assert _notification.priority == 2
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "accountAddress": self.issuer["account_address"],
            "isBuy": False,
            "price": 100,
            "amount": 1000000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type
                == NotificationType.FORCE_CANCEL_ORDER
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Multi event logs
    def test_normal_2(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipForceCancelOrder"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(
            issuer=self.issuer,
            exchange_contract_address=exchange_contract_address,
            token_list=token_list_contract,
        )

        # Create Order
        membership_transfer_to_exchange(
            invoker=self.issuer,
            exchange={"address": exchange_contract_address},
            token=token,
            amount=5000,
        )
        make_sell(
            invoker=self.issuer,
            exchange={"address": exchange_contract_address},
            token=token,
            amount=1000,
            price=100,
        )
        make_sell(
            invoker=self.issuer,
            exchange={"address": exchange_contract_address},
            token=token,
            amount=4000,
            price=10,
        )

        # Force Cancel Order
        force_cancel_order(
            invoker=eth_account["agent"],
            exchange={"address": exchange_contract_address},
            order_id=1,
        )
        force_cancel_order(
            invoker=eth_account["agent"],
            exchange={"address": exchange_contract_address},
            order_id=2,
        )

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (
            session.query(Notification).order_by(Notification.created).all()
        )
        assert len(_notification_list) == 2

        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number - 1, 0, 1, 0
        )
        assert (
            _notification.notification_type == NotificationType.FORCE_CANCEL_ORDER.value
        )
        assert _notification.priority == 2
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "accountAddress": self.issuer["account_address"],
            "isBuy": False,
            "price": 100,
            "amount": 1000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 1, 0
        )
        assert (
            _notification.notification_type == NotificationType.FORCE_CANCEL_ORDER.value
        )
        assert _notification.priority == 2
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 2,
            "accountAddress": self.issuer["account_address"],
            "isBuy": False,
            "price": 10,
            "amount": 4000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type
                == NotificationType.FORCE_CANCEL_ORDER
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # No event logs
    def test_normal_3(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipForceCancelOrder"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(
            issuer=self.issuer,
            exchange_contract_address=exchange_contract_address,
            token_list=token_list_contract,
        )

        # Create Order
        membership_transfer_to_exchange(
            invoker=self.issuer,
            exchange={"address": exchange_contract_address},
            token=token,
            amount=1000000,
        )
        make_sell(
            invoker=self.issuer,
            exchange={"address": exchange_contract_address},
            token=token,
            amount=1000000,
            price=100,
        )

        # Not Cancel Order
        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number.latest_block_number == block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_4>
    # Error occur
    @mock.patch(
        "web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception())
    )
    def test_error_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, _ = watcher_factory("WatchMembershipForceCancelOrder")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number is None


class TestWatchMembershipBuyAgreement:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipBuyAgreement"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 0, 1
        )
        assert _notification.notification_type == NotificationType.BUY_AGREEMENT.value
        assert _notification.priority == 1
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 1,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 1000000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type
                == NotificationType.BUY_AGREEMENT
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Multi event logs
    def test_normal_2(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipBuyAgreement"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (
            session.query(Notification).order_by(Notification.created).all()
        )
        assert len(_notification_list) == 2

        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number - 1, 0, 0, 1
        )
        assert _notification.notification_type == NotificationType.BUY_AGREEMENT.value
        assert _notification.priority == 1
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 1,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 600000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 0, 1
        )
        assert _notification.notification_type == NotificationType.BUY_AGREEMENT.value
        assert _notification.priority == 1
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 2,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 400000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type
                == NotificationType.BUY_AGREEMENT
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # No event logs
    def test_normal_3(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipBuyAgreement"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Not Buy Order
        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number.latest_block_number == block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_4>
    # Error occur
    @mock.patch(
        "web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception())
    )
    def test_error_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, _ = watcher_factory("WatchMembershipBuyAgreement")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number is None


class TestWatchMembershipSellAgreement:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipSellAgreement"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 0, 2
        )
        assert _notification.notification_type == NotificationType.SELL_AGREEMENT.value
        assert _notification.priority == 2
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 1,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 1000000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type
                == NotificationType.SELL_AGREEMENT
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Multi event logs
    def test_normal_2(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipSellAgreement"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (
            session.query(Notification).order_by(Notification.created).all()
        )
        assert len(_notification_list) == 2

        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number - 1, 0, 0, 2
        )
        assert _notification.notification_type == NotificationType.SELL_AGREEMENT.value
        assert _notification.priority == 2
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 1,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 600000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 0, 2
        )
        assert _notification.notification_type == NotificationType.SELL_AGREEMENT.value
        assert _notification.priority == 2
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 2,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 400000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type
                == NotificationType.SELL_AGREEMENT
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # No event logs
    def test_normal_3(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipSellAgreement"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Not Buy Order
        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number.latest_block_number == block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch(
        "web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception())
    )
    def test_error_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, _ = watcher_factory("WatchMembershipSellAgreement")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number is None


class TestWatchMembershipBuySettlementOK:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipBuySettlementOK"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Confirm Agreement
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 1, 1
        )
        assert (
            _notification.notification_type == NotificationType.BUY_SETTLEMENT_OK.value
        )
        assert _notification.priority == 1
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 1,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 1000000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type
                == NotificationType.BUY_SETTLEMENT_OK
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Multi event logs
    def test_normal_2(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipBuySettlementOK"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Confirm Agreement
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 2)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (
            session.query(Notification).order_by(Notification.created).all()
        )
        assert len(_notification_list) == 2

        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number - 1, 0, 1, 1
        )
        assert (
            _notification.notification_type == NotificationType.BUY_SETTLEMENT_OK.value
        )
        assert _notification.priority == 1
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 1,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 600000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 1, 1
        )
        assert (
            _notification.notification_type == NotificationType.BUY_SETTLEMENT_OK.value
        )
        assert _notification.priority == 1
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 2,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 400000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type
                == NotificationType.BUY_SETTLEMENT_OK
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # No event logs
    def test_normal_3(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipBuySettlementOK"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Not Confirm Agreement
        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number.latest_block_number == block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch(
        "web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception())
    )
    def test_error_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, _ = watcher_factory("WatchMembershipBuySettlementOK")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number is None


class TestWatchMembershipSellSettlementOK:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipSellSettlementOK"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Confirm Agreement
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 1, 2
        )
        assert (
            _notification.notification_type == NotificationType.SELL_SETTLEMENT_OK.value
        )
        assert _notification.priority == 1
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 1,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 1000000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type
                == NotificationType.SELL_SETTLEMENT_OK
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Multi event logs
    def test_normal_2(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipSellSettlementOK"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Confirm Agreement
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 2)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (
            session.query(Notification).order_by(Notification.created).all()
        )
        assert len(_notification_list) == 2

        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number - 1, 0, 1, 2
        )
        assert (
            _notification.notification_type == NotificationType.SELL_SETTLEMENT_OK.value
        )
        assert _notification.priority == 1
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 1,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 600000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 1, 2
        )
        assert (
            _notification.notification_type == NotificationType.SELL_SETTLEMENT_OK.value
        )
        assert _notification.priority == 1
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 2,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 400000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type
                == NotificationType.SELL_SETTLEMENT_OK
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # No event logs
    def test_normal_3(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipSellSettlementOK"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Not Confirm Agreement
        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number.latest_block_number == block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch(
        "web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception())
    )
    def test_error_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, _ = watcher_factory("WatchMembershipSellSettlementOK")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number is None


class TestWatchMembershipBuySettlementNG:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipBuySettlementNG"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Cancel Agreement
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 0, 1
        )
        assert (
            _notification.notification_type == NotificationType.BUY_SETTLEMENT_NG.value
        )
        assert _notification.priority == 2
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 1,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 1000000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type
                == NotificationType.BUY_SETTLEMENT_NG
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Multi event logs
    def test_normal_2(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipBuySettlementNG"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Cancel Agreement
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 2)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (
            session.query(Notification).order_by(Notification.created).all()
        )
        assert len(_notification_list) == 2

        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number - 1, 0, 0, 1
        )
        assert (
            _notification.notification_type == NotificationType.BUY_SETTLEMENT_NG.value
        )
        assert _notification.priority == 2
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 1,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 600000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 0, 1
        )
        assert (
            _notification.notification_type == NotificationType.BUY_SETTLEMENT_NG.value
        )
        assert _notification.priority == 2
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 2,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 400000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type
                == NotificationType.BUY_SETTLEMENT_NG
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # No event logs
    def test_normal_3(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipBuySettlementNG"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Not Cancel Agreement
        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number.latest_block_number == block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch(
        "web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception())
    )
    def test_error_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, _ = watcher_factory("WatchMembershipBuySettlementNG")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number is None


class TestWatchMembershipSellSettlementNG:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipSellSettlementNG"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Cancel Agreement
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 0, 2
        )
        assert (
            _notification.notification_type == NotificationType.SELL_SETTLEMENT_NG.value
        )
        assert _notification.priority == 2
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 1,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 1000000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type
                == NotificationType.SELL_SETTLEMENT_NG
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Multi event logs
    def test_normal_2(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipSellSettlementNG"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Cancel Agreement
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 2)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (
            session.query(Notification).order_by(Notification.created).all()
        )
        assert len(_notification_list) == 2

        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number - 1, 0, 0, 2
        )
        assert (
            _notification.notification_type == NotificationType.SELL_SETTLEMENT_NG.value
        )
        assert _notification.priority == 2
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 1,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 600000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(
            block_number, 0, 0, 2
        )
        assert (
            _notification.notification_type == NotificationType.SELL_SETTLEMENT_NG.value
        )
        assert _notification.priority == 2
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "tokenAddress": token["address"],
            "orderId": 1,
            "agreementId": 2,
            "buyAddress": self.trader["account_address"],
            "sellAddress": self.issuer["account_address"],
            "price": 100,
            "amount": 400000,
            "agentAddress": self.agent["account_address"],
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト会員権",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetMembership",
        }

        _notification_block_number: NotificationBlockNumber = (
            session.query(NotificationBlockNumber)
            .filter(
                NotificationBlockNumber.notification_type
                == NotificationType.SELL_SETTLEMENT_NG
            )
            .filter(
                NotificationBlockNumber.contract_address == exchange_contract_address
            )
            .first()
        )
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # No event logs
    def test_normal_3(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, exchange_contract_address = watcher_factory(
            "WatchMembershipSellSettlementNG"
        )

        token_list_contract = shared_contract["TokenList"]
        token = issue_token(self.issuer, exchange_contract_address, token_list_contract)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Not Cancel Agreement
        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number.latest_block_number == block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch(
        "web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception())
    )
    def test_error_1(
        self, watcher_factory, session, shared_contract, mocked_company_list
    ):
        watcher, _ = watcher_factory("WatchMembershipSellSettlementNG")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = (
            session.query(Notification).order_by(Notification.created).first()
        )
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number is None
