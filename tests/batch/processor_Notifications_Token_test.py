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

from datetime import datetime, timezone
from importlib import reload
from typing import TYPE_CHECKING, Callable
from unittest import mock
from unittest.mock import MagicMock

import pytest
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import RPCEndpoint

from app import config
from app.model.db import (
    IDXShareToken,
    IDXTokenListRegister,
    Listing,
    Notification,
    NotificationAttributeValue,
    NotificationBlockNumber,
    NotificationType,
)
from tests.account_config import eth_account
from tests.conftest import DeployedContract, SharedContract, UnitTestAccount
from tests.contract_modules import (
    bond_change_to_redeemed,
    coupon_register_list,
    coupon_transfer_to_exchange,
    coupon_withdraw_from_exchange,
    issue_bond_token,
    issue_coupon_token,
    issue_share_token,
    register_bond_list,
    register_personalinfo,
    register_share_list,
    share_apply_for_transfer,
    share_approve_transfer,
    share_cancel_transfer,
    share_change_to_canceled,
    share_force_lock,
    share_force_unlock,
    share_set_transfer_approval_required,
    transfer_coupon_token,
    transfer_share_token,
    untransferable_share_token,
)

if TYPE_CHECKING:
    from batch.processor_Notifications_Token import EventWatcher

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


@pytest.fixture(scope="function")
def watcher_factory(
    async_session: AsyncSession, shared_contract: SharedContract
) -> Callable[[str], EventWatcher]:
    def _watcher(cls_name):
        config.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]

        from batch import processor_Notifications_Token

        test_module = reload(processor_Notifications_Token)
        test_module.db_session = async_session

        cls = getattr(test_module, cls_name)
        watcher = cls()
        watcher.from_block = web3.eth.block_number
        return watcher

    return _watcher


async def prepare_coupon_token(
    issuer: UnitTestAccount,
    exchange: DeployedContract,
    token_list: DeployedContract,
    async_session: AsyncSession,
):
    # Issue token
    args = {
        "name": "テストクーポン",
        "symbol": "COUPON",
        "totalSupply": 1000000,
        "tradableExchange": exchange["address"],
        "details": "クーポン詳細",
        "returnDetails": "リターン詳細",
        "memo": "クーポンメモ欄",
        "expirationDate": "20191231",
        "transferable": True,
        "contactInformation": "問い合わせ先",
        "privacyPolicy": "プライバシーポリシー",
    }
    token = issue_coupon_token(issuer, args)
    coupon_register_list(issuer, token, token_list)

    _listing = Listing()
    _listing.token_address = token["address"]
    _listing.is_public = True
    _listing.max_holding_quantity = 1000000
    _listing.max_sell_amount = 1000000
    _listing.owner_address = issuer["account_address"]
    async_session.add(_listing)
    await async_session.commit()

    return token


async def prepare_bond_token(
    issuer: UnitTestAccount,
    exchange: DeployedContract,
    token_list: DeployedContract,
    personal_info: DeployedContract,
    async_session: AsyncSession,
):
    # Issue token
    args = {
        "name": "テスト債券",
        "symbol": "BOND",
        "totalSupply": 1000000,
        "tradableExchange": exchange["address"],
        "faceValue": 10000,
        "interestRate": 602,
        "interestPaymentDate1": "0101",
        "interestPaymentDate2": "0201",
        "interestPaymentDate3": "0301",
        "interestPaymentDate4": "0401",
        "interestPaymentDate5": "0501",
        "interestPaymentDate6": "0601",
        "interestPaymentDate7": "0701",
        "interestPaymentDate8": "0801",
        "interestPaymentDate9": "0901",
        "interestPaymentDate10": "1001",
        "interestPaymentDate11": "1101",
        "interestPaymentDate12": "1201",
        "redemptionDate": "20191231",
        "redemptionValue": 10000,
        "returnDate": "20191231",
        "returnAmount": "商品券をプレゼント",
        "purpose": "新商品の開発資金として利用。",
        "memo": "メモ",
        "contactInformation": "問い合わせ先",
        "privacyPolicy": "プライバシーポリシー",
        "personalInfoAddress": personal_info["address"],
        "transferable": True,
        "isRedeemed": False,
        "faceValueCurrency": "JPY",
        "interestPaymentCurrency": "JPY",
        "redemptionValueCurrency": "JPY",
        "baseFxRate": "",
    }
    token = issue_bond_token(issuer, args)
    register_bond_list(issuer, token, token_list)

    _listing = Listing()
    _listing.token_address = token["address"]
    _listing.is_public = True
    _listing.max_holding_quantity = 1000000
    _listing.max_sell_amount = 1000000
    _listing.owner_address = issuer["account_address"]
    async_session.add(_listing)
    await async_session.commit()

    return token


