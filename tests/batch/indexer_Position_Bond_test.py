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
from app.errors import ServiceUnavailable
from app.contracts import Contract
from app.model.db import (
    Listing,
    IDXPosition,
    IDXPositionBondBlockNumber
)
from batch import indexer_Position_Bond
from batch.indexer_Position_Bond import Processor
from batch.indexer_Position_Bond import main, LOG
from tests.account_config import eth_account
from tests.contract_modules import (
    cancel_agreement,
    issue_bond_token,
    make_buy,
    register_bond_list,
    bond_transfer_to_exchange,
    create_security_token_escrow,
    finish_security_token_escrow,
    cancel_order,
    force_cancel_order,
    make_sell,
    take_sell,
    get_latest_agreementid,
    get_latest_orderid,
    get_latest_security_escrow_id
)
from tests.utils import PersonalInfoUtils

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    indexer_Position_Bond.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    return indexer_Position_Bond


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
    def issue_token_bond(issuer, exchange_contract_address, personal_info_contract_address, token_list):
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
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, escrow_contract.address, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        bond_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 2
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        _position = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_2>
    # Single Token
    # Multi event logs
    # - Transfer
    def test_normal_2(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, escrow_contract.address, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        bond_transfer_to_exchange(
            self.issuer, {"address": escrow_contract.address}, token, 10000)
        bond_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 3000)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 2
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        _position: IDXPosition = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000 - 3000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 10000
        assert _position.exchange_commitment == 0
        _position = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 3000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_3>
    # Multi Token
    # Multi event logs
    # - Transfer
    def test_normal_3(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)
        personal_info_contract = shared_contract["PersonalInfo"]
        token2 = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token2["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.trader2["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        bond_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)
        bond_transfer_to_exchange(
            self.issuer, {"address": self.trader2["account_address"]}, token, 3000)
        bond_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token2, 5000)
        bond_transfer_to_exchange(
            self.issuer, {"address": self.trader2["account_address"]}, token2, 3000)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 6
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        _position = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000 - 3000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[2]
        assert _position.id == 3
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 3000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[3]
        assert _position.id == 4
        assert _position.token_address == token2["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 5000 - 3000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[4]
        assert _position.id == 5
        assert _position.token_address == token2["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 5000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[5]
        assert _position.id == 6
        assert _position.token_address == token2["address"]
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 3000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_4>
    # Single Token
    # Single event logs
    # - Lock
    def test_normal_4(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        token_contract = Contract.get_contract(
            "IbetStraightBond", token["address"])
        tx_hash = token_contract.functions.authorizeLockAddress(
            self.trader["account_address"],
            True
        ).transact({
            'from': self.issuer['account_address'],
            'gas': 4000000
        })
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Lock
        tx_hash = token_contract.functions.lock(self.trader["account_address"], 3000).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 1
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        _position = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 3000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_5>
    # Single Token
    # Single event logs
    # - Lock
    # - Unlock
    def test_normal_5(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        token_contract = Contract.get_contract(
            "IbetStraightBond", token["address"])
        tx_hash = token_contract.functions.authorizeLockAddress(
            self.trader["account_address"],
            True
        ).transact({
            'from': self.issuer['account_address'],
            'gas': 4000000
        })
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
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 2
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        _position = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 3000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 100
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_6>
    # Single Token
    # Single event logs
    # - Issue(add balance)
    def test_normal_6(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        # Issue(add balance)
        token_contract = Contract.get_contract(
            "IbetStraightBond", token["address"])
        tx_hash = token_contract.functions.issueFrom(
            self.issuer["account_address"], config.ZERO_ADDRESS, 50000).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 1
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        _position = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 + 50000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_7>
    # Single Token
    # Single event logs
    # - Redeem
    def test_normal_7(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract
        )
        self.listing_token(token["address"], session)

        # Redeem
        token_contract = Contract.get_contract(
            "IbetStraightBond", token["address"])
        tx_hash = token_contract.functions.redeemFrom(
            self.issuer["account_address"], config.ZERO_ADDRESS, 50000).transact(
            {'from': self.issuer['account_address'], 'gas': 4000000}
        )
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 1
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        _position = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 50000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_8>
    # Single Token
    # Single event logs
    # - Transfer
    # - Apply For Transfer
    def test_normal_8(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract
        )
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract["address"],
            self.issuer["account_address"]
        )
        PersonalInfoUtils.register(
            self.trader2["account_address"],
            personal_info_contract["address"],
            self.issuer["account_address"]
        )

        # Transfer
        bond_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            token,
            10000
        )

        token_contract = Contract.get_contract(
            "IbetStraightBond", token["address"])
        tx_hash = token_contract.functions.setTransferApprovalRequired(
            True
        ).transact({
            'from': self.issuer['account_address'],
            'gas': 4000000
        })
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Apply For Transfer
        tx_hash = token_contract.functions.applyForTransfer(
            self.trader2["account_address"],
            2000,
            "test"
        ).transact({
            'from': self.trader['account_address'],
            'gas': 4000000
        })
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 2
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        _position = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000 - 2000
        assert _position.pending_transfer == 2000
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _idx_position_bond_block_number.latest_block_number == block_number

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
        token = self.issue_token_bond(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract
        )
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract["address"],
            self.issuer["account_address"]
        )
        PersonalInfoUtils.register(
            self.trader2["account_address"],
            personal_info_contract["address"],
            self.issuer["account_address"]
        )

        # Transfer
        bond_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            token,
            10000
        )

        token_contract = Contract.get_contract(
            "IbetStraightBond", token["address"])
        tx_hash = token_contract.functions.setTransferApprovalRequired(
            True
        ).transact({
            'from': self.issuer['account_address'],
            'gas': 4000000
        })
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Apply For Transfer
        tx_hash = token_contract.functions.applyForTransfer(
            self.trader2["account_address"],
            2000,
            "test"
        ).transact({
            'from': self.trader['account_address'],
            'gas': 4000000
        })
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Approve
        tx_hash = token_contract.functions.approveTransfer(
            0,
            "test"
        ).transact({
            'from': self.issuer['account_address'],
            'gas': 4000000
        })
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 3
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        _position = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000 - 2000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[2]
        assert _position.id == 3
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader2["account_address"]
        assert _position.balance == 2000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _idx_position_bond_block_number.latest_block_number == block_number

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
        token = self.issue_token_bond(
            self.issuer,
            config.ZERO_ADDRESS,
            personal_info_contract["address"],
            token_list_contract
        )
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"],
            personal_info_contract["address"],
            self.issuer["account_address"]
        )
        PersonalInfoUtils.register(
            self.trader2["account_address"],
            personal_info_contract["address"],
            self.issuer["account_address"]
        )

        # Transfer
        bond_transfer_to_exchange(
            self.issuer,
            {"address": self.trader["account_address"]},
            token,
            10000
        )

        token_contract = Contract.get_contract(
            "IbetStraightBond",
            token["address"]
        )
        tx_hash = token_contract.functions.setTransferApprovalRequired(
            True
        ).transact({
            'from': self.issuer['account_address'],
            'gas': 4000000
        })
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Apply For Transfer
        tx_hash = token_contract.functions.applyForTransfer(
            self.trader2["account_address"],
            2000,
            "test"
        ).transact({
            'from': self.trader['account_address'],
            'gas': 4000000
        })
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Cancel
        tx_hash = token_contract.functions.cancelTransfer(
            0,
            "test"
        ).transact({
            'from': self.issuer['account_address'],
            'gas': 4000000
        })
        web3.eth.waitForTransactionReceipt(tx_hash)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 2
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        _position = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        _position = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 10000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_11>
    # Single Token
    # Multi event with Escrow logs
    # - CreateEscrow
    # - EscrowFinished
    # - CreateEscrow
    def test_normal_11(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, escrow_contract.address, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Deposit and Escrow
        bond_transfer_to_exchange(
            self.issuer, {"address": escrow_contract.address}, token, 10000)
        create_security_token_escrow(self.issuer, {"address": escrow_contract.address},
                                     token, self.trader["account_address"], self.issuer["account_address"], 200)
        finish_security_token_escrow(
            self.issuer, {"address": escrow_contract.address}, get_latest_security_escrow_id({"address": escrow_contract.address}))
        create_security_token_escrow(self.issuer, {"address": escrow_contract.address},
                                     token, self.trader["account_address"], self.issuer["account_address"], 300)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 2
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        _position: IDXPosition = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 10000 - 200 - 300
        assert _position.exchange_commitment == 300
        _position: IDXPosition = _position_list[1]
        assert _position.id == 2
        assert _position.token_address == token["address"]
        assert _position.account_address == self.trader["account_address"]
        assert _position.balance == 0
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 200
        assert _position.exchange_commitment == 0
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_12>
    # Single Token
    # Multi event with IbetExchange logs
    # - Transfer
    # - MakeOrder
    # - CancelOrder
    # - MakeOrder
    # - ForceCancelOrder
    # - MakeOrder
    def test_normal_12(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        agent = eth_account['agent']
        token = self.issue_token_bond(
            self.issuer, exchange_contract['address'], personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        bond_transfer_to_exchange(
            self.issuer, exchange_contract, token, 10000)
        make_sell(self.issuer, exchange_contract, token, 111, 1000)
        cancel_order(self.issuer, exchange_contract, get_latest_orderid(exchange_contract))
        make_sell(self.issuer, exchange_contract, token, 222, 1000)
        force_cancel_order(agent, exchange_contract, get_latest_orderid(exchange_contract))
        make_sell(self.issuer, exchange_contract, token, 333, 1000)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 1
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        _position: IDXPosition = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000 + 111 + 222
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 10000 - 111 - 222 - 333
        assert _position.exchange_commitment == 333
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_13>
    # Single Token
    # Multi event with IbetExchange logs
    # - Transfer
    # - MakeOrder
    # - TakeOrder
    # - CancelAgreement
    # - MakeOrder
    # - TakeOrder
    def test_normal_13(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]
        personal_info_contract = shared_contract["PersonalInfo"]
        agent = eth_account['agent']
        token = self.issue_token_bond(
            self.issuer, exchange_contract['address'], personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        bond_transfer_to_exchange(
            self.issuer, exchange_contract, token, 10000)
        make_buy(self.trader, exchange_contract, token, 111, 1000)
        take_sell(self.issuer, exchange_contract, get_latest_orderid(exchange_contract), 55)
        cancel_agreement(agent, exchange_contract, get_latest_orderid(exchange_contract), get_latest_agreementid(exchange_contract, get_latest_orderid(exchange_contract)))
        make_buy(self.trader, exchange_contract, token, 111, 1000)
        take_sell(self.issuer, exchange_contract, get_latest_orderid(exchange_contract), 66)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 1
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        _position: IDXPosition = _position_list[0]
        assert _position.id == 1
        assert _position.token_address == token["address"]
        assert _position.account_address == self.issuer["account_address"]
        assert _position.balance == 1000000 - 10000 + 55
        assert _position.pending_transfer == 0
        assert _position.exchange_balance == 10000 - 55 - 66
        assert _position.exchange_commitment == 66
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_14>
    # No event logs
    def test_normal_14(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        # Not Event
        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_15>
    # Not listing Token is NOT indexed,
    # and indexed properly after listing
    def test_normal_15(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        bond_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).all()
        assert len(_idx_position_bond_block_number) == 0

        # Listing
        self.listing_token(token["address"], session)

        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        session.rollback()
        _position_list = session.query(
            IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 2
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_16>
    # Single Token
    # Multi event logs
    # - Transfer
    # Duplicate events to be removed
    def test_normal_16(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        personal_info_contract = shared_contract["PersonalInfo"]

        token = self.issue_token_bond(
            self.issuer, escrow_contract.address, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        for i in range(0, 5):
            # Transfer
            bond_transfer_to_exchange(
                self.issuer, {"address": self.trader["account_address"]}, token, 1000)

        # Get events for token address
        events = Contract.get_contract('IbetStraightBond', token["address"]).events.Transfer.getLogs(
                    fromBlock=0,
                    toBlock=10000
                )
        # Ensure 5 events squashed to 2 events
        assert len(events) == 5
        filtered_events = processor.remove_duplicate_event_by_token_account_desc(events, ["from", "to"])
        assert len(filtered_events) == 2

    # <Normal_17>
    # When stored index is 9,999,999 and current block number is 19,999,999,
    # then processor must process "__sync_all" method 10 times.
    def test_normal_17(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        personal_info_contract = shared_contract["PersonalInfo"]

        current_block_number = 20000000 - 1
        latest_block_number = 10000000 - 1

        mock_lib = MagicMock()

        token = self.issue_token_bond(
            self.issuer, escrow_contract.address, personal_info_contract["address"], token_list_contract)

        # Setting current block number to 19,999,999
        self.listing_token(token["address"], session)
        with mock.patch("web3.eth.Eth.blockNumber", current_block_number):
            with mock.patch.object(Processor, "_Processor__sync_all", return_value=mock_lib) as __sync_all_mock:
                idx_position_bond_block_number = IDXPositionBondBlockNumber()
                idx_position_bond_block_number.id = 1
                idx_position_bond_block_number.token_address = token["address"]
                # Setting stored index to 9,999,999
                idx_position_bond_block_number.latest_block_number = latest_block_number
                session.merge(idx_position_bond_block_number)
                session.commit()
                __sync_all_mock.return_value = None
                processor.initial_sync()
                # Then processor call "__sync_all" method 10 times.
                assert __sync_all_mock.call_count == 10

        with mock.patch("web3.eth.Eth.blockNumber", current_block_number):
            with mock.patch.object(Processor, "_Processor__sync_all", return_value=mock_lib) as __sync_all_mock:
                # Stored index is 19,999,999
                __sync_all_mock.return_value = None
                processor.sync_new_logs()
                # Then processor call "__sync_all" method once.
                assert __sync_all_mock.call_count == 1

        new_token = self.issue_token_bond(
            self.issuer, escrow_contract.address, personal_info_contract["address"], token_list_contract)
        self.listing_token(new_token["address"], session)

        with mock.patch("web3.eth.Eth.blockNumber", current_block_number):
            with mock.patch.object(Processor, "_Processor__sync_all", return_value=mock_lib) as __sync_all_mock:
                # Stored index is 19,999,999
                __sync_all_mock.return_value = None
                processor.sync_new_logs()
                # Then processor call "__sync_all" method 20 times.
                assert __sync_all_mock.call_count == 20

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
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)
        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        # Transfer
        bond_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        block_number_current = web3.eth.blockNumber
        # Run initial sync
        processor.initial_sync()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Latest_block is incremented in "initial_sync" process.
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        assert _idx_position_bond_block_number.latest_block_number == block_number_current

        # Transfer
        bond_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        block_number_current = web3.eth.blockNumber
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
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).\
            filter(IDXPositionBondBlockNumber.token_address == token["address"]).first()
        assert _idx_position_bond_block_number.latest_block_number == block_number_current

    # <Error_1_2>: ServiceUnavailable occurs in __sync_xx method.
    @mock.patch("web3.eth.Eth.getCode", MagicMock(side_effect=ServiceUnavailable()))
    def test_error_1_2(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        bond_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        # Expect that initial_sync() raises ServiceUnavailable.
        with pytest.raises(ServiceUnavailable):
            processor.initial_sync()
        # Clear cache in DB session.
        session.rollback()
        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Any latest_block is not saved in "initial_sync" process.
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).all()
        assert len(_idx_position_bond_block_number) == 0
        # Clear cache in DB session.
        session.rollback()

        # Transfer
        bond_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        # Expect that sync_new_logs() raises ServiceUnavailable.
        with pytest.raises(ServiceUnavailable):
            processor.sync_new_logs()
        # Clear cache in DB session.
        session.rollback()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Any latest_block is not saved in "sync_new_logs" process.
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).all()
        assert len(_idx_position_bond_block_number) == 0

    # <Error_2_1>: ServiceUnavailable occurs in "initial_sync" / "sync_new_logs".
    def test_error_2_1(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        bond_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        # Expect that initial_sync() raises ServiceUnavailable.
        with mock.patch("web3.eth.Eth.block_number", side_effect=ServiceUnavailable()), \
                pytest.raises(ServiceUnavailable):
            processor.initial_sync()
        # Clear cache in DB session.
        session.rollback()
        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Any latest_block is not saved in "initial_sync" process when ServiceUnavailable occurs.
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).all()
        assert len(_idx_position_bond_block_number) == 0
        # Clear cache in DB session.
        session.rollback()

        # Transfer
        bond_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)
        # Expect that sync_new_logs() raises ServiceUnavailable.
        with mock.patch("web3.eth.Eth.block_number", side_effect=ServiceUnavailable()), \
                pytest.raises(ServiceUnavailable):
            processor.sync_new_logs()

        # Clear cache in DB session.
        session.rollback()
        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Any latest_block is not saved in "sync_new_logs" process when ServiceUnavailable occurs.
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).all()
        assert len(_idx_position_bond_block_number) == 0

    # <Error_2_2>: SQLAlchemyError occurs in "initial_sync" / "sync_new_logs".
    def test_error_2_2(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        bond_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        # Expect that initial_sync() raises SQLAlchemyError.
        with mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()), \
                pytest.raises(SQLAlchemyError):
            processor.initial_sync()
        # Clear cache in DB session.
        session.rollback()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Any latest_block is not saved in "initial_sync" process when SQLAlchemyError occurs.
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).all()
        assert len(_idx_position_bond_block_number) == 0
        # Clear cache in DB session.
        session.rollback()

        # Transfer
        bond_transfer_to_exchange(
            self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        # Expect that sync_new_logs() raises SQLAlchemyError.
        with mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()), \
                pytest.raises(SQLAlchemyError):
            processor.sync_new_logs()

        # Clear cache in DB session.
        session.rollback()
        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
        # Any latest_block is not saved in "sync_new_logs" process when SQLAlchemyError occurs.
        _idx_position_bond_block_number = session.query(IDXPositionBondBlockNumber).all()
        assert len(_idx_position_bond_block_number) == 0

    # <Error_3>: ServiceUnavailable occurs and is handled in mainloop.
    def test_error_3(self, main_func, shared_contract, session, caplog):
        # Mocking time.sleep to break mainloop
        time_mock = MagicMock(wraps=time)
        time_mock.sleep.side_effect = [True, TypeError()]

        # Run mainloop once and fail with web3 utils error
        with mock.patch("batch.indexer_Position_Bond.time", time_mock),\
            mock.patch("batch.indexer_Position_Bond.Processor.initial_sync", return_value=True), \
            mock.patch("web3.eth.Eth.block_number", side_effect=ServiceUnavailable()), \
                pytest.raises(TypeError):
            # Expect that sync_new_logs() raises ServiceUnavailable and handled in mainloop.
            main_func()

        assert 1 == caplog.record_tuples.count((LOG.name, logging.DEBUG, "Initial sync is processed successfully"))
        assert 1 == caplog.record_tuples.count((LOG.name, logging.WARNING, "An external service was unavailable"))
        caplog.clear()
