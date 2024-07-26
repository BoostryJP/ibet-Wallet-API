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
from datetime import UTC, datetime
from decimal import Decimal
from unittest import mock
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.blockchain import BondToken, CouponToken, MembershipToken, ShareToken
from app.model.db import (
    IDXBondToken as BondTokenModel,
    IDXCouponToken as CouponTokenModel,
    IDXMembershipToken as MembershipTokenModel,
    IDXShareToken as ShareTokenModel,
    IDXTokenListItem,
    Listing,
)
from batch import indexer_Token_Detail_ShortTerm
from batch.indexer_Token_Detail_ShortTerm import LOG, Processor, main
from tests.account_config import eth_account
from tests.contract_modules import (
    coupon_register_list,
    issue_bond_token,
    issue_coupon_token,
    issue_share_token,
    membership_issue,
    membership_register_list,
    register_bond_list,
    register_share_list,
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    return indexer_Token_Detail_ShortTerm


@pytest.fixture(scope="function")
def processor(test_module, session):
    config.BOND_TOKEN_ENABLED = True
    config.SHARE_TOKEN_ENABLED = True
    config.MEMBERSHIP_TOKEN_ENABLED = True
    config.COUPON_TOKEN_ENABLED = True
    processor = test_module.Processor()
    return processor


@pytest.fixture(scope="function")
def main_func(test_module):
    LOG = logging.getLogger("ibet_wallet_batch")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield main
    LOG.propagate = False
    LOG.setLevel(default_log_level)


@mock.patch("app.config.BOND_TOKEN_ENABLED", True)
@mock.patch("app.config.SHARE_TOKEN_ENABLED", True)
@mock.patch("app.config.COUPON_TOKEN_ENABLED", True)
@mock.patch("app.config.MEMBERSHIP_TOKEN_ENABLED", True)
class TestProcessor:
    issuer = eth_account["issuer"]
    user1 = eth_account["user1"]
    user2 = eth_account["user2"]
    trader = eth_account["trader"]
    agent = eth_account["agent"]

    @staticmethod
    async def listing_token(token_address, token_template, async_session: AsyncSession):
        _listing = Listing()
        _listing.token_address = token_address
        _listing.is_public = True
        _listing.max_holding_quantity = 1000000
        _listing.max_sell_amount = 1000000
        _listing.owner_address = TestProcessor.issuer["account_address"]
        async_session.add(_listing)

        _idx_token_list_item = IDXTokenListItem()
        _idx_token_list_item.token_address = token_address
        _idx_token_list_item.token_template = token_template
        _idx_token_list_item.owner_address = TestProcessor.issuer["account_address"]
        async_session.add(_idx_token_list_item)
        await async_session.commit()

    @staticmethod
    def issue_token_bond_with_args(issuer, token_list, args):
        # Issue token
        token = issue_bond_token(issuer, args)
        register_bond_list(issuer, token, token_list)

        return token

    @staticmethod
    def issue_token_share_with_args(issuer, token_list, args):
        # Issue token
        token = issue_share_token(issuer, args)
        register_share_list(issuer, token, token_list)

        return token

    @staticmethod
    def issue_token_coupon_with_args(issuer, token_list, args):
        # Issue token
        token = issue_coupon_token(issuer, args)
        coupon_register_list(issuer, token, token_list)

        return token

    @staticmethod
    def issue_token_membership_with_args(issuer, token_list, args):
        # Issue token
        token = membership_issue(issuer, args)
        membership_register_list(issuer, token, token_list)

        return token

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Multiple listed tokens and no events
    @pytest.mark.asyncio
    async def test_normal_1(
        self,
        processor: Processor,
        shared_contract,
        async_session: AsyncSession,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        _bond_token_expected_list = []
        # Issue bond token
        for i in range(10):
            args = {
                "name": f"テスト債券{str(i+1)}",
                "symbol": f"BOND{str(i+1)}",
                "totalSupply": 1000000 + 1,
                "tradableExchange": exchange_contract["address"],
                "faceValue": int((i + 1) * 10000),
                "interestRate": 602 + 1,
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
                "redemptionValue": 10000 + 1,
                "returnDate": "20191231",
                "returnAmount": f"商品券をプレゼント{str(i+1)}",
                "purpose": f"新商品の開発資金として利用。{str(i+1)}",
                "memo": f"メモ{str(i+1)}",
                "contactInformation": f"問い合わせ先{str(i+1)}",
                "privacyPolicy": f"プライバシーポリシー{str(i+1)}",
                "personalInfoAddress": personal_info_contract["address"],
                "transferable": True,
                "isRedeemed": False,
                "faceValueCurrency": "JPY",
                "interestPaymentCurrency": "JPY",
                "redemptionValueCurrency": "JPY",
                "baseFxRate": "",
            }
            token = self.issue_token_bond_with_args(
                self.issuer, token_list_contract, args
            )
            await self.listing_token(
                token["address"], "IbetStraightBond", async_session
            )
            # Fetch data for cache
            async_session.add(
                (await BondToken.get(async_session, token["address"])).to_model()
            )
            _bond_token_expected_list.append({"token_address": token["address"]})

        _share_token_expected_list = []
        # Issue share token
        for i in range(10):
            args = {
                "name": f"テスト株式{str(i+1)}",
                "symbol": f"SHARE{str(i+1)}",
                "tradableExchange": exchange_contract["address"],
                "personalInfoAddress": personal_info_contract["address"],
                "issuePrice": int((i + 1) * 1000),
                "principalValue": 1000 + i,
                "totalSupply": 1000000 + i,
                "dividends": 101 + i,
                "dividendRecordDate": "20200401",
                "dividendPaymentDate": "20200502",
                "cancellationDate": "20200603",
                "contactInformation": f"問い合わせ先{str(i+1)}",
                "privacyPolicy": f"プライバシーポリシー{str(i+1)}",
                "memo": "メモ",
                "transferable": True,
            }
            token = self.issue_token_share_with_args(
                self.issuer, token_list_contract, args
            )
            await self.listing_token(token["address"], "IbetShare", async_session)
            # Fetch data for cache
            async_session.add(
                (await ShareToken.get(async_session, token["address"])).to_model()
            )
            _share_token_expected_list.append({"token_address": token["address"]})

        _membership_token_expected_list = []
        # Issue membership token
        for i in range(10):
            args = {
                "name": f"テスト会員権{str(i+1)}",
                "symbol": f"MEMBERSHIP{str(i+1)}",
                "initialSupply": int((i + 1) * 1000000),
                "tradableExchange": exchange_contract["address"],
                "details": f"詳細{str(i+1)}",
                "returnDetails": f"リターン詳細{str(i+1)}",
                "expirationDate": "20191231",
                "memo": f"メモ{str(i+1)}",
                "transferable": True,
                "contactInformation": f"問い合わせ先{str(i+1)}",
                "privacyPolicy": f"プライバシーポリシー{str(i+1)}",
            }
            token = self.issue_token_membership_with_args(
                self.issuer, token_list_contract, args
            )
            await self.listing_token(token["address"], "IbetMembership", async_session)
            # Fetch data for cache
            async_session.add(
                (await MembershipToken.get(async_session, token["address"])).to_model()
            )
            _membership_token_expected_list.append({"token_address": token["address"]})

        _coupon_token_expected_list = []
        # issue coupon token
        for i in range(10):
            args = {
                "name": f"テストクーポン{str(i+1)}",
                "symbol": f"COUPON{str(i+1)}",
                "totalSupply": int((i + 1) * 1000000),
                "tradableExchange": exchange_contract["address"],
                "details": f"クーポン詳細{str(i+1)}",
                "returnDetails": f"リターン詳細{str(i+1)}",
                "memo": f"クーポンメモ欄{str(i+1)}",
                "expirationDate": "20191231",
                "transferable": True,
                "contactInformation": f"問い合わせ先{str(i+1)}",
                "privacyPolicy": f"プライバシーポリシー{str(i+1)}",
            }

            token = self.issue_token_coupon_with_args(
                self.issuer, token_list_contract, args
            )
            await self.listing_token(token["address"], "IbetCoupon", async_session)
            # Fetch data for cache
            async_session.add(
                (await CouponToken.get(async_session, token["address"])).to_model()
            )
            _coupon_token_expected_list.append({"token_address": token["address"]})

        await async_session.commit()
        current = datetime.now(UTC).replace(tzinfo=None)
        await asyncio.sleep(1)

        # Run target process
        processor.SEC_PER_RECORD = 0
        with mock.patch("app.config.TOKEN_SHORT_TERM_FETCH_INTERVAL_MSEC", 0):
            await processor.process()

        await async_session.rollback()
        # assertion
        for _expect_dict in _bond_token_expected_list:
            _bond_token: BondTokenModel = (
                await async_session.scalars(
                    select(BondTokenModel)
                    .where(
                        BondTokenModel.token_address == _expect_dict["token_address"]
                    )
                    .limit(1)
                )
            ).first()
            assert _bond_token.short_term_cache_created > current

        for _expect_dict in _share_token_expected_list:
            _share_token: ShareTokenModel = (
                await async_session.scalars(
                    select(ShareTokenModel)
                    .where(
                        ShareTokenModel.token_address == _expect_dict["token_address"]
                    )
                    .limit(1)
                )
            ).first()
            assert _share_token.short_term_cache_created > current

        for _expect_dict in _membership_token_expected_list:
            _membership_token: MembershipTokenModel = (
                await async_session.scalars(
                    select(MembershipTokenModel)
                    .where(
                        MembershipTokenModel.token_address
                        == _expect_dict["token_address"]
                    )
                    .limit(1)
                )
            ).first()
            assert _membership_token.short_term_cache_created > current

        for _expect_dict in _coupon_token_expected_list:
            _coupon_token: CouponTokenModel = (
                await async_session.scalars(
                    select(CouponTokenModel)
                    .where(
                        CouponTokenModel.token_address == _expect_dict["token_address"]
                    )
                    .limit(1)
                )
            ).first()
            assert _coupon_token.short_term_cache_created > current

    # <Normal_2>
    # Multiple listed tokens and multiple events
    # - Bond
    #   - ChangeStatus
    #   - ChangeFaceValue
    #   - ChangeRedemptionValue
    #   - ChangeTransferApprovalRequired
    #   - ChangeOfferingStatus
    #   - ChangeToRedeemed
    #   - ChangeOwner
    @pytest.mark.asyncio
    async def test_normal_2(
        self,
        processor: Processor,
        shared_contract,
        async_session: AsyncSession,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        _bond_token_expected_list = []
        # Issue bond token
        for i in range(5):
            args = {
                "name": f"テスト債券{str(i+1)}",
                "symbol": f"BOND{str(i+1)}",
                "totalSupply": 1000000 + 1,
                "tradableExchange": exchange_contract["address"],
                "faceValue": int(10000),
                "interestRate": 602 + 1,
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
                "redemptionValue": 10000 + 1,
                "returnDate": "20191231",
                "returnAmount": f"商品券をプレゼント{str(i+1)}",
                "purpose": f"新商品の開発資金として利用。{str(i+1)}",
                "memo": f"メモ{str(i+1)}",
                "contactInformation": f"問い合わせ先{str(i+1)}",
                "privacyPolicy": f"プライバシーポリシー{str(i+1)}",
                "personalInfoAddress": personal_info_contract["address"],
                "transferable": True,
                "isRedeemed": False,
                "faceValueCurrency": "JPY",
                "interestPaymentCurrency": "JPY",
                "redemptionValueCurrency": "JPY",
                "baseFxRate": "",
            }
            token = self.issue_token_bond_with_args(
                self.issuer, token_list_contract, args
            )
            await self.listing_token(
                token["address"], "IbetStraightBond", async_session
            )
            bond_token = await BondToken.get(async_session, token["address"])
            async_session.add(bond_token.to_model())

            # Change attributes to occur events
            token_contract = Contract.get_contract(
                contract_name="IbetStraightBond", address=token["address"]
            )
            token_contract.functions.setRedemptionValue(99999).transact(
                {"from": self.issuer["account_address"]}
            )
            token_contract.functions.changeToRedeemed().transact(
                {"from": self.issuer["account_address"]}
            )
            token_contract.functions.changeOfferingStatus(False).transact(
                {"from": self.issuer["account_address"]}
            )
            token_contract.functions.setTransferApprovalRequired(True).transact(
                {"from": self.issuer["account_address"]}
            )
            token_contract.functions.setFaceValue(1).transact(
                {"from": self.issuer["account_address"]}
            )
            token_contract.functions.setStatus(False).transact(
                {"from": self.issuer["account_address"]}
            )

            token_contract = Contract.get_contract(
                contract_name="Ownable", address=token["address"]
            )
            token_contract.functions.transferOwnership(
                self.agent["account_address"]
            ).transact({"from": self.issuer["account_address"]})

            # Fetch data for cache
            _bond_token_expected_list.append({"token_address": token["address"]})

        await async_session.commit()
        # Then
        await processor.process()

        await async_session.rollback()
        # assertion
        for _expect_dict in _bond_token_expected_list:
            _bond_token: BondTokenModel = (
                await async_session.scalars(
                    select(BondTokenModel)
                    .where(
                        BondTokenModel.token_address == _expect_dict["token_address"]
                    )
                    .limit(1)
                )
            ).first()
            # Short-Term Cache attributes is updated instantly.
            assert _bond_token.is_redeemed == True
            assert _bond_token.is_offering == False
            assert _bond_token.transfer_approval_required == True
            assert _bond_token.status == False
            assert _bond_token.owner_address == self.agent["account_address"]

            # Not Short-Term Cache attributes is not updated.
            assert _bond_token.redemption_value == 10001
            assert _bond_token.face_value == 10000

    # <Normal_3>
    # Multiple listed tokens and multiple events
    # - Share
    #   - ChangeStatus
    #   - ChangeTransferApprovalRequired
    #   - ChangeOfferingStatus
    #   - ChangeDividendInformation
    #   - ChangeToCanceled
    #   - ChangeOwner
    @pytest.mark.asyncio
    async def test_normal_3(
        self,
        processor: Processor,
        shared_contract,
        async_session: AsyncSession,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        _share_token_expected_list = []
        # Issue bond token
        for i in range(5):
            args = {
                "name": f"テスト株式{str(i+1)}",
                "symbol": f"SHARE{str(i+1)}",
                "tradableExchange": exchange_contract["address"],
                "personalInfoAddress": personal_info_contract["address"],
                "issuePrice": int((i + 1) * 1000),
                "principalValue": 1000 + i,
                "totalSupply": 1000000 + i,
                "dividends": 101 + i,
                "dividendRecordDate": "20200401",
                "dividendPaymentDate": "20200502",
                "cancellationDate": "20200603",
                "contactInformation": f"問い合わせ先{str(i+1)}",
                "privacyPolicy": f"プライバシーポリシー{str(i+1)}",
                "memo": "メモ",
                "transferable": True,
            }
            token = self.issue_token_share_with_args(
                self.issuer, token_list_contract, args
            )
            await self.listing_token(
                token["address"], "IbetStraightBond", async_session
            )
            # Fetch data for cache
            share_token = await ShareToken.get(async_session, token["address"])
            async_session.add(share_token.to_model())

            # Change attributes to occur events
            token_contract = Contract.get_contract(
                contract_name="IbetShare", address=token["address"]
            )

            token_contract.functions.setStatus(False).transact(
                {"from": self.issuer["account_address"]}
            )
            token_contract.functions.setTransferApprovalRequired(True).transact(
                {"from": self.issuer["account_address"]}
            )
            token_contract.functions.changeOfferingStatus(False).transact(
                {"from": self.issuer["account_address"]}
            )
            token_contract.functions.changeToCanceled().transact(
                {"from": self.issuer["account_address"]}
            )
            token_contract.functions.setDividendInformation(
                50, "20200401", "20200401"
            ).transact({"from": self.issuer["account_address"]})

            token_contract = Contract.get_contract(
                contract_name="Ownable", address=token["address"]
            )
            token_contract.functions.transferOwnership(
                self.agent["account_address"]
            ).transact({"from": self.issuer["account_address"]})

            _share_token_expected_list.append({"token_address": token["address"]})

        await async_session.commit()
        # Then
        await processor.process()

        await async_session.rollback()
        # assertion
        for _expect_dict in _share_token_expected_list:
            _share_token: ShareTokenModel = (
                await async_session.scalars(
                    select(ShareTokenModel)
                    .where(
                        ShareTokenModel.token_address == _expect_dict["token_address"]
                    )
                    .limit(1)
                )
            ).first()
            # Short-Term Cache attributes is updated instantly.
            assert _share_token.status == False
            assert _share_token.transfer_approval_required == True
            assert _share_token.is_offering == False
            assert _share_token.is_canceled == True
            assert _share_token.dividend_information == {
                "dividends": float(Decimal(str(50)) * Decimal("0.0000000000001")),
                "dividend_record_date": "20200401",
                "dividend_payment_date": "20200401",
            }
            assert _share_token.owner_address == self.agent["account_address"]

    # <Normal_4>
    # Multiple listed tokens and multiple events
    # - Membership/Coupon
    #   - ChangeStatus
    #   - ChangeOwner
    @pytest.mark.asyncio
    async def test_normal_4(
        self,
        processor: Processor,
        shared_contract,
        async_session: AsyncSession,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        _membership_token_expected_list = []
        # Issue bond token
        for i in range(5):
            args = {
                "name": f"テスト会員権{str(i+1)}",
                "symbol": f"MEMBERSHIP{str(i+1)}",
                "initialSupply": int((i + 1) * 1000000),
                "tradableExchange": exchange_contract["address"],
                "details": f"詳細{str(i+1)}",
                "returnDetails": f"リターン詳細{str(i+1)}",
                "expirationDate": "20191231",
                "memo": f"メモ{str(i+1)}",
                "transferable": True,
                "contactInformation": f"問い合わせ先{str(i+1)}",
                "privacyPolicy": f"プライバシーポリシー{str(i+1)}",
            }
            token = self.issue_token_membership_with_args(
                self.issuer, token_list_contract, args
            )
            await self.listing_token(token["address"], "IbetMembership", async_session)
            async_session.add(
                (await MembershipToken.get(async_session, token["address"])).to_model()
            )

            # Change attributes to occur events
            token_contract = Contract.get_contract(
                contract_name="IbetMembership", address=token["address"]
            )

            token_contract.functions.setStatus(False).transact(
                {"from": self.issuer["account_address"]}
            )

            token_contract = Contract.get_contract(
                contract_name="Ownable", address=token["address"]
            )
            token_contract.functions.transferOwnership(
                self.agent["account_address"]
            ).transact({"from": self.issuer["account_address"]})

            # Fetch data for cache
            _membership_token_expected_list.append({"token_address": token["address"]})

        _coupon_token_expected_list = []
        # issue coupon token
        for i in range(5):
            args = {
                "name": f"テストクーポン{str(i+1)}",
                "symbol": f"COUPON{str(i+1)}",
                "totalSupply": int((i + 1) * 1000000),
                "tradableExchange": exchange_contract["address"],
                "details": f"クーポン詳細{str(i+1)}",
                "returnDetails": f"リターン詳細{str(i+1)}",
                "memo": f"クーポンメモ欄{str(i+1)}",
                "expirationDate": "20191231",
                "transferable": True,
                "contactInformation": f"問い合わせ先{str(i+1)}",
                "privacyPolicy": f"プライバシーポリシー{str(i+1)}",
            }

            token = self.issue_token_coupon_with_args(
                self.issuer, token_list_contract, args
            )
            await self.listing_token(token["address"], "IbetCoupon", async_session)
            async_session.add(
                (await CouponToken.get(async_session, token["address"])).to_model()
            )

            # Change attributes to occur events
            token_contract = Contract.get_contract(
                contract_name="IbetCoupon", address=token["address"]
            )

            token_contract.functions.setStatus(False).transact(
                {"from": self.issuer["account_address"]}
            )

            token_contract = Contract.get_contract(
                contract_name="Ownable", address=token["address"]
            )
            token_contract.functions.transferOwnership(
                self.agent["account_address"]
            ).transact({"from": self.issuer["account_address"]})

            # Fetch data for cache
            _coupon_token_expected_list.append({"token_address": token["address"]})

        await async_session.commit()
        # Then
        await processor.process()

        await async_session.rollback()
        # assertion
        for _expect_dict in _membership_token_expected_list:
            _membership_token: MembershipTokenModel = (
                await async_session.scalars(
                    select(MembershipTokenModel)
                    .where(
                        MembershipTokenModel.token_address
                        == _expect_dict["token_address"]
                    )
                    .limit(1)
                )
            ).first()
            assert _membership_token.status == False
            assert _membership_token.owner_address == self.agent["account_address"]

        # assertion
        for _expect_dict in _coupon_token_expected_list:
            _coupon_token: CouponTokenModel = (
                await async_session.scalars(
                    select(CouponTokenModel)
                    .where(
                        CouponTokenModel.token_address == _expect_dict["token_address"]
                    )
                    .limit(1)
                )
            ).first()
            assert _coupon_token.status == False
            assert _coupon_token.owner_address == self.agent["account_address"]

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1_1>: ServiceUnavailable occurs in __sync_xx method.
    # <Error_1_2>: SQLAlchemyError occurs in "process"
    # <Error_2>: ServiceUnavailable occurs and is handled in mainloop.

    # <Error_1_1>: ServiceUnavailable occurs in __sync_xx method.
    @pytest.mark.asyncio
    async def test_error_1_1(
        self, processor: Processor, shared_contract, async_session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]
        args = {
            "name": "テストクーポン",
            "symbol": "COUPON",
            "totalSupply": 1000000,
            "tradableExchange": exchange_contract["address"],
            "details": "クーポン詳細",
            "returnDetails": "リターン詳細",
            "memo": "クーポンメモ欄",
            "expirationDate": "20191231",
            "transferable": True,
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
        }
        token = self.issue_token_coupon_with_args(
            self.issuer, token_list_contract, args
        )
        await self.listing_token(token["address"], "IbetCoupon", async_session)
        coupon_data = await CouponToken.get(async_session, token["address"])
        async_session.add(coupon_data.to_model())

        await async_session.commit()
        await asyncio.sleep(1)
        current = datetime.now(UTC).replace(tzinfo=None)

        # Expect that process() raises ServiceUnavailable.
        with (
            mock.patch(
                "web3.AsyncWeb3.AsyncHTTPProvider.make_request",
                MagicMock(side_effect=ServiceUnavailable()),
            ),
            pytest.raises(ServiceUnavailable),
        ):
            await processor.process()

        # Assertion
        _coupon_token: CouponTokenModel = (
            await async_session.scalars(
                select(CouponTokenModel)
                .where(CouponTokenModel.token_address == token["address"])
                .limit(1)
            )
        ).first()
        assert _coupon_token.short_term_cache_created < current

        token = self.issue_token_coupon_with_args(
            self.issuer, token_list_contract, args
        )
        await self.listing_token(token["address"], "IbetCoupon", async_session)
        coupon_data = await CouponToken.get(async_session, token["address"])
        async_session.add(coupon_data.to_model())

        await async_session.commit()
        await asyncio.sleep(1)
        current = datetime.now(UTC).replace(tzinfo=None)

        # Expect that process() raises ServiceUnavailable.
        with (
            mock.patch(
                "web3.AsyncWeb3.AsyncHTTPProvider.make_request",
                MagicMock(side_effect=ServiceUnavailable()),
            ),
            pytest.raises(ServiceUnavailable),
        ):
            await processor.process()

        # Assertion
        await async_session.rollback()
        _coupon_token: CouponTokenModel = (
            await async_session.scalars(
                select(CouponTokenModel)
                .where(CouponTokenModel.token_address == token["address"])
                .limit(1)
            )
        ).first()
        assert _coupon_token.short_term_cache_created < current

    # <Error_1_2>: SQLAlchemyError occurs in "process".
    @pytest.mark.asyncio
    async def test_error_1_2(
        self, processor: Processor, shared_contract, async_session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]
        args = {
            "name": "テストクーポン",
            "symbol": "COUPON",
            "totalSupply": 1000000,
            "tradableExchange": exchange_contract["address"],
            "details": "クーポン詳細",
            "returnDetails": "リターン詳細",
            "memo": "クーポンメモ欄",
            "expirationDate": "20191231",
            "transferable": True,
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
        }
        token = self.issue_token_coupon_with_args(
            self.issuer, token_list_contract, args
        )
        await self.listing_token(token["address"], "IbetCoupon", async_session)
        coupon_data = await CouponToken.get(async_session, token["address"])
        async_session.add(coupon_data.to_model())

        await async_session.commit()
        await asyncio.sleep(1)
        current = datetime.now(UTC).replace(tzinfo=None)

        # Expect that process() raises SQLAlchemyError.
        with (
            mock.patch.object(AsyncSession, "commit", side_effect=SQLAlchemyError()),
            pytest.raises(SQLAlchemyError),
        ):
            await processor.process()

        # Assertion
        _coupon_token: CouponTokenModel = (
            await async_session.scalars(
                select(CouponTokenModel)
                .where(CouponTokenModel.token_address == token["address"])
                .limit(1)
            )
        ).first()
        assert _coupon_token.short_term_cache_created < current

    # <Error_2>: ServiceUnavailable occurs and is handled in mainloop.
    @pytest.mark.asyncio
    async def test_error_2(self, main_func, shared_contract, async_session, caplog):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]
        args = {
            "name": "テストクーポン",
            "symbol": "COUPON",
            "totalSupply": 1000000,
            "tradableExchange": exchange_contract["address"],
            "details": "クーポン詳細",
            "returnDetails": "リターン詳細",
            "memo": "クーポンメモ欄",
            "expirationDate": "20191231",
            "transferable": True,
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
        }
        token = self.issue_token_coupon_with_args(
            self.issuer, token_list_contract, args
        )
        await self.listing_token(token["address"], "IbetCoupon", async_session)
        coupon_data = await CouponToken.get(async_session, token["address"])
        async_session.add(coupon_data.to_model())

        await async_session.commit()

        # Mocking asyncio.sleep to break mainloop
        time_mock = MagicMock(wraps=asyncio)
        time_mock.sleep.side_effect = [TypeError()]

        # Run mainloop once and fail with web3 utils error
        with (
            mock.patch("batch.indexer_Token_Detail_ShortTerm.asyncio", time_mock),
            mock.patch(
                "web3.AsyncWeb3.AsyncHTTPProvider.make_request",
                MagicMock(side_effect=ServiceUnavailable()),
            ),
            pytest.raises(TypeError),
        ):
            # Expect that process() raises ServiceUnavailable and handled in mainloop.
            await main_func()

        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "Service started successfully")
        )
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.WARNING, "An external service was unavailable")
        )
        caplog.clear()
