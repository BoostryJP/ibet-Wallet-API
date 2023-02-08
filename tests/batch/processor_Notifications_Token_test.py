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
from __future__ import annotations
import pytest
from unittest import mock
from unittest.mock import MagicMock
from importlib import reload
from eth_typing import ChecksumAddress
from sqlalchemy.orm import Session
from typing import Callable, TYPE_CHECKING
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.types import RPCEndpoint

from app import config
from app.model.db import (
    Notification,
    NotificationType,
    NotificationBlockNumber,
    Listing,
    IDXTokenListItem
)
from tests.account_config import eth_account
from tests.conftest import SharedContract, DeployedContract, TestAccount
from tests.contract_modules import (
    issue_coupon_token,
    coupon_register_list,
    transfer_coupon_token,
    coupon_transfer_to_exchange,
    coupon_withdraw_from_exchange,
    issue_share_token,
    register_share_list,
    share_set_transfer_approval_required,
    share_apply_for_transfer,
    register_personalinfo,
    transfer_share_token,
    share_approve_transfer,
    share_cancel_transfer
)

if TYPE_CHECKING:
    from batch.processor_Notifications_Token import Watcher

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="function")
def watcher_factory(session: Session, shared_contract: SharedContract, db_engine) -> Callable[[str], Watcher]:
    def _watcher(cls_name):
        config.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]

        from batch import processor_Notifications_Token
        test_module = reload(processor_Notifications_Token)
        processor_Notifications_Token.db_engine = db_engine
        test_module.db_session = session

        cls = getattr(test_module, cls_name)
        watcher = cls()
        watcher.from_block = web3.eth.block_number
        return watcher

    return _watcher


def prepare_coupon_token(issuer: ChecksumAddress, exchange: DeployedContract, token_list: DeployedContract, session: Session):
    # Issue token
    args = {
        'name': 'テストクーポン',
        'symbol': 'COUPON',
        'totalSupply': 1000000,
        'tradableExchange': exchange["address"],
        'details': 'クーポン詳細',
        'returnDetails': 'リターン詳細',
        'memo': 'クーポンメモ欄',
        'expirationDate': '20191231',
        'transferable': True,
        'contactInformation': '問い合わせ先',
        'privacyPolicy': 'プライバシーポリシー'
    }
    token = issue_coupon_token(issuer, args)
    coupon_register_list(issuer, token, token_list)

    _listing = Listing()
    _listing.token_address = token["address"]
    _listing.is_public = True
    _listing.max_holding_quantity = 1000000
    _listing.max_sell_amount = 1000000
    _listing.owner_address = issuer
    session.add(_listing)
    session.commit()

    return token


