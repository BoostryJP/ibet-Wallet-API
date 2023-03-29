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
import json
import logging
from datetime import datetime
from unittest import mock
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from web3 import Web3
from web3.exceptions import ABIEventFunctionNotFound
from web3.middleware import geth_poa_middleware
from web3.types import RPCEndpoint

from app import config
from app.errors import ServiceUnavailable
from app.model.db import (
    IDXTransfer,
    IDXTransferBlockNumber,
    IDXTransferSourceEventType,
    Listing,
)
from batch import indexer_Transfer
from batch.indexer_Transfer import LOG, UTC
from tests.account_config import eth_account
from tests.contract_modules import (
    bond_transfer_to_exchange,
    coupon_register_list,
    issue_bond_token,
    issue_coupon_token,
    issue_share_token,
    membership_issue,
    membership_register_list,
    membership_transfer_to_exchange,
    register_bond_list,
    register_share_list,
    share_lock,
    share_transfer_to_exchange,
    share_unlock,
    transfer_coupon_token,
)
from tests.utils import PersonalInfoUtils

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    indexer_Transfer.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"][
        "address"
    ]
    return indexer_Transfer


@pytest.fixture(scope="function")
def caplog(caplog: pytest.LogCaptureFixture):
    LOG = logging.getLogger("ibet_wallet_batch")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield caplog
    LOG.propagate = False
    LOG.setLevel(default_log_level)


@pytest.fixture(scope="function")
def processor(test_module, session):
    processor = test_module.Processor()
    return processor