async def prepare_share_token(
    issuer: UnitTestAccount,
    exchange: DeployedContract,
    token_list: DeployedContract,
    personal_info: DeployedContract,
    async_session: AsyncSession,
):
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
        "transferable": True,
    }
    token = issue_share_token(issuer, args)
    register_share_list(issuer, token, token_list)

    _listing = Listing()
    _listing.token_address = token["address"]
    _listing.is_public = True
    _listing.max_holding_quantity = 1000000
    _listing.max_sell_amount = 1000000
    _listing.owner_address = issuer["account_address"]
    async_session.add(_listing)
    await async_session.commit()

    return token


@pytest.mark.asyncio
class TestWatchTransfer:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["deployer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    async def test_normal_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchTransfer")

        exchange_contract = shared_contract["IbetCouponExchange"]
        token_list_contract = shared_contract["TokenList"]

        # Issue token
        token = await prepare_coupon_token(
            self.issuer, exchange_contract, token_list_contract, async_session
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetCoupon"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Emit Transfer event
        transfer_coupon_token(self.issuer, token, self.trader, 100)

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.TRANSFER
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
            "token_name": "テストクーポン",
            "exchange_address": "",
            "token_type": "IbetCoupon",
        }

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.TRANSFER,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Multi event logs
    async def test_normal_2(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchTransfer")

        exchange_contract = shared_contract["IbetCouponExchange"]
        token_list_contract = shared_contract["TokenList"]

        # Issue token
        token = await prepare_coupon_token(
            self.issuer, exchange_contract, token_list_contract, async_session
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetCoupon"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Emit Transfer event
        transfer_coupon_token(self.issuer, token, self.trader, 100)
        transfer_coupon_token(self.issuer, token, self.trader2, 200)

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created)
            )
        ).all()
        assert len(_notification_list) == 2

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.TRANSFER
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
            "token_name": "テストクーポン",
            "exchange_address": "",
            "token_type": "IbetCoupon",
        }

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.TRANSFER
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
            "token_name": "テストクーポン",
            "exchange_address": "",
            "token_type": "IbetCoupon",
        }

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.TRANSFER,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # No event logs
    async def test_normal_3(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchTransfer")

        exchange_contract = shared_contract["IbetCouponExchange"]
        token_list_contract = shared_contract["TokenList"]

        # Issue token
        token = await prepare_coupon_token(
            self.issuer, exchange_contract, token_list_contract, async_session
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetCoupon"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Not emit Transfer event
        pass

        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created).limit(1)
            )
        ).first()
        assert _notification is None

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_4>
    # Transfer from DEX
    async def test_normal_4(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchTransfer")

        exchange_contract = shared_contract["IbetCouponExchange"]
        token_list_contract = shared_contract["TokenList"]

        # Issue token
        token = await prepare_coupon_token(
            self.issuer, exchange_contract, token_list_contract, async_session
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetCoupon"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Transfer to DEX
        coupon_transfer_to_exchange(
            invoker=self.issuer, exchange=exchange_contract, token=token, amount=100
        )

        # Emit Transfer event: Withdraw from DEX
        coupon_withdraw_from_exchange(
            invoker=self.issuer, exchange=exchange_contract, token=token, amount=100
        )

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created)
            )
        ).all()

        assert (
            len(_notification_list) == 1
        )  # Notification from which the DEX is the transferor will not be registered.

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 1, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.TRANSFER
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
            "token_name": "テストクーポン",
            "exchange_address": "",
            "token_type": "IbetCoupon",
        }

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.TRANSFER,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch(
        "web3.eth.async_eth.AsyncEth.get_logs",
        MagicMock(side_effect=Exception()),
    )
    async def test_error_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchTransfer")

        exchange_contract = shared_contract["IbetCouponExchange"]
        token_list_contract = shared_contract["TokenList"]
        token = await prepare_coupon_token(
            self.issuer, exchange_contract, token_list_contract, async_session
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetCoupon"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Run target process
        await watcher.loop()

        # Assertion
        _notification = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created).limit(1)
            )
        ).first()
        assert _notification is None

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number is None


@pytest.mark.asyncio
class TestWatchApplyForTransfer:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["deployer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    async def test_normal_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchApplyForTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Emit ApplyForTransfer event
        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)
        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)
        share_apply_for_transfer(self.trader, token, self.trader2, 100, "TEST_DATA")

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.priority == 0
        assert _notification.address == self.trader2["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 0,
            "from": self.trader["account_address"],
            "to": self.trader2["account_address"],
            "value": 100,
            "data": "TEST_DATA",
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.APPLY_FOR_TRANSFER,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Multi event logs
    async def test_normal_2(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchApplyForTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Emmit ApplyForTransfer event
        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)
        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)
        share_apply_for_transfer(self.trader, token, self.trader2, 10, "TEST_DATA1")
        share_apply_for_transfer(self.trader, token, self.trader2, 20, "TEST_DATA2")

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created)
            )
        ).all()
        assert len(_notification_list) == 2

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.APPLY_FOR_TRANSFER
        assert _notification.priority == 0
        assert _notification.address == self.trader2["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 0,
            "from": self.trader["account_address"],
            "to": self.trader2["account_address"],
            "value": 10,
            "data": "TEST_DATA1",
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.APPLY_FOR_TRANSFER
        assert _notification.priority == 0
        assert _notification.address == self.trader2["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 1,
            "from": self.trader["account_address"],
            "to": self.trader2["account_address"],
            "value": 20,
            "data": "TEST_DATA2",
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.APPLY_FOR_TRANSFER,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # No event logs
    async def test_normal_3(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchApplyForTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Not emit ApplyForTransfer event
        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)
        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created).limit(1)
            )
        ).first()
        assert _notification is None

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch(
        "web3.eth.async_eth.AsyncEth.get_logs",
        MagicMock(side_effect=Exception()),
    )
    async def test_error_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchApplyForTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)

        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        # Transfer
        share_apply_for_transfer(self.trader, token, self.trader2, 10, "TEST_DATA1")

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Run target process
        await watcher.loop()

        # Assertion
        _notification = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created).limit(1)
            )
        ).first()
        assert _notification is None

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number is None