def prepare_share_token(issuer: TestAccount,
                        exchange: DeployedContract,
                        token_list: DeployedContract,
                        personal_info: DeployedContract,
                        session: Session):
    # Issue token
    args = {
        "name": "テスト株式",
        "symbol": "SHARE",
        "tradableExchange": exchange["address"],
        "personalInfoAddress": personal_info["address"],
        "totalSupply": 1000000,
        "issuePrice": 10000,
        "principalValue": 10000,
        "dividends": 101,
        "dividendRecordDate": "20200909",
        "dividendPaymentDate": "20201001",
        "cancellationDate": "20210101",
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
    _listing.owner_address = issuer
    session.add(_listing)
    session.commit()

    return token


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

        exchange_contract = shared_contract["IbetCouponExchange"]
        token_list_contract = shared_contract["TokenList"]
        token = prepare_coupon_token(self.issuer, exchange_contract, token_list_contract, session)

        # Transfer
        tx_hash = transfer_coupon_token(self.issuer, token, self.trader, 100)

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetCoupon"
        session.add(idx_token_list_item)
        session.commit()

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.get_transaction(tx_hash).blockNumber

        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == self.trader
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "from": self.issuer,
            "to": self.trader,
            "value": 100,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テストクーポン",
            "exchange_address": "",
            "token_type": "IbetCoupon"
        }

        _notification_block_number: NotificationBlockNumber = session.query(NotificationBlockNumber).\
            filter(NotificationBlockNumber.notification_type == NotificationType.TRANSFER).\
            filter(NotificationBlockNumber.contract_address == token["address"]).\
            first()
        assert _notification_block_number.latest_block_number >= block_number

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchTransfer")

        exchange_contract = shared_contract["IbetCouponExchange"]
        token_list_contract = shared_contract["TokenList"]
        token = prepare_coupon_token(self.issuer, exchange_contract, token_list_contract, session)

        # Transfer
        tx_hash = transfer_coupon_token(self.issuer, token, self.trader, 100)
        block_number1 = web3.eth.get_transaction(tx_hash).blockNumber
        tx_hash = transfer_coupon_token(self.issuer, token, self.trader2, 200)
        block_number2 = web3.eth.get_transaction(tx_hash).blockNumber

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetCoupon"
        session.add(idx_token_list_item)
        session.commit()

        # Run target process
        watcher.loop()

        # Assertion
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2

        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number1, 0, 0, 0)
        assert _notification.notification_type == NotificationType.TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == self.trader
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "from": self.issuer,
            "to": self.trader,
            "value": 100,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テストクーポン",
            "exchange_address": "",
            "token_type": "IbetCoupon"
        }

        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number2, 0, 0, 0)
        assert _notification.notification_type == NotificationType.TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == self.trader2
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "from": self.issuer,
            "to": self.trader2,
            "value": 200,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テストクーポン",
            "exchange_address": "",
            "token_type": "IbetCoupon"
        }

        _notification_block_number: NotificationBlockNumber = session.query(NotificationBlockNumber).\
            filter(NotificationBlockNumber.notification_type == NotificationType.TRANSFER).\
            filter(NotificationBlockNumber.contract_address == token["address"]).\
            first()
        assert _notification_block_number.latest_block_number >= block_number2

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchTransfer")

        exchange_contract = shared_contract["IbetCouponExchange"]
        token_list_contract = shared_contract["TokenList"]
        token = prepare_coupon_token(self.issuer, exchange_contract, token_list_contract, session)

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetCoupon"
        session.add(idx_token_list_item)
        session.commit()

        # Not Transfer
        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        block_number = web3.eth.block_number
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number.latest_block_number >= block_number

    # <Normal_4>
    # Transfer from DEX
    def test_normal_4(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchTransfer")

        exchange_contract = shared_contract["IbetCouponExchange"]
        token_list_contract = shared_contract["TokenList"]
        token = prepare_coupon_token(self.issuer, exchange_contract, token_list_contract, session)

        # Transfer to DEX
        tx_hash = coupon_transfer_to_exchange(
            invoker=self.issuer,
            exchange=exchange_contract,
            token=token,
            amount=100
        )
        block_number1 = web3.eth.get_transaction(tx_hash).blockNumber

        # Withdraw from DEX
        tx_hash = coupon_withdraw_from_exchange(
            invoker=self.issuer,
            exchange=exchange_contract,
            token=token,
            amount=100
        )
        block_number2 = web3.eth.get_transaction(tx_hash).blockNumber

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetCoupon"
        session.add(idx_token_list_item)
        session.commit()

        # Run target process
        watcher.loop()

        # Assertion
        _notification_list = session.query(Notification).\
            order_by(Notification.created).\
            all()

        assert len(_notification_list) == 1  # Notification from which the DEX is the transferor will not be registered.

        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number1, 0, 1, 0)
        assert _notification.notification_type == NotificationType.TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == exchange_contract["address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "from": self.issuer,
            "to": exchange_contract["address"],
            "value": 100,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テストクーポン",
            "exchange_address": "",
            "token_type": "IbetCoupon"
        }

        _notification_block_number: NotificationBlockNumber = session.query(NotificationBlockNumber).\
            filter(NotificationBlockNumber.notification_type == NotificationType.TRANSFER).\
            filter(NotificationBlockNumber.contract_address == token["address"]).\
            first()
        assert _notification_block_number.latest_block_number >= block_number2

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchTransfer")

        exchange_contract = shared_contract["IbetCouponExchange"]
        token_list_contract = shared_contract["TokenList"]
        token = prepare_coupon_token(self.issuer, exchange_contract, token_list_contract, session)

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetCoupon"
        session.add(idx_token_list_item)
        session.commit()

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number is None


