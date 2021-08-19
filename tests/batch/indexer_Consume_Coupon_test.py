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
from app.model import (
    Listing,
    IDXConsumeCoupon
)
from batch import indexer_Consume_Coupon
from tests.account_config import eth_account
from tests.contract_modules import (
    issue_coupon_token,
    coupon_register_list,
    transfer_coupon_token,
    consume_coupon_token,
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    indexer_Consume_Coupon.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    return indexer_Consume_Coupon


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
    # Single token
    # Single event logs
    def test_normal_1(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_coupon(
            self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(token["address"], session)

        # Consume
        consume_coupon_token(self.issuer, token, 1000)
        block_number = web3.eth.blockNumber

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _consume_coupon_list = session.query(IDXConsumeCoupon).order_by(IDXConsumeCoupon.created).all()
        assert len(_consume_coupon_list) == 1
        block = web3.eth.getBlock(block_number)
        _consume_coupon = _consume_coupon_list[0]
        assert _consume_coupon.id == 1
        assert _consume_coupon.transaction_hash == block["transactions"][0].hex()
        assert _consume_coupon.token_address == token["address"]
        assert _consume_coupon.account_address == self.issuer["account_address"]
        assert _consume_coupon.amount == 1000
        assert _consume_coupon.block_timestamp is not None

    # <Normal_2>
    # Single token
    # Multi event logs
    def test_normal_2(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_coupon(
            self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(token["address"], session)

        # Consume
        consume_coupon_token(self.issuer, token, 1000)
        block_number = web3.eth.blockNumber
        transfer_coupon_token(self.issuer, token, self.trader["account_address"], 2000)
        consume_coupon_token(self.trader, token, 2000)
        block_number2 = web3.eth.blockNumber

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _consume_coupon_list = session.query(IDXConsumeCoupon).order_by(IDXConsumeCoupon.created).all()
        assert len(_consume_coupon_list) == 2
        block = web3.eth.getBlock(block_number)
        _consume_coupon = _consume_coupon_list[0]
        assert _consume_coupon.id == 1
        assert _consume_coupon.transaction_hash == block["transactions"][0].hex()
        assert _consume_coupon.token_address == token["address"]
        assert _consume_coupon.account_address == self.issuer["account_address"]
        assert _consume_coupon.amount == 1000
        assert _consume_coupon.block_timestamp is not None
        block = web3.eth.getBlock(block_number2)
        _consume_coupon = _consume_coupon_list[1]
        assert _consume_coupon.id == 2
        assert _consume_coupon.transaction_hash == block["transactions"][0].hex()
        assert _consume_coupon.token_address == token["address"]
        assert _consume_coupon.account_address == self.trader["account_address"]
        assert _consume_coupon.amount == 2000
        assert _consume_coupon.block_timestamp is not None

    # <Normal_3>
    # Multi token
    # Multi event logs
    def test_normal_3(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_coupon(
            self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(token["address"], session)
        token2 = self.issue_token_coupon(
            self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(token2["address"], session)

        # Consume
        consume_coupon_token(self.issuer, token, 1000)
        block_number = web3.eth.blockNumber
        transfer_coupon_token(self.issuer, token, self.trader["account_address"], 2000)
        consume_coupon_token(self.trader, token, 2000)
        block_number2 = web3.eth.blockNumber
        consume_coupon_token(self.issuer, token2, 3000)
        block_number3 = web3.eth.blockNumber
        transfer_coupon_token(self.issuer, token2, self.trader["account_address"], 4000)
        consume_coupon_token(self.trader, token2, 4000)
        block_number4 = web3.eth.blockNumber

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _consume_coupon_list = session.query(IDXConsumeCoupon).order_by(IDXConsumeCoupon.created).all()
        assert len(_consume_coupon_list) == 4
        block = web3.eth.getBlock(block_number)
        _consume_coupon = _consume_coupon_list[0]
        assert _consume_coupon.id == 1
        assert _consume_coupon.transaction_hash == block["transactions"][0].hex()
        assert _consume_coupon.token_address == token["address"]
        assert _consume_coupon.account_address == self.issuer["account_address"]
        assert _consume_coupon.amount == 1000
        assert _consume_coupon.block_timestamp is not None
        block = web3.eth.getBlock(block_number2)
        _consume_coupon = _consume_coupon_list[1]
        assert _consume_coupon.id == 2
        assert _consume_coupon.transaction_hash == block["transactions"][0].hex()
        assert _consume_coupon.token_address == token["address"]
        assert _consume_coupon.account_address == self.trader["account_address"]
        assert _consume_coupon.amount == 2000
        assert _consume_coupon.block_timestamp is not None
        block = web3.eth.getBlock(block_number3)
        _consume_coupon = _consume_coupon_list[2]
        assert _consume_coupon.id == 3
        assert _consume_coupon.transaction_hash == block["transactions"][0].hex()
        assert _consume_coupon.token_address == token2["address"]
        assert _consume_coupon.account_address == self.issuer["account_address"]
        assert _consume_coupon.amount == 3000
        assert _consume_coupon.block_timestamp is not None
        block = web3.eth.getBlock(block_number4)
        _consume_coupon = _consume_coupon_list[3]
        assert _consume_coupon.id == 4
        assert _consume_coupon.transaction_hash == block["transactions"][0].hex()
        assert _consume_coupon.token_address == token2["address"]
        assert _consume_coupon.account_address == self.trader["account_address"]
        assert _consume_coupon.amount == 4000
        assert _consume_coupon.block_timestamp is not None

    # <Normal_4>
    # No event logs
    def test_normal_4(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_coupon(
            self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(token["address"], session)

        # Not Consume
        # Run target process
        processor.sync_new_logs()

        # Assertion
        _consume_coupon_list = session.query(IDXConsumeCoupon).order_by(IDXConsumeCoupon.created).all()
        assert len(_consume_coupon_list) == 0

    # <Normal_5>
    # Not Listing Token
    def test_normal_5(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_coupon(
            self.issuer, config.ZERO_ADDRESS, token_list_contract)

        # Consume
        consume_coupon_token(self.issuer, token, 1000)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _consume_coupon_list = session.query(IDXConsumeCoupon).order_by(IDXConsumeCoupon.created).all()
        assert len(_consume_coupon_list) == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        token = self.issue_token_coupon(
            self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(token["address"], session)

        # Consume
        consume_coupon_token(self.issuer, token, 1000)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _consume_coupon_list = session.query(IDXConsumeCoupon).order_by(IDXConsumeCoupon.created).all()
        assert len(_consume_coupon_list) == 0
