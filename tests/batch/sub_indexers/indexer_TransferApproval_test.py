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
from datetime import datetime
from unittest import mock
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from web3 import Web3
from web3.exceptions import ABIEventNotFound
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from app.errors import ServiceUnavailable
from app.model.db import IDXTransferApproval, IDXTransferApprovalBlockNumber, Listing
from batch.sub_indexers import indexer_TransferApproval
from batch.sub_indexers.indexer_TransferApproval import LOG, Processor
from tests.account_config import eth_account
from tests.helpers import IbetShareTestHelper
from tests.helpers.ibet_exchange_helpers import (
    approve_transfer_security_token_escrow,
    cancel_security_token_escrow,
    create_security_token_escrow,
    finish_security_token_escrow,
    get_latest_security_escrow_id,
)
from tests.types import DeployedContract, SharedContract, UnitTestAccount

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


@pytest.fixture(scope="session", autouse=True)
def test_module(shared_contract: SharedContract):
    indexer_TransferApproval.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"][
        "address"
    ]


@pytest_asyncio.fixture(scope="function", loop_scope="session")
async def processor() -> Processor:
    processor = Processor()
    await processor.sync_new_logs()
    return processor


@pytest.fixture(scope="function")
def caplog(caplog: pytest.LogCaptureFixture):
    batch_logger = logging.getLogger("ibet_wallet_batch")
    default_log_level = batch_logger.level
    batch_logger.setLevel(logging.DEBUG)
    batch_logger.propagate = True
    yield caplog
    batch_logger.propagate = False
    batch_logger.setLevel(default_log_level)