class TestWatchApplyForTransfer:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["deployer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchApplyForTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = prepare_share_token(self.issuer, exchange_contract, token_list_contract, personal_info_contract, session)

        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)

        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        tx_hash = share_apply_for_transfer(self.trader, token, self.trader2, 100, "TEST_DATA")
        block_number = web3.eth.get_transaction(tx_hash).blockNumber

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetShare"
        session.add(idx_token_list_item)
        session.commit()

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.APPLY_FOR_TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == self.trader2
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 0,
            "from": self.trader,
            "to": self.trader2,
            "value": 100,
            "data": "TEST_DATA"
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

        _notification_block_number: NotificationBlockNumber = session.query(NotificationBlockNumber).\
            filter(NotificationBlockNumber.notification_type == NotificationType.APPLY_FOR_TRANSFER).\
            filter(NotificationBlockNumber.contract_address == token["address"]).\
            first()
        assert _notification_block_number.latest_block_number >= block_number

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchApplyForTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        token = prepare_share_token(self.issuer, exchange_contract, token_list_contract, personal_info_contract, session)

        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)

        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        # Transfer
        tx_hash = share_apply_for_transfer(self.trader, token, self.trader2, 10, "TEST_DATA1")
        block_number1 = web3.eth.get_transaction(tx_hash).blockNumber
        tx_hash = share_apply_for_transfer(self.trader, token, self.trader2, 20, "TEST_DATA2")
        block_number2 = web3.eth.get_transaction(tx_hash).blockNumber

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetShare"
        session.add(idx_token_list_item)
        session.commit()

        # Run target process
        watcher.loop()

        # Assertion
        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2

        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number1, 0, 0, 0)
        assert _notification.notification_type == NotificationType.APPLY_FOR_TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == self.trader2
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 0,
            "from": self.trader,
            "to": self.trader2,
            "value": 10,
            "data": "TEST_DATA1"
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number2, 0, 0, 0)
        assert _notification.notification_type == NotificationType.APPLY_FOR_TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == self.trader2
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 1,
            "from": self.trader,
            "to": self.trader2,
            "value": 20,
            "data": "TEST_DATA2"
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

        _notification_block_number: NotificationBlockNumber = session.query(NotificationBlockNumber).\
            filter(NotificationBlockNumber.notification_type == NotificationType.APPLY_FOR_TRANSFER).\
            filter(NotificationBlockNumber.contract_address == token["address"]).\
            first()
        assert _notification_block_number.latest_block_number >= block_number2

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchApplyForTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        token = prepare_share_token(self.issuer, exchange_contract, token_list_contract, personal_info_contract, session)

        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)

        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetShare"
        session.add(idx_token_list_item)
        session.commit()

        # Not Transfer
        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        block_number = web3.eth.block_number
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number.latest_block_number >= block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchApplyForTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        token = prepare_share_token(self.issuer, exchange_contract, token_list_contract, personal_info_contract, session)

        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)

        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        # Transfer
        share_apply_for_transfer(self.trader, token, self.trader2, 10, "TEST_DATA1")

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetShare"
        session.add(idx_token_list_item)
        session.commit()

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number is None


class TestWatchApproveTransfer:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["deployer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchApproveTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = prepare_share_token(self.issuer, exchange_contract, token_list_contract, personal_info_contract, session)

        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)

        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        share_apply_for_transfer(self.trader, token, self.trader2, 100, "TEST_DATA")
        tx_hash = share_approve_transfer(self.issuer, token, 0, "TEST_DATA")
        block_number = web3.eth.get_transaction(tx_hash).blockNumber

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetShare"
        session.add(idx_token_list_item)
        session.commit()

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.APPROVE_TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == self.trader
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 0,
            "from": self.trader,
            "to": self.trader2,
            "data": "TEST_DATA"
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

        _notification_block_number: NotificationBlockNumber = session.query(NotificationBlockNumber).\
            filter(NotificationBlockNumber.notification_type == NotificationType.APPROVE_TRANSFER).\
            filter(NotificationBlockNumber.contract_address == token["address"]).\
            first()
        assert _notification_block_number.latest_block_number >= block_number

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchApproveTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        token = prepare_share_token(self.issuer, exchange_contract, token_list_contract, personal_info_contract, session)

        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)

        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        # Transfer
        share_apply_for_transfer(self.trader, token, self.trader2, 10, "TEST_DATA1")
        share_apply_for_transfer(self.trader, token, self.trader2, 20, "TEST_DATA2")
        tx_hash = share_approve_transfer(self.issuer, token, 0, "TEST_DATA1")
        block_number1 = web3.eth.get_transaction(tx_hash).blockNumber
        tx_hash = share_approve_transfer(self.issuer, token, 1, "TEST_DATA2")
        block_number2 = web3.eth.get_transaction(tx_hash).blockNumber

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetShare"
        session.add(idx_token_list_item)
        session.commit()

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2

        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number1, 0, 0, 0)
        assert _notification.notification_type == NotificationType.APPROVE_TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == self.trader
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 0,
            "from": self.trader,
            "to": self.trader2,
            "data": "TEST_DATA1"
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number2, 0, 0, 0)
        assert _notification.notification_type == NotificationType.APPROVE_TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == self.trader
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 1,
            "from": self.trader,
            "to": self.trader2,
            "data": "TEST_DATA2"
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

        _notification_block_number: NotificationBlockNumber = session.query(NotificationBlockNumber).\
            filter(NotificationBlockNumber.notification_type == NotificationType.APPROVE_TRANSFER).\
            filter(NotificationBlockNumber.contract_address == token["address"]).\
            first()
        assert _notification_block_number.latest_block_number >= block_number2

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchApplyForTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        token = prepare_share_token(self.issuer, exchange_contract, token_list_contract, personal_info_contract, session)

        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)

        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetShare"
        session.add(idx_token_list_item)
        session.commit()

        # Not Transfer
        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        block_number = web3.eth.block_number
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number.latest_block_number >= block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchApplyForTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        token = prepare_share_token(self.issuer, exchange_contract, token_list_contract, personal_info_contract, session)

        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)

        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        # Transfer
        share_apply_for_transfer(self.trader, token, self.trader2, 10, "TEST_DATA1")
        share_approve_transfer(self.issuer, token, 0, "TEST_DATA1")

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetShare"
        session.add(idx_token_list_item)
        session.commit()

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number is None


