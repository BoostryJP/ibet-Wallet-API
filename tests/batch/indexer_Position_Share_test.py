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
from unittest import mock
from unittest.mock import MagicMock

from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import ABIEventFunctionNotFound

from app import config
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.db import (
    Listing,
    IDXPosition
)
from batch import indexer_Position_Share
from batch.indexer_Position_Share import main, LOG
from tests.account_config import eth_account
from tests.contract_modules import (
    issue_share_token,
    register_share_list,
    share_transfer_to_exchange,
)
from tests.utils import PersonalInfoUtils

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    indexer_Position_Share.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    return indexer_Position_Share


@pytest.fixture(scope="function")
def main_func(test_module):
    LOG = logging.getLogger("Processor")
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
    def issue_token_share(issuer, exchange_contract_address, personal_info_contract_address, token_list):
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
    # Single Token
    # Single event logs
    # - Transfer
    def test_normal_1(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)

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
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.trader2["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)
        share_transfer_to_exchange(self.issuer, {"address": self.trader2["account_address"]}, token, 3000)

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
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)
        personal_info_contract = shared_contract["PersonalInfo"]
        token2 = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token2["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.trader2["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)
        share_transfer_to_exchange(self.issuer, {"address": self.trader2["account_address"]}, token, 3000)
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token2, 5000)
        share_transfer_to_exchange(self.issuer, {"address": self.trader2["account_address"]}, token2, 3000)

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
    # - Lock
    def test_normal_4(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.authorize(self.trader["account_address"], True).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Lock
        tx_hash = token_contract.functions.lock(self.trader["account_address"], 3000).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 1
        _position = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 3000
        assert _position.pending_transfer is None

    # <Normal_5>
    # Single Token
    # Single event logs
    # - Lock
    # - Unlock
    def test_normal_5(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.authorize(self.trader["account_address"], True).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Lock
        tx_hash = token_contract.functions.lock(self.trader["account_address"], 3000).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Unlock
        tx_hash = token_contract.functions.unlock(
            self.issuer["account_address"], self.trader2["account_address"], 100).transact(
            {'from': self.trader['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 2
        _position = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 3000
        assert _position.pending_transfer is None
        _position = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 100
        assert _position.pending_transfer is None

    # <Normal_6>
    # Single Token
    # Single event logs
    # - Issue(add balance)
    def test_normal_6(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        # Issue(add balance)
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.issueFrom(
            self.issuer["account_address"], config.ZERO_ADDRESS, 50000).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 1
        _position = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 + 50000
        assert _position.pending_transfer is None

    # <Normal_7>
    # Single Token
    # Single event logs
    # - Redeem
    def test_normal_7(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        # Redeem
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.redeemFrom(
            self.issuer["account_address"], config.ZERO_ADDRESS, 50000).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 1
        _position = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 50000
        assert _position.pending_transfer is None

    # <Normal_8>
    # Single Token
    # Single event logs
    # - Transfer
    # - Apply For Transfer
    def test_normal_8(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.trader2["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setTransferApprovalRequired(True).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Apply For Transfer
        tx_hash = token_contract.functions.applyForTransfer(self.trader2["account_address"], 2000, "test").transact(
            {'from': self.trader['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

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
        assert _position.balance == 10000 - 2000
        assert _position.pending_transfer == 2000

    # <Normal_9>
    # Single Token
    # Single event logs
    # - Transfer
    # - Apply For Transfer
    # - Approve
    def test_normal_9(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.trader2["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setTransferApprovalRequired(True).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Apply For Transfer
        tx_hash = token_contract.functions.applyForTransfer(self.trader2["account_address"], 2000, "test").transact(
            {'from': self.trader['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Approve
        tx_hash = token_contract.functions.approveTransfer(0, "test").transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 3
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
        assert _position.balance == 10000 - 2000
        assert _position.pending_transfer == 0
        _position = _position_list[2]
        assert _position.id == 3
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 2000
        assert _position.pending_transfer == 0

    # <Normal_10>
    # Single Token
    # Single event logs
    # - Transfer
    # - Apply For Transfer
    # - Cancel
    def test_normal_10(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.trader2["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setTransferApprovalRequired(True).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Apply For Transfer
        tx_hash = token_contract.functions.applyForTransfer(self.trader2["account_address"], 2000, "test").transact(
            {'from': self.trader['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Cancel
        tx_hash = token_contract.functions.cancelTransfer(0, "test").transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

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
        assert _position.pending_transfer == 0

    # <Normal_11>
    # No event logs
    def test_normal_11(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        # Not Event
        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0

    # <Normal_12>
    # Not Listing Token
    def test_normal_12(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1_1>: ABIEventFunctionNotFound occurs in __sync_xx method.
    # <Error_1_2>: ServiceUnavailable occurs in __sync_xx method.
    # <Error_2_1>: ServiceUnavailable occurs in "initial_sync" / "sync_new_logs".
    # <Error_2_2>: SQLAlchemyError occurs in "initial_sync" / "sync_new_logs".
    # <Error_3>: ServiceUnavailable occurs and is handled in mainloop.

    # <Error_1_1>: ABIEventFunctionNotFound occurs in __sync_xx method.
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=ABIEventFunctionNotFound()))
    def test_error_1_1(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)
        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        share_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        block_number_current = web3.eth.blockNumber
        # Run initial sync
        processor.initial_sync()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Latest_block is incremented in "initial_sync" process.
        assert processor.latest_block == block_number_current

        # Transfer
        share_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        block_number_current = web3.eth.blockNumber
        # Run target process
        processor.sync_new_logs()

        # Run target process
        processor.sync_new_logs()
        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Latest_block is incremented in "sync_new_logs" process.
        assert processor.latest_block == block_number_current

    # <Error_1_2>: ServiceUnavailable occurs in __sync_xx method.
    def test_error_1_2(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        share_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        block_number_bf = processor.latest_block
        # Expect that initial_sync() raises ServiceUnavailable.
        with mock.patch("web3.contract.ContractFunction.call", MagicMock(side_effect=ServiceUnavailable())), \
                pytest.raises(ServiceUnavailable):
            processor.initial_sync()
        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        assert processor.latest_block == block_number_bf

        # Transfer
        share_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        block_number_bf = processor.latest_block
        # Expect that sync_new_logs() raises ServiceUnavailable.
        with mock.patch("web3.contract.ContractFunction.call", MagicMock(side_effect=ServiceUnavailable())), \
                pytest.raises(ServiceUnavailable):
            processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Latest_block is NOT incremented in "sync_new_logs" process.
        assert processor.latest_block == block_number_bf

    # <Error_2_1>: ServiceUnavailable occurs in "initial_sync" / "sync_new_logs".
    def test_error_2_1(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        share_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        block_number_bf = processor.latest_block
        # Expect that initial_sync() raises ServiceUnavailable.
        with mock.patch("web3.eth.Eth.block_number", side_effect=ServiceUnavailable()), \
                pytest.raises(ServiceUnavailable):
            processor.initial_sync()
        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        assert processor.latest_block == block_number_bf

        # Transfer
        share_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        block_number_bf = processor.latest_block
        # Expect that sync_new_logs() raises ServiceUnavailable.
        with mock.patch("web3.eth.Eth.block_number", side_effect=ServiceUnavailable()), \
                pytest.raises(ServiceUnavailable):
            processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Latest_block is NOT incremented in "sync_new_logs" process.
        assert processor.latest_block == block_number_bf

    # <Error_2_2>: SQLAlchemyError occurs in "initial_sync" / "sync_new_logs".
    def test_error_2_2(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        share_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        block_number_bf = processor.latest_block
        # Expect that initial_sync() raises SQLAlchemyError.
        with mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()), \
                pytest.raises(SQLAlchemyError):
            processor.initial_sync()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        assert processor.latest_block == block_number_bf

        # Transfer
        share_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        block_number_bf = processor.latest_block
        # Expect that sync_new_logs() raises SQLAlchemyError.
        with mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()), \
                pytest.raises(SQLAlchemyError):
            processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Latest_block is NOT incremented in "sync_new_logs" process.
        assert processor.latest_block == block_number_bf

    # <Error_3>: ServiceUnavailable occurs and is handled in mainloop.
    def test_error_3(self, main_func, shared_contract, session, caplog):
        # Mocking time.sleep to break mainloop
        time_mock = MagicMock(wraps=time)
        time_mock.sleep.side_effect = TypeError()

        # Run mainloop once and fail with web3 utils error
        with mock.patch("batch.indexer_Position_Share.time", time_mock),\
            mock.patch("batch.indexer_Position_Share.Processor.initial_sync", return_value=True), \
            mock.patch("web3.eth.Eth.block_number", side_effect=ServiceUnavailable()), \
                pytest.raises(TypeError):
            # Expect that initial_sync() raises ServiceUnavailable and handled in mainloop.
            main_func()

        assert 1 == caplog.record_tuples.count((LOG.name, logging.WARNING, "An external service was unavailable"))
        caplog.clear()