@pytest.mark.asyncio
class TestWatchApproveTransfer:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["deployer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    async def test_normal_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchApproveTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Emit ApproveTransfer event
        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)
        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)
        share_apply_for_transfer(self.trader, token, self.trader2, 100, "TEST_DATA")
        share_approve_transfer(self.issuer, token, 0, "TEST_DATA")

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.APPROVE_TRANSFER
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 0,
            "from": self.trader["account_address"],
            "to": self.trader2["account_address"],
            "data": "TEST_DATA",
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.APPROVE_TRANSFER,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Multi event logs
    async def test_normal_2(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchApproveTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Emit ApproveTransfer event
        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)
        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)
        share_apply_for_transfer(self.trader, token, self.trader2, 10, "TEST_DATA1")
        share_apply_for_transfer(self.trader, token, self.trader2, 20, "TEST_DATA2")
        share_approve_transfer(self.issuer, token, 0, "TEST_DATA1")
        share_approve_transfer(self.issuer, token, 1, "TEST_DATA2")

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created)
            )
        ).all()
        assert len(_notification_list) == 2

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.APPROVE_TRANSFER
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 0,
            "from": self.trader["account_address"],
            "to": self.trader2["account_address"],
            "data": "TEST_DATA1",
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.APPROVE_TRANSFER
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 1,
            "from": self.trader["account_address"],
            "to": self.trader2["account_address"],
            "data": "TEST_DATA2",
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.APPROVE_TRANSFER,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # No event logs
    async def test_normal_3(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchApplyForTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # No emit ApproveTransfer event
        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)
        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created).limit(1)
            )
        ).first()
        assert _notification is None

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch(
        "web3.eth.async_eth.AsyncEth.get_logs",
        MagicMock(side_effect=Exception()),
    )
    async def test_error_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchApplyForTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)

        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        # Transfer
        share_apply_for_transfer(self.trader, token, self.trader2, 10, "TEST_DATA1")
        share_approve_transfer(self.issuer, token, 0, "TEST_DATA1")

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Run target process
        await watcher.loop()

        # Assertion
        _notification = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created).limit(1)
            )
        ).first()
        assert _notification is None

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number is None


