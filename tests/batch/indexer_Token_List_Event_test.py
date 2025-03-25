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
from unittest import mock
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from web3 import Web3
from web3.exceptions import ABIEventNotFound
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.db import IDXTokenListBlockNumber, IDXTokenListRegister, Listing
from batch import indexer_Token_List_Event
from batch.indexer_Token_List_Event import LOG, Processor, main
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
    config.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    return indexer_Token_List_Event.Processor


@pytest.fixture(scope="function")
def processor(test_module, async_session):
    LOG = logging.getLogger("ibet_wallet_batch")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True

    processor = test_module()
    yield processor

    LOG.propagate = False
    LOG.setLevel(default_log_level)


@pytest.fixture(scope="function")
def main_func(test_module):
    LOG = logging.getLogger("ibet_wallet_batch")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield main
    LOG.propagate = False
    LOG.setLevel(default_log_level)


@pytest.mark.asyncio
class TestProcessor:
    issuer = eth_account["issuer"]
    user1 = eth_account["user1"]
    user2 = eth_account["user2"]
    trader = eth_account["trader"]
    agent = eth_account["agent"]

    @staticmethod
    async def listing_token(token_address, async_session):
        _listing = Listing()
        _listing.token_address = token_address
        _listing.is_public = True
        _listing.max_holding_quantity = 1000000
        _listing.max_sell_amount = 1000000
        _listing.owner_address = TestProcessor.issuer["account_address"]
        async_session.add(_listing)
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
    # no token is listed
    async def test_normal_1(
        self,
        processor: Processor,
        shared_contract,
        async_session: AsyncSession,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        _token_list_block_number = IDXTokenListBlockNumber()
        _token_list_block_number.latest_block_number = web3.eth.block_number
        _token_list_block_number.contract_address = token_list_contract["address"]
        async_session.add(_token_list_block_number)
        await async_session.commit()

        # Run target process
        await processor.process()

        # assertion
        _token_list = (await async_session.scalars(select(IDXTokenListRegister))).all()
        assert len(_token_list) == 0

    # <Normal_2>
    # Multiple token is listed
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
        _token_expected_list = []

        _token_list_block_number = IDXTokenListBlockNumber()
        _token_list_block_number.latest_block_number = web3.eth.block_number
        _token_list_block_number.contract_address = token_list_contract["address"]
        async_session.add(_token_list_block_number)
        await async_session.commit()

        # Issue bond token
        for i in range(2):
            args = {
                "name": f"テスト債券{str(i + 1)}",
                "symbol": "BOND",
                "totalSupply": 1000000,
                "tradableExchange": exchange_contract["address"],
                "faceValue": int((i + 1) * 10000),
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
            await self.listing_token(token["address"], async_session)
            _token_expected_list.append(
                {
                    "token_address": token["address"],
                    "token_template": "IbetStraightBond",
                    "owner_address": self.issuer["account_address"],
                }
            )

        # Issue share token
        for i in range(2):
            args = {
                "name": "テスト株式",
                "symbol": "SHARE",
                "tradableExchange": exchange_contract["address"],
                "personalInfoAddress": personal_info_contract["address"],
                "issuePrice": int((i + 1) * 1000),
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
            }
            token = self.issue_token_share_with_args(
                self.issuer, token_list_contract, args
            )
            await self.listing_token(token["address"], async_session)
            _token_expected_list.append(
                {
                    "token_address": token["address"],
                    "token_template": "IbetShare",
                    "owner_address": self.issuer["account_address"],
                }
            )

        # Issue membership token
        for i in range(2):
            args = {
                "name": "テスト会員権",
                "symbol": "MEMBERSHIP",
                "initialSupply": int((i + 1) * 1000000),
                "tradableExchange": exchange_contract["address"],
                "details": "詳細",
                "returnDetails": "リターン詳細",
                "expirationDate": "20191231",
                "memo": "メモ",
                "transferable": True,
                "contactInformation": "問い合わせ先",
                "privacyPolicy": "プライバシーポリシー",
            }
            token = self.issue_token_membership_with_args(
                self.issuer, token_list_contract, args
            )
            await self.listing_token(token["address"], async_session)
            _token_expected_list.append(
                {
                    "token_address": token["address"],
                    "token_template": "IbetMembership",
                    "owner_address": self.issuer["account_address"],
                }
            )

        # Issue coupon token
        for i in range(2):
            args = {
                "name": "テストクーポン",
                "symbol": "COUPON",
                "totalSupply": int((i + 1) * 1000000),
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
            await self.listing_token(token["address"], async_session)
            _token_expected_list.append(
                {
                    "token_address": token["address"],
                    "token_template": "IbetCoupon",
                    "owner_address": self.issuer["account_address"],
                }
            )

        # register unknown token template
        TokenListContract = Contract.get_contract(
            "TokenList", token_list_contract["address"]
        )
        web3.eth.default_account = self.issuer["account_address"]
        args = {
            "name": "TestToken",
            "symbol": "Test",
            "totalSupply": 1000000,
            "tradableExchange": exchange_contract["address"],
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
            "personalInfoAddress": personal_info_contract["address"],
            "transferable": True,
            "isRedeemed": False,
            "faceValueCurrency": "JPY",
            "interestPaymentCurrency": "JPY",
            "redemptionValueCurrency": "JPY",
            "baseFxRate": "",
        }
        test_token = issue_bond_token(self.issuer, args)
        TokenListContract.functions.register(
            test_token["address"], "UnknownTokenTemplate"
        ).transact({"from": self.issuer["account_address"]})

        # Run target process
        await processor.process()

        # assertion
        for _expect_dict in _token_expected_list:
            token_list_item: IDXTokenListRegister = (
                await async_session.scalars(
                    select(IDXTokenListRegister)
                    .where(
                        IDXTokenListRegister.token_address
                        == _expect_dict["token_address"]
                    )
                    .limit(1)
                )
            ).first()

            assert token_list_item.token_template == _expect_dict["token_template"]
            assert token_list_item.owner_address == _expect_dict["owner_address"]

    # <Normal_3_1>
    # When processed block_number is not stored and current block number is 9,999,999,
    # then processor should call "__sync_register" method 10 times.
    async def test_normal_3_1(
        self,
        processor: Processor,
        shared_contract,
        async_session: AsyncSession,
        block_number: None,
        caplog: pytest.LogCaptureFixture,
    ):
        token_list_contract = shared_contract["TokenList"]

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        mock_lib = MagicMock()

        current_block_number = 10000000 - 1
        block_number_mock = AsyncMock()
        block_number_mock.return_value = current_block_number

        # Run target process
        with mock.patch(
            "web3.eth.async_eth.AsyncEth.block_number", block_number_mock()
        ):
            with mock.patch.object(
                Processor, "_Processor__sync_register", return_value=mock_lib
            ) as __sync_register_mock:
                __sync_register_mock.return_value = None
                await processor.process()

                # Then processor calls "__sync_register" method 10 times.
                assert __sync_register_mock.call_count == 10

                idx_token_list_block_number: IDXTokenListBlockNumber = (
                    await async_session.scalars(
                        select(IDXTokenListBlockNumber).limit(1)
                    )
                ).first()
                assert (
                    idx_token_list_block_number.latest_block_number
                    == current_block_number
                )

                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=0, to=999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=1000000, to=1999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=2000000, to=2999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=3000000, to=3999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=4000000, to=4999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=5000000, to=5999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=6000000, to=6999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=7000000, to=7999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=8000000, to=8999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=9000000, to=9999999")
                )

        with mock.patch(
            "web3.eth.async_eth.AsyncEth.block_number", block_number_mock()
        ):
            with mock.patch.object(
                Processor, "_Processor__sync_register", return_value=mock_lib
            ) as __sync_register_mock:
                __sync_register_mock.return_value = None
                await processor.process()

                # Then processor does not call "__sync_register" method.
                assert __sync_register_mock.call_count == 0

    # <Normal_3_2>
    # When processed block_number is 9,999,999 and current block number is 19,999,999,
    # then processor should call "__sync_register" method 10 times.
    async def test_normal_3_2(
        self,
        processor: Processor,
        shared_contract,
        async_session: AsyncSession,
        block_number: None,
        caplog: pytest.LogCaptureFixture,
    ):
        token_list_contract = shared_contract["TokenList"]

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        mock_lib = MagicMock()

        latest_block_number = 10000000 - 1
        _token_list_block_number = IDXTokenListBlockNumber()
        _token_list_block_number.latest_block_number = latest_block_number
        _token_list_block_number.contract_address = token_list_contract["address"]
        async_session.add(_token_list_block_number)
        await async_session.commit()

        current_block_number = 20000000 - 1
        block_number_mock = AsyncMock()
        block_number_mock.return_value = current_block_number

        # Run target process
        with mock.patch(
            "web3.eth.async_eth.AsyncEth.block_number", block_number_mock()
        ):
            with mock.patch.object(
                Processor, "_Processor__sync_register", return_value=mock_lib
            ) as __sync_register_mock:
                __sync_register_mock.return_value = None
                await processor.process()

                async_session.expunge_all()
                # Then processor calls "__sync_register" method 10 times.
                assert __sync_register_mock.call_count == 10

                idx_token_list_block_number: IDXTokenListBlockNumber = (
                    await async_session.scalars(
                        select(IDXTokenListBlockNumber).limit(1)
                    )
                ).first()
                assert (
                    idx_token_list_block_number.latest_block_number
                    == current_block_number
                )

                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=10000000, to=10999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=11000000, to=11999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=12000000, to=12999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=13000000, to=13999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=14000000, to=14999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=15000000, to=15999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=16000000, to=16999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=17000000, to=17999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=18000000, to=18999999")
                )
                assert 1 == caplog.record_tuples.count(
                    (LOG.name, logging.INFO, "Syncing from=19000000, to=19999999")
                )

        with mock.patch(
            "web3.eth.async_eth.AsyncEth.block_number", block_number_mock()
        ):
            with mock.patch.object(
                Processor, "_Processor__sync_register", return_value=mock_lib
            ) as __sync_register_mock:
                __sync_register_mock.return_value = None
                await processor.process()

                # Then processor does not call "__sync_register" method.
                assert __sync_register_mock.call_count == 0

    # <Normal_3_3>
    # When processed block_number is 19,999,999 and current block number is 19,999,999,
    # then processor should not call "__sync_register" method.
    async def test_normal_3_3(
        self,
        processor: Processor,
        shared_contract,
        async_session: AsyncSession,
        block_number: None,
        caplog: pytest.LogCaptureFixture,
    ):
        token_list_contract = shared_contract["TokenList"]

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        mock_lib = MagicMock()

        latest_block_number = 20000000 - 1
        _token_list_block_number = IDXTokenListBlockNumber()
        _token_list_block_number.latest_block_number = latest_block_number
        _token_list_block_number.contract_address = token_list_contract["address"]
        async_session.add(_token_list_block_number)
        await async_session.commit()

        current_block_number = 20000000 - 1
        block_number_mock = AsyncMock()
        block_number_mock.return_value = current_block_number

        # Run target process
        with mock.patch(
            "web3.eth.async_eth.AsyncEth.block_number", block_number_mock()
        ):
            with mock.patch.object(
                Processor, "_Processor__sync_register", return_value=mock_lib
            ) as __sync_register_mock:
                __sync_register_mock.return_value = None
                await processor.process()

                # Then processor does not call "__sync_register" method.
                assert __sync_register_mock.call_count == 0

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1>: ABIEventNotFound occurs in __sync_xx method.
    # <Error_2_1>: ServiceUnavailable occurs in __sync_xx method.
    # <Error_2_2>: SQLAlchemyError occurs in "process".
    # <Error_3>: ServiceUnavailable occurs and is handled in mainloop.

    # <Error_1>: ABIEventNotFound occurs in __sync_xx method.
    @mock.patch(
        "web3.eth.async_eth.AsyncEth.get_logs",
        MagicMock(side_effect=ABIEventNotFound()),
    )
    async def test_error_1(self, processor: Processor, shared_contract, async_session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]

        _token_list_block_number = IDXTokenListBlockNumber()
        _token_list_block_number.latest_block_number = web3.eth.block_number
        _token_list_block_number.contract_address = token_list_contract["address"]
        async_session.add(_token_list_block_number)
        await async_session.commit()

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
        await self.listing_token(token["address"], async_session)

        block_number_current = web3.eth.block_number
        # Run initial sync
        await processor.process()

        # Assertion
        async_session.expunge_all()
        _token_list = (await async_session.scalars(select(IDXTokenListRegister))).all()
        _token_list_block_number: IDXTokenListBlockNumber = (
            await async_session.scalars(select(IDXTokenListBlockNumber))
        ).first()
        assert len(_token_list) == 0
        # Latest_block is incremented in "process" process.
        assert _token_list_block_number.latest_block_number == block_number_current

        token = self.issue_token_coupon_with_args(
            self.issuer, token_list_contract, args
        )
        await self.listing_token(token["address"], async_session)

        block_number_current = web3.eth.block_number
        # Run target process
        await processor.process()

        # Run target process
        await processor.process()

        # Assertion
        async_session.expunge_all()
        await async_session.rollback()
        # Assertion
        _token_list = (await async_session.scalars(select(IDXTokenListRegister))).all()
        _token_list_block_number: IDXTokenListBlockNumber = (
            await async_session.scalars(select(IDXTokenListBlockNumber).limit(1))
        ).first()
        assert len(_token_list) == 0
        # Latest_block is incremented in "process" process.
        assert _token_list_block_number.latest_block_number == block_number_current

    # <Error_2_1>: ServiceUnavailable occurs in __sync_xx method.
    async def test_error_2_1(
        self, processor: Processor, shared_contract, async_session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]

        _token_list_block_number = IDXTokenListBlockNumber()
        _token_list_block_number.latest_block_number = web3.eth.block_number
        _token_list_block_number.contract_address = token_list_contract["address"]
        async_session.add(_token_list_block_number)
        await async_session.commit()

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
        await self.listing_token(token["address"], async_session)

        _token_list_block_number_bf: IDXTokenListBlockNumber = (
            await async_session.scalars(select(IDXTokenListBlockNumber).limit(1))
        ).first()
        # Expect that process() raises ServiceUnavailable.
        with (
            mock.patch(
                "web3.AsyncWeb3.AsyncHTTPProvider.make_request",
                MagicMock(side_effect=ServiceUnavailable()),
            ),
            pytest.raises(ServiceUnavailable),
        ):
            await processor.process()

        await async_session.rollback()
        # Assertion
        _token_list = (await async_session.scalars(select(IDXTokenListRegister))).all()
        _token_list_block_number_af: IDXTokenListBlockNumber = (
            await async_session.scalars(select(IDXTokenListBlockNumber).limit(1))
        ).first()
        assert len(_token_list) == 0
        assert (
            _token_list_block_number_bf.latest_block_number
            == _token_list_block_number_af.latest_block_number
        )

        token = self.issue_token_coupon_with_args(
            self.issuer, token_list_contract, args
        )
        await self.listing_token(token["address"], async_session)

        await async_session.rollback()
        _token_list_block_number_bf: IDXTokenListBlockNumber = (
            await async_session.scalars(select(IDXTokenListBlockNumber).limit(1))
        ).first()

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
        _token_list = (await async_session.scalars(select(IDXTokenListRegister))).all()
        _token_list_block_number_af: IDXTokenListBlockNumber = (
            await async_session.scalars(select(IDXTokenListBlockNumber).limit(1))
        ).first()
        assert len(_token_list) == 0
        assert (
            _token_list_block_number_bf.latest_block_number
            == _token_list_block_number_af.latest_block_number
        )

    # <Error_2_2>: SQLAlchemyError occurs in "process".
    async def test_error_2_2(
        self, processor: Processor, shared_contract, async_session
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]

        _token_list_block_number = IDXTokenListBlockNumber()
        _token_list_block_number.latest_block_number = web3.eth.block_number
        _token_list_block_number.contract_address = token_list_contract["address"]
        async_session.add(_token_list_block_number)
        await async_session.commit()

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
        await self.listing_token(token["address"], async_session)

        # Expect that process() raises SQLAlchemyError.
        with (
            mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()),
            pytest.raises(SQLAlchemyError),
        ):
            await processor.process()

        # Assertion
        _token_list = (await async_session.scalars(select(IDXTokenListRegister))).all()
        _token_list_block_number_af: IDXTokenListBlockNumber = (
            await async_session.scalars(select(IDXTokenListBlockNumber).limit(1))
        ).first()
        assert len(_token_list) == 0
        assert (
            _token_list_block_number_af.latest_block_number
            == _token_list_block_number.latest_block_number
        )

        token = self.issue_token_coupon_with_args(
            self.issuer, token_list_contract, args
        )
        await self.listing_token(token["address"], async_session)

        await async_session.rollback()

        # Expect that process() raises SQLAlchemyError.
        with (
            mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()),
            pytest.raises(SQLAlchemyError),
        ):
            await processor.process()

        # Assertion
        await async_session.rollback()
        _token_list = (await async_session.scalars(select(IDXTokenListRegister))).all()
        _token_list_block_number_af: IDXTokenListBlockNumber = (
            await async_session.scalars(select(IDXTokenListBlockNumber).limit(1))
        ).first()
        assert len(_token_list) == 0
        assert (
            _token_list_block_number_af.latest_block_number
            == _token_list_block_number.latest_block_number
        )

    # <Error_3>: ServiceUnavailable occurs and is handled in mainloop.
    async def test_error_3(self, main_func, shared_contract, async_session, caplog):
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
        await self.listing_token(token["address"], async_session)

        # Mocking time.sleep to break mainloop
        asyncio_mock = MagicMock(wraps=asyncio)
        asyncio_mock.sleep.side_effect = [TypeError()]

        # Run mainloop once and fail with web3 utils error
        with (
            mock.patch("batch.indexer_Token_List_Event.asyncio", asyncio_mock),
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
            (LOG.name, 25, "An external service was unavailable")
        )
        caplog.clear()