class TestProcessor:
    issuer = eth_account["issuer"]
    trader = eth_account["trader"]
    trader2 = eth_account["agent"]

    @staticmethod
    def issue_token_bond(
        issuer, exchange_contract_address, personal_info_contract_address, token_list
    ):
        # Issue token
        args = {
            "name": "テスト債券",
            "symbol": "BOND",
            "totalSupply": 1000000,
            "tradableExchange": exchange_contract_address,
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
            "personalInfoAddress": personal_info_contract_address,
            "transferable": True,
            "isRedeemed": False,
        }
        token = issue_bond_token(issuer, args)
        register_bond_list(issuer, token, token_list)

        return token

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
    def issue_token_share(
        issuer, exchange_contract_address, personal_info_contract_address, token_list
    ):
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
            "transferable": True,
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

    # <Normal_1_1>
    # IbetShare
    # Single event logs
    #  - Transfer
    #  - Unlock
    def test_normal_1_1(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract,
        )
        self.listing_token(share_token["address"], session)
        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"],
        )

        # emit "Transfer"
        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            share_token,
            100000,
        )
        block_number_1 = web3.eth.block_number

        # emit "Unlock"
        share_lock(self.trader, share_token, self.trader2["account_address"], 50000)
        share_unlock(
            self.trader2,
            share_token,
            self.trader["account_address"],
            self.trader2["account_address"],
            50000,
            json.dumps({"message": "unlock"}),
        )
        block_number_2 = web3.eth.block_number

        # Execute batch processing
        processor.sync_new_logs()

        # Assertion
        idx_transfer_list = (
            session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        )
        assert len(idx_transfer_list) == 2

        block1 = web3.eth.get_block(block_number_1)
        idx_transfer: IDXTransfer = idx_transfer_list[0]
        assert idx_transfer.id == 1
        assert idx_transfer.transaction_hash == block1["transactions"][0].hex()
        assert idx_transfer.token_address == share_token["address"]
        assert idx_transfer.from_address == self.issuer["account_address"]
        assert idx_transfer.to_address == self.trader["account_address"]
        assert idx_transfer.value == 100000
        assert idx_transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert idx_transfer.data is None
        assert idx_transfer.created is not None
        assert idx_transfer.modified is not None

        block2 = web3.eth.get_block(block_number_2)
        idx_transfer: IDXTransfer = idx_transfer_list[1]
        assert idx_transfer.id == 2
        assert idx_transfer.transaction_hash == block2["transactions"][0].hex()
        assert idx_transfer.token_address == share_token["address"]
        assert idx_transfer.from_address == self.trader["account_address"]
        assert idx_transfer.to_address == self.trader2["account_address"]
        assert idx_transfer.value == 50000
        assert idx_transfer.source_event == IDXTransferSourceEventType.UNLOCK.value
        assert idx_transfer.data == {"message": "unlock"}
        assert idx_transfer.created is not None
        assert idx_transfer.modified is not None

        idx_block_number: IDXTransferBlockNumber = (
            session.query(IDXTransferBlockNumber)
            .filter(IDXTransferBlockNumber.contract_address == share_token["address"])
            .first()
        )
        assert idx_block_number.latest_block_number == block_number_2

    # <Normal_1_2>
    # IbetShare
    # Single event logs
    # - Unlock: Data is not registered because "from" and "to" are the same
    def test_normal_1_2(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract,
        )
        self.listing_token(share_token["address"], session)
        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"],
        )

        # emit "Unlock"
        share_lock(self.trader, share_token, self.trader2["account_address"], 50000)
        share_unlock(
            self.trader2,
            share_token,
            self.trader["account_address"],
            self.trader["account_address"],
            50000,
        )
        block_number = web3.eth.block_number

        # Execute batch processing
        processor.sync_new_logs()

        # Assertion
        idx_transfer_list = (
            session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        )
        assert len(idx_transfer_list) == 0

        idx_block_number: IDXTransferBlockNumber = (
            session.query(IDXTransferBlockNumber)
            .filter(IDXTransferBlockNumber.contract_address == share_token["address"])
            .first()
        )
        assert idx_block_number.latest_block_number == block_number

    # <Normal_2>
    # IbetShare
    # Multi event logs
    # - Transfer(twice)
    # - Unlock(twice)
    def test_normal_2(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract,
        )
        self.listing_token(share_token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"],
        )

        PersonalInfoUtils.register(
            self.trader2["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"],
        )

        # emit "Transfer"
        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            share_token,
            100000,
        )
        block_number_1 = web3.eth.block_number

        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader2["account_address"]},
            share_token,
            200000,
        )
        block_number_2 = web3.eth.block_number

        # emit "Unlock"
        share_lock(self.trader, share_token, self.trader2["account_address"], 100000)
        share_unlock(
            self.trader2,
            share_token,
            self.trader["account_address"],
            self.trader2["account_address"],
            50000,
            json.dumps({"message": "unlock"}),
        )
        block_number_3 = web3.eth.block_number

        share_unlock(
            self.trader2,
            share_token,
            self.trader["account_address"],
            self.trader2["account_address"],
            50000,
            json.dumps({"message": "unlock"}),
        )
        block_number_4 = web3.eth.block_number

        # Execute batch processing
        processor.sync_new_logs()

        # Assertion
        idx_transfer_list = (
            session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        )
        assert len(idx_transfer_list) == 4

        block = web3.eth.get_block(block_number_1)
        idx_transfer = idx_transfer_list[0]
        assert idx_transfer.id == 1
        assert idx_transfer.transaction_hash == block["transactions"][0].hex()
        assert idx_transfer.token_address == share_token["address"]
        assert idx_transfer.from_address == self.issuer["account_address"]
        assert idx_transfer.to_address == self.trader["account_address"]
        assert idx_transfer.value == 100000
        assert idx_transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert idx_transfer.data is None
        assert idx_transfer.created is not None
        assert idx_transfer.modified is not None

        block = web3.eth.get_block(block_number_2)
        idx_transfer = idx_transfer_list[1]
        assert idx_transfer.id == 2
        assert idx_transfer.transaction_hash == block["transactions"][0].hex()
        assert idx_transfer.token_address == share_token["address"]
        assert idx_transfer.from_address == self.issuer["account_address"]
        assert idx_transfer.to_address == self.trader2["account_address"]
        assert idx_transfer.value == 200000
        assert idx_transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert idx_transfer.data is None
        assert idx_transfer.created is not None
        assert idx_transfer.modified is not None

        block = web3.eth.get_block(block_number_3)
        idx_transfer = idx_transfer_list[2]
        assert idx_transfer.id == 3
        assert idx_transfer.transaction_hash == block["transactions"][0].hex()
        assert idx_transfer.token_address == share_token["address"]
        assert idx_transfer.from_address == self.trader["account_address"]
        assert idx_transfer.to_address == self.trader2["account_address"]
        assert idx_transfer.value == 50000
        assert idx_transfer.source_event == IDXTransferSourceEventType.UNLOCK.value
        assert idx_transfer.data == {"message": "unlock"}
        assert idx_transfer.created is not None
        assert idx_transfer.modified is not None

        block = web3.eth.get_block(block_number_4)
        idx_transfer = idx_transfer_list[3]
        assert idx_transfer.id == 4
        assert idx_transfer.transaction_hash == block["transactions"][0].hex()
        assert idx_transfer.token_address == share_token["address"]
        assert idx_transfer.from_address == self.trader["account_address"]
        assert idx_transfer.to_address == self.trader2["account_address"]
        assert idx_transfer.value == 50000
        assert idx_transfer.source_event == IDXTransferSourceEventType.UNLOCK.value
        assert idx_transfer.data == {"message": "unlock"}
        assert idx_transfer.created is not None
        assert idx_transfer.modified is not None

        idx_block_number: IDXTransferBlockNumber = (
            session.query(IDXTransferBlockNumber)
            .filter(IDXTransferBlockNumber.contract_address == share_token["address"])
            .first()
        )
        assert idx_block_number.latest_block_number == block_number_4

    # <Normal_3>
    # IbetStraightBond, IbetMembership, IbetCoupon
    def test_normal_3(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        bond_token = self.issue_token_bond(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract,
        )
        self.listing_token(bond_token["address"], session)
        membership_token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(membership_token["address"], session)
        coupon_token = self.issue_token_coupon(
            self.issuer, config.ZERO_ADDRESS, token_list_contract
        )
        self.listing_token(coupon_token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"],
        )

        # emit "Transfer"
        bond_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, bond_token, 100000
        )
        bond_block_number = web3.eth.block_number
        membership_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            membership_token,
            200000,
        )
        membership_block_number = web3.eth.block_number
        transfer_coupon_token(
            self.issuer, coupon_token, self.trader["account_address"], 300000
        )
        coupon_block_number = web3.eth.block_number
        latest_block_number = web3.eth.block_number

        # Execute batch processing
        processor.sync_new_logs()

        # Assertion
        idx_transfer_list = (
            session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        )
        assert len(idx_transfer_list) == 3

        block = web3.eth.get_block(bond_block_number)
        idx_transfer = idx_transfer_list[0]
        assert idx_transfer.id == 1
        assert idx_transfer.transaction_hash == block["transactions"][0].hex()
        assert idx_transfer.token_address == bond_token["address"]
        assert idx_transfer.from_address == self.issuer["account_address"]
        assert idx_transfer.to_address == self.trader["account_address"]
        assert idx_transfer.value == 100000
        assert idx_transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert idx_transfer.data is None
        assert idx_transfer.created is not None
        assert idx_transfer.modified is not None

        block = web3.eth.get_block(membership_block_number)
        idx_transfer = idx_transfer_list[1]
        assert idx_transfer.id == 2
        assert idx_transfer.transaction_hash == block["transactions"][0].hex()
        assert idx_transfer.token_address == membership_token["address"]
        assert idx_transfer.from_address == self.issuer["account_address"]
        assert idx_transfer.to_address == self.trader["account_address"]
        assert idx_transfer.value == 200000
        assert idx_transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert idx_transfer.data is None
        assert idx_transfer.created is not None
        assert idx_transfer.modified is not None

        block = web3.eth.get_block(coupon_block_number)
        idx_transfer = idx_transfer_list[2]
        assert idx_transfer.id == 3
        assert idx_transfer.transaction_hash == block["transactions"][0].hex()
        assert idx_transfer.token_address == coupon_token["address"]
        assert idx_transfer.from_address == self.issuer["account_address"]
        assert idx_transfer.to_address == self.trader["account_address"]
        assert idx_transfer.value == 300000
        assert idx_transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert idx_transfer.data is None
        assert idx_transfer.created is not None
        assert idx_transfer.modified is not None

        idx_block_number: IDXTransferBlockNumber = (
            session.query(IDXTransferBlockNumber)
            .filter(IDXTransferBlockNumber.contract_address == bond_token["address"])
            .first()
        )
        assert idx_block_number.latest_block_number == latest_block_number

        idx_block_number: IDXTransferBlockNumber = (
            session.query(IDXTransferBlockNumber)
            .filter(
                IDXTransferBlockNumber.contract_address == membership_token["address"]
            )
            .first()
        )
        assert idx_block_number.latest_block_number == latest_block_number

        idx_block_number: IDXTransferBlockNumber = (
            session.query(IDXTransferBlockNumber)
            .filter(IDXTransferBlockNumber.contract_address == coupon_token["address"])
            .first()
        )
        assert idx_block_number.latest_block_number == latest_block_number

    # <Normal_4_1>
    # No blocks have been generated since the last transaction occurred
    # block_to <= skip_block
    def test_normal_4_1(self, processor, shared_contract, session, caplog):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract,
        )
        self.listing_token(share_token["address"], session)
        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"],
        )

        # emit "Transfer"
        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            share_token,
            100000,
        )
        block_number_1 = web3.eth.block_number

        """
        1st execution
        """
        # Execute batch processing
        processor.sync_new_logs()

        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 1

        block = web3.eth.get_block(block_number_1)
        _transfer = _transfer_list[0]
        assert _transfer.id == 1
        assert _transfer.transaction_hash == block["transactions"][0].hex()
        assert _transfer.token_address == share_token["address"]
        assert _transfer.from_address == self.issuer["account_address"]
        assert _transfer.to_address == self.trader["account_address"]
        assert _transfer.value == 100000
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        assert _transfer.created is not None
        assert _transfer.modified is not None

        idx_block_number: IDXTransferBlockNumber = (
            session.query(IDXTransferBlockNumber)
            .filter(IDXTransferBlockNumber.contract_address == share_token["address"])
            .first()
        )
        assert idx_block_number.latest_block_number == block_number_1

        """
        2nd execution
        """
        # Execute batch processing
        caplog.clear()
        processor.sync_new_logs()

        # Assertion
        session.rollback()
        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 1

        idx_block_number: IDXTransferBlockNumber = (
            session.query(IDXTransferBlockNumber)
            .filter(IDXTransferBlockNumber.contract_address == share_token["address"])
            .first()
        )
        assert idx_block_number.latest_block_number == block_number_1

        assert 2 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                f"{share_token['address']}: block_to <= skip_block",
            )
        )
        caplog.clear()

    # <Normal_4_2>
    # Data that has already been synchronized is not processed
    # block_from <= skip_block < block_to
    def test_normal_4_2(self, processor, shared_contract, session, caplog):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract,
        )
        self.listing_token(share_token["address"], session)
        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"],
        )

        # emit "Transfer"
        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            share_token,
            100000,
        )
        block_number_1 = web3.eth.block_number
        block_timestamp_1 = web3.eth.get_block(block_number_1)["timestamp"]

        """
        1st execution
        """
        # Execute batch processing
        processor.sync_new_logs()

        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 1

        block = web3.eth.get_block(block_number_1)
        _transfer = _transfer_list[0]
        assert _transfer.id == 1
        assert _transfer.transaction_hash == block["transactions"][0].hex()
        assert _transfer.token_address == share_token["address"]
        assert _transfer.from_address == self.issuer["account_address"]
        assert _transfer.to_address == self.trader["account_address"]
        assert _transfer.value == 100000
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        assert _transfer.created is not None
        assert _transfer.modified is not None

        idx_block_number: IDXTransferBlockNumber = (
            session.query(IDXTransferBlockNumber)
            .filter(IDXTransferBlockNumber.contract_address == share_token["address"])
            .first()
        )
        assert idx_block_number.latest_block_number == block_number_1

        """
        2nd execution
        """
        web3.provider.make_request(RPCEndpoint("evm_mine"), [block_timestamp_1 + 1])
        block_number_2 = web3.eth.block_number

        # Execute batch processing
        caplog.clear()
        processor.sync_new_logs()

        # Assertion
        session.rollback()
        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 1

        idx_block_number: IDXTransferBlockNumber = (
            session.query(IDXTransferBlockNumber)
            .filter(IDXTransferBlockNumber.contract_address == share_token["address"])
            .first()
        )
        assert idx_block_number.latest_block_number == block_number_2

        assert 2 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                f"{share_token['address']}: block_from <= skip_block < block_to",
            )
        )
        caplog.clear()

    # <Normal_4_3>
    # Data that has already been synchronized
    # block_to <= skip_block
    def test_normal_4_3(self, processor, shared_contract, session, caplog):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract,
        )
        self.listing_token(share_token["address"], session)
        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"],
        )

        # emit "Transfer"
        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            share_token,
            100000,
        )
        block_number_1 = web3.eth.block_number
        block_timestamp_1 = web3.eth.get_block(block_number_1)["timestamp"]

        """
        1st execution
        """
        # Execute batch processing
        processor.sync_new_logs()

        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 1

        block = web3.eth.get_block(block_number_1)
        _transfer = _transfer_list[0]
        assert _transfer.id == 1
        assert _transfer.transaction_hash == block["transactions"][0].hex()
        assert _transfer.token_address == share_token["address"]
        assert _transfer.from_address == self.issuer["account_address"]
        assert _transfer.to_address == self.trader["account_address"]
        assert _transfer.value == 100000
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        assert _transfer.created is not None
        assert _transfer.modified is not None

        idx_block_number: IDXTransferBlockNumber = (
            session.query(IDXTransferBlockNumber)
            .filter(IDXTransferBlockNumber.contract_address == share_token["address"])
            .first()
        )
        assert idx_block_number.latest_block_number == block_number_1

        idx_block_number.latest_block_number += 999999

        session.merge(idx_block_number)
        session.commit()

        """
        2nd execution
        """
        web3.provider.make_request(RPCEndpoint("evm_mine"), [block_timestamp_1 + 1])
        block_number_2 = web3.eth.block_number

        # Execute batch processing
        caplog.clear()

        processor.sync_new_logs()

        # Assertion
        session.rollback()
        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 1

        idx_block_number: IDXTransferBlockNumber = (
            session.query(IDXTransferBlockNumber)
            .filter(IDXTransferBlockNumber.contract_address == share_token["address"])
            .first()
        )
        assert idx_block_number.latest_block_number == block_number_2

        assert 2 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                f"{share_token['address']}: block_to <= skip_block",
            )
        )
        caplog.clear()

    # <Normal_4_4>
    # Data that has already been synchronized,
    # but there is no index_transfer_block_number due to ibet-Wallet-API version upgrade.
    # block_to <= skip_block
    def test_normal_4_4(self, processor, shared_contract, session, caplog):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract,
        )
        self.listing_token(share_token["address"], session)
        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"],
        )

        # emit "Transfer"
        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            share_token,
            100000,
        )
        block_number_1 = web3.eth.block_number
        block = web3.eth.get_block(block_number_1)

        idx_transfer = IDXTransfer()
        idx_transfer.id = 1
        idx_transfer.transaction_hash = block["transactions"][0].hex()
        idx_transfer.from_address = self.issuer["account_address"]
        idx_transfer.to_address = self.issuer["account_address"]
        idx_transfer.value = 100000
        idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
        idx_transfer.token_address = share_token["address"]
        idx_transfer.created = datetime.fromtimestamp(block["timestamp"], UTC)
        session.merge(idx_transfer)
        session.commit()

        # Execute batch processing
        caplog.clear()
        processor.sync_new_logs()

        # Assertion
        session.rollback()

        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 1

        idx_block_number: IDXTransferBlockNumber = (
            session.query(IDXTransferBlockNumber)
            .filter(IDXTransferBlockNumber.contract_address == share_token["address"])
            .first()
        )
        assert idx_block_number.latest_block_number == block_number_1

        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                f"Skip Registry Transfer data in DB: blockNumber={block_number_1}",
            )
        )
        caplog.clear()

    # <Normal_4_5>
    # No event logs
    def test_normal_4_5(self, processor, shared_contract, session, caplog):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract,
        )
        self.listing_token(share_token["address"], session)
        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"],
        )

        # Latest block number
        block_number = web3.eth.block_number

        # Execute batch processing
        caplog.clear()
        processor.sync_new_logs()

        # Assertion
        idx_transfer_list = (
            session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        )
        assert len(idx_transfer_list) == 0

        idx_block_number: IDXTransferBlockNumber = (
            session.query(IDXTransferBlockNumber)
            .filter(IDXTransferBlockNumber.contract_address == share_token["address"])
            .first()
        )
        assert idx_block_number.latest_block_number == block_number

        assert 2 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                f"{share_token['address']}: skip_block < block_from < block_to",
            )
        )
        caplog.clear()

    # <Normal_5>
    # Not Listing Token
    def test_normal_5(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract,
        )

        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"],
        )

        # Transfer
        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            share_token,
            100000,
        )
        block_number = web3.eth.block_number

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 0

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1_1>: ABIEventFunctionNotFound occurs in __sync_xx method.
    # <Error_1_2>: ServiceUnavailable occurs in __sync_xx method.
    # <Error_2_1>: ServiceUnavailable occurs
    # <Error_2_2>: SQLAlchemyError occurs

    # <Error_1_1>: ABIEventFunctionNotFound occurs in __sync_xx method.
    @mock.patch(
        "web3.contract.ContractEvent.getLogs",
        MagicMock(side_effect=ABIEventFunctionNotFound()),
    )
    def test_error_1_1(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract,
        )
        self.listing_token(share_token["address"], session)
        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"],
        )

        # emit "Transfer"
        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            share_token,
            100000,
        )

        # Execute batch processing
        processor.sync_new_logs()  # first execution
        processor.sync_new_logs()  # second execution

        # Assertion
        session.rollback()
        idx_transfer_list = (
            session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        )
        assert len(idx_transfer_list) == 0

    # <Error_1_2>: ServiceUnavailable occurs in __sync_xx method.
    def test_error_1_2(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract,
        )
        self.listing_token(share_token["address"], session)
        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"],
        )

        # emit "Transfer"
        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            share_token,
            100000,
        )

        # Execute batch processing
        with mock.patch(
            "web3.eth.Eth.get_block", MagicMock(side_effect=ServiceUnavailable())
        ), pytest.raises(ServiceUnavailable):
            processor.sync_new_logs()

        # Assertion
        session.rollback()
        idx_transfer_list = (
            session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        )
        assert len(idx_transfer_list) == 0

    # <Error_2_1>: ServiceUnavailable occurs
    def test_error_2_1(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract,
        )
        self.listing_token(share_token["address"], session)
        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"],
        )

        # emit "Transfer"
        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            share_token,
            100000,
        )

        # Execute batch processing
        with mock.patch(
            "web3.providers.rpc.HTTPProvider.make_request",
            MagicMock(side_effect=ServiceUnavailable()),
        ), pytest.raises(ServiceUnavailable):
            processor.sync_new_logs()

        # Assertion
        idx_transfer_list = (
            session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        )
        assert len(idx_transfer_list) == 0

    # <Error_2_2>: SQLAlchemyError occurs
    def test_error_2_2(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        share_token = self.issue_token_share(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract_address,
            token_list_contract,
        )
        self.listing_token(share_token["address"], session)
        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract_address,
            self.issuer["account_address"],
        )

        # emit "Transfer"
        share_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            share_token,
            100000,
        )

        # Execute batch processing
        with mock.patch.object(
            Session, "commit", side_effect=SQLAlchemyError()
        ), pytest.raises(SQLAlchemyError):
            processor.sync_new_logs()

        # Assertion
        _transfer_list = session.query(IDXTransfer).order_by(IDXTransfer.created).all()
        assert len(_transfer_list) == 0