@pytest.mark.asyncio
class TestWatchCancelTransfer:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["deployer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    async def test_normal_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchCancelTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Emit CancelTransfer event
        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)
        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)
        share_apply_for_transfer(self.trader, token, self.trader2, 100, "TEST_DATA")
        share_cancel_transfer(self.issuer, token, 0, "TEST_DATA")

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.CANCEL_TRANSFER
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 0,
            "from": self.trader["account_address"],
            "to": self.trader2["account_address"],
            "data": "TEST_DATA",
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.CANCEL_TRANSFER,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Single Token / Multi event logs
    async def test_normal_2(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchCancelTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Emit CancelTransfer event
        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)
        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)
        share_apply_for_transfer(self.trader, token, self.trader2, 10, "TEST_DATA1")
        share_apply_for_transfer(self.trader, token, self.trader2, 20, "TEST_DATA2")
        share_cancel_transfer(self.issuer, token, 0, "TEST_DATA1")
        share_cancel_transfer(self.issuer, token, 1, "TEST_DATA2")

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created)
            )
        ).all()
        assert len(_notification_list) == 2

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.CANCEL_TRANSFER
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 0,
            "from": self.trader["account_address"],
            "to": self.trader2["account_address"],
            "data": "TEST_DATA1",
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.CANCEL_TRANSFER
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 1,
            "from": self.trader["account_address"],
            "to": self.trader2["account_address"],
            "data": "TEST_DATA2",
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.CANCEL_TRANSFER,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # Multi token / Multi event logs
    async def test_normal_3(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchCancelTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token (1)
        token_1 = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token_1["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)
        transfer_share_token(self.issuer, self.trader, token_1, 100)
        share_set_transfer_approval_required(self.issuer, token_1, True)
        share_apply_for_transfer(self.trader, token_1, self.trader2, 10, "TEST_DATA1")
        share_apply_for_transfer(self.trader, token_1, self.trader2, 20, "TEST_DATA2")

        # Issue token (2)
        token_2 = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token_2["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        transfer_share_token(self.issuer, self.trader, token_2, 100)
        share_set_transfer_approval_required(self.issuer, token_2, True)
        share_apply_for_transfer(self.trader, token_2, self.trader2, 10, "TEST_DATA1")
        share_apply_for_transfer(self.trader, token_2, self.trader2, 20, "TEST_DATA2")

        # Emit CancelTransfer event
        share_cancel_transfer(self.issuer, token_1, 0, "TEST_DATA1")
        share_cancel_transfer(self.issuer, token_1, 1, "TEST_DATA2")
        share_cancel_transfer(self.issuer, token_2, 0, "TEST_DATA1")
        share_cancel_transfer(self.issuer, token_2, 1, "TEST_DATA2")

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created)
            )
        ).all()
        assert len(_notification_list) == 4

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 3, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.CANCEL_TRANSFER
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 0,
            "from": self.trader["account_address"],
            "to": self.trader2["account_address"],
            "data": "TEST_DATA1",
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token_1["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 2, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.CANCEL_TRANSFER
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 1,
            "from": self.trader["account_address"],
            "to": self.trader2["account_address"],
            "data": "TEST_DATA2",
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token_1["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number - 1, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.CANCEL_TRANSFER
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 0,
            "from": self.trader["account_address"],
            "to": self.trader2["account_address"],
            "data": "TEST_DATA1",
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token_2["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.CANCEL_TRANSFER
        assert _notification.priority == 0
        assert _notification.address == self.trader["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "index": 1,
            "from": self.trader["account_address"],
            "to": self.trader2["account_address"],
            "data": "TEST_DATA2",
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token_2["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.CANCEL_TRANSFER,
                        NotificationBlockNumber.contract_address == token_1["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_4>
    # No event logs
    async def test_normal_4(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchCancelTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )
        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Not emit CancelTransfer event
        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)
        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        # Run target process
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created).limit(1)
            )
        ).first()
        assert _notification is None

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch(
        "web3.eth.async_eth.AsyncEth.get_logs",
        MagicMock(side_effect=Exception()),
    )
    async def test_error_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchApplyForTransfer")

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.trader2, personal_info_contract)

        transfer_share_token(self.issuer, self.trader, token, 100)
        share_set_transfer_approval_required(self.issuer, token, True)

        # Transfer
        share_apply_for_transfer(self.trader, token, self.trader2, 10, "TEST_DATA1")
        share_cancel_transfer(self.issuer, token, 0, "TEST_DATA1")

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Run target process
        await watcher.loop()

        # Assertion
        _notification = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created).limit(1)
            )
        ).first()
        assert _notification is None

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number is None


@pytest.mark.asyncio
class TestWatchForceLock:
    issuer = eth_account["issuer"]
    lock_account = eth_account["user1"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    async def test_normal_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchForceLock")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Emit ForceLock event
        share_force_lock(
            invoker=self.issuer,
            token=token,
            lock_address=self.lock_account["account_address"],
            account_address=self.issuer["account_address"],
            amount=10,
            data_str="test_data",
        )

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.FORCE_LOCK
        assert _notification.priority == 0
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "accountAddress": self.issuer["account_address"],
            "lockAddress": self.lock_account["account_address"],
            "value": 10,
            "data": "test_data",
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.FORCE_LOCK,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Multi event logs
    async def test_normal_2(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchForceLock")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Emit ForceLock event
        share_force_lock(
            invoker=self.issuer,
            token=token,
            lock_address=self.lock_account["account_address"],
            account_address=self.issuer["account_address"],
            amount=10,
            data_str="test_data",
        )
        share_force_lock(
            invoker=self.issuer,
            token=token,
            lock_address=self.lock_account["account_address"],
            account_address=self.issuer["account_address"],
            amount=10,
            data_str="test_data",
        )

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (await async_session.scalars(select(Notification))).all()
        assert len(_notification_list) == 2

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.FORCE_LOCK,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # No event logs
    async def test_normal_3(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchForceLock")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Not emit ForceLock event
        pass

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (await async_session.scalars(select(Notification))).all()
        assert len(_notification_list) == 0

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch(
        "web3.eth.async_eth.AsyncEth.get_logs",
        MagicMock(side_effect=Exception()),
    )
    async def test_error_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchForceLock")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Run target process
        await watcher.loop()

        # Assertion
        _notification = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created).limit(1)
            )
        ).first()
        assert _notification is None

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number is None


