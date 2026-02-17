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

import logging
from typing import Sequence
from unittest import mock
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from eth_utils.address import to_checksum_address
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from web3 import Web3
from web3.exceptions import ABIEventNotFound
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import EventData

from app import config
from app.errors import ServiceUnavailable
from app.model.db import IDXPosition, IDXPositionMembershipBlockNumber, Listing
from batch.sub_indexers import indexer_Position_Membership
from batch.sub_indexers.indexer_Position_Membership import LOG, Processor
from tests.account_config import eth_account
from tests.helpers import IbetMembershipTestHelper
from tests.helpers.ibet_exchange_helpers import (
    create_token_escrow,
    finish_token_escrow,
    get_latest_escrow_id,
)
from tests.types import DeployedContract, SharedContract, UnitTestAccount

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


@pytest.fixture(scope="session", autouse=True)
def test_module(shared_contract: SharedContract):
    indexer_Position_Membership.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract[
        "TokenList"
    ]["address"]


@pytest_asyncio.fixture(scope="function")
async def processor() -> Processor:
    processor = Processor()
    await processor.sync_new_logs()
    return processor


@pytest.mark.asyncio
class TestProcessor:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["agent"]

    @staticmethod
    def issue_token_membership(
        issuer: UnitTestAccount,
        exchange_contract_address: str,
        token_list: DeployedContract,
    ):
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
        token = IbetMembershipTestHelper.issue(issuer["account_address"], args)
        IbetMembershipTestHelper.register_token_list(
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
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token.address, session)

        # Transfer
        IbetMembershipTestHelper.transfer_token(
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

        _idx_position_membership_block_number = session.scalars(
            select(IDXPositionMembershipBlockNumber)
            .where(IDXPositionMembershipBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_membership_block_number is not None
        assert _idx_position_membership_block_number.latest_block_number == block_number

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
        assert _position.pending_transfer is None
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
        assert _position.pending_transfer is None
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
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token.address, session)

        # Transfer
        IbetMembershipTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            10000,
        )
        IbetMembershipTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
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
        assert len(_position_list) == 3

        _idx_position_membership_block_number = session.scalars(
            select(IDXPositionMembershipBlockNumber)
            .where(IDXPositionMembershipBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_membership_block_number is not None
        assert _idx_position_membership_block_number.latest_block_number == block_number

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
        assert _position.pending_transfer is None
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
        assert _position.pending_transfer is None
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
        assert _position.pending_transfer is None
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
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token.address, session)
        token2 = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token2.address, session)

        # Transfer
        IbetMembershipTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            10000,
        )
        IbetMembershipTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader2["account_address"],
            3000,
        )
        IbetMembershipTestHelper.transfer_token(
            self.issuer["account_address"],
            token2.address,
            self.trader["account_address"],
            5000,
        )
        IbetMembershipTestHelper.transfer_token(
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

        _idx_position_membership_block_number = session.scalars(
            select(IDXPositionMembershipBlockNumber)
            .where(IDXPositionMembershipBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_membership_block_number is not None
        assert _idx_position_membership_block_number.latest_block_number == block_number

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
        assert _position.pending_transfer is None
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
        assert _position.pending_transfer is None
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
        assert _position.pending_transfer is None
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
        assert _position.pending_transfer is None
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
        assert _position.pending_transfer is None
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
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

    # <Normal_4>
    # Single Token
    # Multi event logs
    # Escrow
    # - Transfer
    # - Commitment
    async def test_normal_4(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        escrow_contract = shared_contract["IbetEscrow"]
        token = self.issue_token_membership(
            self.issuer, escrow_contract["address"], token_list_contract
        )
        self.listing_token(token.address, session)

        # Deposit and Escrow
        IbetMembershipTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            escrow_contract["address"],
            10000,
        )
        create_token_escrow(
            self.issuer,
            {"address": escrow_contract["address"]},
            {"address": token.address},
            self.trader["account_address"],
            self.issuer["account_address"],
            200,
        )
        finish_token_escrow(
            self.issuer,
            {"address": escrow_contract["address"]},
            get_latest_escrow_id({"address": escrow_contract["address"]}),
        )
        create_token_escrow(
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

        _idx_position_membership_block_number = session.scalars(
            select(IDXPositionMembershipBlockNumber)
            .where(IDXPositionMembershipBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_membership_block_number is not None
        assert _idx_position_membership_block_number.latest_block_number == block_number

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
        assert _position.pending_transfer is None
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
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 200
        assert _position.exchange_commitment == 0

    # <Normal_5>
    # No event logs
    async def test_normal_5(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token.address, session)

        # Not Transfer
        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 0

        _idx_position_membership_block_number = session.scalars(
            select(IDXPositionMembershipBlockNumber)
            .where(IDXPositionMembershipBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_membership_block_number is not None
        assert _idx_position_membership_block_number.latest_block_number == block_number

    # <Normal_6>
    # Not listing Token is NOT indexed,
    # and indexed properly after listing
    async def test_normal_6(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )

        # Transfer
        IbetMembershipTestHelper.transfer_token(
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

        _idx_position_membership_block_numbers: Sequence[
            IDXPositionMembershipBlockNumber
        ] = session.scalars(select(IDXPositionMembershipBlockNumber)).all()
        assert len(_idx_position_membership_block_numbers) == 0

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

        _idx_position_membership_block_number = session.scalars(
            select(IDXPositionMembershipBlockNumber)
            .where(IDXPositionMembershipBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_membership_block_number is not None
        assert _idx_position_membership_block_number.latest_block_number == block_number

    # <Normal_7>
    # Single Token
    # Multi event logs
    # - Transfer
    # Duplicate events to be removed
    async def test_normal_7(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token.address, session)
        from_block = web3.eth.block_number
        for _ in range(0, 5):
            # Transfer
            IbetMembershipTestHelper.transfer_token(
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

    # <Normal_8>
    # When stored index is 9,999,999 and current block number is 19,999,999,
    # then processor must process "__sync_all" method 10 times.
    async def test_normal_8(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        token_list_contract = shared_contract["TokenList"]
        escrow_contract = shared_contract["IbetEscrow"]
        current_block_number = 20000000 - 1
        latest_block_number = 10000000 - 1

        mock_lib = MagicMock()

        token = self.issue_token_membership(
            self.issuer, escrow_contract["address"], token_list_contract
        )

        # Setting current block number to 19,999,999
        self.listing_token(token.address, session)
        block_number_mock = AsyncMock()
        block_number_mock.return_value = current_block_number
        with mock.patch(
            "web3.eth.async_eth.AsyncEth.block_number", block_number_mock()
        ):
            with mock.patch.object(
                Processor, "_Processor__sync_all", return_value=mock_lib
            ) as __sync_all_mock:
                idx_position_membership_block_number = (
                    IDXPositionMembershipBlockNumber()
                )
                idx_position_membership_block_number.token_address = token.address
                idx_position_membership_block_number.exchange_address = escrow_contract[
                    "address"
                ]
                # Setting stored index to 9,999,999
                idx_position_membership_block_number.latest_block_number = (
                    latest_block_number
                )
                session.merge(idx_position_membership_block_number)
                session.commit()
                __sync_all_mock.return_value = None
                await processor.sync_new_logs()
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

        new_token = self.issue_token_membership(
            self.issuer, escrow_contract["address"], token_list_contract
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

    # <Normal_9>
    # Single Token
    # Multi event logs (Over 1000)
    # - Transfer
    async def test_normal_9(
        self, processor: Processor, shared_contract: SharedContract, session: Session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token.address, session)

        # Transfer
        for i in range(1001):
            IbetMembershipTestHelper.transfer_token(
                self.issuer["account_address"],
                token.address,
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

        _idx_position_membership_block_number = session.scalars(
            select(IDXPositionMembershipBlockNumber)
            .where(IDXPositionMembershipBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_membership_block_number is not None
        assert _idx_position_membership_block_number.latest_block_number == block_number

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
        assert _position.balance == 1000000 - 1001
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
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
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token.address, session)

        # Transfer
        IbetMembershipTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            10000,
        )

        block_number_current = web3.eth.block_number
        # Run initial sync
        await processor.sync_new_logs()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 0
        # Latest_block is incremented in "initial_sync" process.
        _idx_position_membership_block_number = session.scalars(
            select(IDXPositionMembershipBlockNumber)
            .where(IDXPositionMembershipBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_membership_block_number is not None
        assert (
            _idx_position_membership_block_number.latest_block_number
            == block_number_current
        )

        # Transfer
        IbetMembershipTestHelper.transfer_token(
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
        _idx_position_membership_block_number = session.scalars(
            select(IDXPositionMembershipBlockNumber)
            .where(IDXPositionMembershipBlockNumber.token_address == token.address)
            .limit(1)
        ).first()
        assert _idx_position_membership_block_number is not None
        assert (
            _idx_position_membership_block_number.latest_block_number
            == block_number_current
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
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token.address, session)

        # Transfer
        IbetMembershipTestHelper.transfer_token(
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
            await processor.sync_new_logs()

        # Clear cache in DB session.
        session.rollback()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 0

        # Any latest_block is not saved in "initial_sync" process when ServiceUnavailable occurs.
        _idx_position_membership_block_number = session.scalars(
            select(IDXPositionMembershipBlockNumber)
        ).all()
        assert len(_idx_position_membership_block_number) == 0

        # Clear cache in DB session.
        session.rollback()

        # Transfer
        IbetMembershipTestHelper.transfer_token(
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

        # Any latest_block is not saved in "sync_new_logs" process when ServiceUnavailable occurs.
        _idx_position_membership_block_number = session.scalars(
            select(IDXPositionMembershipBlockNumber)
        ).all()
        assert len(_idx_position_membership_block_number) == 0

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
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token.address, session)

        # Transfer
        IbetMembershipTestHelper.transfer_token(
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
            await processor.sync_new_logs()

        # Clear cache in DB session.
        session.rollback()

        # Assertion
        _position_list: Sequence[IDXPosition] = session.scalars(
            select(IDXPosition).order_by(IDXPosition.created)
        ).all()
        assert len(_position_list) == 0

        # Any latest_block is not saved in "initial_sync" process when SQLAlchemyError occurs.
        _idx_position_membership_block_number = session.scalars(
            select(IDXPositionMembershipBlockNumber)
        ).all()
        assert len(_idx_position_membership_block_number) == 0

        # Clear cache in DB session.
        session.rollback()

        # Transfer
        IbetMembershipTestHelper.transfer_token(
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
        _idx_position_membership_block_number = session.scalars(
            select(IDXPositionMembershipBlockNumber)
        ).all()
        assert len(_idx_position_membership_block_number) == 0

        assert 0 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.ERROR,
                "An exception occurred during event synchronization",
            )
        )
