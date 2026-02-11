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
import uuid
from collections.abc import Iterator
from unittest import mock
from unittest.mock import MagicMock

import pytest
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3
from web3.exceptions import ABIEventNotFound
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from app.config import ZERO_ADDRESS
from app.errors import ServiceUnavailable
from app.model.db import TokenHolder, TokenHolderBatchStatus, TokenHoldersList
from batch.indexer_Token_Holders import LOG, Processor
from tests.account_config import eth_account
from tests.helpers import (
    IbetCouponTestHelper,
    IbetMembershipTestHelper,
    IbetShareTestHelper,
    IbetStraightBondTestHelper,
)
from tests.helpers.ibet_exchange_helpers import (
    approve_transfer_security_token_escrow,
    create_security_token_escrow,
    finish_security_token_escrow,
    get_latest_security_escrow_id,
)
from tests.types import DeployedContract, SharedContract, UnitTestAccount

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


@pytest.fixture(scope="function")
def processor() -> Iterator[Processor]:
    LOG = logging.getLogger("ibet_wallet_batch")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True

    processor = Processor()
    yield processor

    LOG.propagate = False
    LOG.setLevel(default_log_level)


@pytest.mark.asyncio
class TestProcessor:
    issuer = eth_account["issuer"]
    user1 = eth_account["user1"]
    user2 = eth_account["user2"]
    trader = eth_account["trader"]
    agent = eth_account["agent"]

    target_process_name = "INDEXER-TOKEN_HOLDERS"

    @staticmethod
    def issue_token_bond(
        issuer: UnitTestAccount,
        exchange_contract_address: str,
        personal_info_contract_address: str,
        token_list: DeployedContract,
        amount: int = 1000000,
    ):
        # Issue token
        args = {
            "name": "テスト債券",
            "symbol": "BOND",
            "totalSupply": amount,
            "tradableExchange": exchange_contract_address,
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
            "personalInfoAddress": personal_info_contract_address,
            "transferable": True,
            "isRedeemed": False,
            "faceValueCurrency": "JPY",
            "interestPaymentCurrency": "JPY",
            "redemptionValueCurrency": "JPY",
            "baseFxRate": "",
            "requirePersonalInfoRegistered": False,
        }
        token = IbetStraightBondTestHelper.issue(issuer["account_address"], args)
        IbetStraightBondTestHelper.register_token_list(
            issuer["account_address"],
            token.address,
            token_list["address"],
        )
        return token

    @staticmethod
    def issue_token_share(
        issuer: UnitTestAccount,
        exchange_contract_address: str,
        personal_info_contract_address: str,
        token_list: DeployedContract,
        amount: int = 1000000,
    ):
        # Issue token
        args = {
            "name": "テスト株式",
            "symbol": "SHARE",
            "tradableExchange": exchange_contract_address,
            "personalInfoAddress": personal_info_contract_address,
            "issuePrice": 1000,
            "principalValue": 1000,
            "totalSupply": amount,
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
    def issue_token_coupon(
        issuer: UnitTestAccount,
        exchange_contract_address: str,
        token_list: DeployedContract,
        amount: int = 1000000,
    ):
        # Issue token
        args = {
            "name": "テストクーポン",
            "symbol": "COUPON",
            "totalSupply": amount,
            "tradableExchange": exchange_contract_address,
            "details": "クーポン詳細",
            "returnDetails": "リターン詳細",
            "memo": "クーポンメモ欄",
            "expirationDate": "20191231",
            "transferable": True,
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
        }
        token = IbetCouponTestHelper.issue(issuer["account_address"], args)
        IbetCouponTestHelper.register_token_list(
            issuer["account_address"],
            token.address,
            token_list["address"],
        )
        return token

    @staticmethod
    def issue_token_membership(
        issuer: UnitTestAccount,
        exchange_contract_address: str,
        token_list: DeployedContract,
        amount: int = 1000000,
    ):
        # Issue token
        args = {
            "name": "テスト会員権",
            "symbol": "MEMBERSHIP",
            "initialSupply": amount,
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
    def token_holders_list(
        token_address: str,
        block_number: int,
        status: TokenHolderBatchStatus = TokenHolderBatchStatus.PENDING,
    ) -> TokenHoldersList:
        target_token_holders_list = TokenHoldersList()
        target_token_holders_list.list_id = str(uuid.uuid4())
        target_token_holders_list.token_address = token_address
        target_token_holders_list.batch_status = status.value
        target_token_holders_list.block_number = block_number
        return target_token_holders_list

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Events
    # - Transfer
    # - IssueFrom
    # - RedeemFrom
    # from StraightBond token
    async def test_normal_1_1(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        exchange_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issuer issues bond token.
        token = self.issue_token_bond(
            self.issuer,
            exchange_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
        )

        # Issuer transfers issued token to user1, trader and exchange.
        # - "Transfer" event is emitted from token contract.
        # - user1: 20000
        IbetStraightBondTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            20000,
        )

        # Issuer issues token to user1.
        # - "Issue" event is emitted from token contract.
        # - user1: 60000
        IbetStraightBondTestHelper.mint(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            40000,
        )

        # Issuer redeems token from user1.
        # - "Redeem" event is emitted from token contract.
        # - user1: 50000
        IbetStraightBondTestHelper.burn(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            10000,
        )

        # Register instruction to collect token holders.
        target_token_holders_list = self.token_holders_list(
            token.address, web3.eth.block_number
        )
        async_session.add(target_token_holders_list)
        await async_session.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        # - No effect on holder balance because collection is done before this transfer.
        IbetStraightBondTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            10000,
        )

        # Run processor
        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            await processor.collect()

        # Verify the result
        # - user1's hold_balance is 50000
        user1_record = (
            await async_session.scalars(
                select(TokenHolder)
                .where(
                    and_(
                        TokenHolder.holder_list == target_token_holders_list.id,
                        TokenHolder.account_address == self.user1["account_address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert user1_record is not None
        assert user1_record.hold_balance == 50000

        assert (
            len(
                list(
                    (
                        await async_session.scalars(
                            select(TokenHolder).where(
                                TokenHolder.holder_list == target_token_holders_list.id
                            )
                        )
                    ).all()
                )
            )
            == 1
        )

    # <Normal_1_2>
    # Events
    # - Transfer
    # - IssueFrom
    # - RedeemFrom
    # from Share token
    async def test_normal_1_2(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        exchange_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issuer issues share token.
        token = self.issue_token_share(
            self.issuer,
            exchange_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
        )

        # Issuer transfers issued token to user1, trader and exchange.
        # - "Transfer" event is emitted from token contract.
        # - user1: 20000
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            20000,
        )

        # Issuer issues token to user1.
        # - "Issue" event is emitted from token contract.
        # - user1: 60000
        IbetShareTestHelper.mint(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            40000,
        )

        # Issuer redeems token from user1.
        # - "Redeem" event is emitted from token contract.
        # - user1: 50000
        IbetShareTestHelper.burn(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            10000,
        )

        # Register instruction to collect token holders.
        target_token_holders_list = self.token_holders_list(
            token.address, web3.eth.block_number
        )
        async_session.add(target_token_holders_list)
        await async_session.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        # - No effect on holder balance because collection is done before this transfer.
        IbetShareTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            10000,
        )

        # Run processor
        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            await processor.collect()

        # Verify the result
        # - user1's hold_balance is 50000
        user1_record = (
            await async_session.scalars(
                select(TokenHolder)
                .where(
                    and_(
                        TokenHolder.holder_list == target_token_holders_list.id,
                        TokenHolder.account_address == self.user1["account_address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert user1_record is not None
        assert user1_record.hold_balance == 50000

        assert (
            len(
                list(
                    (
                        await async_session.scalars(
                            select(TokenHolder).where(
                                TokenHolder.holder_list == target_token_holders_list.id
                            )
                        )
                    ).all()
                )
            )
            == 1
        )

    # <Normal_1_3>
    # Events
    # - HolderChanged
    # from Exchange contract
    async def test_normal_1_3(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issuer issues bond token.
        token = self.issue_token_bond(
            self.issuer,
            escrow_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
            10000,
        )

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        # Issuer transfers issued token to user1.
        # - "Transfer" event is emitted from token contract.
        # - user1: 10000
        IbetStraightBondTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            10000,
        )

        # User1 transfers some token to exchange.
        # - user1: 10000
        IbetStraightBondTestHelper.transfer_token(
            self.user1["account_address"],
            token.address,
            escrow_contract["address"],
            1000,
        )

        # User1 creates escrow to User2 via agent.
        # - user1: 10000
        # - user2: 0
        create_security_token_escrow(
            self.user1,
            {"address": escrow_contract["address"]},
            {"address": token.address},
            self.user2["account_address"],
            self.agent["account_address"],
            1000,
        )
        _latest_security_escrow_id = get_latest_security_escrow_id(
            {"address": escrow_contract["address"]}
        )

        # Agent finishes the escrow.
        # - "HolderChanged" event is emitted from exchange contract.
        # - user1: 9000
        # - user2: 1000
        finish_security_token_escrow(
            self.agent,
            {"address": escrow_contract["address"]},
            _latest_security_escrow_id,
        )

        # Register instruction to collect token holders.
        target_token_holders_list = self.token_holders_list(
            token.address, web3.eth.block_number
        )
        async_session.add(target_token_holders_list)
        await async_session.commit()

        # Run processor
        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            await processor.collect()

        # Verify the result
        user1_record = (
            await async_session.scalars(
                select(TokenHolder)
                .where(
                    and_(
                        TokenHolder.holder_list == target_token_holders_list.id,
                        TokenHolder.account_address == self.user1["account_address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert user1_record is not None
        assert user1_record.hold_balance == 9000

        user2_record = (
            await async_session.scalars(
                select(TokenHolder)
                .where(
                    and_(
                        TokenHolder.holder_list == target_token_holders_list.id,
                        TokenHolder.account_address == self.user2["account_address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert user2_record is not None
        assert user2_record.hold_balance == 1000

    # <Normal_2_1>
    # Events
    # - Lock
    # - ForceLock
    # - Unlock
    # - ForceUnlock
    # - ForceChangeLockAccount
    # from StraightBond token
    async def test_normal_2_1(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issuer issues bond token.
        token = self.issue_token_bond(
            self.issuer,
            escrow_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
            0,
        )

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        # Issuer issues token to user1.
        IbetStraightBondTestHelper.mint(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            15000,
        )

        # User1 lock some token to issuer.
        # - "Lock" event is emitted from token contract.
        # - user1: (hold: 15000, locked: 2000)
        IbetStraightBondTestHelper.lock_token(
            self.user1["account_address"],
            token.address,
            self.issuer["account_address"],
            2000,
            "",
        )

        # Issuer force lock some token of user1.
        # - "ForceLock" event is emitted from token contract.
        # - user1: (hold: 15000, locked: 4000)
        IbetStraightBondTestHelper.force_lock_token(
            self.issuer["account_address"],
            token.address,
            self.issuer["account_address"],
            self.user1["account_address"],
            2000,
            "",
        )

        # Issuer(lock_address) unlock some token from user1.
        # - "Unlock" event is emitted from token contract.
        # - user1: (hold: 15000, locked: 3000)
        IbetStraightBondTestHelper.unlock_token(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            self.user1["account_address"],
            1000,
            "",
        )

        # Issuer force unlock some token from user1.
        # - "ForceUnlock" event is emitted from token contract.
        # - user1: (hold: 15000, locked: 2000)
        IbetStraightBondTestHelper.force_unlock_token(
            self.issuer["account_address"],
            token.address,
            self.issuer["account_address"],
            self.user1["account_address"],
            self.user1["account_address"],
            1000,
            "",
        )

        # Issuer change lock account from user1 to user2.
        # - "ForceChangeLockAccount" event is emitted from token contract.
        # - user1: (hold: 15000, locked: 1000)
        # - user2: (hold: 0, locked: 1000)
        IbetStraightBondTestHelper.force_change_locked_account(
            self.issuer["account_address"],
            token.address,
            self.issuer["account_address"],
            self.user1["account_address"],
            self.user2["account_address"],
            1000,
            "force_unlock",
        )

        # Register instruction to collect token holders.
        target_token_holders_list = self.token_holders_list(
            token.address, web3.eth.block_number
        )
        async_session.add(target_token_holders_list)
        await async_session.commit()

        # Run processor
        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            await processor.collect()

        # Verify the result
        user1_record = (
            await async_session.scalars(
                select(TokenHolder)
                .where(
                    and_(
                        TokenHolder.holder_list == target_token_holders_list.id,
                        TokenHolder.account_address == self.user1["account_address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert user1_record is not None
        assert user1_record.hold_balance == 13000
        assert user1_record.locked_balance == 1000

        user2_record = (
            await async_session.scalars(
                select(TokenHolder)
                .where(
                    and_(
                        TokenHolder.holder_list == target_token_holders_list.id,
                        TokenHolder.account_address == self.user2["account_address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert user2_record is not None
        assert user2_record.hold_balance == 0
        assert user2_record.locked_balance == 1000

    # <Normal_2_2>
    # Events
    # - Lock
    # - ForceLock
    # - Unlock
    # - ForceUnlock
    # - ForceChangeLockAccount
    # from Share token
    async def test_normal_2_2(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issuer issues share token.
        token = self.issue_token_share(
            self.issuer,
            escrow_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
            0,
        )

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        # Issuer issues token to user1.
        IbetShareTestHelper.mint(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            15000,
        )

        # User1 lock some token to issuer.
        # - "Lock" event is emitted from token contract.
        # - user1: (hold: 15000, locked: 2000)
        IbetShareTestHelper.lock_token(
            self.user1["account_address"],
            token.address,
            self.issuer["account_address"],
            2000,
            "",
        )

        # Issuer force lock some token of user1.
        # - "ForceLock" event is emitted from token contract.
        # - user1: (hold: 15000, locked: 4000)
        IbetShareTestHelper.force_lock_token(
            self.issuer["account_address"],
            token.address,
            self.issuer["account_address"],
            self.user1["account_address"],
            2000,
            "",
        )

        # Issuer(lock_address) unlock some token from user1.
        # - "Unlock" event is emitted from token contract.
        # - user1: (hold: 15000, locked: 3000)
        IbetShareTestHelper.unlock_token(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            self.user1["account_address"],
            1000,
            "",
        )

        # Issuer force unlock some token from user1.
        # - "ForceUnlock" event is emitted from token contract.
        # - user1: (hold: 15000, locked: 2000)
        IbetShareTestHelper.force_unlock_token(
            self.issuer["account_address"],
            token.address,
            self.issuer["account_address"],
            self.user1["account_address"],
            self.user1["account_address"],
            1000,
            "",
        )

        # Issuer change lock account from user1 to user2.
        # - "ForceChangeLockAccount" event is emitted from token contract.
        # - user1: (hold: 15000, locked: 1000)
        # - user2: (hold: 0, locked: 1000)
        IbetShareTestHelper.force_change_locked_account(
            self.issuer["account_address"],
            token.address,
            self.issuer["account_address"],
            self.user1["account_address"],
            self.user2["account_address"],
            1000,
            "force_unlock",
        )

        # Register instruction to collect token holders.
        target_token_holders_list = self.token_holders_list(
            token.address, web3.eth.block_number
        )
        async_session.add(target_token_holders_list)
        await async_session.commit()

        # Run processor
        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            await processor.collect()

        # Verify the result
        user1_record = (
            await async_session.scalars(
                select(TokenHolder)
                .where(
                    and_(
                        TokenHolder.holder_list == target_token_holders_list.id,
                        TokenHolder.account_address == self.user1["account_address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert user1_record is not None
        assert user1_record.hold_balance == 13000
        assert user1_record.locked_balance == 1000

        user2_record = (
            await async_session.scalars(
                select(TokenHolder)
                .where(
                    and_(
                        TokenHolder.holder_list == target_token_holders_list.id,
                        TokenHolder.account_address == self.user2["account_address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert user2_record is not None
        assert user2_record.hold_balance == 0
        assert user2_record.locked_balance == 1000

    # <Normal_3_1>
    # Events
    # - (no events)
    # ApplyForTransfer:pending
    # Escrow:pending
    # with transfer_approval_required token
    async def test_normal_3_1(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issuer issues bond token.
        token = self.issue_token_bond(
            self.issuer,
            escrow_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
            0,
        )

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        # Issuer issues token to User1.
        # - user1: 30000
        IbetStraightBondTestHelper.mint(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            30000,
        )

        # Issuer sets transfer approval required.
        IbetStraightBondTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token.address,
            True,
        )

        # User1 applies for transfer to User2.
        # - "Transfer" event is NOT emitted from token contract.
        # - user1: 30000
        # - user2: 0
        IbetStraightBondTestHelper.apply_for_token_transfer(
            self.user1["account_address"],
            token.address,
            self.user2["account_address"],
            10000,
        )

        # User1 creates escrow to User2 via agent.
        # - user1: 30000
        # - user2: 0
        IbetStraightBondTestHelper.transfer_token(
            self.user1["account_address"],
            token.address,
            escrow_contract["address"],
            10000,
        )
        create_security_token_escrow(
            self.user1,
            {"address": escrow_contract["address"]},
            {"address": token.address},
            self.user2["account_address"],
            self.agent["account_address"],
            10000,
        )
        _latest_security_escrow_id = get_latest_security_escrow_id(
            {"address": escrow_contract["address"]}
        )

        # Agent finishes the escrow.
        # - "HolderChanged" event is NOT emitted from exchange contract.
        # - user1: 30000
        # - user2: 0
        finish_security_token_escrow(
            self.agent,
            {"address": escrow_contract["address"]},
            _latest_security_escrow_id,
        )

        # Register instruction to collect token holders.
        target_token_holders_list = self.token_holders_list(
            token.address, web3.eth.block_number
        )
        async_session.add(target_token_holders_list)
        await async_session.commit()

        # Then execute processor.
        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            await processor.collect()

        user1_record = (
            await async_session.scalars(
                select(TokenHolder)
                .where(
                    and_(
                        TokenHolder.holder_list == target_token_holders_list.id,
                        TokenHolder.account_address == self.user1["account_address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert user1_record is not None
        assert user1_record.hold_balance == 30000

        user2_record = (
            await async_session.scalars(
                select(TokenHolder)
                .where(
                    and_(
                        TokenHolder.holder_list == target_token_holders_list.id,
                        TokenHolder.account_address == self.user2["account_address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert user2_record is None  # Because User2 has not received tokens yet.

    # <Normal_3_1>
    # Events
    # - Transfer
    # - HolderChanged
    # with transfer_approval_required token
    async def test_normal_3_2(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issuer issues bond token.
        token = self.issue_token_bond(
            self.issuer,
            escrow_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
            0,
        )

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        # Issuer issues token to User1.
        # - user1: 30000
        IbetStraightBondTestHelper.mint(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            30000,
        )

        # Issuer sets transfer approval required.
        IbetStraightBondTestHelper.set_transfer_approval_required(
            self.issuer["account_address"],
            token.address,
            True,
        )

        # User1 applies for transfer to User2.
        # - user1: 30000
        # - user2: 0
        IbetStraightBondTestHelper.apply_for_token_transfer(
            self.user1["account_address"],
            token.address,
            self.user2["account_address"],
            10000,
        )

        # Issuer approves transfer from User1 to User2.
        # - "Transfer" event is emitted from token contract.
        # - user1: 20000
        # - user2: 10000
        IbetStraightBondTestHelper.approve_token_transfer(
            self.issuer["account_address"], token.address, 0, ""
        )

        # User1 creates escrow to User2 via agent.
        # - user1: 20000
        # - user2: 10000
        IbetStraightBondTestHelper.transfer_token(
            self.user1["account_address"],
            token.address,
            escrow_contract["address"],
            10000,
        )
        create_security_token_escrow(
            self.user1,
            {"address": escrow_contract["address"]},
            {"address": token.address},
            self.user2["account_address"],
            self.agent["account_address"],
            10000,
        )
        _latest_security_escrow_id = get_latest_security_escrow_id(
            {"address": escrow_contract["address"]}
        )

        # Agent finishes the escrow.
        # - user1: 20000
        # - user2: 10000
        finish_security_token_escrow(
            self.agent,
            {"address": escrow_contract["address"]},
            _latest_security_escrow_id,
        )

        # Issuer approves the escrow transfer.
        # - "HolderChanged" event is emitted from exchange contract.
        # - user1: 10000
        # - user2: 20000
        approve_transfer_security_token_escrow(
            self.issuer,
            {"address": escrow_contract["address"]},
            _latest_security_escrow_id,
            "",
        )

        # Register instruction to collect token holders.
        target_token_holders_list = self.token_holders_list(
            token.address, web3.eth.block_number
        )
        async_session.add(target_token_holders_list)
        await async_session.commit()

        # Then execute processor.
        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            await processor.collect()

        user1_record = (
            await async_session.scalars(
                select(TokenHolder)
                .where(
                    and_(
                        TokenHolder.holder_list == target_token_holders_list.id,
                        TokenHolder.account_address == self.user1["account_address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert user1_record is not None
        assert user1_record.hold_balance == 10000

        user2_record = (
            await async_session.scalars(
                select(TokenHolder)
                .where(
                    and_(
                        TokenHolder.holder_list == target_token_holders_list.id,
                        TokenHolder.account_address == self.user2["account_address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert user2_record is not None
        assert user2_record.hold_balance == 20000

    # <Normal_4>
    # Events
    # - Consume
    # from Coupon token
    async def test_normal_4(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        escrow_contract = shared_contract["IbetEscrow"]

        # Issuer issues coupon token.
        token = self.issue_token_coupon(
            self.issuer, escrow_contract["address"], token_list_contract
        )

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        # Issuer transfers issued token to User1.
        # - user1: 10000
        IbetCouponTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            10000,
        )

        # User1 consumes some token.
        # - "Consume" event is emitted from token contract.
        # - user1: 9000
        IbetCouponTestHelper.consume_token(
            self.user1["account_address"],
            token.address,
            1000,
        )

        # Register instruction to collect token holders.
        target_token_holders_list = self.token_holders_list(
            token.address, web3.eth.block_number
        )
        async_session.add(target_token_holders_list)
        await async_session.commit()

        # Run processor
        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            await processor.collect()

        user1_record = (
            await async_session.scalars(
                select(TokenHolder)
                .where(
                    and_(
                        TokenHolder.holder_list == target_token_holders_list.id,
                        TokenHolder.account_address == self.user1["account_address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert user1_record is not None
        assert user1_record.hold_balance == 9000

    # <Normal_5>
    # Jobs are queued and pending jobs are to be processed one by one.
    async def test_normal_5(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        exchange_contract = shared_contract["IbetSecurityTokenEscrow"]

        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            await processor.collect()
        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            await processor.collect()
        assert 2 == caplog.record_tuples.count(
            (LOG.name, logging.DEBUG, "There are no pending collect batch")
        )

        # Issuer issues bond token.
        token = self.issue_token_bond(
            self.issuer,
            exchange_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
        )
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        target_token_holders_list1 = self.token_holders_list(
            token.address, web3.eth.block_number
        )
        async_session.add(target_token_holders_list1)
        await async_session.commit()

        IbetStraightBondTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            20000,
        )
        IbetStraightBondTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.trader["account_address"],
            10000,
        )

        target_token_holders_list2 = self.token_holders_list(
            token.address, web3.eth.block_number
        )
        async_session.add(target_token_holders_list2)
        await async_session.commit()

        caplog.clear()
        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            await processor.collect()

        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            await processor.collect()

        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.INFO,
                f"Token holder list({target_token_holders_list1.list_id}) status changes to be done.",
            )
        )
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.INFO,
                f"Token holder list({target_token_holders_list2.list_id}) status changes to be done.",
            )
        )
        assert 2 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "Collect job has been completed")
        )

    # <Normal_6>
    # When stored checkpoint is 9,999,999 and current block number is 19,999,999,
    # then processor should call "__process_all" method 10 times.
    async def test_normal_6(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        exchange_contract = shared_contract["IbetSecurityTokenEscrow"]
        current_block_number = 20000000 - 1
        checkpoint_block_number = 10000000 - 1

        token = self.issue_token_bond(
            self.issuer,
            exchange_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
        )
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        # Insert collection record with above token and checkpoint block number
        target_token_holders_list = self.token_holders_list(
            token.address, current_block_number
        )
        async_session.add(target_token_holders_list)
        completed_token_holders_list = self.token_holders_list(
            token.address, checkpoint_block_number, status=TokenHolderBatchStatus.DONE
        )
        async_session.add(completed_token_holders_list)
        await async_session.commit()

        # Setting current block number to 19,999,999
        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            # Setting stored index to 9,999,999
            await processor.collect()
            # Then processor call "__process_all" method 10 times.
            assert 1 == caplog.record_tuples.count(
                (LOG.name, logging.INFO, "process from=10000000, to=10999999")
            )
            assert 1 == caplog.record_tuples.count(
                (LOG.name, logging.INFO, "process from=11000000, to=11999999")
            )
            assert 1 == caplog.record_tuples.count(
                (LOG.name, logging.INFO, "process from=12000000, to=12999999")
            )
            assert 1 == caplog.record_tuples.count(
                (LOG.name, logging.INFO, "process from=13000000, to=13999999")
            )
            assert 1 == caplog.record_tuples.count(
                (LOG.name, logging.INFO, "process from=14000000, to=14999999")
            )
            assert 1 == caplog.record_tuples.count(
                (LOG.name, logging.INFO, "process from=15000000, to=15999999")
            )
            assert 1 == caplog.record_tuples.count(
                (LOG.name, logging.INFO, "process from=16000000, to=16999999")
            )
            assert 1 == caplog.record_tuples.count(
                (LOG.name, logging.INFO, "process from=17000000, to=17999999")
            )
            assert 1 == caplog.record_tuples.count(
                (LOG.name, logging.INFO, "process from=18000000, to=18999999")
            )
            assert 1 == caplog.record_tuples.count(
                (LOG.name, logging.INFO, "process from=19000000, to=19999999")
            )

            async_session.expunge_all()
            await async_session.rollback()
            processed_list = (
                await async_session.scalars(
                    select(TokenHoldersList)
                    .where(TokenHoldersList.id == target_token_holders_list.id)
                    .limit(1)
                )
            ).first()
            assert processed_list is not None
            assert processed_list.block_number == 19999999
            assert processed_list.batch_status == TokenHolderBatchStatus.DONE.value

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # There is no target token holders list id with batch_status PENDING.
    async def test_error_1(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        token_list_contract = shared_contract["TokenList"]

        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            await processor.collect()

        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.DEBUG, "There are no pending collect batch")
        )

    # <Error_2>
    # There is target token holders list id with batch_status PENDING.
    # And target token is not contained in "TokenList" contract.
    async def test_error_2(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        token_list_contract = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        # Insert collection definition with token address Zero
        target_token_holders_list = TokenHoldersList()
        target_token_holders_list.token_address = ZERO_ADDRESS
        target_token_holders_list.list_id = str(uuid.uuid4())
        target_token_holders_list.batch_status = TokenHolderBatchStatus.PENDING.value
        target_token_holders_list.block_number = 1000
        async_session.add(target_token_holders_list)
        await async_session.commit()

        # Debug message should be shown that points out token contract must be listed.
        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            await processor.collect()
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                "Token contract must be listed to TokenList contract.",
            )
        )

        # Batch status of token holders list expects to be "ERROR"
        error_record_num = len(
            list(
                (
                    await async_session.scalars(
                        select(TokenHoldersList).where(
                            TokenHoldersList.batch_status
                            == TokenHolderBatchStatus.FAILED.value
                        )
                    )
                ).all()
            )
        )
        assert error_record_num == 1

    # <Error_3>
    # Failed to get Logs because of ABIEventNotFound.
    @mock.patch(
        "web3.eth.async_eth.AsyncEth.get_logs",
        MagicMock(side_effect=ABIEventNotFound()),
    )
    async def test_error_3(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issuer issues bond token.
        token = self.issue_token_bond(
            self.issuer,
            escrow_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
        )

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        IbetStraightBondTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            20000,
        )
        IbetStraightBondTestHelper.transfer_token(
            self.user1["account_address"],
            token.address,
            escrow_contract["address"],
            10000,
        )
        current_block_number = web3.eth.block_number

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(
            token.address, current_block_number
        )
        async_session.add(target_token_holders_list)
        await async_session.commit()

        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            await processor.collect()
        _records = (
            await async_session.scalars(
                select(TokenHolder).where(
                    TokenHolder.holder_list == target_token_holders_list.id
                )
            )
        ).all()
        assert len(_records) == 0

    # <Error_4>
    # Failed to get Logs because of blockchain(ServiceUnavailable).
    async def test_error_4(
        self,
        processor: Processor,
        shared_contract: SharedContract,
        async_session: AsyncSession,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issuer issues bond token.
        token = self.issue_token_bond(
            self.issuer,
            escrow_contract["address"],
            personal_info_contract["address"],
            token_list_contract,
        )

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        IbetStraightBondTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            20000,
        )
        IbetStraightBondTestHelper.transfer_token(
            self.user1["account_address"],
            token.address,
            escrow_contract["address"],
            10000,
        )
        current_block_number = web3.eth.block_number

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(
            token.address, current_block_number
        )
        async_session.add(target_token_holders_list)
        await async_session.commit()

        with (
            mock.patch(
                "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
                token_list_contract["address"],
            ),
            mock.patch(
                "web3.eth.async_eth.AsyncEth.get_code", side_effect=ServiceUnavailable()
            ),
            pytest.raises(ServiceUnavailable),
        ):
            await processor.collect()

        _records = (
            await async_session.scalars(
                select(TokenHolder).where(
                    TokenHolder.holder_list == target_token_holders_list.id
                )
            )
        ).all()
        assert len(_records) == 0

        IbetStraightBondTestHelper.transfer_token(
            self.issuer["account_address"],
            token.address,
            self.user1["account_address"],
            20000,
        )
        IbetStraightBondTestHelper.transfer_token(
            self.user1["account_address"],
            token.address,
            escrow_contract["address"],
            10000,
        )
        current_block_number = web3.eth.block_number

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(
            token.address, current_block_number
        )
        async_session.add(target_token_holders_list)
        await async_session.commit()

        with (
            mock.patch(
                "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
                token_list_contract["address"],
            ),
            mock.patch(
                "web3.eth.async_eth.AsyncEth.get_code", side_effect=ServiceUnavailable()
            ),
            pytest.raises(ServiceUnavailable),
        ):
            await processor.collect()

        await async_session.rollback()
        _records = (
            await async_session.scalars(
                select(TokenHolder).where(
                    TokenHolder.holder_list == target_token_holders_list.id
                )
            )
        ).all()
        assert len(_records) == 0