@pytest.mark.asyncio
class TestWatchForceUnlock:
    issuer = eth_account["issuer"]
    lock_account = eth_account["user1"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single event logs
    async def test_normal_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchForceUnlock")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Emit ForceUnlock event
        share_force_lock(
            invoker=self.issuer,
            token=token,
            lock_address=self.lock_account["account_address"],
            account_address=self.issuer["account_address"],
            amount=10,
        )
        share_force_unlock(
            invoker=self.issuer,
            token=token,
            lock_address=self.lock_account["account_address"],
            target=self.issuer["account_address"],
            recipient=self.issuer["account_address"],
            amount=10,
            data_str="test_data",
        )

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification.notification_category == "event_log"
        assert _notification.notification_type == NotificationType.FORCE_UNLOCK
        assert _notification.priority == 0
        assert _notification.address == self.issuer["account_address"]
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "accountAddress": self.issuer["account_address"],
            "lockAddress": self.lock_account["account_address"],
            "recipientAddress": self.issuer["account_address"],
            "value": 10,
            "data": "test_data",
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.FORCE_UNLOCK,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Multi event logs
    async def test_normal_2(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchForceUnlock")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Emit ForceUnlock event
        share_force_lock(
            invoker=self.issuer,
            token=token,
            lock_address=self.lock_account["account_address"],
            account_address=self.issuer["account_address"],
            amount=20,
        )
        share_force_unlock(
            invoker=self.issuer,
            token=token,
            lock_address=self.lock_account["account_address"],
            target=self.issuer["account_address"],
            recipient=self.issuer["account_address"],
            amount=10,
            data_str="test_data",
        )
        share_force_unlock(
            invoker=self.issuer,
            token=token,
            lock_address=self.lock_account["account_address"],
            target=self.issuer["account_address"],
            recipient=self.issuer["account_address"],
            amount=10,
            data_str="test_data",
        )

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (await async_session.scalars(select(Notification))).all()
        assert len(_notification_list) == 2

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.FORCE_UNLOCK,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # No event logs
    async def test_normal_3(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchForceUnlock")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Not emit ForceLock event
        pass

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (await async_session.scalars(select(Notification))).all()
        assert len(_notification_list) == 0

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # ###########################################################################
    # # Error Case
    # ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch(
        "web3.eth.async_eth.AsyncEth.get_logs",
        MagicMock(side_effect=Exception()),
    )
    async def test_error_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchForceUnlock")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Run target process
        await watcher.loop()

        # Assertion
        _notification = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created).limit(1)
            )
        ).first()
        assert _notification is None

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number is None


