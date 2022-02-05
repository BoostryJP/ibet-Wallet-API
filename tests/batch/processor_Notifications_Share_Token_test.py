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
    NotificationType,
    Listing
)
from app.contracts import Contract
from tests.account_config import eth_account
from tests.contract_modules import (
    issue_share_token,
    register_share_list,
    share_transfer_to_exchange,
    share_withdraw_from_exchange
)
from tests.utils import PersonalInfoUtils

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="function")
def watcher_factory(session, shared_contract):
    def _watcher(cls_name):
        config.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]

        from batch import processor_Notifications_Share_Token
        test_module = reload(processor_Notifications_Share_Token)
        cls = getattr(test_module, cls_name)
        watcher = cls()
        watcher.from_block = web3.eth.blockNumber
        return watcher

    return _watcher


def issue_token(issuer, exchange, personal_info, token_list, session):
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
    register_share_list(issuer, token, token_list)

    _listing = Listing()
    _listing.token_address = token["address"]
    _listing.is_public = True
    _listing.max_holding_quantity = 1000000
    _listing.max_sell_amount = 1000000
    _listing.owner_address = issuer["account_address"]
    session.add(_listing)
    session.commit()

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
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchStartOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Offering Start
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setOfferingStatus(True).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        watcher.loop()

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
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchStartOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)
        token2 = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

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
        watcher.loop()

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
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchStartOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Not Offering Start
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
        watcher = watcher_factory("WatchStartOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Run target process
        watcher.loop()

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
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchStopOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Offering Start
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setOfferingStatus(False).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        watcher.loop()

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
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchStopOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)
        token2 = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

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
        watcher.loop()

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
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchStopOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Not Offering Stop
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
        watcher = watcher_factory("WatchStopOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Run target process
        watcher.loop()

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
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchSuspend")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Suspend
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setStatus(False).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        watcher.loop()

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
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchSuspend")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)
        token2 = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

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
        watcher.loop()

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
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchSuspend")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Not Suspend
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
        watcher = watcher_factory("WatchSuspend")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Run target process
        watcher.loop()

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
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchApplyForOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

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
        watcher.loop()

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
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchApplyForOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)
        token2 = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

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
        watcher.loop()

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
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchApplyForOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Not Apply For Offering
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
        watcher = watcher_factory("WatchApplyForOffering")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Run target process
        watcher.loop()

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
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchAllot")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Allot
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.allot(self.trader["account_address"], 100).transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        watcher.loop()

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
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchAllot")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

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
        watcher.loop()

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
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchAllot")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Not Allot
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
        watcher = watcher_factory("WatchAllot")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Run target process
        watcher.loop()

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
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Transfer
        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 100)

        # Run target process
        watcher.loop()

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
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        token = issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Transfer
        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.trader2["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 100)
        share_transfer_to_exchange(self.issuer, {"address": self.trader2["account_address"]}, token, 200)

        # Run target process
        watcher.loop()

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
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Not Transfer
        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

    # <Normal_4>
    # Transfer from DEX
    def test_normal_4(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        token = issue_token(
            self.issuer,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            session
        )

        # Transfer to DEX
        share_transfer_to_exchange(
            invoker=self.issuer,
            token=token,
            exchange=exchange_contract,
            amount=100
        )

        # Withdraw from DEX
        share_withdraw_from_exchange(
            invoker=self.issuer,
            token=token,
            exchange=exchange_contract,
            amount=100
        )

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.blockNumber
        _notification_list = session.query(Notification). \
            order_by(Notification.created). \
            all()

        assert len(_notification_list) == 1  # Notification from which the DEX is the transferor will not be registered.

        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 1, 0)
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
    def test_error_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token_list_contract = shared_contract["TokenList"]
        issue_token(
            self.issuer, exchange_contract, personal_info_contract, token_list_contract, session)

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None