class TestWatchCancelTransfer:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["deployer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    def test_normal_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchCancelTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = prepare_share_token(self.issuer, exchange_contract, token_list_contract, personal_info_contract, session)

        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)

        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        share_apply_for_transfer(self.trader, token, self.trader2, 100, "TEST_DATA")
        tx_hash = share_cancel_transfer(self.issuer, token, 0, "TEST_DATA")
        block_number = web3.eth.get_transaction(tx_hash).blockNumber

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetShare"
        session.add(idx_token_list_item)
        session.commit()

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
        assert _notification.notification_type == NotificationType.CANCEL_TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == self.trader
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 0,
            "from": self.trader,
            "to": self.trader2,
            "data": "TEST_DATA"
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

        _notification_block_number: NotificationBlockNumber = session.query(NotificationBlockNumber).\
            filter(NotificationBlockNumber.notification_type == NotificationType.CANCEL_TRANSFER).\
            filter(NotificationBlockNumber.contract_address == token["address"]).\
            first()
        assert _notification_block_number.latest_block_number >= block_number

    # <Normal_2>
    # Multi event logs
    def test_normal_2(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchCancelTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        token = prepare_share_token(self.issuer, exchange_contract, token_list_contract, personal_info_contract, session)

        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)

        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        # Transfer
        share_apply_for_transfer(self.trader, token, self.trader2, 10, "TEST_DATA1")
        share_apply_for_transfer(self.trader, token, self.trader2, 20, "TEST_DATA2")
        tx_hash = share_cancel_transfer(self.issuer, token, 0, "TEST_DATA1")
        block_number1 = web3.eth.get_transaction(tx_hash).blockNumber
        tx_hash = share_cancel_transfer(self.issuer, token, 1, "TEST_DATA2")
        block_number2 = web3.eth.get_transaction(tx_hash).blockNumber

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetShare"
        session.add(idx_token_list_item)
        session.commit()

        # Run target process
        watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = session.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2

        _notification = _notification_list[0]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number1, 0, 0, 0)
        assert _notification.notification_type == NotificationType.CANCEL_TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == self.trader
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 0,
            "from": self.trader,
            "to": self.trader2,
            "data": "TEST_DATA1"
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

        _notification = _notification_list[1]
        assert _notification.notification_id == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number2, 0, 0, 0)
        assert _notification.notification_type == NotificationType.CANCEL_TRANSFER.value
        assert _notification.priority == 0
        assert _notification.address == self.trader
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 1,
            "from": self.trader,
            "to": self.trader2,
            "data": "TEST_DATA2"
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare"
        }

        _notification_block_number: NotificationBlockNumber = session.query(NotificationBlockNumber).\
            filter(NotificationBlockNumber.notification_type == NotificationType.CANCEL_TRANSFER).\
            filter(NotificationBlockNumber.contract_address == token["address"]).\
            first()
        assert _notification_block_number.latest_block_number >= block_number2

    # <Normal_3>
    # No event logs
    def test_normal_3(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchCancelTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        token = prepare_share_token(self.issuer, exchange_contract, token_list_contract, personal_info_contract, session)

        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)

        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetShare"
        session.add(idx_token_list_item)
        session.commit()

        # Not Transfer
        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        block_number = web3.eth.block_number
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number.latest_block_number >= block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, watcher_factory, session, shared_contract, mocked_company_list):
        watcher = watcher_factory("WatchApplyForTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        token = prepare_share_token(self.issuer, exchange_contract, token_list_contract, personal_info_contract, session)

        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)

        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        # Transfer
        share_apply_for_transfer(self.trader, token, self.trader2, 10, "TEST_DATA1")
        share_cancel_transfer(self.issuer, token, 0, "TEST_DATA1")

        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer
        idx_token_list_item.token_template = "IbetShare"
        session.add(idx_token_list_item)
        session.commit()

        # Run target process
        watcher.loop()

        # Assertion
        _notification = session.query(Notification).order_by(Notification.created).first()
        assert _notification is None

        _notification_block_number = session.query(NotificationBlockNumber).first()
        assert _notification_block_number is None