@pytest.mark.asyncio
class TestWatchChangeToRedeemed:
    issuer = eth_account["issuer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Initial Sync
    async def test_normal_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchChangeToRedeemed")
        exchange_contract = shared_contract["IbetStraightBondExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_bond_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetStraightBond"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification is None

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.CHANGE_TO_REDEEMED,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Single event logs
    async def test_normal_2(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchChangeToRedeemed")
        exchange_contract = shared_contract["IbetStraightBondExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_bond_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetStraightBond"
        async_session.add(idx_token_list_item)

        notification_block_number = NotificationBlockNumber()
        notification_block_number.notification_type = (
            NotificationType.CHANGE_TO_REDEEMED
        )
        notification_block_number.contract_address = token["address"]
        notification_block_number.latest_block_number = web3.eth.block_number
        async_session.add(notification_block_number)
        await async_session.commit()

        # Emit ChangeToRedeemed event
        bond_change_to_redeemed(
            invoker=self.issuer,
            token=token,
        )

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        async_session.expunge_all()

        _notification_list = (await async_session.scalars(select(Notification))).all()
        assert len(_notification_list) == 1
        assert _notification_list[0].notification_category == "event_log"
        assert (
            _notification_list[0].notification_type
            == NotificationType.CHANGE_TO_REDEEMED
        )
        assert _notification_list[0].priority == 0
        assert _notification_list[0].address is None
        assert _notification_list[0].args == {}
        assert _notification_list[0].metainfo == {
            "company_name": "株式会社DEMO",
            "exchange_address": "",
            "token_address": token["address"],
            "token_name": "テスト債券",
            "token_type": "IbetStraightBond",
        }

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.CHANGE_TO_REDEEMED,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # Multi event logs
    async def test_normal_3(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchChangeToRedeemed")
        exchange_contract = shared_contract["IbetStraightBondExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_bond_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetStraightBond"
        async_session.add(idx_token_list_item)

        notification_block_number = NotificationBlockNumber()
        notification_block_number.notification_type = (
            NotificationType.CHANGE_TO_REDEEMED
        )
        notification_block_number.contract_address = token["address"]
        notification_block_number.latest_block_number = web3.eth.block_number
        async_session.add(notification_block_number)
        await async_session.commit()

        # Emit ChangeToRedeemed event
        bond_change_to_redeemed(
            invoker=self.issuer,
            token=token,
        )
        bond_change_to_redeemed(
            invoker=self.issuer,
            token=token,
        )

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        async_session.expunge_all()

        _notification_list = (await async_session.scalars(select(Notification))).all()
        assert len(_notification_list) == 2
        assert _notification_list[0].notification_category == "event_log"
        assert (
            _notification_list[0].notification_type
            == NotificationType.CHANGE_TO_REDEEMED
        )
        assert _notification_list[0].priority == 0
        assert _notification_list[0].address is None
        assert _notification_list[0].args == {}
        assert _notification_list[0].metainfo == {
            "company_name": "株式会社DEMO",
            "exchange_address": "",
            "token_address": token["address"],
            "token_name": "テスト債券",
            "token_type": "IbetStraightBond",
        }
        assert _notification_list[1].notification_category == "event_log"
        assert (
            _notification_list[1].notification_type
            == NotificationType.CHANGE_TO_REDEEMED
        )
        assert _notification_list[1].priority == 0
        assert _notification_list[1].address is None
        assert _notification_list[1].args == {}
        assert _notification_list[1].metainfo == {
            "company_name": "株式会社DEMO",
            "exchange_address": "",
            "token_address": token["address"],
            "token_name": "テスト債券",
            "token_type": "IbetStraightBond",
        }

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.CHANGE_TO_REDEEMED,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_4>
    # No event logs
    async def test_normal_4(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchChangeToRedeemed")
        exchange_contract = shared_contract["IbetStraightBondExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_bond_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetStraightBond"
        async_session.add(idx_token_list_item)

        notification_block_number = NotificationBlockNumber()
        notification_block_number.notification_type = (
            NotificationType.CHANGE_TO_REDEEMED
        )
        notification_block_number.contract_address = token["address"]
        notification_block_number.latest_block_number = web3.eth.block_number
        async_session.add(notification_block_number)
        await async_session.commit()

        # Not emit ChangeToRedeemed event
        pass

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (await async_session.scalars(select(Notification))).all()
        assert len(_notification_list) == 0

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_5>
    # Skip past data on initial sync
    async def test_normal_5(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchChangeToRedeemed")
        exchange_contract = shared_contract["IbetStraightBondExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_bond_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetStraightBond"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Emit ChangeToRedeemed event
        bond_change_to_redeemed(
            invoker=self.issuer,
            token=token,
        )
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (await async_session.scalars(select(Notification))).all()
        assert len(_notification_list) == 0

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # ###########################################################################
    # # Error Case
    # ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch(
        "web3.eth.async_eth.AsyncEth.get_logs",
        MagicMock(side_effect=Exception()),
    )
    async def test_error_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchChangeToRedeemed")
        exchange_contract = shared_contract["IbetStraightBondExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_bond_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetStraightBond"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Run target process
        await watcher.loop()

        # Assertion
        _notification = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created).limit(1)
            )
        ).first()
        assert _notification is None

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number is None


@pytest.mark.asyncio
class TestWatchChangeToCanceled:
    issuer = eth_account["issuer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Initial Sync
    async def test_normal_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchChangeToCanceled")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification = (
            await async_session.scalars(
                select(Notification)
                .where(
                    Notification.notification_id
                    == "0x{:012x}{:06x}{:06x}{:02x}".format(block_number, 0, 0, 0)
                )
                .limit(1)
            )
        ).first()
        assert _notification is None

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.CHANGE_TO_CANCELED,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_2>
    # Single event logs
    async def test_normal_2(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchChangeToCanceled")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)

        notification_block_number = NotificationBlockNumber()
        notification_block_number.notification_type = (
            NotificationType.CHANGE_TO_CANCELED
        )
        notification_block_number.contract_address = token["address"]
        notification_block_number.latest_block_number = web3.eth.block_number
        async_session.add(notification_block_number)
        await async_session.commit()

        # Emit ChangeToCanceled event
        share_change_to_canceled(
            invoker=self.issuer,
            token=token,
        )

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        async_session.expunge_all()

        _notification_list = (await async_session.scalars(select(Notification))).all()
        assert len(_notification_list) == 1
        assert _notification_list[0].notification_category == "event_log"
        assert (
            _notification_list[0].notification_type
            == NotificationType.CHANGE_TO_CANCELED
        )
        assert _notification_list[0].priority == 0
        assert _notification_list[0].address is None
        assert _notification_list[0].args == {}
        assert _notification_list[0].metainfo == {
            "company_name": "株式会社DEMO",
            "exchange_address": "",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "token_type": "IbetShare",
        }

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.CHANGE_TO_CANCELED,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_3>
    # Multi event logs
    async def test_normal_3(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchChangeToCanceled")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)

        notification_block_number = NotificationBlockNumber()
        notification_block_number.notification_type = (
            NotificationType.CHANGE_TO_CANCELED
        )
        notification_block_number.contract_address = token["address"]
        notification_block_number.latest_block_number = web3.eth.block_number
        async_session.add(notification_block_number)
        await async_session.commit()

        # Emit ChangeToCanceled event
        share_change_to_canceled(
            invoker=self.issuer,
            token=token,
        )
        share_change_to_canceled(
            invoker=self.issuer,
            token=token,
        )

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        async_session.expunge_all()

        _notification_list = (await async_session.scalars(select(Notification))).all()
        assert len(_notification_list) == 2
        assert _notification_list[0].notification_category == "event_log"
        assert (
            _notification_list[0].notification_type
            == NotificationType.CHANGE_TO_CANCELED
        )
        assert _notification_list[0].priority == 0
        assert _notification_list[0].address is None
        assert _notification_list[0].args == {}
        assert _notification_list[0].metainfo == {
            "company_name": "株式会社DEMO",
            "exchange_address": "",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "token_type": "IbetShare",
        }
        assert _notification_list[1].notification_category == "event_log"
        assert (
            _notification_list[1].notification_type
            == NotificationType.CHANGE_TO_CANCELED
        )
        assert _notification_list[1].priority == 0
        assert _notification_list[1].address is None
        assert _notification_list[1].args == {}
        assert _notification_list[1].metainfo == {
            "company_name": "株式会社DEMO",
            "exchange_address": "",
            "token_address": token["address"],
            "token_name": "テスト株式",
            "token_type": "IbetShare",
        }

        _notification_block_number: NotificationBlockNumber = (
            await async_session.scalars(
                select(NotificationBlockNumber)
                .where(
                    and_(
                        NotificationBlockNumber.notification_type
                        == NotificationType.CHANGE_TO_CANCELED,
                        NotificationBlockNumber.contract_address == token["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_4>
    # No event logs
    async def test_normal_4(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchChangeToCanceled")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)

        notification_block_number = NotificationBlockNumber()
        notification_block_number.notification_type = (
            NotificationType.CHANGE_TO_CANCELED
        )
        notification_block_number.contract_address = token["address"]
        notification_block_number.latest_block_number = web3.eth.block_number
        async_session.add(notification_block_number)
        await async_session.commit()

        # Not emit ChangeToCanceled event
        pass

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (await async_session.scalars(select(Notification))).all()
        assert len(_notification_list) == 0

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # <Normal_5>
    # Skip past data on initial sync
    async def test_normal_5(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchChangeToCanceled")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Emit ChangeToCanceled event
        share_change_to_canceled(
            invoker=self.issuer,
            token=token,
        )
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])

        # Run target process
        await watcher.loop()

        # Assertion
        block_number = web3.eth.block_number

        _notification_list = (await async_session.scalars(select(Notification))).all()
        assert len(_notification_list) == 0

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number.latest_block_number == block_number

    # ###########################################################################
    # # Error Case
    # ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch(
        "web3.eth.async_eth.AsyncEth.get_logs",
        MagicMock(side_effect=Exception()),
    )
    async def test_error_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchChangeToCanceled")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Run target process
        await watcher.loop()

        # Assertion
        _notification = (
            await async_session.scalars(
                select(Notification).order_by(Notification.created).limit(1)
            )
        ).first()
        assert _notification is None

        _notification_block_number = (
            await async_session.scalars(select(NotificationBlockNumber).limit(1))
        ).first()
        assert _notification_block_number is None


@pytest.mark.asyncio
class TestWatchWatchTransferableAttribute:
    issuer = eth_account["issuer"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Initial Sync
    async def test_normal_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchTransferableAttribute")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Run target process
        await watcher.loop()

        # Assertion
        _notification = (
            await async_session.scalars(select(Notification).limit(1))
        ).first()
        assert _notification is None

        _notification_attribute_value: NotificationAttributeValue = (
            await async_session.scalars(
                select(NotificationAttributeValue)
                .where(
                    and_(
                        NotificationAttributeValue.contract_address == token["address"],
                        NotificationAttributeValue.attribute_key == "transferable",
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_attribute_value.attribute == {"transferable": True}

    # <Normal_2>
    # Attribute not changed
    @pytest.mark.freeze_time(datetime(2025, 7, 31, 1, 35, 0, tzinfo=timezone.utc))
    async def test_normal_2(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchTransferableAttribute")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token = IDXShareToken()
        idx_token.token_address = token["address"]
        idx_token.token_template = "IbetShare"
        idx_token.name = "test_token"
        idx_token.transferable = True
        idx_token.short_term_cache_created = datetime(
            2025, 7, 31, 1, 35, 0, tzinfo=timezone.utc
        )
        async_session.add(idx_token)

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)

        notification_attribute_value = NotificationAttributeValue()
        notification_attribute_value.contract_address = token["address"]
        notification_attribute_value.attribute_key = "transferable"
        notification_attribute_value.attribute = {"transferable": True}
        async_session.add(notification_attribute_value)
        await async_session.commit()

        # Run target process
        await watcher.loop()

        # Assertion
        async_session.expunge_all()
        _notification = (
            await async_session.scalars(select(Notification).limit(1))
        ).first()
        assert _notification is None

        _notification_attribute_value: NotificationAttributeValue = (
            await async_session.scalars(
                select(NotificationAttributeValue)
                .where(
                    and_(
                        NotificationAttributeValue.contract_address == token["address"],
                        NotificationAttributeValue.attribute_key == "transferable",
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_attribute_value.attribute == {"transferable": True}

    # <Normal_3>
    # Attribute changed
    @pytest.mark.freeze_time(datetime(2025, 7, 31, 1, 35, 0, tzinfo=timezone.utc))
    async def test_normal_3(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchTransferableAttribute")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token = IDXShareToken()
        idx_token.token_address = token["address"]
        idx_token.token_template = "IbetShare"
        idx_token.name = "test_token"
        idx_token.transferable = False
        idx_token.short_term_cache_created = datetime(
            2025, 7, 31, 1, 35, 0, tzinfo=timezone.utc
        )
        async_session.add(idx_token)

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)

        notification_attribute_value = NotificationAttributeValue()
        notification_attribute_value.contract_address = token["address"]
        notification_attribute_value.attribute_key = "transferable"
        notification_attribute_value.attribute = {"transferable": True}
        async_session.add(notification_attribute_value)
        await async_session.commit()

        # Run target process
        await watcher.loop()

        # Assertion
        async_session.expunge_all()
        _notification = (
            await async_session.scalars(select(Notification).limit(1))
        ).first()
        attribute_key_hash = Web3.keccak(text="transferable").hex()[0:8]
        assert _notification.notification_category == "attribute_change"
        assert (
            _notification.notification_id[14:]
            == f"{token['address'].replace('0x', '').lower()}{attribute_key_hash}00"
        )
        assert _notification.notification_type == NotificationType.TRANSFERABLE_CHANGED
        assert _notification.priority == 0
        assert _notification.address is None
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "previous": True,
            "current": False,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "test_token",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification_attribute_value: NotificationAttributeValue = (
            await async_session.scalars(
                select(NotificationAttributeValue)
                .where(
                    and_(
                        NotificationAttributeValue.contract_address == token["address"],
                        NotificationAttributeValue.attribute_key == "transferable",
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_attribute_value.attribute == {"transferable": False}

    # <Normal_4>
    # Attribute changed (On chain access)
    @pytest.mark.freeze_time(datetime(2025, 7, 31, 1, 35, 0, tzinfo=timezone.utc))
    async def test_normal_4(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchTransferableAttribute")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        untransferable_share_token(self.issuer, token)

        idx_token = IDXShareToken()
        idx_token.token_address = token["address"]
        idx_token.token_template = "IbetShare"
        idx_token.name = "test_token"
        idx_token.transferable = True  # Cache expired
        idx_token.short_term_cache_created = datetime(
            2025, 7, 30, 1, 35, 0, tzinfo=timezone.utc
        )  # Cache expired
        async_session.add(idx_token)

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)

        notification_attribute_value = NotificationAttributeValue()
        notification_attribute_value.contract_address = token["address"]
        notification_attribute_value.attribute_key = "transferable"
        notification_attribute_value.attribute = {"transferable": True}
        async_session.add(notification_attribute_value)
        await async_session.commit()

        # Run target process
        await watcher.loop()

        # Assertion
        async_session.expunge_all()
        _notification = (
            await async_session.scalars(select(Notification).limit(1))
        ).first()
        attribute_key_hash = Web3.keccak(text="transferable").hex()[0:8]
        assert _notification.notification_category == "attribute_change"
        assert (
            _notification.notification_id[14:]
            == f"{token['address'].replace('0x', '').lower()}{attribute_key_hash}00"
        )
        assert _notification.notification_type == NotificationType.TRANSFERABLE_CHANGED
        assert _notification.priority == 0
        assert _notification.address is None
        assert _notification.block_timestamp is not None
        assert _notification.args == {
            "previous": True,
            "current": False,
        }
        assert _notification.metainfo == {
            "company_name": "株式会社DEMO",
            "token_address": token["address"],
            "token_name": "test_token",
            "exchange_address": "",
            "token_type": "IbetShare",
        }

        _notification_attribute_value: NotificationAttributeValue = (
            await async_session.scalars(
                select(NotificationAttributeValue)
                .where(
                    and_(
                        NotificationAttributeValue.contract_address == token["address"],
                        NotificationAttributeValue.attribute_key == "transferable",
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_attribute_value.attribute == {"transferable": False}

    # ###########################################################################
    # # Error Case
    # ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch(
        "web3.eth.async_eth.AsyncEth.get_logs",
        MagicMock(side_effect=Exception()),
    )
    async def test_error_1(
        self, watcher_factory, async_session, shared_contract, mocked_company_list
    ):
        watcher = watcher_factory("WatchTransferableAttribute")
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = await prepare_share_token(
            self.issuer,
            exchange_contract,
            token_list_contract,
            personal_info_contract,
            async_session,
        )

        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token["address"]
        idx_token_list_item.owner_address = self.issuer["account_address"]
        idx_token_list_item.token_template = "IbetShare"
        async_session.add(idx_token_list_item)
        await async_session.commit()

        # Run target process
        await watcher.loop()

        # Assertion
        async_session.expunge_all()
        _notification = (
            await async_session.scalars(select(Notification).limit(1))
        ).first()
        assert _notification is None

        _notification_attribute_value: NotificationAttributeValue = (
            await async_session.scalars(
                select(NotificationAttributeValue)
                .where(
                    and_(
                        NotificationAttributeValue.contract_address == token["address"],
                        NotificationAttributeValue.attribute_key == "transferable",
                    )
                )
                .limit(1)
            )
        ).first()
        assert _notification_attribute_value is None
