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
    Listing,
    IDXPosition
)
from batch import indexer_Position_Bond
from tests.account_config import eth_account
from tests.contract_modules import (
    issue_bond_token,
    register_bond_list,
    bond_transfer_to_exchange,
)
from tests.utils import PersonalInfoUtils

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    indexer_Position_Bond.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    return indexer_Position_Bond


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
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        bond_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)

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
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])
        PersonalInfoUtils.register(
            self.trader2["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        bond_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)
        bond_transfer_to_exchange(self.issuer, {"address": self.trader2["account_address"]}, token, 3000)

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
        bond_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)
        bond_transfer_to_exchange(self.issuer, {"address": self.trader2["account_address"]}, token, 3000)
        bond_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token2, 5000)
        bond_transfer_to_exchange(self.issuer, {"address": self.trader2["account_address"]}, token2, 3000)

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
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        token_contract = Contract.get_contract("IbetStraightBond", token["address"])
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
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        token_contract = Contract.get_contract("IbetStraightBond", token["address"])
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
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        # Issue(add balance)
        token_contract = Contract.get_contract("IbetStraightBond", token["address"])
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
    # No event logs
    def test_normal_7(self, processor, shared_contract, session):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
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
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        bond_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)

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
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, config.ZERO_ADDRESS, personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract["address"], self.issuer["account_address"])

        # Transfer
        bond_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 10000)

        # Run target process
        processor.sync_new_logs()

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _position_list = session.query(IDXPosition).order_by(IDXPosition.created).all()
        assert len(_position_list) == 0
