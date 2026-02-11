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

import asyncio
import logging
from typing import Awaitable, Callable, Sequence
from unittest import mock
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from eth_utils.address import to_checksum_address
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from web3 import Web3
from web3.exceptions import ABIEventNotFound, TransactionNotFound
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import EventData

from app import config
from app.errors import ServiceUnavailable
from app.model.db import (
    IDXLock,
    IDXLockedPosition,
    IDXPosition,
    IDXPositionShareBlockNumber,
    IDXUnlock,
    Listing,
)
from batch import indexer_Position_Share
from batch.indexer_Position_Share import LOG, Processor, main
from tests.account_config import eth_account
from tests.helpers import IbetShareTestHelper, PersonalInfoHelper
from tests.helpers.ibet_exchange_helpers import (
    abort_security_token_delivery,
    confirm_security_token_delivery,
    create_security_token_delivery,
    create_security_token_escrow,
    finish_security_token_dvlivery,
    finish_security_token_escrow,
    get_latest_security_delivery_id,
    get_latest_security_escrow_id,
)
from tests.types import DeployedContract, SharedContract, UnitTestAccount

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


@pytest.fixture(scope="session", autouse=True)
def test_module(shared_contract: SharedContract):
    indexer_Position_Share.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"][
        "address"
    ]


@pytest.fixture(scope="function")
def main_func():
    LOG = logging.getLogger("ibet_wallet_batch")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield main
    LOG.propagate = False
    LOG.setLevel(default_log_level)


@pytest_asyncio.fixture(scope="function")
async def processor() -> Processor:
    processor = Processor()
    await processor.initial_sync()
    return processor


