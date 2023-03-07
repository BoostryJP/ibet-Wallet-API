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
from unittest import mock
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from web3 import Web3
from web3.exceptions import ABIEventFunctionNotFound
from web3.middleware import geth_poa_middleware

from app import config
from app.errors import ServiceUnavailable
from app.model.db import AgreementStatus, IDXAgreement, IDXOrder, Listing
from batch import indexer_DEX
from batch.indexer_DEX import LOG, main
from tests.account_config import eth_account
from tests.conftest import ibet_exchange_contract
from tests.contract_modules import (
    cancel_agreement,
    cancel_order,
    confirm_agreement,
    coupon_register_list,
    issue_coupon_token,
    make_buy,
    make_sell,
    membership_issue,
    membership_register_list,
    membership_transfer_to_exchange,
    take_buy,
    take_sell,
    transfer_coupon_token,
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="function")
def processor_factory(session, shared_contract):
    def _processor(membership=False, coupon=False):
        # Create exchange contract for each test method.
        exchange_address = {
            "membership": None,
            "coupon": None,
        }

        indexer_DEX.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = None
        indexer_DEX.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = None

        if membership is True:
            membership_exchange = ibet_exchange_contract(
                shared_contract["PaymentGateway"]["address"]
            )
            indexer_DEX.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = membership_exchange[
                "address"
            ]
            exchange_address["membership"] = membership_exchange["address"]
        if coupon is True:
            coupon_exchange = ibet_exchange_contract(
                shared_contract["PaymentGateway"]["address"]
            )
            indexer_DEX.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = coupon_exchange[
                "address"
            ]
            exchange_address["coupon"] = coupon_exchange["address"]

        processor = indexer_DEX.Processor()
        processor.initial_sync()

        return processor, exchange_address

    return _processor


@pytest.fixture(scope="function")
def main_func(processor_factory):
    LOG = logging.getLogger("ibet_wallet_batch")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield main
    LOG.propagate = False
    LOG.setLevel(default_log_level)