@pytest.mark.asyncio
class TestProcessor:
    issuer = eth_account["issuer"]
    account1 = eth_account["user1"]
    account2 = eth_account["user2"]
    escrow_agent = eth_account["agent"]

    @staticmethod
    def issue_token_share(
        issuer: UnitTestAccount,
        exchange_contract: DeployedContract | None,
        personal_info_contract: DeployedContract,
        token_list_contract: DeployedContract,
    ):
        if exchange_contract is None:
            exchange_contract_address = config.ZERO_ADDRESS
        else:
            exchange_contract_address = exchange_contract["address"]
        # Issue token
        args = {
            "name": "テスト株式",
            "symbol": "SHARE",
            "tradableExchange": exchange_contract_address,
            "personalInfoAddress": personal_info_contract["address"],
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
            token_list_contract["address"],
        )
        return token

    @staticmethod
    async def list_token(async_session: AsyncSession, token_address: str):
        _listing = Listing()
        _listing.token_address = token_address
        _listing.is_public = True
        _listing.owner_address = TestProcessor.issuer["account_address"]
        async_session.add(_listing)
        await async_session.commit()

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Single Token
    #  - ApplyForTransfer
    async def test_normal_1_1(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )
        await self.list_token(token_address=token.address, async_session=async_session)

        # Transfer token: from issuer to account1
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.account1["account_address"],
            10000,
        )

        # Change transfer approval required to True
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token.address,
            True,
        )

        # Apply for transfer
        IbetShareTestHelper.apply_for_token_transfer(
            self.account1["account_address"],
            token.address,
            self.account2["account_address"],
            2000,
            "978266096",  # 2000/12/31 12:34:56
        )

        # Run target process
        await processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token.address
        assert _transfer_approval.exchange_address is None
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 2000
        assert _transfer_approval.application_datetime == datetime.strptime(
            "2000/12/31 12:34:56", "%Y/%m/%d %H:%M:%S"
        )
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

    # <Normal_1_2>
    # Single Token
    #  - ApplyForTransfer
    #  - ApproveTransfer
    async def test_normal_1_2(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue Token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )
        await self.list_token(token_address=token.address, async_session=async_session)

        # Transfer token: from issuer to account1
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.account1["account_address"],
            10000,
        )

        # Change transfer approval required to True
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token.address,
            True,
        )

        # Apply for transfer
        IbetShareTestHelper.apply_for_token_transfer(
            self.account1["account_address"],
            token.address,
            self.account2["account_address"],
            2000,
            "978266096",  # 2000/12/31 12:34:56
        )

        # Approve transfer
        IbetShareTestHelper.approve_token_transfer(
            self.issuer["account_address"],
            token.address,
            0,
            "1609418096",  # 2020/12/31 12:34:56
        )

        # Run target process
        await processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token.address
        assert _transfer_approval.exchange_address is None
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 2000
        assert _transfer_approval.application_datetime == datetime.strptime(
            "2000/12/31 12:34:56", "%Y/%m/%d %H:%M:%S"
        )
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime == datetime.strptime(
            "2020/12/31 12:34:56", "%Y/%m/%d %H:%M:%S"
        )
        assert _transfer_approval.approval_blocktimestamp is not None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is True

    # <Normal_1_3>
    # Single Token
    #  - ApplyForTransfer
    #  - CancelTransfer
    async def test_normal_1_3(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )
        await self.list_token(token_address=token.address, async_session=async_session)

        # Transfer token: from issuer to account1
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.account1["account_address"],
            10000,
        )

        # Change transfer approval required to True
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token.address,
            True,
        )

        # Apply for transfer
        IbetShareTestHelper.apply_for_token_transfer(
            self.account1["account_address"],
            token.address,
            self.account2["account_address"],
            2000,
            "978266096",  # 2000/12/31 12:34:56
        )

        # Cancel transfer
        IbetShareTestHelper.cancel_token_transfer_application(
            self.issuer["account_address"],
            token.address,
            0,
            "test_data",
        )

        # Run target process
        await processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token.address
        assert _transfer_approval.exchange_address is None
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 2000
        assert _transfer_approval.application_datetime == datetime.strptime(
            "2000/12/31 12:34:56", "%Y/%m/%d %H:%M:%S"
        )
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is True
        assert _transfer_approval.transfer_approved is None

    # <Normal_1_4>
    # Multi Token
    #  - ApplyForTransfer
    #  - ApproveTransfer
    async def test_normal_1_4(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue Token
        token_1 = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )
        await self.list_token(
            token_address=token_1.address, async_session=async_session
        )

        token_2 = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )
        await self.list_token(
            token_address=token_2.address, async_session=async_session
        )

        # Transfer token: from issuer to account1
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token_1.address,
            self.account1["account_address"],
            10000,
        )
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token_2.address,
            self.account1["account_address"],
            10000,
        )

        # Change transfer approval required to True
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token_1.address,
            True,
        )
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token_2.address,
            True,
        )

        # Apply for transfer
        IbetShareTestHelper.apply_for_token_transfer(
            self.account1["account_address"],
            token_1.address,
            self.account2["account_address"],
            2000,
            "978266096",  # 2000/12/31 12:34:56
        )
        IbetShareTestHelper.apply_for_token_transfer(
            self.account1["account_address"],
            token_2.address,
            self.account2["account_address"],
            3000,
            "978266097",  # 2000/12/31 12:34:57
        )

        # Approve transfer
        IbetShareTestHelper.approve_token_transfer(
            self.issuer["account_address"],
            token_1.address,
            0,
            "1609418096",  # 2020/12/31 12:34:56
        )
        IbetShareTestHelper.approve_token_transfer(
            self.issuer["account_address"],
            token_2.address,
            0,
            "1609418097",  # 2020/12/31 12:34:57
        )

        # Run target process
        await processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 2

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_1.address
        assert _transfer_approval.exchange_address is None
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 2000
        assert _transfer_approval.application_datetime == datetime.strptime(
            "2000/12/31 12:34:56", "%Y/%m/%d %H:%M:%S"
        )
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime == datetime.strptime(
            "2020/12/31 12:34:56", "%Y/%m/%d %H:%M:%S"
        )
        assert _transfer_approval.approval_blocktimestamp is not None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is True

        _transfer_approval = _transfer_approval_list[1]
        assert _transfer_approval.id == 2
        assert _transfer_approval.token_address == token_2.address
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 3000
        assert _transfer_approval.application_datetime == datetime.strptime(
            "2000/12/31 12:34:57", "%Y/%m/%d %H:%M:%S"
        )
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime == datetime.strptime(
            "2020/12/31 12:34:57", "%Y/%m/%d %H:%M:%S"
        )
        assert _transfer_approval.approval_blocktimestamp is not None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is True

    # <Normal_1_5>
    # No event logs
    async def test_normal_1_5(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )
        await self.list_token(token_address=token.address, async_session=async_session)

        # Transfer token: from issuer to account1
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.account1["account_address"],
            10000,
        )

        # Change transfer approval required to True
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token.address,
            True,
        )

        # ApplyForTransfer events not emitted
        # Run target process
        await processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 0

    # <Normal_1_6>
    # Not listed token
    async def test_normal_1_6(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )

        # Transfer token: from issuer to account1
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.account1["account_address"],
            10000,
        )

        # Change transfer approval required to True
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token.address,
            True,
        )

        # Apply for transfer
        IbetShareTestHelper.apply_for_token_transfer(
            self.account1["account_address"],
            token.address,
            self.account2["account_address"],
            2000,
            "978266096",  # 2000/12/31 12:34:56
        )

        # Run target process
        await processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 0

    # <Normal_1_7>
    # Skip processing with no new block (token events)
    async def test_normal_1_7(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )
        await self.list_token(token_address=token.address, async_session=async_session)

        # Run target process first time
        await processor.sync_new_logs()

        # Run target process second time without new block
        caplog.clear()
        await processor.sync_new_logs()

        latest_block = web3.eth.block_number
        next_block = latest_block + 1

        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                f"Skip ApplyForTransfer(token): {token.address} block_from({next_block}) > block_to({latest_block})",
            )
        )
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                f"Skip CancelTransfer(token): {token.address} block_from({next_block}) > block_to({latest_block})",
            )
        )
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                f"Skip ApproveTransfer(token): {token.address} block_from({next_block}) > block_to({latest_block})",
            )
        )

    # <Normal_2_1>
    # IbetSecurityTokenEscrow
    #  - ApplyForTransfer
    async def test_normal_2_1(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        st_escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=st_escrow_contract,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )
        await self.list_token(token_address=token.address, async_session=async_session)

        # Transfer token: from issuer to account1
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.account1["account_address"],
            10000,
        )

        # Change transfer approval required to True
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token.address,
            True,
        )

        # Deposit token to escrow
        IbetShareTestHelper.transfer_token(
            self.account1["account_address"],
            token.address,
            st_escrow_contract["address"],
            10000,
        )

        # Create escrow
        create_security_token_escrow(
            invoker=self.account1,
            exchange={"address": st_escrow_contract["address"]},
            token={"address": token.address},
            recipient_address=self.account2["account_address"],
            agent_address=self.escrow_agent["account_address"],
            amount=10000,
            transfer_application_data="978266096",  # 2000/12/31 12:34:56
            data="test_escrow_data",
        )

        # Run target process
        await processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token.address
        assert _transfer_approval.exchange_address == st_escrow_contract["address"]
        assert _transfer_approval.application_id == get_latest_security_escrow_id(
            {"address": st_escrow_contract["address"]}
        )
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 10000
        assert _transfer_approval.application_datetime == datetime.strptime(
            "2000/12/31 12:34:56", "%Y/%m/%d %H:%M:%S"
        )
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.escrow_finished is None
        assert _transfer_approval.transfer_approved is None

    # <Normal_2_2>
    # IbetSecurityTokenEscrow
    #  - ApplyForTransfer
    #  - CancelTransfer
    async def test_normal_2_2(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        st_escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=st_escrow_contract,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )
        await self.list_token(token_address=token.address, async_session=async_session)

        # Transfer token: from issuer to account1
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.account1["account_address"],
            10000,
        )

        # Change transfer approval required to True
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token.address,
            True,
        )

        # Deposit token to escrow
        IbetShareTestHelper.transfer_token(
            self.account1["account_address"],
            token.address,
            st_escrow_contract["address"],
            10000,
        )

        # Create escrow
        create_security_token_escrow(
            invoker=self.account1,
            exchange={"address": st_escrow_contract["address"]},
            token={"address": token.address},
            recipient_address=self.account2["account_address"],
            agent_address=self.escrow_agent["account_address"],
            amount=10000,
            transfer_application_data="978266096",  # 2000/12/31 12:34:56
            data="test_escrow_data",
        )

        # Cancel escrow
        escrow_id = get_latest_security_escrow_id(
            {"address": st_escrow_contract["address"]}
        )
        cancel_security_token_escrow(
            invoker=self.account1,
            exchange={"address": st_escrow_contract["address"]},
            escrow_id=escrow_id,
        )

        # Run target process
        await processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token.address
        assert _transfer_approval.exchange_address == st_escrow_contract["address"]
        assert _transfer_approval.application_id == escrow_id
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 10000
        assert _transfer_approval.application_datetime == datetime.strptime(
            "2000/12/31 12:34:56", "%Y/%m/%d %H:%M:%S"
        )
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is True
        assert _transfer_approval.escrow_finished is None
        assert _transfer_approval.transfer_approved is None

    # <Normal_2_3>
    # IbetSecurityTokenEscrow
    #  - ApplyForTransfer
    #  - FinishTransfer
    async def test_normal_2_3(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        st_escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=st_escrow_contract,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )
        await self.list_token(token_address=token.address, async_session=async_session)

        # Transfer token: from issuer to account1
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.account1["account_address"],
            10000,
        )

        # Change transfer approval required to True
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token.address,
            True,
        )

        # Deposit token to escrow
        IbetShareTestHelper.transfer_token(
            self.account1["account_address"],
            token.address,
            st_escrow_contract["address"],
            10000,
        )

        # Create escrow
        create_security_token_escrow(
            invoker=self.account1,
            exchange={"address": st_escrow_contract["address"]},
            token={"address": token.address},
            recipient_address=self.account2["account_address"],
            agent_address=self.escrow_agent["account_address"],
            amount=10000,
            transfer_application_data="978266096",  # 2000/12/31 12:34:56
            data="test_escrow_data",
        )
        escrow_id = get_latest_security_escrow_id(
            {"address": st_escrow_contract["address"]}
        )

        # Finish escrow
        finish_security_token_escrow(
            invoker=self.escrow_agent,
            exchange={"address": st_escrow_contract["address"]},
            escrow_id=escrow_id,
        )

        # Run target process
        await processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token.address
        assert _transfer_approval.exchange_address == st_escrow_contract["address"]
        assert _transfer_approval.application_id == escrow_id
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 10000
        assert _transfer_approval.application_datetime == datetime.strptime(
            "2000/12/31 12:34:56", "%Y/%m/%d %H:%M:%S"
        )
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.escrow_finished is True
        assert _transfer_approval.transfer_approved is None

    # <Normal_2_4>
    # IbetSecurityTokenEscrow
    #  - ApplyForTransfer
    #  - ApproveTransfer
    async def test_normal_2_4(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        st_escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=st_escrow_contract,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )
        await self.list_token(token_address=token.address, async_session=async_session)

        # Transfer token: from issuer to account1
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.account1["account_address"],
            10000,
        )

        # Change transfer approval required to True
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token.address,
            True,
        )

        # Deposit token to escrow
        IbetShareTestHelper.transfer_token(
            self.account1["account_address"],
            token.address,
            st_escrow_contract["address"],
            10000,
        )

        # Create escrow
        create_security_token_escrow(
            invoker=self.account1,
            exchange={"address": st_escrow_contract["address"]},
            token={"address": token.address},
            recipient_address=self.account2["account_address"],
            agent_address=self.escrow_agent["account_address"],
            amount=10000,
            transfer_application_data="978266096",  # 2000/12/31 12:34:56
            data="test_escrow_data",
        )
        escrow_id = get_latest_security_escrow_id(
            {"address": st_escrow_contract["address"]}
        )

        # Finish escrow
        finish_security_token_escrow(
            invoker=self.escrow_agent,
            exchange={"address": st_escrow_contract["address"]},
            escrow_id=escrow_id,
        )

        # Approve transfer
        approve_transfer_security_token_escrow(
            invoker=self.issuer,
            exchange={"address": st_escrow_contract["address"]},
            escrow_id=escrow_id,
            transfer_approval_data="1609418096",  # 2020/12/31 12:34:56
        )

        # Run target process
        await processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token.address
        assert _transfer_approval.exchange_address == st_escrow_contract["address"]
        assert _transfer_approval.application_id == escrow_id
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 10000
        assert _transfer_approval.application_datetime == datetime.strptime(
            "2000/12/31 12:34:56", "%Y/%m/%d %H:%M:%S"
        )
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime == datetime.strptime(
            "2020/12/31 12:34:56", "%Y/%m/%d %H:%M:%S"
        )
        assert _transfer_approval.approval_blocktimestamp is not None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.escrow_finished is True
        assert _transfer_approval.transfer_approved is True

    # <Normal_2_5>
    # Skip processing with no new block (exchange events)
    async def test_normal_2_5(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        st_escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issue token with exchange
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=st_escrow_contract,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )
        await self.list_token(token_address=token.address, async_session=async_session)

        # Run target process first time
        await processor.sync_new_logs()

        # Run target process second time without new block
        caplog.clear()
        await processor.sync_new_logs()

        latest_block = web3.eth.block_number
        next_block = latest_block + 1

        # token-side skips
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                f"Skip ApplyForTransfer(token): {token.address} block_from({next_block}) > block_to({latest_block})",
            )
        )
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                f"Skip CancelTransfer(token): {token.address} block_from({next_block}) > block_to({latest_block})",
            )
        )
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                f"Skip ApproveTransfer(token): {token.address} block_from({next_block}) > block_to({latest_block})",
            )
        )

        # exchange-side skips
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                f"Skip ApplyForTransfer(exchange): {st_escrow_contract['address']} block_from({next_block}) > block_to({latest_block})",
            )
        )
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                f"Skip CancelTransfer(exchange): {st_escrow_contract['address']} block_from({next_block}) > block_to({latest_block})",
            )
        )
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                f"Skip EscrowFinished(exchange): {st_escrow_contract['address']} block_from({next_block}) > block_to({latest_block})",
            )
        )
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                f"Skip ApproveTransfer(exchange): {st_escrow_contract['address']} block_from({next_block}) > block_to({latest_block})",
            )
        )

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1_1>: ABIEventNotFound occurs in __sync_xx method.
    # <Error_1_2>: ServiceUnavailable occurs in __sync_xx method.
    # <Error_2_1>: ServiceUnavailable occurs in "initial_sync" / "sync_new_logs".
    # <Error_2_2>: SQLAlchemyError occurs in "initial_sync" / "sync_new_logs".

    # <Error_1_1>: ABIEventNotFound occurs in __sync_xx method.
    @mock.patch(
        "web3.eth.async_eth.AsyncEth.get_logs",
        MagicMock(side_effect=ABIEventNotFound()),
    )
    async def test_error_1_1(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )
        await self.list_token(token_address=token.address, async_session=async_session)

        # Transfer token: from issuer to account1
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.account1["account_address"],
            5000,
        )

        # Change transfer approval required to True
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token.address,
            True,
        )

        # Apply for transfer
        IbetShareTestHelper.apply_for_token_transfer(
            self.account1["account_address"],
            token.address,
            self.account2["account_address"],
            2000,
            "978266096",  # 2000/12/31 12:34
        )
        block_number_current = web3.eth.block_number

        # Run initial sync
        await processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 0
        # Latest_block is incremented in "initial_sync" process.
        idx_transfer_approval_block_number = (
            await async_session.scalars(
                select(IDXTransferApprovalBlockNumber)
                .where(IDXTransferApprovalBlockNumber.token_address == token.address)
                .limit(1)
            )
        ).first()
        assert idx_transfer_approval_block_number is not None
        assert (
            idx_transfer_approval_block_number.latest_block_number
            == block_number_current
        )

        # Apply for transfer
        IbetShareTestHelper.apply_for_token_transfer(
            self.account1["account_address"],
            token.address,
            self.account2["account_address"],
            2000,
            "978266096",  # 2000/12/31 12:34:56
        )
        block_number_current = web3.eth.block_number

        # Run target process
        await processor.sync_new_logs()

        # Run target process
        await processor.sync_new_logs()

        # Assertion
        await async_session.rollback()
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 0
        # Latest_block is incremented in "initial_sync" process.
        idx_transfer_approval_block_number = (
            await async_session.scalars(
                select(IDXTransferApprovalBlockNumber)
                .where(IDXTransferApprovalBlockNumber.token_address == token.address)
                .limit(1)
            )
        ).first()
        assert idx_transfer_approval_block_number is not None
        assert (
            idx_transfer_approval_block_number.latest_block_number
            == block_number_current
        )

    # <Error_1_2>: ServiceUnavailable occurs in __sync_xx method.
    async def test_error_1_2(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )
        await self.list_token(token_address=token.address, async_session=async_session)

        # Transfer token: from issuer to account1
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.account1["account_address"],
            5000,
        )

        # Change transfer approval required to True
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token.address,
            True,
        )

        # Apply for transfer
        IbetShareTestHelper.apply_for_token_transfer(
            self.account1["account_address"],
            token.address,
            self.account2["account_address"],
            2000,
            "978266096",  # 2000/12/31 12:34:56
        )

        # Expect that initial_sync() raises ServiceUnavailable.
        with (
            mock.patch(
                "web3.eth.async_eth.AsyncEth.get_block",
                MagicMock(side_effect=ServiceUnavailable()),
            ),
            pytest.raises(ServiceUnavailable),
        ):
            await processor.sync_new_logs()
        # Assertion
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 0
        idx_transfer_approval_block_number = (
            await async_session.scalars(
                select(IDXTransferApprovalBlockNumber)
                .where(IDXTransferApprovalBlockNumber.token_address == token.address)
                .limit(1)
            )
        ).first()
        assert idx_transfer_approval_block_number is None

        # Apply for transfer
        IbetShareTestHelper.apply_for_token_transfer(
            self.account1["account_address"],
            token.address,
            self.account2["account_address"],
            2000,
            "978266096",  # 2000/12/31 12:34:56
        )

        # Expect that sync_new_logs() raises ServiceUnavailable.
        with (
            mock.patch(
                "web3.eth.async_eth.AsyncEth.get_block",
                MagicMock(side_effect=ServiceUnavailable()),
            ),
            pytest.raises(ServiceUnavailable),
        ):
            await processor.sync_new_logs()

        # Assertion
        await async_session.rollback()
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 0
        # Latest_block is NOT incremented in "sync_new_logs" process.
        idx_transfer_approval_block_number = (
            await async_session.scalars(
                select(IDXTransferApprovalBlockNumber)
                .where(IDXTransferApprovalBlockNumber.token_address == token.address)
                .limit(1)
            )
        ).first()
        assert idx_transfer_approval_block_number is None

    # <Error_2_1>: ServiceUnavailable occurs in "initial_sync" / "sync_new_logs".
    async def test_error_2_1(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )
        await self.list_token(token_address=token.address, async_session=async_session)

        # Transfer token: from issuer to account1
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.account1["account_address"],
            5000,
        )

        # Change transfer approval required to True
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token.address,
            True,
        )

        # Apply for transfer
        IbetShareTestHelper.apply_for_token_transfer(
            self.account1["account_address"],
            token.address,
            self.account2["account_address"],
            2000,
            "978266096",  # 2000/12/31 12:34:56
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
        # Assertion
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 0
        idx_transfer_approval_block_number = (
            await async_session.scalars(
                select(IDXTransferApprovalBlockNumber)
                .where(IDXTransferApprovalBlockNumber.token_address == token.address)
                .limit(1)
            )
        ).first()
        assert idx_transfer_approval_block_number is None

        # Apply for transfer
        IbetShareTestHelper.apply_for_token_transfer(
            self.account1["account_address"],
            token.address,
            self.account2["account_address"],
            2000,
            "978266096",  # 2000/12/31 12:34:56
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

        # Assertion
        await async_session.rollback()
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 0
        # Latest_block is NOT incremented in "sync_new_logs" process.
        idx_transfer_approval_block_number = (
            await async_session.scalars(
                select(IDXTransferApprovalBlockNumber)
                .where(IDXTransferApprovalBlockNumber.token_address == token.address)
                .limit(1)
            )
        ).first()
        assert idx_transfer_approval_block_number is None

    # <Error_2_2>: SQLAlchemyError occurs in "initial_sync" / "sync_new_logs".
    async def test_error_2_2(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract,
        )
        await self.list_token(token_address=token.address, async_session=async_session)

        # Transfer token: from issuer to account1
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.account1["account_address"],
            5000,
        )

        # Change transfer approval required to True
        IbetShareTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token.address,
            True,
        )

        # Apply for transfer
        IbetShareTestHelper.apply_for_token_transfer(
            self.account1["account_address"],
            token.address,
            self.account2["account_address"],
            2000,
            "978266096",  # 2000/12/31 12:34:56
        )

        # Expect that initial_sync() raises SQLAlchemyError.
        with (
            mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()),
            pytest.raises(SQLAlchemyError),
        ):
            await processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 0
        idx_transfer_approval_block_number = (
            await async_session.scalars(
                select(IDXTransferApprovalBlockNumber)
                .where(IDXTransferApprovalBlockNumber.token_address == token.address)
                .limit(1)
            )
        ).first()
        assert idx_transfer_approval_block_number is None

        # Apply for transfer
        IbetShareTestHelper.apply_for_token_transfer(
            self.account1["account_address"],
            token.address,
            self.account2["account_address"],
            2000,
            "978266096",  # 2000/12/31 12:34:56
        )

        # Expect that sync_new_logs() raises SQLAlchemyError.
        with (
            mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()),
            pytest.raises(SQLAlchemyError),
        ):
            await processor.sync_new_logs()

        # Assertion
        await async_session.rollback()
        _transfer_approval_list = (
            await async_session.scalars(
                select(IDXTransferApproval).order_by(IDXTransferApproval.created)
            )
        ).all()
        assert len(_transfer_approval_list) == 0
        # Latest_block is NOT incremented in "sync_new_logs" process.
        idx_transfer_approval_block_number = (
            await async_session.scalars(
                select(IDXTransferApprovalBlockNumber)
                .where(IDXTransferApprovalBlockNumber.token_address == token.address)
                .limit(1)
            )
        ).first()
        assert idx_transfer_approval_block_number is None
