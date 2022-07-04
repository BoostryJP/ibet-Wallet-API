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
import time
import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List, Optional
from unittest import mock
from unittest.mock import MagicMock
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import ABIEventFunctionNotFound

from app import config
from app.errors import ServiceUnavailable
from app.model.db import (
    Listing,
    IDXTokenListItem,
    IDXTokenListBlockNumber
)
from batch import indexer_Token_List
from batch.indexer_Token_List import Processor, LOG, main
from tests.account_config import eth_account
from tests.contract_modules import (
    issue_bond_token,
    register_bond_list,
    issue_share_token,
    register_share_list,
    issue_coupon_token,
    coupon_register_list,
    membership_issue,
    membership_register_list
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

@pytest.fixture(scope="session")
def test_module(shared_contract):
    indexer_Token_List.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    return indexer_Token_List


@pytest.fixture(scope="function")
def processor(test_module, session):
    processor = test_module.Processor()
    return processor


@pytest.fixture(scope="function")
def main_func(test_module):
    LOG = logging.getLogger("Processor")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield main
    LOG.propagate = False
    LOG.setLevel(default_log_level)


class TestProcessor:
    issuer = eth_account["issuer"]
    user1 = eth_account["user1"]
    user2 = eth_account["user2"]
    trader = eth_account["trader"]
    agent = eth_account["agent"]

    @staticmethod
    def listing_token(token_address, session):
        _listing = Listing()
        _listing.token_address = token_address
        _listing.is_public = True
        _listing.max_holding_quantity = 1000000
        _listing.max_sell_amount = 1000000
        _listing.owner_address = TestProcessor.issuer["account_address"]
        session.add(_listing)
        session.commit()

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
    def test_normal_1(self, processor: Processor, shared_contract, session: Session, block_number: None):
        token_list_contract = shared_contract["TokenList"]
        _token_list_block_number = IDXTokenListBlockNumber()
        _token_list_block_number.latest_block_number = web3.eth.block_number
        _token_list_block_number.contract_address = token_list_contract['address']
        session.add(_token_list_block_number)
        session.commit()

        # Run target process
        processor.process()

        # assertion
        _token_list: List[IDXTokenListItem] = session.query(IDXTokenListItem).all()
        assert len(_token_list) == 0

    # <Normal_2>
    # Multiple token is listed
    def test_normal_2(self, processor: Processor, shared_contract, session: Session, block_number: None):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract['address']
        _token_expected_list = []

        _token_list_block_number = IDXTokenListBlockNumber()
        _token_list_block_number.latest_block_number = web3.eth.block_number
        _token_list_block_number.contract_address = token_list_contract['address']
        session.add(_token_list_block_number)
        session.commit()

        # Issue bond token
        for i in range(10):
            args = {
                "name": f"テスト債券{str(i+1)}",
                "symbol": "BOND",
                "totalSupply": 1000000,
                "tradableExchange": exchange_contract["address"],
                "faceValue": int((i+1)*10000),
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
            }
            token = self.issue_token_bond_with_args(
                self.issuer, token_list_contract, args
            )
            self.listing_token(token["address"], session)
            _token_expected_list.append({
                "token_address": token["address"],
                "token_template": "IbetStraightBond",
                "owner_address": self.issuer["account_address"]
            })

        # Issue share token
        for i in range(10):
            args = {
                "name": "テスト株式",
                "symbol": "SHARE",
                "tradableExchange": exchange_contract["address"],
                "personalInfoAddress": personal_info_contract["address"],
                "issuePrice": int((i+1)*1000),
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
            self.listing_token(token["address"], session)
            _token_expected_list.append({
                "token_address": token["address"],
                "token_template": "IbetShare",
                "owner_address": self.issuer["account_address"]
            })

        # Issue membership token
        for i in range(10):
            args = {
                "name": "テスト会員権",
                "symbol": "MEMBERSHIP",
                "initialSupply": int((i+1)*1000000),
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
            self.listing_token(token["address"], session)
            _token_expected_list.append({
                "token_address": token["address"],
                "token_template": "IbetMembership",
                "owner_address": self.issuer["account_address"]
            })

        # issue coupon token
        for i in range(10):
            args = {
                "name": "テストクーポン",
                "symbol": "COUPON",
                "totalSupply":  int((i+1)*1000000),
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
            self.listing_token(token["address"], session)
            _token_expected_list.append({
                "token_address": token["address"],
                "token_template": "IbetCoupon",
                "owner_address": self.issuer["account_address"]
            })

        # Run target process
        processor.process()

        # assertion
        for _expect_dict in _token_expected_list:
            token_list_item: IDXTokenListItem = session.query(IDXTokenListItem).\
                filter(IDXTokenListItem.token_address == _expect_dict["token_address"]).one()

            assert token_list_item.token_template == _expect_dict["token_template"]
            assert token_list_item.owner_address == _expect_dict["owner_address"]

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1>: ABIEventFunctionNotFound occurs in __sync_xx method.
    # <Error_2_1>: ServiceUnavailable occurs in __sync_xx method.
    # <Error_2_2>: SQLAlchemyError occurs in "process".
    # <Error_3>: ServiceUnavailable occurs and is handled in mainloop.

    # <Error_1>: ABIEventFunctionNotFound occurs in __sync_xx method.
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=ABIEventFunctionNotFound()))
    def test_error_1(self, processor: Processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]

        _token_list_block_number = IDXTokenListBlockNumber()
        _token_list_block_number.latest_block_number = web3.eth.block_number
        _token_list_block_number.contract_address = token_list_contract["address"]
        session.add(_token_list_block_number)
        session.commit()

        args = {
            "name": "テストクーポン",
            "symbol": "COUPON",
            "totalSupply":  1000000,
            "tradableExchange": exchange_contract["address"],
            "details": "クーポン詳細",
            "returnDetails": "リターン詳細",
            "memo": "クーポンメモ欄",
            "expirationDate": "20191231",
            "transferable": True,
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
        }
        token = self.issue_token_coupon_with_args(self.issuer, token_list_contract, args)
        self.listing_token(token["address"], session)

        block_number_current = web3.eth.block_number
        # Run initial sync
        processor.process()

        # Assertion
        _token_list: List[IDXTokenListItem] = session.query(IDXTokenListItem).all()
        _token_list_block_number: Optional[IDXTokenListBlockNumber] = session.query(IDXTokenListBlockNumber).first()
        assert len(_token_list) == 0
        # Latest_block is incremented in "process" process.
        assert _token_list_block_number.latest_block_number == block_number_current

        token = self.issue_token_coupon_with_args(self.issuer, token_list_contract, args)
        self.listing_token(token["address"], session)

        block_number_current = web3.eth.block_number
        # Run target process
        processor.process()

        # Run target process
        processor.process()

        # Assertion
        session.rollback()
        # Assertion
        _token_list: List[IDXTokenListItem] = session.query(IDXTokenListItem).all()
        _token_list_block_number: Optional[IDXTokenListBlockNumber] = session.query(IDXTokenListBlockNumber).first()
        assert len(_token_list) == 0
        # Latest_block is incremented in "process" process.
        assert _token_list_block_number.latest_block_number == block_number_current

    # <Error_2_1>: ServiceUnavailable occurs in __sync_xx method.
    def test_error_2_1(self, processor: Processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]

        _token_list_block_number = IDXTokenListBlockNumber()
        _token_list_block_number.latest_block_number = web3.eth.block_number
        _token_list_block_number.contract_address = token_list_contract["address"]
        session.add(_token_list_block_number)
        session.commit()

        args = {
            "name": "テストクーポン",
            "symbol": "COUPON",
            "totalSupply":  1000000,
            "tradableExchange": exchange_contract["address"],
            "details": "クーポン詳細",
            "returnDetails": "リターン詳細",
            "memo": "クーポンメモ欄",
            "expirationDate": "20191231",
            "transferable": True,
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
        }
        token = self.issue_token_coupon_with_args(self.issuer, token_list_contract, args)
        self.listing_token(token["address"], session)

        _token_list_block_number_bf: Optional[IDXTokenListBlockNumber] = session.query(IDXTokenListBlockNumber).first()
        # Expect that process() raises ServiceUnavailable.
        with mock.patch("web3.providers.rpc.HTTPProvider.make_request", MagicMock(side_effect=ServiceUnavailable())), \
                pytest.raises(ServiceUnavailable):
            processor.process()

        session.rollback()
        # Assertion
        _token_list: List[IDXTokenListItem] = session.query(IDXTokenListItem).all()
        _token_list_block_number_af: Optional[IDXTokenListBlockNumber] = session.query(IDXTokenListBlockNumber).first()
        assert len(_token_list) == 0
        assert _token_list_block_number_bf.latest_block_number == _token_list_block_number_af.latest_block_number

        token = self.issue_token_coupon_with_args(self.issuer, token_list_contract, args)
        self.listing_token(token["address"], session)

        session.rollback()
        _token_list_block_number_bf: Optional[IDXTokenListBlockNumber] = session.query(IDXTokenListBlockNumber).first()

        # Expect that process() raises ServiceUnavailable.
        with mock.patch("web3.providers.rpc.HTTPProvider.make_request", MagicMock(side_effect=ServiceUnavailable())), \
                pytest.raises(ServiceUnavailable):
            processor.process()

        # Assertion
        session.rollback()
        _token_list: List[IDXTokenListItem] = session.query(IDXTokenListItem).all()
        _token_list_block_number_af: Optional[IDXTokenListBlockNumber] = session.query(IDXTokenListBlockNumber).first()
        assert len(_token_list) == 0
        assert _token_list_block_number_bf.latest_block_number == _token_list_block_number_af.latest_block_number

    # <Error_2_2>: SQLAlchemyError occurs in "process".
    def test_error_2_2(self, processor: Processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]

        _token_list_block_number = IDXTokenListBlockNumber()
        _token_list_block_number.latest_block_number = web3.eth.block_number
        _token_list_block_number.contract_address = token_list_contract["address"]
        session.add(_token_list_block_number)
        session.commit()

        args = {
            "name": "テストクーポン",
            "symbol": "COUPON",
            "totalSupply":  1000000,
            "tradableExchange": exchange_contract["address"],
            "details": "クーポン詳細",
            "returnDetails": "リターン詳細",
            "memo": "クーポンメモ欄",
            "expirationDate": "20191231",
            "transferable": True,
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
        }
        token = self.issue_token_coupon_with_args(self.issuer, token_list_contract, args)
        self.listing_token(token["address"], session)

        # Expect that process() raises SQLAlchemyError.
        with mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()), \
                pytest.raises(SQLAlchemyError):
            processor.process()

        # Assertion
        _token_list: List[IDXTokenListItem] = session.query(IDXTokenListItem).all()
        _token_list_block_number_af: Optional[IDXTokenListBlockNumber] = session.query(IDXTokenListBlockNumber).first()
        assert len(_token_list) == 0
        assert _token_list_block_number_af.latest_block_number == _token_list_block_number.latest_block_number

        token = self.issue_token_coupon_with_args(self.issuer, token_list_contract, args)
        self.listing_token(token["address"], session)

        session.rollback()

        # Expect that process() raises SQLAlchemyError.
        with mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()), \
                pytest.raises(SQLAlchemyError):
            processor.process()

        # Assertion
        session.rollback()
        _token_list: List[IDXTokenListItem] = session.query(IDXTokenListItem).all()
        _token_list_block_number_af: Optional[IDXTokenListBlockNumber] = session.query(IDXTokenListBlockNumber).first()
        assert len(_token_list) == 0
        assert _token_list_block_number_af.latest_block_number == _token_list_block_number.latest_block_number

    # <Error_3>: ServiceUnavailable occurs and is handled in mainloop.
    def test_error_3(self, main_func, shared_contract, session, caplog):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]

        args = {
            "name": "テストクーポン",
            "symbol": "COUPON",
            "totalSupply":  1000000,
            "tradableExchange": exchange_contract["address"],
            "details": "クーポン詳細",
            "returnDetails": "リターン詳細",
            "memo": "クーポンメモ欄",
            "expirationDate": "20191231",
            "transferable": True,
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
        }
        token = self.issue_token_coupon_with_args(self.issuer, token_list_contract, args)
        self.listing_token(token["address"], session)

        # Mocking time.sleep to break mainloop
        time_mock = MagicMock(wraps=time)
        time_mock.sleep.side_effect = [TypeError()]

        # Run mainloop once and fail with web3 utils error
        with mock.patch("batch.indexer_Token_List.time", time_mock),\
            mock.patch("web3.providers.rpc.HTTPProvider.make_request", MagicMock(side_effect=ServiceUnavailable())), \
                pytest.raises(TypeError):
            # Expect that process() raises ServiceUnavailable and handled in mainloop.
            main_func()

        assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, "Service started successfully"))
        assert 1 == caplog.record_tuples.count((LOG.name, logging.WARNING, "An external service was unavailable"))
        caplog.clear()
