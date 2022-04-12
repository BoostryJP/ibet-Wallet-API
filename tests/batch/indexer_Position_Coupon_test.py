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
import pytest
from unittest import mock
from unittest.mock import MagicMock

from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.contracts import Contract
from app.model.db import (
    IDXPosition,
    Listing
)
from batch import indexer_Position_Coupon
from tests.account_config import eth_account
from tests.contract_modules import (
    cancel_order,
    coupon_transfer_to_exchange,
    create_token_escrow,
    finish_token_escrow,
    force_cancel_order,
    get_latest_escrow_id,
    get_latest_orderid,
    make_sell,
    membership_transfer_to_exchange,
    issue_coupon_token,
    coupon_register_list,
    transfer_coupon_token,
    consume_coupon_token
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    indexer_Position_Coupon.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    return indexer_Position_Coupon


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
    def issue_token_coupon(issuer, exchange_contract_address, token_list):
        # Issue token
        args = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 1000000,
            'tradableExchange': exchange_contract_address,
            'details': 'クーポン詳細',
            'returnDetails': 'リターン詳細',
            'memo': 'クーポンメモ欄',
            'expirationDate': '20191231',
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
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
    # Single Token
    # Single event logs
    # - Transfer
    def test_normal_1(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_coupon(self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(token["address"], session)

        # Transfer
        transfer_coupon_token(self.issuer, token, self.trader["account_address"], 10000)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 2
        _position = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000
        assert _position.pending_transfer is None
        _position = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000
        assert _position.pending_transfer is None

    # <Normal_2>
    # Single Token
    # Multi event logs
    # - Transfer
    def test_normal_2(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_coupon(self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(token["address"], session)

        # Transfer
        transfer_coupon_token(self.issuer, token, self.trader["account_address"], 10000)
        transfer_coupon_token(self.issuer, token, self.trader2["account_address"], 3000)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 3
        _position: IDXPosition = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000 - 3000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[2]
        assert _position.id == 3
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 3000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

    # <Normal_3>
    # Multi Token
    # Multi event logs
    # - Transfer
    def test_normal_3(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_coupon(self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(token["address"], session)
        token2 = self.issue_token_coupon(self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(token2["address"], session)

        # Transfer
        transfer_coupon_token(self.issuer, token, self.trader["account_address"], 10000)
        transfer_coupon_token(self.issuer, token, self.trader2["account_address"], 3000)
        transfer_coupon_token(self.issuer, token2, self.trader["account_address"], 5000)
        transfer_coupon_token(self.issuer, token2, self.trader2["account_address"], 3000)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 6
        _position = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000 - 3000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[2]
        assert _position.id == 3
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 3000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[3]
        assert _position.id == 4
        assert _position.token_address == token2["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 5000 - 3000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[4]
        assert _position.id == 5
        assert _position.token_address == token2["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 5000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[5]
        assert _position.id == 6
        assert _position.token_address == token2["address"]
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 3000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

    # <Normal_4>
    # Single Token
    # Single event logs
    # - Transfer
    # - Consume
    def test_normal_4(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_coupon(self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(token["address"], session)

        # Transfer
        transfer_coupon_token(self.issuer, token, self.trader["account_address"], 10000)

        # Consume
        consume_coupon_token(self.issuer, token, 3000)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 2
        _position = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000 - 3000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0

    # <Normal_5>
    # Single Token
    # Multi event logs
    # Exchange
    # - Transfer
    # - Commitment
    def test_normal_5(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        coupon_exchange = shared_contract["IbetCouponExchange"]
        agent = eth_account['agent']
        token = self.issue_token_coupon(self.issuer, coupon_exchange["address"], token_list_contract)
        self.listing_token(token["address"], session)

        # Transfer
        coupon_transfer_to_exchange(self.issuer, {"address": coupon_exchange["address"]}, token, 10000)
        make_sell(self.issuer, coupon_exchange, token, 111, 1000)
        cancel_order(self.issuer, coupon_exchange, get_latest_orderid(coupon_exchange))
        make_sell(self.issuer, coupon_exchange, token, 222, 1000)
        force_cancel_order(agent, coupon_exchange, get_latest_orderid(coupon_exchange))
        make_sell(self.issuer, coupon_exchange, token, 333, 1000)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 1
        _position: IDXPosition = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000 + 111 + 222
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 10000 - 111 - 222 - 333
        assert _position.exchange_commitment == 333

    # <Normal_6>
    # Single Token
    # Multi event logs
    # Escrow
    # - Transfer
    # - Commitment
    def test_normal_6(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        escrow_contract = shared_contract["IbetEscrow"]
        token = self.issue_token_coupon(self.issuer, escrow_contract.address, token_list_contract)
        self.listing_token(token["address"], session)

        # Deposit and Escrow
        coupon_transfer_to_exchange(
            self.issuer, {"address": escrow_contract.address}, token, 10000)
        create_token_escrow(self.issuer, {"address": escrow_contract.address},
                                     token, self.trader["account_address"], self.issuer["account_address"], 200)
        finish_token_escrow(
            self.issuer, {"address": escrow_contract.address}, get_latest_escrow_id({"address": escrow_contract.address}))
        create_token_escrow(self.issuer, {"address": escrow_contract.address},
                                     token, self.trader["account_address"], self.issuer["account_address"], 300)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 2
        _position: IDXPosition = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 10000 - 200 - 300
        assert _position.exchange_commitment == 300
        _position: IDXPosition = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 0
        assert _position.pending_transfer is None
        assert _position.exchange_balance == 200
        assert _position.exchange_commitment == 0

    # <Normal_7>
    # No event logs
    def test_normal_7(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_coupon(self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(token["address"], session)

        # Not Event
        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0

    # <Normal_8>
    # Not Listing Token
    def test_normal_8(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_coupon(self.issuer, config.ZERO_ADDRESS, token_list_contract)

        # Transfer
        membership_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0

    # <Normal_9>
    # Single Token
    # Multi event logs
    # - Transfer
    # Duplicate events to be removed
    def test_normal_9(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_coupon(self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(token["address"], session)
        for i in range(0, 5):
            # Transfer
            transfer_coupon_token(self.issuer, token, self.trader["account_address"], 10000)

        # Get events for token address
        events = Contract.get_contract('IbetCoupon', token["address"]).events.Transfer.getLogs(
                    fromBlock=0,
                    toBlock=10000
                )
        # Ensure 5 events squashed to 2 events
        assert len(events) == 5
        filtered_events = list(processor.remove_duplicate_event_by_token_account_desc(events, ["from", "to"]))
        assert len(filtered_events) == 2

    # <Normal_10>
    # Single Token
    # Multi event logs
    # - Transfer
    # Last event log block number to be stored in block number processor
    def test_normal_10(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_coupon(self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(token["address"], session)
        for i in range(0, 5):
            # Transfer
            transfer_coupon_token(self.issuer, token, self.trader["account_address"], 10000)

        # Run target process
        processor.sync_new_logs()

        # Get events for token address
        events = Contract.get_contract('IbetCoupon', token["address"]).events.Transfer.getLogs(
                    fromBlock=0,
                    toBlock=10000
                )

        idx_position_block_number = processor.get_idx_position_block_number(session)

        # Ensure last block number is properly stored in db
        assert events[-1]['blockNumber'] == idx_position_block_number

    # <Normal_11>
    # Single Token
    # Multi event logs
    # - Transfer
    # Expect that "sync new log" process starts from the latest block index.
    def test_normal_11(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]

        token = self.issue_token_coupon(self.issuer, config.ZERO_ADDRESS, token_list_contract)

        self.listing_token(token["address"], session)
        for i in range(0, 5):
            # Transfer
            coupon_transfer_to_exchange(
                self.issuer, {"address": self.trader["account_address"]}, token, 1000)

        # Set index position
        processor.set_idx_position_block_number(session, 10000)
        session.commit()

        latest_block_bf = processor.get_idx_position_block_number(session)
        # Stored index is higher than current block number, so init sync is skipped.
        processor.initial_sync()

        # Run target process
        processor.sync_new_logs()
        latest_block_af = processor.get_idx_position_block_number(session)

        # Expect that processor doesn't sync any blocks.
        assert latest_block_bf == latest_block_af == 10000

        processor.set_idx_position_block_number(session, -1)
        session.commit()
        assert processor.get_idx_position_block_number(session) == -1

        # Run target process
        processor.sync_new_logs()
        # Get events for token address
        events = Contract.get_contract('IbetCoupon', token["address"]).events.Transfer.getLogs(
                    fromBlock=0,
                    toBlock=10000
                )
        idx_position_block_number = processor.get_idx_position_block_number(session)

        # Ensure last block number is properly stored in db
        assert events[-1]['blockNumber'] == idx_position_block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_coupon(self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(token["address"], session)

        # Transfer
        transfer_coupon_token(self.issuer, token, self.trader["account_address"], 10000)

        # Run target process
        processor.sync_new_logs()

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
