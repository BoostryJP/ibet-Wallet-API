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
from datetime import datetime

from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import ABIEventFunctionNotFound

from app import config
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.db import (
    Listing,
    IDXTransferApproval
)
from batch import indexer_TransferApproval
from batch.indexer_TransferApproval import main, LOG
from tests.account_config import eth_account
from tests.contract_modules import (
    issue_share_token,
    register_share_list,
    share_transfer_to_exchange
)
from tests.utils import PersonalInfoUtils

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    indexer_TransferApproval.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    return indexer_TransferApproval


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
    account1 = eth_account["user1"]
    account2 = eth_account["user2"]
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
    # - Apply For Transfer
    def test_normal_1(self, processor, shared_contract, session):
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
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setTransferApprovalRequired(True).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Apply For Transfer
        tx_hash = token_contract.functions.applyForTransfer(
            self.trader2["account_address"], 2000, "978266096").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval).order_by(IDXTransferApproval.created).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token["address"]
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == self.trader["account_address"]
        assert _transfer_approval.to_address == self.trader2["account_address"]
        assert _transfer_approval.value == 2000
        assert _transfer_approval.application_datetime == \
               datetime.strptime("2000/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is None

    # <Normal_2>
    # Single Token
    # - Apply For Transfer
    # - Approve
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
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setTransferApprovalRequired(True).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Apply For Transfer
        tx_hash = token_contract.functions.applyForTransfer(
            self.trader2["account_address"], 2000, "978266096").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Approve
        tx_hash = token_contract.functions.approveTransfer(0, "1609418096").transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval).order_by(IDXTransferApproval.created).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token["address"]
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == self.trader["account_address"]
        assert _transfer_approval.to_address == self.trader2["account_address"]
        assert _transfer_approval.value == 2000
        assert _transfer_approval.application_datetime == \
               datetime.strptime("2000/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime == \
               datetime.strptime("2020/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.approval_blocktimestamp is not None
        assert _transfer_approval.cancelled is None

    # <Normal_3>
    # Single Token
    # - Apply For Transfer
    # - Cancel
    def test_normal_3(self, processor, shared_contract, session):
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
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setTransferApprovalRequired(True).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Apply For Transfer
        tx_hash = token_contract.functions.applyForTransfer(
            self.trader2["account_address"], 2000, "978266096").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Cancel
        tx_hash = token_contract.functions.cancelTransfer(0, "test_data").transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval).order_by(IDXTransferApproval.created).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token["address"]
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == self.trader["account_address"]
        assert _transfer_approval.to_address == self.trader2["account_address"]
        assert _transfer_approval.value == 2000
        assert _transfer_approval.application_datetime == \
               datetime.strptime("2000/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is True

    # <Normal_4>
    # Multi Token
    # - Apply For Transfer
    # - Approve
    def test_normal_4(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)
        token2 = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token2["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.trader2["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token2, 10000)

        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setTransferApprovalRequired(True).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        token_contract2 = Contract.get_contract("IbetShare", token2["address"])
        tx_hash = token_contract2.functions.setTransferApprovalRequired(True).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Apply For Transfer
        tx_hash = token_contract.functions.applyForTransfer(
            self.trader2["account_address"], 2000, "978266096").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        tx_hash = token_contract2.functions.applyForTransfer(
            self.trader2["account_address"], 3000, "test_data").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Approve
        tx_hash = token_contract.functions.approveTransfer(0, "1609418096").transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        tx_hash = token_contract2.functions.approveTransfer(0, "test_data").transact(
            {"from": self.issuer["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval).order_by(IDXTransferApproval.created).all()
        assert len(_transfer_approval_list) == 2
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token["address"]
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == self.trader["account_address"]
        assert _transfer_approval.to_address == self.trader2["account_address"]
        assert _transfer_approval.value == 2000
        assert _transfer_approval.application_datetime == \
               datetime.strptime("2000/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime == \
               datetime.strptime("2020/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.approval_blocktimestamp is not None
        assert _transfer_approval.cancelled is None
        _transfer_approval = _transfer_approval_list[1]
        assert _transfer_approval.id == 2
        assert _transfer_approval.token_address == token2["address"]
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == self.trader["account_address"]
        assert _transfer_approval.to_address == self.trader2["account_address"]
        assert _transfer_approval.value == 3000
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is not None
        assert _transfer_approval.cancelled is None

    # <Normal_5>
    # No event logs
    def test_normal_5(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.trader2["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setTransferApprovalRequired(True).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Not Apply For Transfer
        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval).order_by(IDXTransferApproval.created).all()
        assert len(_transfer_approval_list) == 0

    # <Normal_6>
    # Not Listing Token
    def test_normal_6(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.trader2["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        share_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setTransferApprovalRequired(True).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Apply For Transfer
        tx_hash = token_contract.functions.applyForTransfer(
            self.trader2["account_address"], 2000, "978266096").transact(
            {"from": self.trader["account_address"], "gas": 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval).order_by(IDXTransferApproval.created).all()
        assert len(_transfer_approval_list) == 0

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
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        # Register personal info
        PersonalInfoUtils.register(
            self.account1["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.account2["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        # Transfer token: from issuer to account1
        share_transfer_to_exchange(self.issuer, {"address": self.account1["account_address"]}, token, 5000)
        # Change transfer approval required to True
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setTransferApprovalRequired(True).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        # Apply for transfer
        tx_hash = token_contract.functions.applyForTransfer(
            self.account2["account_address"],
            2000,
            "1"
        ).transact({
            "from": self.account1["account_address"]
        })
        web3.eth.waitForTransactionReceipt(tx_hash)

        block_number_current = web3.eth.blockNumber

        # Run initial sync
        processor.initial_sync()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 0
        # Latest_block is incremented in "initial_sync" process.
        assert processor.latest_block == block_number_current

        # Apply for transfer
        tx_hash = token_contract.functions.applyForTransfer(
            self.account2["account_address"],
            2000,
            "2"
        ).transact({
            "from": self.account1["account_address"]
        })
        web3.eth.waitForTransactionReceipt(tx_hash)
        block_number_current = web3.eth.blockNumber

        # Run target process
        processor.sync_new_logs()

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 0
        # Latest_block is incremented in "initial_sync" process.
        assert processor.latest_block == block_number_current

    # <Error_1_2>: ServiceUnavailable occurs in __sync_xx method.
    @mock.patch("web3.eth.Eth.getBlock", MagicMock(side_effect=ServiceUnavailable()))
    def test_error_1_2(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        # Register personal info
        PersonalInfoUtils.register(
            self.account1["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.account2["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer token: from issuer to account1
        share_transfer_to_exchange(self.issuer, {"address": self.account1["account_address"]}, token, 5000)
        # Change transfer approval required to True
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setTransferApprovalRequired(True).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Apply for transfer
        tx_hash = token_contract.functions.applyForTransfer(
            self.account2["account_address"],
            2000,
            "1"
        ).transact({
            "from": self.account1["account_address"]
        })
        web3.eth.waitForTransactionReceipt(tx_hash)

        block_number_bf = processor.latest_block
        # Expect that initial_sync() raises ServiceUnavailable.
        with pytest.raises(ServiceUnavailable):
            processor.initial_sync()
        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 0
        assert processor.latest_block == block_number_bf

        # Apply for transfer
        tx_hash = token_contract.functions.applyForTransfer(
            self.account2["account_address"],
            2000,
            "2"
        ).transact({
            "from": self.account1["account_address"]
        })
        web3.eth.waitForTransactionReceipt(tx_hash)

        block_number_bf = processor.latest_block
        # Expect that sync_new_logs() raises ServiceUnavailable.
        with pytest.raises(ServiceUnavailable):
            processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 0
        # Latest_block is NOT incremented in "sync_new_logs" process.
        assert processor.latest_block == block_number_bf

    # <Error_2_1>: ServiceUnavailable occurs in "initial_sync" / "sync_new_logs".
    def test_error_2_1(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        # Register personal info
        PersonalInfoUtils.register(
            self.account1["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.account2["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer token: from issuer to account1
        share_transfer_to_exchange(self.issuer, {"address": self.account1["account_address"]}, token, 5000)
        # Change transfer approval required to True
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setTransferApprovalRequired(True).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        # Apply for transfer
        tx_hash = token_contract.functions.applyForTransfer(
            self.account2["account_address"],
            2000,
            "1"
        ).transact({
            "from": self.account1["account_address"]
        })
        web3.eth.waitForTransactionReceipt(tx_hash)

        block_number_bf = processor.latest_block
        # Expect that initial_sync() raises ServiceUnavailable.
        with mock.patch("web3.eth.Eth.block_number", side_effect=ServiceUnavailable()), \
                pytest.raises(ServiceUnavailable):
            processor.initial_sync()
        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 0
        assert processor.latest_block == block_number_bf

        # Apply for transfer
        tx_hash = token_contract.functions.applyForTransfer(
            self.account2["account_address"],
            2000,
            "2"
        ).transact({
            "from": self.account1["account_address"]
        })
        web3.eth.waitForTransactionReceipt(tx_hash)

        block_number_bf = processor.latest_block
        # Expect that sync_new_logs() raises ServiceUnavailable.
        with mock.patch("web3.eth.Eth.block_number", side_effect=ServiceUnavailable()), \
                pytest.raises(ServiceUnavailable):
            processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 0
        # Latest_block is NOT incremented in "sync_new_logs" process.
        assert processor.latest_block == block_number_bf

    # <Error_2_2>: SQLAlchemyError occurs in "initial_sync" / "sync_new_logs".
    def test_error_2_2(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        # Register personal info
        PersonalInfoUtils.register(
            self.account1["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.account2["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer token: from issuer to account1
        share_transfer_to_exchange(self.issuer, {"address": self.account1["account_address"]}, token, 5000)
        # Change transfer approval required to True
        token_contract = Contract.get_contract("IbetShare", token["address"])
        tx_hash = token_contract.functions.setTransferApprovalRequired(True).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)
        # Apply for transfer
        tx_hash = token_contract.functions.applyForTransfer(
            self.account2["account_address"],
            2000,
            "1"
        ).transact({
            "from": self.account1["account_address"]
        })
        web3.eth.waitForTransactionReceipt(tx_hash)

        block_number_bf = processor.latest_block
        # Expect that initial_sync() raises SQLAlchemyError.
        with mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()), \
                pytest.raises(SQLAlchemyError):
            processor.initial_sync()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 0
        assert processor.latest_block == block_number_bf

        # Apply for transfer
        tx_hash = token_contract.functions.applyForTransfer(
            self.account2["account_address"],
            2000,
            "2"
        ).transact({
            "from": self.account1["account_address"]
        })
        web3.eth.waitForTransactionReceipt(tx_hash)

        block_number_bf = processor.latest_block
        # Expect that sync_new_logs() raises SQLAlchemyError.
        with mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()), \
                pytest.raises(SQLAlchemyError):
            processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 0
        # Latest_block is NOT incremented in "sync_new_logs" process.
        assert processor.latest_block == block_number_bf

    # <Error_3>: ServiceUnavailable occurs and is handled in mainloop.
    def test_error_3(self, main_func, shared_contract, session, caplog):
        # Mocking time.sleep to break mainloop
        time_mock = MagicMock(wraps=time)
        time_mock.sleep.side_effect = TypeError()

        # Run mainloop once and fail with web3 utils error
        with mock.patch("batch.indexer_TransferApproval.time", time_mock),\
            mock.patch("batch.indexer_TransferApproval.Processor.initial_sync", return_value=True), \
            mock.patch("web3.eth.Eth.block_number", side_effect=ServiceUnavailable()), \
                pytest.raises(TypeError):
            # Expect that initial_sync() raises ServiceUnavailable and handled in mainloop.
            main_func()

        assert 1 == caplog.record_tuples.count((LOG.name, logging.WARNING, "An external service was unavailable"))
        caplog.clear()