class TestProcessor:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

    @staticmethod
    def issue_token_membership(issuer, exchange_contract_address, token_list):
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
        token = membership_issue(issuer, args)
        membership_register_list(issuer, token, token_list)

        return token

    @staticmethod
    def issue_token_coupon(issuer, exchange_contract_address, token_list):
        # Issue token
        args = {
            "name": "テストクーポン",
            "symbol": "COUPON",
            "totalSupply": 1000000,
            "tradableExchange": exchange_contract_address,
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

        return token

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

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # - Create Order
    def test_normal_1(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(membership=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["membership"]
        token = self.issue_token_membership(
            self.issuer, exchange_contract_address, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )
        block_number = web3.eth.block_number

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 1

        block = web3.eth.get_block(block_number)
        _order = _order_list[0]
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is False
        assert _order.price == 100
        assert _order.amount == 1000000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is False
        assert _order.order_timestamp is not None

        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 0

    # <Normal_2>
    # - Create Order
    # - Cancel Order
    def test_normal_2(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(membership=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["membership"]
        token = self.issue_token_membership(
            self.issuer, exchange_contract_address, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )
        block_number = web3.eth.block_number

        # Cancel Order
        cancel_order(self.issuer, {"address": exchange_contract_address}, 1)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 1

        block = web3.eth.get_block(block_number)
        _order = _order_list[0]
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is False
        assert _order.price == 100
        assert _order.amount == 1000000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is True
        assert _order.order_timestamp is not None

        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 0

    # <Normal_3>
    # - Create Order
    # - Order Agreement(Take buy)
    def test_normal_3(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(membership=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["membership"]
        token = self.issue_token_membership(
            self.issuer, exchange_contract_address, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )
        block_number = web3.eth.block_number

        # Order Agreement(Take buy)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 2000)
        block_number2 = web3.eth.block_number

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 1

        block = web3.eth.get_block(block_number)
        _order = _order_list[0]
        assert _order.id == 1
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is False
        assert _order.price == 100
        assert _order.amount == 1000000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is False
        assert _order.order_timestamp is not None

        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 1

        block2 = web3.eth.get_block(block_number2)
        _agreement = _agreement_list[0]
        assert _agreement.transaction_hash == block2["transactions"][0].hex()
        assert _agreement.exchange_address == exchange_contract_address
        assert _agreement.order_id == 1
        assert _agreement.agreement_id == 1
        assert _agreement.unique_order_id == f"{exchange_contract_address}_1"
        assert _agreement.buyer_address == self.trader["account_address"]
        assert _agreement.seller_address == self.issuer["account_address"]
        assert _agreement.counterpart_address == self.trader["account_address"]
        assert _agreement.amount == 2000
        assert _agreement.status == AgreementStatus.PENDING.value
        assert _agreement.agreement_timestamp is not None
        assert _agreement.settlement_timestamp is None

    # <Normal_4>
    # - Create Order
    # - Order Agreement(Take sell)
    def test_normal_4(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(membership=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["membership"]
        token = self.issue_token_membership(
            self.issuer, exchange_contract_address, token_list_contract
        )
        self.listing_token(token["address"], session)

        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 3000
        )

        # Create Order(Make buy)
        make_buy(self.issuer, {"address": exchange_contract_address}, token, 4000, 100)
        block_number = web3.eth.block_number

        # Order Agreement(Take sell)
        membership_transfer_to_exchange(
            self.trader, {"address": exchange_contract_address}, token, 3000
        )
        take_sell(self.trader, {"address": exchange_contract_address}, 1, 3000)
        block_number2 = web3.eth.block_number

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 1

        block = web3.eth.get_block(block_number)
        _order = _order_list[0]
        assert _order.id == 1
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is True
        assert _order.price == 100
        assert _order.amount == 4000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is False
        assert _order.order_timestamp is not None

        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 1

        block2 = web3.eth.get_block(block_number2)
        _agreement = _agreement_list[0]
        assert _agreement.transaction_hash == block2["transactions"][0].hex()
        assert _agreement.exchange_address == exchange_contract_address
        assert _agreement.order_id == 1
        assert _agreement.agreement_id == 1
        assert _agreement.unique_order_id == f"{exchange_contract_address}_1"
        assert _agreement.buyer_address == self.issuer["account_address"]
        assert _agreement.seller_address == self.trader["account_address"]
        assert _agreement.counterpart_address == self.trader["account_address"]
        assert _agreement.amount == 3000
        assert _agreement.status == AgreementStatus.PENDING.value
        assert _agreement.agreement_timestamp is not None
        assert _agreement.settlement_timestamp is None

    # <Normal_5>
    # - Create Order
    # - Order Agreement
    # - Confirm Agreement
    def test_normal_5(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(membership=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["membership"]
        token = self.issue_token_membership(
            self.issuer, exchange_contract_address, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )
        block_number = web3.eth.block_number

        # Order Agreement(Take buy)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 2000)
        block_number2 = web3.eth.block_number

        # Confirm Agreement
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 1

        block = web3.eth.get_block(block_number)
        _order = _order_list[0]
        assert _order.id == 1
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is False
        assert _order.price == 100
        assert _order.amount == 1000000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is False
        assert _order.order_timestamp is not None

        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 1

        block2 = web3.eth.get_block(block_number2)
        _agreement = _agreement_list[0]
        assert _agreement.transaction_hash == block2["transactions"][0].hex()
        assert _agreement.exchange_address == exchange_contract_address
        assert _agreement.order_id == 1
        assert _agreement.agreement_id == 1
        assert _agreement.unique_order_id == f"{exchange_contract_address}_1"
        assert _agreement.buyer_address == self.trader["account_address"]
        assert _agreement.seller_address == self.issuer["account_address"]
        assert _agreement.counterpart_address == self.trader["account_address"]
        assert _agreement.amount == 2000
        assert _agreement.status == AgreementStatus.DONE.value
        assert _agreement.agreement_timestamp is not None
        assert _agreement.settlement_timestamp is not None

    # <Normal_6>
    # - Create Order
    # - Order Agreement
    # - Cancel Agreement
    def test_normal_6(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(membership=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["membership"]
        token = self.issue_token_membership(
            self.issuer, exchange_contract_address, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )
        block_number = web3.eth.block_number

        # Order Agreement(Take buy)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 2000)
        block_number2 = web3.eth.block_number

        # Cancel Agreement
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 1

        block = web3.eth.get_block(block_number)
        _order = _order_list[0]
        assert _order.id == 1
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is False
        assert _order.price == 100
        assert _order.amount == 1000000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is False
        assert _order.order_timestamp is not None

        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 1

        block2 = web3.eth.get_block(block_number2)
        _agreement = _agreement_list[0]
        assert _agreement.transaction_hash == block2["transactions"][0].hex()
        assert _agreement.exchange_address == exchange_contract_address
        assert _agreement.order_id == 1
        assert _agreement.agreement_id == 1
        assert _agreement.unique_order_id == f"{exchange_contract_address}_1"
        assert _agreement.buyer_address == self.trader["account_address"]
        assert _agreement.seller_address == self.issuer["account_address"]
        assert _agreement.counterpart_address == self.trader["account_address"]
        assert _agreement.amount == 2000
        assert _agreement.status == AgreementStatus.CANCELED.value
        assert _agreement.agreement_timestamp is not None
        assert _agreement.settlement_timestamp is None

    # <Normal_7>
    # multi tokens
    # - Create Order
    # - Order Agreement
    # - Confirm Agreement
    def test_normal_7(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(membership=True, coupon=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        membership_exchange_contract_address = exchange_address["membership"]
        coupon_exchange_contract_address = exchange_address["coupon"]

        membership_token = self.issue_token_membership(
            self.issuer, membership_exchange_contract_address, token_list_contract
        )
        self.listing_token(membership_token["address"], session)

        coupon_token = self.issue_token_coupon(
            self.issuer, coupon_exchange_contract_address, token_list_contract
        )
        self.listing_token(coupon_token["address"], session)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer,
            {"address": membership_exchange_contract_address},
            membership_token,
            900000,
        )
        make_sell(
            self.issuer,
            {"address": membership_exchange_contract_address},
            membership_token,
            900000,
            100,
        )
        membership_block_number = web3.eth.block_number

        transfer_coupon_token(
            self.issuer, coupon_token, coupon_exchange_contract_address, 800000
        )
        make_sell(
            self.issuer,
            {"address": coupon_exchange_contract_address},
            coupon_token,
            800000,
            200,
        )
        coupon_block_number = web3.eth.block_number

        # Order Agreement(Take buy)
        take_buy(
            self.trader, {"address": membership_exchange_contract_address}, 1, 1000
        )
        membership_block_number2 = web3.eth.block_number

        take_buy(self.trader, {"address": coupon_exchange_contract_address}, 1, 2000)
        coupon_block_number2 = web3.eth.block_number

        # Confirm Agreement
        confirm_agreement(
            self.agent, {"address": membership_exchange_contract_address}, 1, 1
        )
        confirm_agreement(
            self.agent, {"address": coupon_exchange_contract_address}, 1, 1
        )

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 2

        block = web3.eth.get_block(membership_block_number)
        _order = _order_list[0]
        assert _order.id == 1
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == membership_token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{membership_exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is False
        assert _order.price == 100
        assert _order.amount == 900000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is False
        assert _order.order_timestamp is not None

        block = web3.eth.get_block(coupon_block_number)
        _order = _order_list[1]
        assert _order.id == 2
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == coupon_token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{coupon_exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is False
        assert _order.price == 200
        assert _order.amount == 800000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is False
        assert _order.order_timestamp is not None

        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 2

        block2 = web3.eth.get_block(membership_block_number2)
        _agreement = _agreement_list[0]
        assert _agreement.transaction_hash == block2["transactions"][0].hex()
        assert _agreement.exchange_address == membership_exchange_contract_address
        assert _agreement.order_id == 1
        assert _agreement.agreement_id == 1
        assert _agreement.unique_order_id == f"{membership_exchange_contract_address}_1"
        assert _agreement.buyer_address == self.trader["account_address"]
        assert _agreement.seller_address == self.issuer["account_address"]
        assert _agreement.counterpart_address == self.trader["account_address"]
        assert _agreement.amount == 1000
        assert _agreement.status == AgreementStatus.DONE.value
        assert _agreement.agreement_timestamp is not None
        assert _agreement.settlement_timestamp is not None

        block2 = web3.eth.get_block(coupon_block_number2)
        _agreement = _agreement_list[1]
        assert _agreement.transaction_hash == block2["transactions"][0].hex()
        assert _agreement.exchange_address == coupon_exchange_contract_address
        assert _agreement.order_id == 1
        assert _agreement.agreement_id == 1
        assert _agreement.unique_order_id == f"{coupon_exchange_contract_address}_1"
        assert _agreement.buyer_address == self.trader["account_address"]
        assert _agreement.seller_address == self.issuer["account_address"]
        assert _agreement.counterpart_address == self.trader["account_address"]
        assert _agreement.amount == 2000
        assert _agreement.status == AgreementStatus.DONE.value
        assert _agreement.agreement_timestamp is not None
        assert _agreement.settlement_timestamp is not None

    # <Normal_8>
    # Not Listing Token
    def test_normal_8(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(membership=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["membership"]
        token = self.issue_token_membership(
            self.issuer, exchange_contract_address, token_list_contract
        )

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 1000000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 1000000, 100
        )

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 0
        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 0

    # <Normal_9>
    # Unset Exchange Address
    def test_normal_9(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory()

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        membership_token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(membership_token["address"], session)
        coupon_token = self.issue_token_coupon(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(coupon_token["address"], session)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 0
        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 0

    # <Normal_10>
    # No event logs
    def test_normal_10(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory()

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 0
        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 0

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1_1>: ABIEventFunctionNotFound occurs in __sync_xx method.
    # <Error_1_2>: ServiceUnavailable occurs in __sync_xx method.
    # <Error_2_1>: ServiceUnavailable occurs in "initial_sync" / "sync_new_logs".
    # <Error_2_2>: SQLAlchemyError occurs in "initial_sync" / "sync_new_logs".
    # <Error_3>: ServiceUnavailable occurs and is handled in mainloop.

    # <Error_1_1>: ABIEventFunctionNotFound occurs in __sync_xx method.
    @mock.patch(
        "web3.contract.ContractEvent.getLogs",
        MagicMock(side_effect=ABIEventFunctionNotFound()),
    )
    def test_error_1_1(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(membership=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["membership"]
        token = self.issue_token_membership(
            self.issuer, exchange_contract_address, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 500000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 500000, 100
        )

        block_number_current = web3.eth.block_number
        # Run initial sync
        processor.initial_sync()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 0
        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 0

        # Latest_block is incremented in "initial_sync" process.
        assert processor.latest_block == block_number_current

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 500000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 500000, 100
        )

        block_number_current = web3.eth.block_number
        # Run target process
        processor.sync_new_logs()

        # Run target process
        processor.sync_new_logs()
        # Assertion
        session.rollback()
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 0
        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 0
        # Latest_block is incremented in "sync_new_logs" process.
        assert processor.latest_block == block_number_current

    # <Error_1_2>: ServiceUnavailable occurs in __sync_xx method.
    def test_error_1_2(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(membership=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["membership"]
        token = self.issue_token_membership(
            self.issuer, exchange_contract_address, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 500000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 500000, 100
        )

        block_number_bf = processor.latest_block
        # Expect that initial_sync() raises ServiceUnavailable.
        with mock.patch(
            "web3.eth.Eth.get_block", MagicMock(side_effect=ServiceUnavailable())
        ), pytest.raises(ServiceUnavailable):
            processor.initial_sync()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 0
        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 0
        assert processor.latest_block == block_number_bf

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 500000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 500000, 100
        )

        block_number_bf = processor.latest_block
        # Expect that sync_new_logs() raises ServiceUnavailable.
        with mock.patch(
            "web3.eth.Eth.get_block", MagicMock(side_effect=ServiceUnavailable())
        ), pytest.raises(ServiceUnavailable):
            processor.sync_new_logs()

        # Assertion
        session.rollback()
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 0
        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 0
        # Latest_block is NOT incremented in "sync_new_logs" process.
        assert processor.latest_block == block_number_bf

    # <Error_2_1>: ServiceUnavailable occurs in "initial_sync" / "sync_new_logs".
    def test_error_2_1(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(membership=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["membership"]
        token = self.issue_token_membership(
            self.issuer, exchange_contract_address, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 500000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 500000, 100
        )

        block_number_bf = processor.latest_block
        # Expect that initial_sync() raises ServiceUnavailable.
        with mock.patch(
            "web3.providers.rpc.HTTPProvider.make_request",
            MagicMock(side_effect=ServiceUnavailable()),
        ), pytest.raises(ServiceUnavailable):
            processor.initial_sync()
        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 0
        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 0
        assert processor.latest_block == block_number_bf

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 500000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 500000, 100
        )

        block_number_bf = processor.latest_block
        # Expect that sync_new_logs() raises ServiceUnavailable.
        with mock.patch(
            "web3.providers.rpc.HTTPProvider.make_request",
            MagicMock(side_effect=ServiceUnavailable()),
        ), pytest.raises(ServiceUnavailable):
            processor.sync_new_logs()

        # Assertion
        session.rollback()
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 0
        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 0
        # Latest_block is NOT incremented in "sync_new_logs" process.
        assert processor.latest_block == block_number_bf

    # <Error_2_2>: SQLAlchemyError occurs in "initial_sync" / "sync_new_logs".
    def test_error_2_2(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(membership=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["membership"]
        token = self.issue_token_membership(
            self.issuer, exchange_contract_address, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 500000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 500000, 100
        )

        block_number_bf = processor.latest_block
        # Expect that initial_sync() raises SQLAlchemyError.
        with mock.patch.object(
            Session, "commit", side_effect=SQLAlchemyError()
        ), pytest.raises(SQLAlchemyError):
            processor.initial_sync()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 0
        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 0
        assert processor.latest_block == block_number_bf

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": exchange_contract_address}, token, 500000
        )
        make_sell(
            self.issuer, {"address": exchange_contract_address}, token, 500000, 100
        )

        block_number_bf = processor.latest_block
        # Expect that sync_new_logs() raises SQLAlchemyError.
        with mock.patch.object(
            Session, "commit", side_effect=SQLAlchemyError()
        ), pytest.raises(SQLAlchemyError):
            processor.sync_new_logs()

        # Assertion
        session.rollback()
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 0
        _agreement_list = (
            session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        )
        assert len(_agreement_list) == 0
        # Latest_block is NOT incremented in "sync_new_logs" process.
        assert processor.latest_block == block_number_bf

    # <Error_3>: ServiceUnavailable occurs and is handled in mainloop.
    def test_error_3(
        self, main_func, processor_factory, shared_contract, session, caplog
    ):
        # Mocking time.sleep to break mainloop
        time_mock = MagicMock(wraps=time)
        time_mock.sleep.side_effect = [True, TypeError()]

        # Run mainloop once and fail with web3 utils error
        with mock.patch("batch.indexer_DEX.time", time_mock), mock.patch(
            "batch.indexer_DEX.Processor.initial_sync", return_value=True
        ), mock.patch(
            "web3.providers.rpc.HTTPProvider.make_request",
            MagicMock(side_effect=ServiceUnavailable()),
        ), pytest.raises(
            TypeError
        ):
            # Expect that sync_new_logs() raises ServiceUnavailable and handled in mainloop.
            main_func()

        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.WARNING, "An external service was unavailable")
        )
        caplog.clear()
