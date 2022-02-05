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
from tests.conftest import ibet_exchange_contract
from tests.account_config import eth_account
from tests.contract_modules import (
    issue_share_token,
    register_share_list,
    share_transfer_to_exchange,
    make_sell,
    take_buy,
    cancel_order,
    confirm_agreement,
    cancel_agreement
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="function")
def watcher_factory(session, shared_contract):
    def _watcher(cls_name):
        # Create exchange contract for each test method.
        share_exchange = ibet_exchange_contract(shared_contract["PaymentGateway"]["address"])

        config.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = share_exchange["address"]

        from batch import processor_Notifications_Share_Exchange
        test_module = reload(processor_Notifications_Share_Exchange)
        cls = getattr(test_module, cls_name)
        watcher = cls()
        watcher.from_block = web3.eth.blockNumber
        return watcher, share_exchange["address"]

    return _watcher


def issue_token(issuer, exchange_contract_address, personal_info_contract_address, token_list):
    # Issue token
    args = {
        "name": "テスト株式",
        "symbol": "SHARE",
        "tradableExchange": exchange_contract_address,
        "personalInfoAddress": personal_info_contract_address,
        "issuePrice": 1000,
        "principalValue": 1000,
        "totalSupply": 1000000,
        "dividends": 101,
        "dividendRecordDate": "20200401",
        "dividendPaymentDate": "20200502",
        "cancellationDate": "20200603",
        "contactInformation": "問い合わせ先",
        "privacyPolicy": "プライバシーポリシー",
        "memo": "メモ",
        "transferable": True
    }
    token = issue_share_token(issuer, args)
    register_share_list(issuer, token, token_list)

    return token


class TestWatchShareNewOrder:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareNewOrder")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareNewOrder")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 5000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000, 100)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 4000, 10)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareNewOrder")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Not Create Order
        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_4>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, _ = watcher_factory("WatchShareNewOrder")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchShareCancelOrder:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareCancelOrder")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Cancel Order
        cancel_order(self.issuer, {"address": exchange_contract_address}, 1)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 1, 0)
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareCancelOrder")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 5000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000, 100)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 4000, 10)

        # Cancel Order
        cancel_order(self.issuer, {"address": exchange_contract_address}, 1)
        cancel_order(self.issuer, {"address": exchange_contract_address}, 2)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 1, 0)
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 1, 0)
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareCancelOrder")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Not Cancel Order
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
        watcher, _ = watcher_factory("WatchShareCancelOrder")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchShareBuyAgreement:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareBuyAgreement")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 1)
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareBuyAgreement")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 1)
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 1)
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareBuyAgreement")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Not Buy Order
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
        watcher, _ = watcher_factory("WatchShareBuyAgreement")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchShareSellAgreement:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareSellAgreement")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 2)
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareSellAgreement")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 2)
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 2)
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareSellAgreement")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Not Buy Order
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
        watcher, _ = watcher_factory("WatchShareSellAgreement")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchShareBuySettlementOK:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareBuySettlementOK")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Confirm Agreement
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 1, 1)
        assert _notification.notification_type == NotificationType.BUY_SETTLEMENT_OK.value
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareBuySettlementOK")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Confirm Agreement
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 2)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 1, 1)
        assert _notification.notification_type == NotificationType.BUY_SETTLEMENT_OK.value
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 1, 1)
        assert _notification.notification_type == NotificationType.BUY_SETTLEMENT_OK.value
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareBuySettlementOK")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Not Confirm Agreement
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
        watcher, _ = watcher_factory("WatchShareBuySettlementOK")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchShareSellSettlementOK:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareSellSettlementOK")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Confirm Agreement
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 1, 2)
        assert _notification.notification_type == NotificationType.SELL_SETTLEMENT_OK.value
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareSellSettlementOK")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Confirm Agreement
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 2)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 1, 2)
        assert _notification.notification_type == NotificationType.SELL_SETTLEMENT_OK.value
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 1, 2)
        assert _notification.notification_type == NotificationType.SELL_SETTLEMENT_OK.value
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareSellSettlementOK")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Not Confirm Agreement
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
        watcher, _ = watcher_factory("WatchShareSellSettlementOK")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchShareBuySettlementNG:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareBuySettlementNG")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Cancel Agreement
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 1)
        assert _notification.notification_type == NotificationType.BUY_SETTLEMENT_NG.value
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareBuySettlementNG")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Cancel Agreement
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 2)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 1)
        assert _notification.notification_type == NotificationType.BUY_SETTLEMENT_NG.value
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 1)
        assert _notification.notification_type == NotificationType.BUY_SETTLEMENT_NG.value
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareBuySettlementNG")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Not Cancel Agreement
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
        watcher, _ = watcher_factory("WatchShareBuySettlementNG")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchShareSellSettlementNG:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareSellSettlementNG")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Cancel Agreement
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 2)
        assert _notification.notification_type == NotificationType.SELL_SETTLEMENT_NG.value
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareSellSettlementNG")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Cancel Agreement
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 2)

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 2)
        assert _notification.notification_type == NotificationType.SELL_SETTLEMENT_NG.value
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 2)
        assert _notification.notification_type == NotificationType.SELL_SETTLEMENT_NG.value
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
            "token_name": "テスト株式",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetShare"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher, exchange_contract_address = watcher_factory("WatchShareSellSettlementNG")

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        share_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Not Cancel Agreement
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
        watcher, _ = watcher_factory("WatchShareSellSettlementNG")

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None
