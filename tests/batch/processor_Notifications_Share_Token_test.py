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
    NotificationType,
    Listing
)
from app.contracts import Contract
from tests.account_config import eth_account
from tests.contract_modules import (
    issue_share_token,
    register_share_list,
    share_transfer_to_exchange
)
from tests.utils import PersonalInfoUtils

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="function")
def test_module(session):
    # Create TokenList contract for each test method.
    deployer = eth_account["deployer"]
    token_list_contract_address, _ = Contract.deploy_contract(
        "TokenList", [], deployer["account_address"])

    config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract_address

    from batch import processor_Notifications_Share_Token
    test_module = reload(processor_Notifications_Share_Token)
    test_module.db_session = session

    return test_module


def get_test_target(module, cls_name):
    cls = getattr(module, cls_name)
    obj = cls()
    obj.from_block = web3.eth.blockNumber
    return obj


def issue_token(issuer, exchange, personal_info, token_list_contract_address, session):
    # Issue token
    args = {
        "name": "テスト株式",
        "symbol": "SHARE",
        "tradableExchange": exchange["address"],
        "personalInfoAddress": personal_info["address"],
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
    register_share_list(issuer, token, {"address": token_list_contract_address})

    _listing = Listing()
    _listing.token_address = token["address"]
    _listing.is_public = True
    _listing.max_holding_quantity = 1000000
    _listing.max_sell_amount = 1000000
    _listing.owner_address = issuer["account_address"]
    session.add(_listing)

    return token


class TestWatchStartOffering:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["deployer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchStartOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Offering Start
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setOfferingStatus(True).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        target.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.START_OFFERING.value
        assert _notification.priority == 0
        assert _notification.address is None
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "status": True,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchStartOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)
        token2 = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Offering Start
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setOfferingStatus(True).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        token_contract2 = Contract.get_contract("IbetShare", token2["address"])
        tx_hash2 = token_contract2.functions.setOfferingStatus(True).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash2)

        # Run target process
        target.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
        assert _notification.notification_type == NotificationType.START_OFFERING.value
        assert _notification.priority == 0
        assert _notification.address is None
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "status": True,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.START_OFFERING.value
        assert _notification.priority == 0
        assert _notification.address is None
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "status": True,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token2["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchStartOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Not Offering Start
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
        target = get_test_target(test_module, "WatchStartOffering")

        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchStopOffering:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["deployer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchStopOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Offering Start
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setOfferingStatus(False).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        target.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.STOP_OFFERING.value
        assert _notification.priority == 0
        assert _notification.address is None
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "status": False,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchStopOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)
        token2 = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Offering Stop
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setOfferingStatus(False).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        token_contract2 = Contract.get_contract("IbetShare", token2["address"])
        tx_hash2 = token_contract2.functions.setOfferingStatus(False).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash2)

        # Run target process
        target.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
        assert _notification.notification_type == NotificationType.STOP_OFFERING.value
        assert _notification.priority == 0
        assert _notification.address is None
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "status": False,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.STOP_OFFERING.value
        assert _notification.priority == 0
        assert _notification.address is None
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "status": False,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token2["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchStopOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Not Offering Stop
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
        target = get_test_target(test_module, "WatchStopOffering")

        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchSuspend:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["deployer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchSuspend")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Suspend
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setStatus(False).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        target.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.SUSPEND.value
        assert _notification.priority == 0
        assert _notification.address is None
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "status": False,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchSuspend")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)
        token2 = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Suspend
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setStatus(False).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        token_contract2 = Contract.get_contract("IbetShare", token2["address"])
        tx_hash2 = token_contract2.functions.setStatus(False).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash2)

        # Run target process
        target.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
        assert _notification.notification_type == NotificationType.SUSPEND.value
        assert _notification.priority == 0
        assert _notification.address is None
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "status": False,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.SUSPEND.value
        assert _notification.priority == 0
        assert _notification.address is None
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "status": False,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token2["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchSuspend")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Not Suspend
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
        target = get_test_target(test_module, "WatchSuspend")

        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchApplyForOffering:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["deployer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchApplyForOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Offering Start
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setOfferingStatus(True).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Apply For Offering
        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.applyForOffering(100, "test").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        target.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.APPLY_FOR_OFFERING.value
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "accountAddress": self.trader["account_address"],
            "amount": 100,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchApplyForOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)
        token2 = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Offering Start
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setOfferingStatus(True).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        token_contract2 = Contract.get_contract("IbetShare", token2["address"])
        tx_hash = token_contract2.functions.setOfferingStatus(True).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Apply For Offering
        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.trader2["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        tx_hash = token_contract.functions.applyForOffering(100, "test").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        tx_hash2 = token_contract2.functions.applyForOffering(200, "test").transact(
            {"from": self.trader2["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash2)

        # Run target process
        target.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
        assert _notification.notification_type == NotificationType.APPLY_FOR_OFFERING.value
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "accountAddress": self.trader["account_address"],
            "amount": 100,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.APPLY_FOR_OFFERING.value
        assert _notification.priority == 0
        assert _notification.address == self.trader2["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "accountAddress": self.trader2["account_address"],
            "amount": 200,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token2["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchApplyForOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Not Apply For Offering
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
        target = get_test_target(test_module, "WatchApplyForOffering")

        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchAllot:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["deployer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchAllot")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Allot
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.allot(self.trader["account_address"], 100).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        target.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.ALLOT.value
        assert _notification.priority == 1
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "accountAddress": self.trader["account_address"],
            "amount": 100,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchAllot")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Allot
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.allot(self.trader["account_address"], 100).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        tx_hash = token_contract.functions.allot(self.trader2["account_address"], 200).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        target.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
        assert _notification.notification_type == NotificationType.ALLOT.value
        assert _notification.priority == 1
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "accountAddress": self.trader["account_address"],
            "amount": 100,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.ALLOT.value
        assert _notification.priority == 1
        assert _notification.address == self.trader2["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "accountAddress": self.trader2["account_address"],
            "amount": 200,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchAllot")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Not Allot
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
        target = get_test_target(test_module, "WatchAllot")

        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None


class TestWatchTransfer:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["deployer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Transfer
        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 100)

        # Run target process
        target.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "from": self.issuer["account_address"],
            "to": self.trader["account_address"],
            "value": 100,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Transfer
        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.trader2["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 100)
        share_transfer_to_exchange(self.issuer, {"address": self.trader2["account_address"]}, token, 200)

        # Run target process
        target.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
        assert _notification.notification_type == NotificationType.TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "from": self.issuer["account_address"],
            "to": self.trader["account_address"],
            "value": 100,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }
        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == self.trader2["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "from": self.issuer["account_address"],
            "to": self.trader2["account_address"],
            "value": 200,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

    # <Normal_3>
    # No event logs
    def test_normal_3(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Not Transfer
        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

    # <Normal_4>
    # Transfer from DEX
    def test_normal_4(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchTransfer")

        exchange_contract = {"address": self.trader2["account_address"]}  # Dummy DEX(TX send able address)
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract_address = test_module.TOKEN_LIST_CONTRACT_ADDRESS
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract_address, session)

        # Transfer(to DEX)
        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        share_transfer_to_exchange(self.issuer, exchange_contract, token, 100)

        # Transfer(from DEX)
        share_transfer_to_exchange(
            {"account_address": exchange_contract["address"]}, {"address": self.trader["account_address"]}, token, 100)

        # Run target process
        target.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 1  # Not Transfer from DEX
        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
        assert _notification.notification_type == NotificationType.TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == exchange_contract["address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "from": self.issuer["account_address"],
            "to": exchange_contract["address"],
            "value": 100,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, test_module, session, shared_contract, mocked_company_list):
        target = get_test_target(test_module, "WatchTransfer")

        # Run target process
        target.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None
