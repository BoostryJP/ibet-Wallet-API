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
    Listing,
    IDXTransfer
)
from batch import indexer_Transfer
from tests.account_config import eth_account
from tests.contract_modules import (
    issue_bond_token,
    register_bond_list,
    bond_transfer_to_exchange,
    membership_issue,
    membership_register_list,
    membership_transfer_to_exchange,
    issue_coupon_token,
    coupon_register_list,
    transfer_coupon_token,
    issue_share_token,
    register_share_list,
    share_transfer_to_exchange
)
from tests.utils import PersonalInfoUtils

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    indexer_Transfer.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    return indexer_Transfer


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
    def issue_token_bond(issuer,
                         exchange_contract_address,
                         personal_info_contract_address,
                         token_list):
        # Issue token
        args = {
            'name': 'テスト債券',
            'symbol': 'BOND',
            'totalSupply': 1000000,
            'tradableExchange': exchange_contract_address,
            'faceValue': 10000,
            'interestRate': 602,
            'interestPaymentDate1': '0101',
            'interestPaymentDate2': '0201',
            'interestPaymentDate3': '0301',
            'interestPaymentDate4': '0401',
            'interestPaymentDate5': '0501',
            'interestPaymentDate6': '0601',
            'interestPaymentDate7': '0701',
            'interestPaymentDate8': '0801',
            'interestPaymentDate9': '0901',
            'interestPaymentDate10': '1001',
            'interestPaymentDate11': '1101',
            'interestPaymentDate12': '1201',
            'redemptionDate': '20191231',
            'redemptionValue': 10000,
            'returnDate': '20191231',
            'returnAmount': '商品券をプレゼント',
            'purpose': '新商品の開発資金として利用。',
            'memo': 'メモ',
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー',
            'personalInfoAddress': personal_info_contract_address,
            'transferable': True,
            'isRedeemed': False
        }
        token = issue_bond_token(issuer, args)
        register_bond_list(issuer, token, token_list)

        return token

    @staticmethod
    def issue_token_membership(issuer,
                               exchange_contract_address,
                               token_list):
        # Issue token
        args = {
            'name': 'テスト会員権',
            'symbol': 'MEMBERSHIP',
            'initialSupply': 1000000,
            'tradableExchange': exchange_contract_address,
            'details': '詳細',
            'returnDetails': 'リターン詳細',
            'expirationDate': '20191231',
            'memo': 'メモ',
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
        }
        token = membership_issue(issuer, args)
        membership_register_list(issuer, token, token_list)

        return token

    @staticmethod
    def issue_token_coupon(issuer,
                           exchange_contract_address,
                           token_list):
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
    def issue_token_share(issuer,
                          exchange_contract_address,
                          personal_info_contract_address,
                          token_list):
        # Issue token
        args = {
            "name": "テスト株式",
            "symbol": "SHARE",
            "tradableExchange": exchange_contract_address,
            "personalInfoAddress": personal_info_contract_address,
            "issuePrice": 1000,
            "principalValue": 1000,
            "totalSupply": 1000000,
            "dividends": 101,
            "dividendRecordDate": "20200401",
            "dividendPaymentDate": "20200502",
            "cancellationDate": "20200603",
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
            "memo": "メモ",
            "transferable": True
        }
        token = issue_share_token(issuer, args)
        register_share_list(issuer, token, token_list)

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
    # IbetShare
    # Single event logs
    def test_normal_1(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract
        )
        self.listing_token(share_token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"]
        )

        # Transfer
        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            share_token,
            100000
        )
        block_number = web3.eth.blockNumber

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 1

        block = web3.eth.getBlock(block_number)
        _transfer = _transfer_list[0]
        assert _transfer.id == 1
        assert _transfer.transaction_hash == block["transactions"][0].hex()
        assert _transfer.token_address == share_token["address"]
        assert _transfer.from_address == self.issuer["account_address"]
        assert _transfer.to_address == self.trader["account_address"]
        assert _transfer.value == 100000
        assert _transfer.created is not None
        assert _transfer.modified is not None

    # <Normal_2>
    # IbetShare
    # Multi event logs
    def test_normal_2(self, processor, shared_contract, session):
        # Prepare data
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract
        )
        self.listing_token(share_token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"]
        )
        PersonalInfoUtils.register(
            self.trader2["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"]
        )

        # Transfer
        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            share_token,
            100000
        )
        block_number = web3.eth.blockNumber
        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader2["account_address"]},
            share_token,
            200000
        )
        block_number2 = web3.eth.blockNumber

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 2

        block = web3.eth.getBlock(block_number)
        _transfer = _transfer_list[0]
        assert _transfer.id == 1
        assert _transfer.transaction_hash == block["transactions"][0].hex()
        assert _transfer.token_address == share_token["address"]
        assert _transfer.from_address == self.issuer["account_address"]
        assert _transfer.to_address == self.trader["account_address"]
        assert _transfer.value == 100000
        assert _transfer.created is not None
        assert _transfer.modified is not None

        block = web3.eth.getBlock(block_number2)
        _transfer = _transfer_list[1]
        assert _transfer.id == 2
        assert _transfer.transaction_hash == block["transactions"][0].hex()
        assert _transfer.token_address == share_token["address"]
        assert _transfer.from_address == self.issuer["account_address"]
        assert _transfer.to_address == self.trader2["account_address"]
        assert _transfer.value == 200000
        assert _transfer.created is not None
        assert _transfer.modified is not None

    # <Normal_3>
    # IbetStraightBond, IbetMembership, IbetCoupon
    def test_normal_3(self, processor, shared_contract, session):
        # Prepare data
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        bond_token = self.issue_token_bond(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract
        )
        self.listing_token(bond_token["address"], session)

        membership_token = self.issue_token_membership(
            self.issuer,
            config.ZERO_ADDRESS,
            token_list_contract
        )
        self.listing_token(membership_token["address"], session)

        coupon_token = self.issue_token_coupon(
            self.issuer,
            config.ZERO_ADDRESS,
            token_list_contract
        )
        self.listing_token(coupon_token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"]
        )

        # Transfer
        bond_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            bond_token,
            100000
        )
        bond_block_number = web3.eth.blockNumber

        membership_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            membership_token,
            200000
        )
        membership_block_number = web3.eth.blockNumber

        transfer_coupon_token(
            self.issuer,
            coupon_token,
            self.trader["account_address"],
            300000
        )
        coupon_block_number = web3.eth.blockNumber

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 3

        block = web3.eth.getBlock(bond_block_number)
        _transfer = _transfer_list[0]
        assert _transfer.id == 1
        assert _transfer.transaction_hash == block["transactions"][0].hex()
        assert _transfer.token_address == bond_token["address"]
        assert _transfer.from_address == self.issuer["account_address"]
        assert _transfer.to_address == self.trader["account_address"]
        assert _transfer.value == 100000
        assert _transfer.created is not None
        assert _transfer.modified is not None

        block = web3.eth.getBlock(membership_block_number)
        _transfer = _transfer_list[1]
        assert _transfer.id == 2
        assert _transfer.transaction_hash == block["transactions"][0].hex()
        assert _transfer.token_address == membership_token["address"]
        assert _transfer.from_address == self.issuer["account_address"]
        assert _transfer.to_address == self.trader["account_address"]
        assert _transfer.value == 200000
        assert _transfer.created is not None
        assert _transfer.modified is not None

        block = web3.eth.getBlock(coupon_block_number)
        _transfer = _transfer_list[2]
        assert _transfer.id == 3
        assert _transfer.transaction_hash == block["transactions"][0].hex()
        assert _transfer.token_address == coupon_token["address"]
        assert _transfer.from_address == self.issuer["account_address"]
        assert _transfer.to_address == self.trader["account_address"]
        assert _transfer.value == 300000
        assert _transfer.created is not None
        assert _transfer.modified is not None

    # <Normal_4>
    # No event logs
    def test_normal_4(self, processor, shared_contract, session):
        # Prepare data
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]

        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract
        )
        self.listing_token(share_token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"]
        )

        # Not Transfer
        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 0

    # <Normal_5>
    # Already Proceed
    def test_normal_5(self, processor, shared_contract, session):
        # Prepare data
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]

        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract
        )
        self.listing_token(share_token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"]
        )

        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            share_token,
            100000)
        block_number = web3.eth.blockNumber

        # Run target process (1)
        processor.sync_new_logs()

        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 1

        block = web3.eth.getBlock(block_number)
        _transfer = _transfer_list[0]
        assert _transfer.id == 1
        assert _transfer.transaction_hash == block["transactions"][0].hex()
        assert _transfer.token_address == share_token["address"]
        assert _transfer.from_address == self.issuer["account_address"]
        assert _transfer.to_address == self.trader["account_address"]
        assert _transfer.value == 100000
        assert _transfer.created is not None
        assert _transfer.modified is not None

        # Run target process (2)
        processor.sync_new_logs()

        # Assertion
        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 1  # prepare same

    # <Normal_6>
    # Not Listing Token
    def test_normal_6(self, processor, shared_contract, session):
        # Prepare data
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract
        )

        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"]
        )

        # Transfer
        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            share_token,
            100000
        )

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, processor, shared_contract, session):
        # Prepare data
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract
        )
        self.listing_token(share_token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"]
        )

        # Transfer
        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            share_token,
            100000
        )

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 0
