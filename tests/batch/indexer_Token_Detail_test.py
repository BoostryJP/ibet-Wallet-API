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
import re
import time
import pytest
from decimal import Decimal
from typing import List
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from unittest import mock
from unittest.mock import MagicMock
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.errors import ServiceUnavailable
from app.model.blockchain import BondToken, ShareToken, MembershipToken, CouponToken
from app.model.db import (
    Listing,
    IDXBondToken as BondTokenModel,
    IDXShareToken as ShareTokenModel,
    IDXMembershipToken as MembershipTokenModel,
    IDXCouponToken as CouponTokenModel,
    IDXTokenListItem
)
from batch import indexer_Token_Detail
from batch.indexer_Token_Detail import Processor, LOG, main
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
    return indexer_Token_Detail


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


class TestProcessor:
    issuer = eth_account["issuer"]
    user1 = eth_account["user1"]
    user2 = eth_account["user2"]
    trader = eth_account["trader"]
    agent = eth_account["agent"]

    @staticmethod
    def listing_token(token_address, token_template, session):
        _listing = Listing()
        _listing.token_address = token_address
        _listing.is_public = True
        _listing.max_holding_quantity = 1000000
        _listing.max_sell_amount = 1000000
        _listing.owner_address = TestProcessor.issuer["account_address"]
        session.add(_listing)

        _idx_token_list_item = IDXTokenListItem()
        _idx_token_list_item.token_address = token_address
        _idx_token_list_item.token_template = token_template
        _idx_token_list_item.owner_address = TestProcessor.issuer["account_address"]
        session.add(_idx_token_list_item)
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
    def test_normal_1(self, processor: Processor, shared_contract, session: Session, block_number: None):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract['address']
        _bond_token_expected_list = []
        # Issue bond token
        for i in range(10):
            args = {
                "name": f"テスト債券{str(i+1)}",
                "symbol": f"BOND{str(i+1)}",
                "totalSupply": 1000000+1,
                "tradableExchange": exchange_contract["address"],
                "faceValue": int((i+1)*10000),
                "interestRate": 602+1,
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
                "redemptionValue": 10000+1,
                "returnDate": "20191231",
                "returnAmount": f"商品券をプレゼント{str(i+1)}",
                "purpose": f"新商品の開発資金として利用。{str(i+1)}",
                "memo": f"メモ{str(i+1)}",
                "contactInformation": f"問い合わせ先{str(i+1)}",
                "privacyPolicy": f"プライバシーポリシー{str(i+1)}",
                "personalInfoAddress": personal_info_contract["address"],
                "transferable": True,
                "isRedeemed": False,
            }
            token = self.issue_token_bond_with_args(
                self.issuer, token_list_contract, args
            )
            self.listing_token(token["address"], "IbetStraightBond", session)
            args = {
                re.sub("([A-Z])", lambda x: "_" + x.group(1).lower(), k): v for k, v in args.items()
            }
            args["interest_rate"] = float(Decimal(str(args["interest_rate"])) * Decimal('0.0001'))
            _bond_token_expected_list.append({**args, "token_address": token["address"]})

        _share_token_expected_list = []
        # Issue share token
        for i in range(10):
            args = {
                "name": f"テスト株式{str(i+1)}",
                "symbol": f"SHARE{str(i+1)}",
                "tradableExchange": exchange_contract["address"],
                "personalInfoAddress": personal_info_contract["address"],
                "issuePrice": int((i+1)*1000),
                "principalValue": 1000+i,
                "totalSupply": 1000000+i,
                "dividends": 101+i,
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
            self.listing_token(token["address"], "IbetShare", session)
            args = {
                re.sub("([A-Z])", lambda x: "_" + x.group(1).lower(), k): v for k, v in args.items()
            }
            args["dividend_information"] = {
                "dividends": float(Decimal(str(args["dividends"])) * Decimal("0.0000000000001")),
                "dividend_record_date": args["dividend_record_date"],
                "dividend_payment_date": args["dividend_payment_date"]
            }
            del args["dividends"]
            del args["dividend_record_date"]
            del args["dividend_payment_date"]
            _share_token_expected_list.append({**args, "token_address": token["address"]})

        _membership_token_expected_list = []
        # Issue membership token
        for i in range(10):
            args = {
                "name": f"テスト会員権{str(i+1)}",
                "symbol": f"MEMBERSHIP{str(i+1)}",
                "initialSupply": int((i+1)*1000000),
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
            self.listing_token(token["address"], "IbetMembership", session)

            args["totalSupply"] = args["initialSupply"]
            del args["initialSupply"]
            args = {
                re.sub("([A-Z])", lambda x: "_" + x.group(1).lower(), k): v for k, v in args.items()
            }
            _membership_token_expected_list.append({**args, "token_address": token["address"]})

        _coupon_token_expected_list = []
        # issue coupon token
        for i in range(10):
            args = {
                "name": f"テストクーポン{str(i+1)}",
                "symbol": f"COUPON{str(i+1)}",
                "totalSupply":  int((i+1)*1000000),
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
            self.listing_token(token["address"], "IbetCoupon", session)
            args = {
                re.sub("([A-Z])", lambda x: "_" + x.group(1).lower(), k): v for k, v in args.items()
            }
            _coupon_token_expected_list.append({**args, "token_address": token["address"]})

        # Run target process
        processor.SEC_PER_RECORD = 0
        processor.process()

        # assertion
        for _expect_dict in _bond_token_expected_list:
            _bond_token: BondTokenModel = session.query(BondTokenModel).filter(BondTokenModel.token_address == _expect_dict["token_address"]).one()
            _bond_token_obj = BondToken.from_model(_bond_token)
            for k, v in _expect_dict.items():
                assert v == getattr(_bond_token_obj, k)

        for _expect_dict in _share_token_expected_list:
            _share_token: ShareTokenModel = session.query(ShareTokenModel).filter(ShareTokenModel.token_address == _expect_dict["token_address"]).one()
            _share_token_obj = ShareToken.from_model(_share_token)
            for k, v in _expect_dict.items():
                assert v == getattr(_share_token_obj, k)

        for _expect_dict in _membership_token_expected_list:
            _membership_token: MembershipTokenModel = session.query(MembershipTokenModel).filter(MembershipTokenModel.token_address == _expect_dict["token_address"]).one()
            _membership_token_obj = MembershipToken.from_model(_membership_token)
            for k, v in _expect_dict.items():
                assert v == getattr(_membership_token_obj, k)

        for _expect_dict in _coupon_token_expected_list:
            _coupon_token: CouponTokenModel = session.query(CouponTokenModel).filter(CouponTokenModel.token_address == _expect_dict["token_address"]).one()
            _coupon_token_obj = CouponToken.from_model(_coupon_token)
            for k, v in _expect_dict.items():
                assert v == getattr(_coupon_token_obj, k)

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1_1>: ServiceUnavailable occurs in __sync_xx method.
    # <Error_1_2>: SQLAlchemyError occurs in "process"
    # <Error_2>: ServiceUnavailable occurs and is handled in mainloop.

    # <Error_1_1>: ServiceUnavailable occurs in __sync_xx method.
    def test_error_1_1(self, processor: Processor, shared_contract, session):
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
        self.listing_token(token["address"], "IbetCoupon", session)

        # Expect that process() raises ServiceUnavailable.
        with mock.patch("web3.providers.rpc.HTTPProvider.make_request", MagicMock(side_effect=ServiceUnavailable())), \
                pytest.raises(ServiceUnavailable):
            processor.process()

        # Assertion
        _coupon_token_list: List[CouponTokenModel] = session.query(CouponTokenModel).all()
        assert len(_coupon_token_list) == 0

        token = self.issue_token_coupon_with_args(self.issuer, token_list_contract, args)
        self.listing_token(token["address"], "IbetCoupon", session)

        # Expect that process() raises ServiceUnavailable.
        with mock.patch("web3.providers.rpc.HTTPProvider.make_request", MagicMock(side_effect=ServiceUnavailable())), \
                pytest.raises(ServiceUnavailable):
            processor.process()

        # Assertion
        session.rollback()
        _coupon_token_list: List[CouponTokenModel] = session.query(CouponTokenModel).all()
        assert len(_coupon_token_list) == 0

    # <Error_1_2>: SQLAlchemyError occurs in "process".
    def test_error_1_2(self, processor: Processor, shared_contract, session):
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
        self.listing_token(token["address"], "IbetCoupon", session)

        # Expect that process() raises SQLAlchemyError.
        with mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()), \
                pytest.raises(SQLAlchemyError):
            processor.process()

        # Assertion
        _coupon_token_list: List[CouponTokenModel] = session.query(CouponTokenModel).all()
        assert len(_coupon_token_list) == 0

        token = self.issue_token_coupon_with_args(self.issuer, token_list_contract, args)
        self.listing_token(token["address"], "IbetCoupon", session)

        # Expect that process() raises SQLAlchemyError.
        with mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()), \
                pytest.raises(SQLAlchemyError):
            processor.process()

        # Assertion
        session.rollback()
        _coupon_token_list: List[CouponTokenModel] = session.query(CouponTokenModel).all()
        assert len(_coupon_token_list) == 0

    # <Error_2>: ServiceUnavailable occurs and is handled in mainloop.
    def test_error_2(self, main_func, shared_contract, session, caplog):
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
        self.listing_token(token["address"], "IbetCoupon", session)
        # Mocking time.sleep to break mainloop
        time_mock = MagicMock(wraps=time)
        time_mock.sleep.side_effect = [TypeError()]

        # Run mainloop once and fail with web3 utils error
        with mock.patch("batch.indexer_Token_Detail.time", time_mock),\
            mock.patch("web3.providers.rpc.HTTPProvider.make_request", MagicMock(side_effect=ServiceUnavailable())), \
                pytest.raises(TypeError):
            # Expect that process() raises ServiceUnavailable and handled in mainloop.
            main_func()

        assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, "Service started successfully"))
        assert 1 == caplog.record_tuples.count((LOG.name, logging.WARNING, "An external service was unavailable"))
        caplog.clear()
