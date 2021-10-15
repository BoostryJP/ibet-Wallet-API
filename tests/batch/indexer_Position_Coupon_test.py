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
from app.model.db import (
    IDXPosition,
    Listing
)
from batch import indexer_Position_Coupon
from tests.account_config import eth_account
from tests.contract_modules import (
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
    _sink = test_module.Sinks()
    _sink.register(test_module.DBSink(session))
    processor = test_module.Processor(_sink, session)
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
        _position = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000
        assert _position.pending_transfer is None
        _position = _position_list[2]
        assert _position.id == 3
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 3000
        assert _position.pending_transfer is None

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
        _position = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000
        assert _position.pending_transfer is None
        _position = _position_list[2]
        assert _position.id == 3
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 3000
        assert _position.pending_transfer is None
        _position = _position_list[3]
        assert _position.id == 4
        assert _position.token_address == token2["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 5000 - 3000
        assert _position.pending_transfer is None
        _position = _position_list[4]
        assert _position.id == 5
        assert _position.token_address == token2["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 5000
        assert _position.pending_transfer is None
        _position = _position_list[5]
        assert _position.id == 6
        assert _position.token_address == token2["address"]
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 3000
        assert _position.pending_transfer is None

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
        _position = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000
        assert _position.pending_transfer is None

    # <Normal_5>
    # No event logs
    def test_normal_5(self, processor, shared_contract, session):
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

    # <Normal_6>
    # Not Listing Token
    def test_normal_6(self, processor, shared_contract, session):
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
