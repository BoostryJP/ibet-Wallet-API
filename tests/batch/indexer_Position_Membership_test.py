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
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.db import IDXPosition, IDXPositionMembershipBlockNumber, Listing
from batch import indexer_Position_Membership
from batch.indexer_Position_Membership import LOG, Processor, main
from tests.account_config import eth_account
from tests.contract_modules import (
    cancel_agreement,
    cancel_order,
    create_token_escrow,
    finish_token_escrow,
    force_cancel_order,
    get_latest_agreementid,
    get_latest_escrow_id,
    get_latest_orderid,
    make_buy,
    make_sell,
    membership_issue,
    membership_register_list,
    membership_transfer_to_exchange,
    take_sell,
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    indexer_Position_Membership.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract[
        "TokenList"
    ]["address"]
    return indexer_Position_Membership


@pytest.fixture(scope="function")
def main_func(test_module):
    LOG = logging.getLogger("ibet_wallet_batch")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield main
    LOG.propagate = False
    LOG.setLevel(default_log_level)


@pytest.fixture(scope="function")
def processor(test_module, session):
    processor = test_module.Processor()
    processor.initial_sync()
    return processor


class TestProcessor:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["agent"]

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
    # Single Token
    # Single event logs
    # - Transfer
    def test_normal_1(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Transfer
        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000
        )

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 2
        _idx_position_membership_block_number = (
            session.query(IDXPositionMembershipBlockNumber)
            .filter(IDXPositionMembershipBlockNumber.token_address == token["address"])
            .first()
        )
        _position = (
            session.query(IDXPosition)
            .filter(IDXPosition.token_address == token["address"])
            .filter(IDXPosition.account_address == self.issuer["account_address"])
            .first()
        )
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = (
            session.query(IDXPosition)
            .filter(IDXPosition.token_address == token["address"])
            .filter(IDXPosition.account_address == self.trader["account_address"])
            .first()
        )
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _idx_position_membership_block_number.latest_block_number == block_number

    # <Normal_2>
    # Single Token
    # Multi event logs
    # - Transfer
    def test_normal_2(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Transfer
        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000
        )
        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader2["account_address"]}, token, 3000
        )

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 3
        _idx_position_membership_block_number = (
            session.query(IDXPositionMembershipBlockNumber)
            .filter(IDXPositionMembershipBlockNumber.token_address == token["address"])
            .first()
        )
        _position = (
            session.query(IDXPosition)
            .filter(IDXPosition.token_address == token["address"])
            .filter(IDXPosition.account_address == self.trader["account_address"])
            .first()
        )
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = (
            session.query(IDXPosition)
            .filter(IDXPosition.token_address == token["address"])
            .filter(IDXPosition.account_address == self.trader2["account_address"])
            .first()
        )
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 3000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = (
            session.query(IDXPosition)
            .filter(IDXPosition.token_address == token["address"])
            .filter(IDXPosition.account_address == self.issuer["account_address"])
            .first()
        )
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000 - 3000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _idx_position_membership_block_number.latest_block_number == block_number

    # <Normal_3>
    # Multi Token
    # Multi event logs
    # - Transfer
    def test_normal_3(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token["address"], session)
        token2 = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token2["address"], session)

        # Transfer
        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000
        )
        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader2["account_address"]}, token, 3000
        )
        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token2, 5000
        )
        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader2["account_address"]}, token2, 3000
        )

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 6
        _idx_position_membership_block_number = (
            session.query(IDXPositionMembershipBlockNumber)
            .filter(IDXPositionMembershipBlockNumber.token_address == token["address"])
            .first()
        )
        _position = (
            session.query(IDXPosition)
            .filter(IDXPosition.token_address == token["address"])
            .filter(IDXPosition.account_address == self.trader["account_address"])
            .first()
        )
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = (
            session.query(IDXPosition)
            .filter(IDXPosition.token_address == token["address"])
            .filter(IDXPosition.account_address == self.trader2["account_address"])
            .first()
        )
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 3000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = (
            session.query(IDXPosition)
            .filter(IDXPosition.token_address == token["address"])
            .filter(IDXPosition.account_address == self.issuer["account_address"])
            .first()
        )
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000 - 3000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = (
            session.query(IDXPosition)
            .filter(IDXPosition.token_address == token2["address"])
            .filter(IDXPosition.account_address == self.trader["account_address"])
            .first()
        )
        assert _position.token_address == token2["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 5000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = (
            session.query(IDXPosition)
            .filter(IDXPosition.token_address == token2["address"])
            .filter(IDXPosition.account_address == self.trader2["account_address"])
            .first()
        )
        assert _position.token_address == token2["address"]
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 3000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = (
            session.query(IDXPosition)
            .filter(IDXPosition.token_address == token2["address"])
            .filter(IDXPosition.account_address == self.issuer["account_address"])
            .first()
        )
        assert _position.token_address == token2["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 5000 - 3000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _idx_position_membership_block_number.latest_block_number == block_number

    # <Normal_4>
    # Single Token
    # Multi event logs
    # Exchange
    # - Transfer
    # - Commitment
    def test_normal_4(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        membership_exchange = shared_contract["IbetMembershipExchange"]
        agent = eth_account["agent"]
        token = self.issue_token_membership(
            self.issuer, membership_exchange["address"], token_list_contract
        )
        self.listing_token(token["address"], session)

        # Transfer
        membership_transfer_to_exchange(
            self.issuer, {"address": membership_exchange["address"]}, token, 10000
        )
        make_sell(self.issuer, membership_exchange, token, 111, 1000)
        cancel_order(
            self.issuer, membership_exchange, get_latest_orderid(membership_exchange)
        )
        make_sell(self.issuer, membership_exchange, token, 222, 1000)
        force_cancel_order(
            agent, membership_exchange, get_latest_orderid(membership_exchange)
        )
        make_sell(self.issuer, membership_exchange, token, 333, 1000)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 1
        _idx_position_membership_block_number = (
            session.query(IDXPositionMembershipBlockNumber)
            .filter(IDXPositionMembershipBlockNumber.token_address == token["address"])
            .first()
        )
        _position: IDXPosition = _position_list[0]
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000 + 111 + 222
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 10000 - 111 - 222 - 333
        assert _position.exchange_commitment == 333
        assert _idx_position_membership_block_number.latest_block_number == block_number

    # <Normal_5>
    # Single Token
    # Multi event logs
    # Escrow
    # - Transfer
    # - Commitment
    def test_normal_5(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        escrow_contract = shared_contract["IbetEscrow"]
        token = self.issue_token_membership(
            self.issuer, escrow_contract.address, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Deposit and Escrow
        membership_transfer_to_exchange(
            self.issuer, {"address": escrow_contract.address}, token, 10000
        )
        create_token_escrow(
            self.issuer,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.issuer["account_address"],
            200,
        )
        finish_token_escrow(
            self.issuer,
            {"address": escrow_contract.address},
            get_latest_escrow_id({"address": escrow_contract.address}),
        )
        create_token_escrow(
            self.issuer,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.issuer["account_address"],
            300,
        )

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 2
        _idx_position_membership_block_number = (
            session.query(IDXPositionMembershipBlockNumber)
            .filter(IDXPositionMembershipBlockNumber.token_address == token["address"])
            .first()
        )
        _position = (
            session.query(IDXPosition)
            .filter(IDXPosition.token_address == token["address"])
            .filter(IDXPosition.account_address == self.issuer["account_address"])
            .first()
        )
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 10000 - 200 - 300
        assert _position.exchange_commitment == 300
        _position = (
            session.query(IDXPosition)
            .filter(IDXPosition.token_address == token["address"])
            .filter(IDXPosition.account_address == self.trader["account_address"])
            .first()
        )
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 0
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 200
        assert _position.exchange_commitment == 0
        assert _idx_position_membership_block_number.latest_block_number == block_number

    # <Normal_6>
    # No event logs
    def test_normal_6(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Not Transfer
        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        _idx_position_membership_block_number = (
            session.query(IDXPositionMembershipBlockNumber)
            .filter(IDXPositionMembershipBlockNumber.token_address == token["address"])
            .first()
        )
        assert _idx_position_membership_block_number.latest_block_number == block_number

    # <Normal_7>
    # Not listing Token is NOT indexed,
    # and indexed properly after listing
    def test_normal_7(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )

        # Transfer
        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000
        )

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        _idx_position_membership_block_number = session.query(
            IDXPositionMembershipBlockNumber
        ).all()
        assert len(_idx_position_membership_block_number) == 0

        # Listing
        self.listing_token(token["address"], session)

        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        session.rollback()
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 2
        _idx_position_membership_block_number = (
            session.query(IDXPositionMembershipBlockNumber)
            .filter(IDXPositionMembershipBlockNumber.token_address == token["address"])
            .first()
        )
        assert _idx_position_membership_block_number.latest_block_number == block_number

    # <Normal_8>
    # Single Token
    # Multi event logs
    # - Transfer
    # Duplicate events to be removed
    def test_normal_8(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token["address"], session)
        from_block = web3.eth.block_number
        for i in range(0, 5):
            # Transfer
            membership_transfer_to_exchange(
                self.issuer, {"address": self.trader["account_address"]}, token, 10000
            )
        to_block = web3.eth.block_number

        # Get events for token address
        events = Contract.get_contract(
            "IbetMembership", token["address"]
        ).events.Transfer.get_logs(fromBlock=from_block, toBlock=to_block)
        # Ensure 5 events squashed to 2 events
        assert len(events) == 5
        filtered_events = processor.remove_duplicate_event_by_token_account_desc(
            events, ["from", "to"]
        )
        assert len(filtered_events) == 2

    # <Normal_9>
    # When stored index is 9,999,999 and current block number is 19,999,999,
    # then processor must process "__sync_all" method 10 times.
    def test_normal_9(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        escrow_contract = shared_contract["IbetEscrow"]
        current_block_number = 20000000 - 1
        latest_block_number = 10000000 - 1

        mock_lib = MagicMock()

        token = self.issue_token_membership(
            self.issuer, escrow_contract.address, token_list_contract
        )

        # Setting current block number to 19,999,999
        self.listing_token(token["address"], session)
        with mock.patch("web3.eth.Eth.block_number", current_block_number):
            with mock.patch.object(
                Processor, "_Processor__sync_all", return_value=mock_lib
            ) as __sync_all_mock:
                idx_position_membership_block_number = (
                    IDXPositionMembershipBlockNumber()
                )
                idx_position_membership_block_number.token_address = token["address"]
                idx_position_membership_block_number.exchange_address = (
                    escrow_contract.address
                )
                # Setting stored index to 9,999,999
                idx_position_membership_block_number.latest_block_number = (
                    latest_block_number
                )
                session.merge(idx_position_membership_block_number)
                session.commit()
                __sync_all_mock.return_value = None
                processor.initial_sync()
                # Then processor call "__sync_all" method 10 times.
                assert __sync_all_mock.call_count == 10

        with mock.patch("web3.eth.Eth.block_number", current_block_number):
            with mock.patch.object(
                Processor, "_Processor__sync_all", return_value=mock_lib
            ) as __sync_all_mock:
                # Stored index is 19,999,999
                __sync_all_mock.return_value = None
                processor.sync_new_logs()
                # Then processor call "__sync_all" method once.
                assert __sync_all_mock.call_count == 1

        new_token = self.issue_token_membership(
            self.issuer, escrow_contract.address, token_list_contract
        )
        self.listing_token(new_token["address"], session)

        with mock.patch("web3.eth.Eth.block_number", current_block_number):
            with mock.patch.object(
                Processor, "_Processor__sync_all", return_value=mock_lib
            ) as __sync_all_mock:
                # Stored index is 19,999,999
                __sync_all_mock.return_value = None
                processor.sync_new_logs()
                # Then processor call "__sync_all" method 20 times.
                assert __sync_all_mock.call_count == 20

    # <Normal_10>
    # Multiple Token
    # Multi event logs
    # - Transfer/Exchange
    # Skip exchange events which has already been synced
    def test_normal_10(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        exchange_contract = shared_contract["IbetCouponExchange"]
        agent = eth_account["agent"]
        personal_info_contract = shared_contract["PersonalInfo"]

        token1 = self.issue_token_membership(
            self.issuer, exchange_contract["address"], token_list_contract
        )
        token2 = self.issue_token_membership(
            self.issuer, exchange_contract["address"], token_list_contract
        )

        # Token1 Listing
        self.listing_token(token1["address"], session)

        # Token1 Operation
        membership_transfer_to_exchange(self.issuer, exchange_contract, token1, 10000)
        make_buy(self.trader, exchange_contract, token1, 111, 1000)
        take_sell(
            self.issuer, exchange_contract, get_latest_orderid(exchange_contract), 55
        )
        cancel_agreement(
            agent,
            exchange_contract,
            get_latest_orderid(exchange_contract),
            get_latest_agreementid(
                exchange_contract, get_latest_orderid(exchange_contract)
            ),
        )
        make_buy(self.trader, exchange_contract, token1, 111, 1000)
        take_sell(
            self.issuer, exchange_contract, get_latest_orderid(exchange_contract), 66
        )

        # Token2 Operation
        membership_transfer_to_exchange(self.issuer, exchange_contract, token2, 10000)
        make_buy(self.trader, exchange_contract, token2, 111, 1000)
        take_sell(
            self.issuer, exchange_contract, get_latest_orderid(exchange_contract), 55
        )
        cancel_agreement(
            agent,
            exchange_contract,
            get_latest_orderid(exchange_contract),
            get_latest_agreementid(
                exchange_contract, get_latest_orderid(exchange_contract)
            ),
        )
        make_buy(self.trader, exchange_contract, token2, 111, 1000)
        take_sell(
            self.issuer, exchange_contract, get_latest_orderid(exchange_contract), 66
        )

        # Run target process
        block_number1 = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 1
        _idx_position_coupon_block_number = (
            session.query(IDXPositionMembershipBlockNumber)
            .filter(IDXPositionMembershipBlockNumber.token_address == token1["address"])
            .first()
        )
        _position: IDXPosition = _position_list[0]
        assert _position.token_address == token1["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000 + 55
        assert _position.exchange_balance == 10000 - 55 - 66
        assert _position.exchange_commitment == 66
        assert _idx_position_coupon_block_number.latest_block_number == block_number1

        # Token2 Listing
        self.listing_token(token2["address"], session)

        # Run target process
        block_number2 = web3.eth.block_number
        processor.sync_new_logs()

        session.rollback()
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 2

        _idx_position_coupon_block_number1 = (
            session.query(IDXPositionMembershipBlockNumber)
            .filter(IDXPositionMembershipBlockNumber.token_address == token1["address"])
            .first()
        )
        _idx_position_coupon_block_number2 = (
            session.query(IDXPositionMembershipBlockNumber)
            .filter(IDXPositionMembershipBlockNumber.token_address == token2["address"])
            .first()
        )

        _position1 = (
            session.query(IDXPosition)
            .filter(IDXPosition.token_address == token1["address"])
            .filter(IDXPosition.account_address == self.issuer["account_address"])
            .first()
        )
        assert _position1.token_address == token1["address"]
        assert _position1.account_address == self.issuer["account_address"]
        assert _position1.balance == 1000000 - 10000 + 55
        assert _position1.exchange_balance == 10000 - 55 - 66
        assert _position1.exchange_commitment == 66
        assert _idx_position_coupon_block_number1.latest_block_number == block_number2

        _position2 = (
            session.query(IDXPosition)
            .filter(IDXPosition.token_address == token2["address"])
            .filter(IDXPosition.account_address == self.issuer["account_address"])
            .first()
        )
        assert _position2.token_address == token2["address"]
        assert _position2.account_address == self.issuer["account_address"]
        assert _position2.balance == 1000000 - 10000 + 55
        assert _position2.exchange_balance == 10000 - 55 - 66
        assert _position2.exchange_commitment == 66
        assert _idx_position_coupon_block_number2.latest_block_number == block_number2

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
        "web3.contract.contract.ContractEvent.get_logs",
        MagicMock(side_effect=ABIEventFunctionNotFound()),
    )
    def test_error_1_1(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Transfer
        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000
        )

        block_number_current = web3.eth.block_number
        # Run initial sync
        processor.initial_sync()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Latest_block is incremented in "initial_sync" process.
        _idx_position_membership_block_number = (
            session.query(IDXPositionMembershipBlockNumber)
            .filter(IDXPositionMembershipBlockNumber.token_address == token["address"])
            .first()
        )
        assert (
            _idx_position_membership_block_number.latest_block_number
            == block_number_current
        )

        # Transfer
        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000
        )

        block_number_current = web3.eth.block_number
        # Run target process
        processor.sync_new_logs()

        # Run target process
        processor.sync_new_logs()

        # Clear cache in DB session.
        session.rollback()
        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Latest_block is incremented in "sync_new_logs" process.
        _idx_position_membership_block_number = (
            session.query(IDXPositionMembershipBlockNumber)
            .filter(IDXPositionMembershipBlockNumber.token_address == token["address"])
            .first()
        )
        assert (
            _idx_position_membership_block_number.latest_block_number
            == block_number_current
        )

    # <Error_1_2>: ServiceUnavailable occurs in __sync_xx method.
    @mock.patch("web3.eth.Eth.get_code", MagicMock(side_effect=ServiceUnavailable()))
    def test_error_1_2(self, processor, shared_contract, session, caplog):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Transfer
        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000
        )

        # Expect that initial_sync() raises ServiceUnavailable.
        with pytest.raises(ServiceUnavailable):
            processor.initial_sync()
        # Clear cache in DB session.
        session.rollback()
        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Any latest_block is not saved in "initial_sync" process.
        _idx_position_membership_block_number = session.query(
            IDXPositionMembershipBlockNumber
        ).all()
        assert len(_idx_position_membership_block_number) == 0
        # Clear cache in DB session.
        session.rollback()

        # Transfer
        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000
        )

        _idx_position_membership_block_number_bf = session.query(
            IDXPositionMembershipBlockNumber
        ).first()
        # Expect that sync_new_logs() raises ServiceUnavailable.
        with pytest.raises(ServiceUnavailable):
            processor.sync_new_logs()
        # Clear cache in DB session.
        session.rollback()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Any latest_block is not saved in "sync_new_logs" process.
        _idx_position_membership_block_number = session.query(
            IDXPositionMembershipBlockNumber
        ).all()
        assert len(_idx_position_membership_block_number) == 0
        assert 0 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.ERROR,
                "An exception occurred during event synchronization",
            )
        )

    # <Error_2_1>: ServiceUnavailable occurs in "initial_sync" / "sync_new_logs".
    def test_error_2_1(self, processor, shared_contract, session, caplog):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Transfer
        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000
        )

        # Expect that initial_sync() raises ServiceUnavailable.
        with mock.patch(
            "web3.providers.rpc.HTTPProvider.make_request",
            MagicMock(side_effect=ServiceUnavailable()),
        ), pytest.raises(ServiceUnavailable):
            processor.initial_sync()
        # Clear cache in DB session.
        session.rollback()
        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Any latest_block is not saved in "initial_sync" process when ServiceUnavailable occurs.
        _idx_position_membership_block_number = session.query(
            IDXPositionMembershipBlockNumber
        ).all()
        assert len(_idx_position_membership_block_number) == 0
        # Clear cache in DB session.
        session.rollback()

        # Transfer
        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000
        )
        # Expect that sync_new_logs() raises ServiceUnavailable.
        with mock.patch(
            "web3.providers.rpc.HTTPProvider.make_request",
            MagicMock(side_effect=ServiceUnavailable()),
        ), pytest.raises(ServiceUnavailable):
            processor.sync_new_logs()

        # Clear cache in DB session.
        session.rollback()
        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Any latest_block is not saved in "sync_new_logs" process when ServiceUnavailable occurs.
        _idx_position_membership_block_number = session.query(
            IDXPositionMembershipBlockNumber
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
    def test_error_2_2(self, processor, shared_contract, session, caplog):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(token["address"], session)

        # Transfer
        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000
        )

        # Expect that initial_sync() raises SQLAlchemyError.
        with mock.patch.object(
            Session, "commit", side_effect=SQLAlchemyError()
        ), pytest.raises(SQLAlchemyError):
            processor.initial_sync()
        # Clear cache in DB session.
        session.rollback()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Any latest_block is not saved in "initial_sync" process when SQLAlchemyError occurs.
        _idx_position_membership_block_number = session.query(
            IDXPositionMembershipBlockNumber
        ).all()
        assert len(_idx_position_membership_block_number) == 0
        # Clear cache in DB session.
        session.rollback()

        # Transfer
        membership_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000
        )

        # Expect that sync_new_logs() raises SQLAlchemyError.
        with mock.patch.object(
            Session, "commit", side_effect=SQLAlchemyError()
        ), pytest.raises(SQLAlchemyError):
            processor.sync_new_logs()

        # Clear cache in DB session.
        session.rollback()
        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Latest_block is NOT incremented in "sync_new_logs" process.
        _idx_position_membership_block_number = session.query(
            IDXPositionMembershipBlockNumber
        ).all()
        assert len(_idx_position_membership_block_number) == 0
        assert 0 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.ERROR,
                "An exception occurred during event synchronization",
            )
        )

    # <Error_3>: ServiceUnavailable occurs and is handled in mainloop.
    def test_error_3(self, main_func, shared_contract, session, caplog):
        # Mocking time.sleep to break mainloop
        time_mock = MagicMock(wraps=time)
        time_mock.sleep.side_effect = [True, TypeError()]

        # Run mainloop once and fail with web3 utils error
        with mock.patch(
            "batch.indexer_Position_Membership.time", time_mock
        ), mock.patch(
            "batch.indexer_Position_Membership.Processor.initial_sync",
            return_value=True,
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
