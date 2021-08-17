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
from app.model import (
    Notification,
    NotificationType
)
from tests.conftest import ibet_exchange_contract
from tests.account_config import eth_account
from tests.contract_modules import (
    issue_bond_token,
    register_bond_list,
    bond_transfer_to_exchange,
    make_sell,
    take_buy,
    cancel_order,
    confirm_agreement,
    cancel_agreement
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="function")
def test_module(session, shared_contract):
    # Create exchange contract for each test method.
    bond_exchange = ibet_exchange_contract(shared_contract["PaymentGateway"]["address"])

    config.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = bond_exchange["address"]

    from batch import processor_Notifications_Bond_Exchange
    test_module = reload(processor_Notifications_Bond_Exchange)
    test_module.db_session = session

    return test_module


def get_test_target(module, cls_name):
    cls = getattr(module, cls_name)
    obj = cls()
    obj.from_block = web3.eth.blockNumber
    return obj


def issue_token(issuer, exchange_contract_address, personal_info_contract_address, token_list):
    # Issue token
    args = {
        'name': 'テスト債券',
        'symbol': 'BOND',
        'totalSupply': 1000000,
        'tradableExchange': exchange_contract_address,
        'faceValue': 10000,
        'interestRate': 602,
        'interestPaymentDate1': '0101',
        'interestPaymentDate2': '0201',
        'interestPaymentDate3': '0301',
        'interestPaymentDate4': '0401',
        'interestPaymentDate5': '0501',
        'interestPaymentDate6': '0601',
        'interestPaymentDate7': '0701',
        'interestPaymentDate8': '0801',
        'interestPaymentDate9': '0901',
        'interestPaymentDate10': '1001',
        'interestPaymentDate11': '1101',
        'interestPaymentDate12': '1201',
        'redemptionDate': '20191231',
        'redemptionValue': 10000,
        'returnDate': '20191231',
        'returnAmount': '商品券をプレゼント',
        'purpose': '新商品の開発資金として利用。',
        'memo': 'メモ',
        'contactInformation': '問い合わせ先',
        'privacyPolicy': 'プライバシーポリシー',
        'personalInfoAddress': personal_info_contract_address,
        'transferable': True,
        'isRedeemed': False
    }
    token = issue_bond_token(issuer, args)
    register_bond_list(issuer, token, token_list)

    return token


class TestWatchBondNewOrder:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondNewOrder")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Run target process
        target.loop()

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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondNewOrder")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 5000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000, 100)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 4000, 10)

        # Run target process
        target.loop()

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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondNewOrder")

        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondNewOrder")

        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchBondCancelOrder:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondCancelOrder")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Cancel Order
        cancel_order(self.issuer, {"address": exchange_contract_address}, 1)

        # Run target process
        target.loop()

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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondCancelOrder")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 5000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000, 100)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 4000, 10)

        # Cancel Order
        cancel_order(self.issuer, {"address": exchange_contract_address}, 1)
        cancel_order(self.issuer, {"address": exchange_contract_address}, 2)

        # Run target process
        target.loop()

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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondCancelOrder")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Not Cancel Order
        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondCancelOrder")

        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchBondBuyAgreement:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondBuyAgreement")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Run target process
        target.loop()

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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondBuyAgreement")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Run target process
        target.loop()

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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondBuyAgreement")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Not Buy Order
        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondBuyAgreement")

        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchBondSellAgreement:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondSellAgreement")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Run target process
        target.loop()

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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondSellAgreement")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Run target process
        target.loop()

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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondSellAgreement")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Not Buy Order
        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondSellAgreement")

        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchBondBuySettlementOK:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondBuySettlementOK")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Confirm Agreement
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)

        # Run target process
        target.loop()

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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondBuySettlementOK")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Confirm Agreement
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 2)

        # Run target process
        target.loop()

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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondBuySettlementOK")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Not Confirm Agreement
        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondBuySettlementOK")

        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchBondSellSettlementOK:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondSellSettlementOK")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Confirm Agreement
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)

        # Run target process
        target.loop()

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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondSellSettlementOK")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Confirm Agreement
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 2)

        # Run target process
        target.loop()

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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondSellSettlementOK")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Not Confirm Agreement
        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondSellSettlementOK")

        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchBondBuySettlementNG:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondBuySettlementNG")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Cancel Agreement
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)

        # Run target process
        target.loop()

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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondBuySettlementNG")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Cancel Agreement
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 2)

        # Run target process
        target.loop()

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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondBuySettlementNG")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Not Cancel Agreement
        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondBuySettlementNG")

        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchBondSellSettlementNG:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondSellSettlementNG")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Cancel Agreement
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)

        # Run target process
        target.loop()

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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondSellSettlementNG")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 600000)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 400000)

        # Cancel Agreement
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 2)

        # Run target process
        target.loop()

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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
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
            "token_name": "テスト債券",
            "exchange_address": exchange_contract_address,
            "token_type": "IbetStraightBond"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondSellSettlementNG")

        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = test_module.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = issue_token(self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Buy Order
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 1000000)

        # Not Cancel Agreement
        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchBondSellSettlementNG")

        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None