@pytest.mark.asyncio
class TestProcessor:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["agent"]

    @staticmethod
    def issue_token_share(
        issuer: UnitTestAccount,
        exchange_contract_address: str,
        personal_info_contract_address: str,
        token_list: DeployedContract,
    ):
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
            "transferable": True,
            "requirePersonalInfoRegistered": False,
        }
        token = IbetShareTestHelper.issue(issuer["account_address"], args)
        IbetShareTestHelper.register_token_list(
            issuer["account_address"],
            token.address,
            token_list["address"],
        )
        return token

    @staticmethod
    def listing_token(token_address: str, session: Session):
        _listing = Listing()
        _listing.token_address = token_address
        _listing.is_public = True
        _listing.max_holding_quantity = 1000000
        _listing.max_sell_amount = 1000000
        _listing.owner_address = TestProcessor.issuer["account_address"]
        session.add(_listing)
        session.commit()

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Single Token
    # Single event logs
    # - Transfer
    async def test_normal_1(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        # Transfer
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            10000,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 2

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.issuer["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.trader["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

    # <Normal_2>
    # Single Token
    # Multi event logs
    # - Transfer
    async def test_normal_2(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        token = self.issue_token_share(
            self.issuer,
            escrow_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        # Transfer
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            escrow_contract["address"],
            10000,
        )
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            3000,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 2

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.issuer["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000 - 3000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 10000
        assert _position.exchange_commitment == 0

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.trader["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 3000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

    # <Normal_3>
    # Multi Token
    # Multi event logs
    # - Transfer
    async def test_normal_3(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)
        personal_info_contract = shared_contract["PersonalInfo"]
        token2 = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token2.address, session)

        # Transfer
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            10000,
        )
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader2["account_address"],
            3000,
        )
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token2.address,
            self.trader["account_address"],
            5000,
        )
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token2.address,
            self.trader2["account_address"],
            3000,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 6

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.trader["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.trader2["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 3000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.issuer["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000 - 3000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token2.address,
                    IDXPosition.account_address == self.trader["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token2.address
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 5000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token2.address,
                    IDXPosition.account_address == self.trader2["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token2.address
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 3000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token2.address,
                    IDXPosition.account_address == self.issuer["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None

        assert _position.token_address == token2.address
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 5000 - 3000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

    # <Normal_4_1>
    # Single Token
    # Single event logs
    # - Lock
    @pytest.mark.parametrize("is_old_token", [False, True])
    async def test_normal_4_1(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        session: Session,
        is_old_token: bool,
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        # Lock
        IbetShareTestHelper.lock_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            1500,
            '{"message": "garnishment"}',
        )
        IbetShareTestHelper.lock_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            1500,
            '{"message": "ibet_wst_bridge"}',
        )
        IbetShareTestHelper.lock_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            1500,
            '{"message": "inheritance"}',
        )

        # Run target process
        block_number = web3.eth.block_number
        if is_old_token:
            with mock.patch(
                "web3.eth.async_eth.AsyncEth.get_transaction",
                MagicMock(side_effect=TransactionNotFound(message="")),
            ):
                await processor.sync_new_logs()
        else:
            await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 1

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

        _position = _position_list[0]
        assert _position.token_address == token.address
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 4500
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

        _locked_list = session.scalars(
            select(IDXLockedPosition).order_by(IDXLockedPosition.created)
        ).all()
        assert len(_locked_list) == 1

        _locked1 = _locked_list[0]
        assert _locked1.token_address == token.address
        assert _locked1.lock_address == self.trader["account_address"]
        assert _locked1.account_address == self.issuer["account_address"]
        assert _locked1.value == 4500

        _lock_list = session.scalars(select(IDXLock).order_by(IDXLock.id)).all()
        assert len(_lock_list) == 3

        _lock1 = _lock_list[0]
        assert _lock1.id == 1
        assert _lock1.token_address == token.address
        assert _lock1.lock_address == self.trader["account_address"]
        assert _lock1.account_address == self.issuer["account_address"]
        assert _lock1.value == 1500
        assert _lock1.data == {"message": "garnishment"}
        assert _lock1.is_forced is False
        _lock2 = _lock_list[1]
        assert _lock2.id == 2
        assert _lock2.token_address == token.address
        assert _lock2.lock_address == self.trader["account_address"]
        assert _lock2.account_address == self.issuer["account_address"]
        assert _lock2.value == 1500
        assert _lock2.data == {"message": "ibet_wst_bridge"}
        assert _lock2.is_forced is False
        _lock3 = _lock_list[2]
        assert _lock3.id == 3
        assert _lock3.token_address == token.address
        assert _lock3.lock_address == self.trader["account_address"]
        assert _lock3.account_address == self.issuer["account_address"]
        assert _lock3.value == 1500
        assert _lock3.data == {}
        assert _lock3.is_forced is False

    # <Normal_4_2>
    # Single Token
    # Single event logs
    # - ForceLock
    @pytest.mark.parametrize("is_old_token", [False, True])
    async def test_normal_4_2(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        session: Session,
        is_old_token: bool,
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            3000,
        )

        # ForceLock
        IbetShareTestHelper.force_lock_token(
            self.issuer["account_address"],
            token.address,
            self.issuer["account_address"],
            self.trader["account_address"],
            1500,
            '{"message": "force_lock"}',
        )
        IbetShareTestHelper.force_lock_token(
            self.issuer["account_address"],
            token.address,
            self.issuer["account_address"],
            self.trader["account_address"],
            1500,
            '{"message": "force_lock"}',
        )

        # Run target process
        block_number = web3.eth.block_number
        if is_old_token:
            with mock.patch(
                "web3.eth.async_eth.AsyncEth.get_transaction",
                MagicMock(side_effect=TransactionNotFound(message="")),
            ):
                await processor.sync_new_logs()
        else:
            await processor.sync_new_logs()

        # Assertion
        _position_issuer = session.scalars(
            select(IDXPosition)
            .where(IDXPosition.account_address == self.issuer["account_address"])
            .limit(1)
        ).first()
        assert _position_issuer is not None
        assert _position_issuer.token_address == token.address
        assert _position_issuer.account_address == self.issuer["account_address"]
        assert _position_issuer.balance == 1000000 - 3000
        assert _position_issuer.pending_transfer == 0
        assert _position_issuer.exchange_balance == 0
        assert _position_issuer.exchange_commitment == 0

        _position_trader = session.scalars(
            select(IDXPosition)
            .where(IDXPosition.account_address == self.trader["account_address"])
            .limit(1)
        ).first()
        assert _position_trader is not None
        assert _position_trader.token_address == token.address
        assert _position_trader.account_address == self.trader["account_address"]
        assert _position_trader.balance == 0
        assert _position_trader.pending_transfer == 0
        assert _position_trader.exchange_balance == 0
        assert _position_trader.exchange_commitment == 0

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

        _locked_list: Sequence[IDXLockedPosition] = session.scalars(
            select(IDXLockedPosition).order_by(IDXLockedPosition.created)
        ).all()
        assert len(_locked_list) == 1
        _locked1 = _locked_list[0]
        assert _locked1.token_address == token.address
        assert _locked1.lock_address == self.issuer["account_address"]
        assert _locked1.account_address == self.trader["account_address"]
        assert _locked1.value == 3000

        _lock_list: Sequence[IDXLock] = session.scalars(
            select(IDXLock).order_by(IDXLock.id)
        ).all()
        assert len(_lock_list) == 2
        _lock1 = _lock_list[0]
        assert _lock1.id == 1
        assert _lock1.token_address == token.address
        assert _lock1.msg_sender == self.issuer["account_address"]
        assert _lock1.lock_address == self.issuer["account_address"]
        assert _lock1.account_address == self.trader["account_address"]
        assert _lock1.value == 1500
        assert _lock1.data == {"message": "force_lock"}
        assert _lock1.is_forced is True
        _lock2 = _lock_list[1]
        assert _lock2.id == 2
        assert _lock2.token_address == token.address
        assert _lock2.msg_sender == self.issuer["account_address"]
        assert _lock2.lock_address == self.issuer["account_address"]
        assert _lock2.account_address == self.trader["account_address"]
        assert _lock2.value == 1500
        assert _lock2.data == {"message": "force_lock"}
        assert _lock2.is_forced is True

    # <Normal_5_1>
    # Single Token
    # Single event logs
    # - Unlock
    @pytest.mark.parametrize("is_old_token", [False, True])
    async def test_normal_5_1(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        session: Session,
        is_old_token: bool,
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        # Lock
        IbetShareTestHelper.lock_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            3000,
            '{"message": "garnishment"}',
        )

        # Unlock
        IbetShareTestHelper.unlock_token(
            self.trader["account_address"],
            token.address,
            self.issuer["account_address"],
            self.trader2["account_address"],
            100,
            '{"message": "garnishment"}',
        )

        # Run target process
        block_number = web3.eth.block_number
        if is_old_token:
            with mock.patch(
                "web3.eth.async_eth.AsyncEth.get_transaction",
                MagicMock(side_effect=TransactionNotFound(message="")),
            ):
                await processor.sync_new_logs()
        else:
            await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 2

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.issuer["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 3000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.trader2["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 100
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

        _locked_list = session.scalars(
            select(IDXLockedPosition).order_by(IDXLockedPosition.created)
        ).all()
        assert len(_locked_list) == 1
        _locked = _locked_list[0]
        assert _locked.token_address == token.address
        assert _locked.lock_address == self.trader["account_address"]
        assert _locked.account_address == self.issuer["account_address"]
        assert _locked.value == 2900

        _lock_list = session.scalars(select(IDXLock).order_by(IDXLock.id)).all()
        assert len(_lock_list) == 1
        _lock1 = _lock_list[0]
        assert _lock1.id == 1
        assert _lock1.token_address == token.address
        assert _lock1.msg_sender == self.issuer["account_address"]
        assert _lock1.lock_address == self.trader["account_address"]
        assert _lock1.account_address == self.issuer["account_address"]
        assert _lock1.value == 3000
        assert _lock1.data == {"message": "garnishment"}

        _unlock_list = session.scalars(select(IDXUnlock).order_by(IDXUnlock.id)).all()
        assert len(_unlock_list) == 1
        _unlock1 = _unlock_list[0]
        assert _unlock1.id == 1
        assert _unlock1.token_address == token.address
        assert _unlock1.msg_sender == self.trader["account_address"]
        assert _unlock1.lock_address == self.trader["account_address"]
        assert _unlock1.account_address == self.issuer["account_address"]
        assert _unlock1.recipient_address == self.trader2["account_address"]
        assert _unlock1.value == 100
        assert _unlock1.data == {"message": "garnishment"}
        assert _unlock1.is_forced is False

    # <Normal_5_2>
    # Single Token
    # Single event logs
    # - ForceUnlock
    @pytest.mark.parametrize("is_old_token", [False, True])
    async def test_normal_5_2(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        session: Session,
        is_old_token: bool,
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        # Lock
        IbetShareTestHelper.lock_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            3000,
            '{"message": "garnishment"}',
        )

        # Unlock
        IbetShareTestHelper.force_unlock_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            self.issuer["account_address"],
            self.trader2["account_address"],
            100,
            '{"message": "garnishment"}',
        )

        # Run target process
        block_number = web3.eth.block_number
        if is_old_token:
            with mock.patch(
                "web3.eth.async_eth.AsyncEth.get_transaction",
                MagicMock(side_effect=TransactionNotFound(message="")),
            ):
                await processor.sync_new_logs()
        else:
            await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 2

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.issuer["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 3000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.trader2["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 100
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

        _locked_list = session.scalars(
            select(IDXLockedPosition).order_by(IDXLockedPosition.created)
        ).all()
        assert len(_locked_list) == 1
        _locked = _locked_list[0]
        assert _locked.token_address == token.address
        assert _locked.lock_address == self.trader["account_address"]
        assert _locked.account_address == self.issuer["account_address"]
        assert _locked.value == 2900

        _lock_list = session.scalars(select(IDXLock).order_by(IDXLock.id)).all()
        assert len(_lock_list) == 1
        _lock1 = _lock_list[0]
        assert _lock1.id == 1
        assert _lock1.token_address == token.address
        assert _lock1.msg_sender == self.issuer["account_address"]
        assert _lock1.lock_address == self.trader["account_address"]
        assert _lock1.account_address == self.issuer["account_address"]
        assert _lock1.value == 3000
        assert _lock1.data == {"message": "garnishment"}

        _unlock_list = session.scalars(select(IDXUnlock).order_by(IDXUnlock.id)).all()
        assert len(_unlock_list) == 1
        _unlock1 = _unlock_list[0]
        assert _unlock1.id == 1
        assert _unlock1.token_address == token.address
        assert _unlock1.msg_sender == self.issuer["account_address"]
        assert _unlock1.lock_address == self.trader["account_address"]
        assert _unlock1.account_address == self.issuer["account_address"]
        assert _unlock1.recipient_address == self.trader2["account_address"]
        assert _unlock1.value == 100
        assert _unlock1.data == {"message": "garnishment"}
        assert _unlock1.is_forced is True

    # <Normal_5_3>
    # Single Token
    # Single event logs
    # - ForceChangeLockedAccount
    @pytest.mark.parametrize("is_old_token", [False, True])
    async def test_normal_5_3(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        session: Session,
        is_old_token: bool,
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        # Transfer
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            3000,
        )

        # Lock
        IbetShareTestHelper.lock_token(
            self.trader["account_address"],
            token.address,
            self.issuer["account_address"],
            3000,
            '{"message": "garnishment"}',
        )

        # ForceChangeLockedAccount
        IbetShareTestHelper.force_change_locked_account(
            self.issuer["account_address"],
            token.address,
            self.issuer["account_address"],  # lock address
            self.trader["account_address"],  # before account address
            self.trader2["account_address"],  # after account address
            100,
            '{"message": "ibet_wst_bridge"}',
        )

        # Run target process
        block_number = web3.eth.block_number
        if is_old_token:
            with mock.patch(
                "web3.eth.async_eth.AsyncEth.get_transaction",
                MagicMock(side_effect=TransactionNotFound(message="")),
            ):
                await processor.sync_new_logs()
        else:
            await processor.sync_new_logs()

        # Assertion
        _position_issuer = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.issuer["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position_issuer is not None
        assert _position_issuer.token_address == token.address
        assert _position_issuer.account_address == self.issuer["account_address"]
        assert _position_issuer.balance == 1000000 - 3000
        assert _position_issuer.pending_transfer == 0
        assert _position_issuer.exchange_balance == 0
        assert _position_issuer.exchange_commitment == 0

        _position_trader_1 = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.trader["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position_trader_1 is not None
        assert _position_trader_1.token_address == token.address
        assert _position_trader_1.account_address == self.trader["account_address"]
        assert _position_trader_1.balance == 0
        assert _position_trader_1.pending_transfer == 0
        assert _position_trader_1.exchange_balance == 0
        assert _position_trader_1.exchange_commitment == 0

        _position_trader_2 = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.trader2["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position_trader_2 is not None
        assert _position_trader_2.token_address == token.address
        assert _position_trader_2.account_address == self.trader2["account_address"]
        assert _position_trader_2.balance == 0
        assert _position_trader_2.pending_transfer == 0
        assert _position_trader_2.exchange_balance == 0
        assert _position_trader_2.exchange_commitment == 0

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

        _locked_list = session.scalars(
            select(IDXLockedPosition).order_by(IDXLockedPosition.created)
        ).all()
        assert len(_locked_list) == 2
        _locked = _locked_list[0]
        assert _locked.token_address == token.address
        assert _locked.lock_address == self.issuer["account_address"]
        assert _locked.account_address == self.trader["account_address"]
        assert _locked.value == 2900
        _locked = _locked_list[1]
        assert _locked.token_address == token.address
        assert _locked.lock_address == self.issuer["account_address"]
        assert _locked.account_address == self.trader2["account_address"]
        assert _locked.value == 100

        _lock_list = session.scalars(select(IDXLock).order_by(IDXLock.id)).all()
        assert len(_lock_list) == 2
        _lock1 = _lock_list[0]
        assert _lock1.id == 1
        assert _lock1.token_address == token.address
        assert _lock1.msg_sender == self.trader["account_address"]
        assert _lock1.lock_address == self.issuer["account_address"]
        assert _lock1.account_address == self.trader["account_address"]
        assert _lock1.value == 3000
        assert _lock1.data == {"message": "garnishment"}
        _lock2 = _lock_list[1]
        assert _lock2.id == 2
        assert _lock2.token_address == token.address
        assert _lock2.msg_sender == self.issuer["account_address"]
        assert _lock2.lock_address == self.issuer["account_address"]
        assert _lock2.account_address == self.trader2["account_address"]
        assert _lock2.value == 100
        assert _lock2.data == {"message": "ibet_wst_bridge"}

        _unlock_list = session.scalars(select(IDXUnlock).order_by(IDXUnlock.id)).all()
        assert len(_unlock_list) == 1
        _unlock1 = _unlock_list[0]
        assert _unlock1.id == 1
        assert _unlock1.token_address == token.address
        assert _unlock1.msg_sender == self.issuer["account_address"]
        assert _unlock1.lock_address == self.issuer["account_address"]
        assert _unlock1.account_address == self.trader["account_address"]
        assert _unlock1.recipient_address == self.trader2["account_address"]
        assert _unlock1.value == 100
        assert _unlock1.data == {"message": "ibet_wst_bridge"}
        assert _unlock1.is_forced is True

    # <Normal_6>
    # Single Token
    # Single event logs
    # - Issue(add balance)
    async def test_normal_6(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        # Issue(add balance)
        IbetShareTestHelper.mint(
            self.issuer["account_address"],
            token.address,
            self.issuer["account_address"],
            50000,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 1

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

        _position = _position_list[0]
        assert _position.token_address == token.address
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 + 50000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

    # <Normal_7>
    # Single Token
    # Single event logs
    # - Redeem
    async def test_normal_7(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        # Redeem
        IbetShareTestHelper.burn(
            self.issuer["account_address"],
            token.address,
            self.issuer["account_address"],
            50000,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 1

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

        _position = _position_list[0]
        assert _position.token_address == token.address
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 50000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

    # <Normal_8>
    # Single Token
    # Single event logs
    # - Apply For Transfer
    async def test_normal_8(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        # Transfer
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            10000,
        )

        # Apply For Transfer
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"], token.address, True
        )
        IbetShareTestHelper.apply_for_token_transfer(
            self.trader["account_address"],
            token.address,
            self.trader2["account_address"],
            2000,
            "test",
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 2

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.issuer["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.trader["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000 - 2000
        assert _position.pending_transfer == 2000
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_9>
    # Single Token
    # Single event logs
    # - Approve Transfer
    async def test_normal_9(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        PersonalInfoHelper.register(
            self.trader["account_address"],
            personal_info_contract["address"],
            self.issuer["account_address"],
        )
        PersonalInfoHelper.register(
            self.trader2["account_address"],
            personal_info_contract["address"],
            self.issuer["account_address"],
        )

        # Transfer
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            10000,
        )

        # Apply For Transfer
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"], token.address, True
        )
        IbetShareTestHelper.apply_for_token_transfer(
            self.trader["account_address"],
            token.address,
            self.trader2["account_address"],
            2000,
            "test",
        )

        # Approve
        IbetShareTestHelper.approve_token_transfer(
            self.issuer["account_address"], token.address, 0, "test"
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 3

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.issuer["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.trader2["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 2000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.trader["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000 - 2000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

    # <Normal_10>
    # Single Token
    # Single event logs
    # - Cancel Transfer
    async def test_normal_10(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        PersonalInfoHelper.register(
            self.trader["account_address"],
            personal_info_contract["address"],
            self.issuer["account_address"],
        )
        PersonalInfoHelper.register(
            self.trader2["account_address"],
            personal_info_contract["address"],
            self.issuer["account_address"],
        )

        # Transfer
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            10000,
        )

        # Apply For Transfer
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"], token.address, True
        )
        IbetShareTestHelper.apply_for_token_transfer(
            self.trader["account_address"],
            token.address,
            self.trader2["account_address"],
            2000,
            "test",
        )

        # Cancel
        IbetShareTestHelper.cancel_token_transfer_application(
            self.trader["account_address"], token.address, 0, "test"
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 2

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.issuer["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.trader["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

    # <Normal_11>
    # Single Token
    # Multi event with Escrow logs
    # - CreateEscrow
    # - EscrowFinished
    # - CreateEscrow
    async def test_normal_11(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            escrow_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        # Deposit and Escrow
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            escrow_contract["address"],
            10000,
        )
        create_security_token_escrow(
            self.issuer,
            {"address": escrow_contract["address"]},
            {"address": token.address},
            self.trader["account_address"],
            self.issuer["account_address"],
            200,
        )
        finish_security_token_escrow(
            self.issuer,
            {"address": escrow_contract["address"]},
            get_latest_security_escrow_id({"address": escrow_contract["address"]}),
        )
        create_security_token_escrow(
            self.issuer,
            {"address": escrow_contract["address"]},
            {"address": token.address},
            self.trader["account_address"],
            self.issuer["account_address"],
            300,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 2

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.issuer["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 10000 - 200 - 300
        assert _position.exchange_commitment == 300

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.trader["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 0
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 200
        assert _position.exchange_commitment == 0

    # <Normal_12>
    # Single Token
    # Multi event with DVP logs
    # - DeliveryCreated
    # - DeliveryCanceled
    # - DeliveryFinished
    # - DeliveryAborted
    async def test_normal_12(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        dvp_contract = shared_contract["IbetSecurityTokenDVP"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            dvp_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        # Deposit and Create Delivery
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            dvp_contract["address"],
            10000,
        )
        create_security_token_delivery(
            self.issuer,
            {"address": dvp_contract["address"]},
            {"address": token.address},
            self.trader["account_address"],
            self.issuer["account_address"],
            200,
        )
        confirm_security_token_delivery(
            self.trader,
            {"address": dvp_contract["address"]},
            get_latest_security_delivery_id({"address": dvp_contract["address"]}),
        )
        finish_security_token_dvlivery(
            self.issuer,
            {"address": dvp_contract["address"]},
            get_latest_security_delivery_id({"address": dvp_contract["address"]}),
        )
        create_security_token_delivery(
            self.issuer,
            {"address": dvp_contract["address"]},
            {"address": token.address},
            self.trader["account_address"],
            self.issuer["account_address"],
            300,
        )
        confirm_security_token_delivery(
            self.trader,
            {"address": dvp_contract["address"]},
            get_latest_security_delivery_id({"address": dvp_contract["address"]}),
        )
        abort_security_token_delivery(
            self.issuer,
            {"address": dvp_contract["address"]},
            get_latest_security_delivery_id({"address": dvp_contract["address"]}),
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _position_issuer = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.issuer["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position_issuer is not None
        assert _position_issuer.token_address == token.address
        assert _position_issuer.account_address == self.issuer["account_address"]
        assert _position_issuer.balance == 1000000 - 10000
        assert _position_issuer.pending_transfer == 0
        assert _position_issuer.exchange_balance == 10000 - 200
        assert _position_issuer.exchange_commitment == 0

        _position_trader = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.trader["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position_trader is not None
        assert _position_trader.token_address == token.address
        assert _position_trader.account_address == self.trader["account_address"]
        assert _position_trader.balance == 0
        assert _position_trader.pending_transfer == 0
        assert _position_trader.exchange_balance == 200
        assert _position_trader.exchange_commitment == 0

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_13>
    # No event logs
    async def test_normal_13(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        # Not Event
        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 0

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_14>
    # Not listing Token is NOT indexed,
    # and indexed properly after listing
    async def test_normal_14(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )

        # Transfer
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            10000,
        )

        # Run target process
        await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 0

        _idx_position_share_block_numbers: Sequence[IDXPositionShareBlockNumber] = (
            session.scalars(
                select(IDXPositionShareBlockNumber).where(
                    IDXPositionShareBlockNumber.token_address == token.address
                )
            ).all()
        )
        assert len(_idx_position_share_block_numbers) == 0

        # Listing
        self.listing_token(token.address, session)

        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        session.rollback()
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 2

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_15>
    # Single Token
    # Multi event logs
    # - Transfer
    # Duplicate events to be removed
    async def test_normal_15(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        from_block = web3.eth.block_number
        for _ in range(0, 5):
            # Transfer
            IbetShareTestHelper.transfer_token(
                self.issuer["account_address"],
                token.address,
                self.trader["account_address"],
                10000,
            )
        to_block = web3.eth.block_number

        # Get events for token address
        events: list[EventData] = token.events.Transfer.get_logs(
            from_block=from_block, to_block=to_block
        )
        # Ensure 5 events squashed to 2 events
        assert len(events) == 5
        filtered_events = processor.remove_duplicate_event_by_token_account_desc(
            events, ["from", "to"]
        )
        assert len(filtered_events) == 2

    # <Normal_16>
    # When stored index is 9,999,999 and current block number is 19,999,999,
    # then processor must process "__sync_all" method 10 times.
    async def test_normal_16(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        token_list_contract = shared_contract["TokenList"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        personal_info_contract = shared_contract["PersonalInfo"]

        current_block_number = 20000000 - 1
        latest_block_number = 10000000 - 1

        mock_lib = MagicMock()

        token = self.issue_token_share(
            self.issuer,
            escrow_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
        )

        # Setting current block number to 19,999,999
        self.listing_token(token.address, session)
        block_number_mock = AsyncMock()
        block_number_mock.return_value = current_block_number
        self.listing_token(token.address, session)
        with mock.patch(
            "web3.eth.async_eth.AsyncEth.block_number", block_number_mock()
        ):
            with mock.patch.object(
                Processor, "_Processor__sync_all", return_value=mock_lib
            ) as __sync_all_mock:
                idx_position_share_block_number = IDXPositionShareBlockNumber()
                idx_position_share_block_number.token_address = token.address
                idx_position_share_block_number.exchange_address = escrow_contract[
                    "address"
                ]
                # Setting stored index to 9,999,999
                idx_position_share_block_number.latest_block_number = (
                    latest_block_number
                )
                session.merge(idx_position_share_block_number)
                session.commit()
                __sync_all_mock.return_value = None
                await processor.initial_sync()
                # Then processor call "__sync_all" method 10 times.
                assert __sync_all_mock.call_count == 10

        with mock.patch(
            "web3.eth.async_eth.AsyncEth.block_number", block_number_mock()
        ):
            with mock.patch.object(
                Processor, "_Processor__sync_all", return_value=mock_lib
            ) as __sync_all_mock:
                # Stored index is 19,999,999
                __sync_all_mock.return_value = None
                await processor.sync_new_logs()
                # Then processor call "__sync_all" method once.
                assert __sync_all_mock.call_count == 1

        new_token = self.issue_token_share(
            self.issuer,
            escrow_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(new_token.address, session)

        with mock.patch(
            "web3.eth.async_eth.AsyncEth.block_number", block_number_mock()
        ):
            with mock.patch.object(
                Processor, "_Processor__sync_all", return_value=mock_lib
            ) as __sync_all_mock:
                # Stored index is 19,999,999
                __sync_all_mock.return_value = None
                await processor.sync_new_logs()
                # Then processor call "__sync_all" method 20 times.
                assert __sync_all_mock.call_count == 20

    # <Normal_17>
    # Single Token
    # Multi event logs (Over 1000)
    # - Transfer
    async def test_normal_17(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            escrow_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        # Transfer
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            escrow_contract["address"],
            10000,
        )

        for i in range(1001):
            IbetShareTestHelper.force_transfer_token(
                self.issuer["account_address"],
                token.address,
                self.issuer["account_address"],
                to_checksum_address(f"0x{hex(i)[2:].zfill(40)}"),
                1,
            )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 1001

        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.latest_block_number == block_number

        _position = session.scalars(
            select(IDXPosition)
            .where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.account_address == self.issuer["account_address"],
                )
            )
            .limit(1)
        ).first()
        assert _position is not None
        assert _position.token_address == token.address
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000 - 1001
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 10000
        assert _position.exchange_commitment == 0

        _positions: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).where(
                and_(
                    IDXPosition.token_address == token.address,
                    IDXPosition.balance == 1,
                )
            )
        ).all()
        assert len(_positions) == 1000

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1>: ABIEventNotFound occurs in __sync_xx method.
    # <Error_2_1>: ServiceUnavailable occurs in "initial_sync" / "sync_new_logs".
    # <Error_2_2>: SQLAlchemyError occurs in "initial_sync" / "sync_new_logs".
    # <Error_3>: ServiceUnavailable occurs and is handled in mainloop.

    # <Error_1>: ABIEventNotFound occurs in __sync_xx method.
    @mock.patch(
        "web3.eth.async_eth.AsyncEth.get_logs",
        MagicMock(side_effect=ABIEventNotFound()),
    )
    async def test_error_1(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        # Transfer
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            10000,
        )

        block_number_current = web3.eth.block_number
        # Run initial sync
        await processor.initial_sync()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 0

        # Latest_block is incremented in "initial_sync" process.
        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert (
            _idx_position_share_block_number.latest_block_number == block_number_current
        )

        # Transfer
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            10000,
        )

        block_number_current = web3.eth.block_number
        # Run target process
        await processor.sync_new_logs()

        # Run target process
        await processor.sync_new_logs()

        # Clear cache in DB session.
        session.rollback()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 0

        # Latest_block is incremented in "sync_new_logs" process.
        _idx_position_share_block_number = session.scalars(
            select(IDXPositionShareBlockNumber)
            .where(IDXPositionShareBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_share_block_number is not None
        assert (
            _idx_position_share_block_number.latest_block_number == block_number_current
        )

    # <Error_2_1>: ServiceUnavailable occurs in "initial_sync" / "sync_new_logs".
    async def test_error_2_1(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        session: Session,
        caplog: pytest.LogCaptureFixture,
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        # Transfer
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            10000,
        )

        # Expect that initial_sync() raises ServiceUnavailable.
        with (
            mock.patch(
                "web3.AsyncWeb3.AsyncHTTPProvider.make_request",
                MagicMock(side_effect=ServiceUnavailable()),
            ),
            pytest.raises(ServiceUnavailable),
        ):
            await processor.initial_sync()

        # Clear cache in DB session.
        session.rollback()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 0

        # Any latest_block is not saved in "initial_sync" process when ServiceUnavailable occurs.
        _idx_position_share_block_number: Sequence[IDXPositionShareBlockNumber] = (
            session.scalars(select(IDXPositionShareBlockNumber)).all()
        )
        assert len(_idx_position_share_block_number) == 0

        # Clear cache in DB session.
        session.rollback()

        # Transfer
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            10000,
        )

        # Expect that sync_new_logs() raises ServiceUnavailable.
        with (
            mock.patch(
                "web3.AsyncWeb3.AsyncHTTPProvider.make_request",
                MagicMock(side_effect=ServiceUnavailable()),
            ),
            pytest.raises(ServiceUnavailable),
        ):
            await processor.sync_new_logs()

        # Clear cache in DB session.
        session.rollback()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 0

        # Latest_block is NOT incremented in "sync_new_logs" process.
        _idx_position_share_block_number: Sequence[IDXPositionShareBlockNumber] = (
            session.scalars(select(IDXPositionShareBlockNumber)).all()
        )
        assert len(_idx_position_share_block_number) == 0

        assert 0 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.ERROR,
                "An exception occurred during event synchronization",
            )
        )

    # <Error_2_2>: SQLAlchemyError occurs in "initial_sync" / "sync_new_logs".
    async def test_error_2_2(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        session: Session,
        caplog: pytest.LogCaptureFixture,
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract,
        )
        self.listing_token(token.address, session)

        # Transfer
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            10000,
        )

        # Expect that initial_sync() raises SQLAlchemyError.
        with (
            mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()),
            pytest.raises(SQLAlchemyError),
        ):
            await processor.initial_sync()

        # Clear cache in DB session.
        session.rollback()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 0

        # Any latest_block is not saved in "initial_sync" process when SQLAlchemyError occurs.
        _idx_position_share_block_number: Sequence[IDXPositionShareBlockNumber] = (
            session.scalars(select(IDXPositionShareBlockNumber)).all()
        )
        assert len(_idx_position_share_block_number) == 0

        # Clear cache in DB session.
        session.rollback()

        # Transfer
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            10000,
        )

        # Expect that sync_new_logs() raises SQLAlchemyError.
        with (
            mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()),
            pytest.raises(SQLAlchemyError),
        ):
            await processor.sync_new_logs()

        # Clear cache in DB session.
        session.rollback()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 0

        # Latest_block is NOT incremented in "sync_new_logs" process.
        _idx_position_share_block_number: Sequence[IDXPositionShareBlockNumber] = (
            session.scalars(select(IDXPositionShareBlockNumber)).all()
        )
        assert len(_idx_position_share_block_number) == 0

        assert 0 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.ERROR,
                "An exception occurred during event synchronization",
            )
        )

    # <Error_3>: ServiceUnavailable occurs and is handled in mainloop.
    async def test_error_3(
        self,
        main_func: Callable[[], Awaitable[None]],
        caplog: pytest.LogCaptureFixture,
    ):
        # Mocking time.sleep to break mainloop
        asyncio_mock = AsyncMock(wraps=asyncio)
        asyncio_mock.sleep.side_effect = [True, TypeError()]

        # Run mainloop once and fail with web3 utils error
        with (
            mock.patch("batch.indexer_Position_Share.asyncio", asyncio_mock),
            mock.patch(
                "batch.indexer_Position_Share.Processor.initial_sync", return_value=True
            ),
            mock.patch(
                "web3.AsyncWeb3.AsyncHTTPProvider.make_request",
                MagicMock(side_effect=ServiceUnavailable()),
            ),
            pytest.raises(TypeError),
        ):
            # Expect that sync_new_logs() raises ServiceUnavailable and handled in mainloop.
            await main_func()

        assert 1 == caplog.record_tuples.count(
            (LOG.name, 25, "An external service was unavailable")
        )
        caplog.clear()
