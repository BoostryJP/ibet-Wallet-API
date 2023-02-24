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
import os
import sys
import uuid
from typing import List
from unittest import mock
from unittest.mock import MagicMock
import pytest
from sqlalchemy.orm import Session

from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import ABIEventFunctionNotFound
from app.errors import ServiceUnavailable

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app import config
from app.config import ZERO_ADDRESS
from app.contracts import Contract
from app.model.db import (
    TokenHoldersList,
    TokenHolderBatchStatus,
    TokenHolder,
    Listing
)
from batch.indexer_Token_Holders import (
    LOG,
    Processor
)
from tests.account_config import eth_account
from tests.contract_modules import (
    issue_bond_token,
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
    get_latest_security_escrow_id,
    transfer_token,
    take_buy,
    confirm_agreement,
    make_buy,
    cancel_agreement,
    register_personalinfo,
    approve_transfer_security_token_escrow,
    register_share_list,
    issue_share_token,
    share_transfer_to_exchange,
    membership_issue,
    membership_register_list,
    membership_transfer_to_exchange,
    coupon_transfer_to_exchange,
    issue_coupon_token,
    coupon_register_list,
    consume_coupon_token,
    bond_apply_for_transfer,
    bond_cancel_transfer,
    bond_approve_transfer,
    bond_issue_from,
    share_set_transfer_approval_required,
    bond_redeem_from,
    bond_set_transfer_approval_required,
    share_issue_from,
    share_redeem_from,
    share_apply_for_transfer,
    share_cancel_transfer,
    share_approve_transfer,
    finish_token_escrow,
    create_token_escrow,
    get_latest_escrow_id,
    bond_lock,
    bond_unlock,
    share_lock,
    share_unlock,
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    return Processor


@pytest.fixture(scope="function")
def processor(test_module, session):
    LOG = logging.getLogger("ibet_wallet_batch")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True

    processor = test_module()
    yield processor

    LOG.propagate = False
    LOG.setLevel(default_log_level)


class TestProcessor:
    issuer = eth_account["issuer"]
    user1 = eth_account["user1"]
    user2 = eth_account["user2"]
    trader = eth_account["trader"]
    agent = eth_account["agent"]

    target_process_name = "INDEXER-TOKEN_HOLDERS"

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

    @staticmethod
    def issue_token_bond(issuer, exchange_contract_address, personal_info_contract_address, token_list):
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
            "transferable": True,
        }
        token = issue_share_token(issuer, args)
        register_share_list(issuer, token, token_list)

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
    def token_holders_list(token, block_number, status: TokenHolderBatchStatus = TokenHolderBatchStatus.PENDING) -> TokenHoldersList:
        target_token_holders_list = TokenHoldersList()
        target_token_holders_list.list_id = str(uuid.uuid4())
        target_token_holders_list.token_address = token["address"]
        target_token_holders_list.batch_status = status.value
        target_token_holders_list.block_number = block_number
        return target_token_holders_list

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # StraightBond
    # Events
    # - Transfer
    # - Exchange
    #   - MakeOrder/CancelOrder/ForceCancelOrder/TakeOrder
    #   - CancelAgreement/ConfirmAgreement
    # - IssueFrom
    # - RedeemFrom
    # - Lock
    def test_normal_1(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]

        # Issuer issues bond token.
        token = self.issue_token_bond(
            self.issuer, exchange_contract["address"], personal_info_contract["address"], token_list_contract
        )
        self.listing_token(token["address"], session)
        token_contract = Contract.get_contract("IbetStraightBond", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        # Issuer transfers issued token to user1, trader and exchange.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        transfer_token(token_contract, self.issuer["account_address"], self.trader["account_address"], 10000)
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract["address"]}, token, 10000)
        # user1: 20000 trader: 10000

        bond_transfer_to_exchange(self.user1, {"address": exchange_contract["address"]}, token, 10000)
        make_sell(self.user1, exchange_contract, token, 10000, 100)
        cancel_order(self.user1, exchange_contract, get_latest_orderid(exchange_contract))
        # user1: 20000 trader: 10000

        bond_transfer_to_exchange(self.user1, exchange_contract, token, 10000)
        make_sell(self.user1, exchange_contract, token, 10000, 100)
        force_cancel_order(self.agent, exchange_contract, get_latest_orderid(exchange_contract))
        # user1: 20000 trader: 10000

        bond_transfer_to_exchange(self.user1, exchange_contract, token, 10000)
        make_sell(self.user1, exchange_contract, token, 10000, 100)
        _latest_order_id = get_latest_orderid(exchange_contract)
        take_buy(self.trader, exchange_contract, _latest_order_id, 10000)
        confirm_agreement(
            self.agent, exchange_contract, _latest_order_id, get_latest_agreementid(exchange_contract, _latest_order_id)
        )
        # user1: 10000 trader: 20000

        bond_transfer_to_exchange(self.user1, exchange_contract, token, 4000)
        make_buy(self.trader, exchange_contract, token, 4000, 100)
        _latest_order_id = get_latest_orderid(exchange_contract)
        take_sell(self.user1, exchange_contract, _latest_order_id, 4000)
        confirm_agreement(
            self.agent, exchange_contract, _latest_order_id, get_latest_agreementid(exchange_contract, _latest_order_id)
        )
        # user1: 6000 trader: 24000

        bond_issue_from(self.issuer, token, self.issuer["account_address"], 40000)
        bond_redeem_from(self.issuer, token, self.trader["account_address"], 10000)
        # user1: 6000 trader: 14000

        bond_issue_from(self.issuer, token, self.trader["account_address"], 30000)
        bond_redeem_from(self.issuer, token, self.issuer["account_address"], 10000)
        # user1: 6000 trader: 44000

        bond_lock(self.trader, token, self.issuer["account_address"], 3000)
        # user1: 6000 trader: (hold: 41000, locked: 3000)

        # Issuer issues other token.
        other_token = self.issue_token_bond(
            self.issuer, exchange_contract["address"], personal_info_contract["address"], token_list_contract
        )
        other_token_contract = Contract.get_contract("IbetStraightBond", other_token["address"])
        transfer_token(other_token_contract, self.issuer["account_address"], self.user1["account_address"], 10000)
        transfer_token(other_token_contract, self.issuer["account_address"], self.trader["account_address"], 10000)
        bond_transfer_to_exchange(self.user1, exchange_contract, other_token, 10000)
        make_sell(self.user1, exchange_contract, other_token, 10000, 100)
        _latest_order_id = get_latest_orderid(exchange_contract)
        take_buy(self.trader, exchange_contract, _latest_order_id, 10000)
        confirm_agreement(
            self.agent, exchange_contract, _latest_order_id, get_latest_agreementid(exchange_contract, _latest_order_id)
        )

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list)
        session.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.hold_balance == 6000
        assert user1_record.locked_balance == 0
        assert trader_record.hold_balance == 41000
        assert trader_record.locked_balance == 3000

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list == target_token_holders_list.id))) == 2

    # <Normal_2>
    # StraightBond
    # Events
    # - ApplyForTransfer
    # - CancelForTransfer
    # - ApproveTransfer
    # - Escrow
    #   - CreateEscrow
    #   - FinishEscrow
    #   - ApproveTransfer
    # - Lock
    # - Unlock
    def test_normal_2(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issuer issues bond token.
        token = self.issue_token_bond(
            self.issuer, escrow_contract.address, personal_info_contract["address"], token_list_contract
        )
        self.listing_token(token["address"], session)

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetStraightBond", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        bond_transfer_to_exchange(self.user1, {"address": escrow_contract.address}, token, 10000)
        # user1: 20000 trader: 0

        # Issuer transfers issued token to user1 and trader.
        bond_set_transfer_approval_required(self.issuer, token, True)
        bond_apply_for_transfer(self.issuer, token, self.user1, 10000, "to user1#1")
        bond_apply_for_transfer(self.issuer, token, self.trader, 10000, "to trader#1")

        bond_cancel_transfer(self.issuer, token, 0, "to user1#1")
        bond_approve_transfer(self.issuer, token, 1, "to trader#1")
        # user1: 20000 trader: 10000

        create_security_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            7000,
        )
        _latest_security_escrow_id = get_latest_security_escrow_id({"address": escrow_contract.address})
        finish_security_token_escrow(self.agent, {"address": escrow_contract.address}, _latest_security_escrow_id)
        approve_transfer_security_token_escrow(self.issuer, {"address": escrow_contract.address}, _latest_security_escrow_id, "")
        # user1: 13000 trader: 17000

        create_security_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            2000,
        )
        _latest_security_escrow_id = get_latest_security_escrow_id({"address": escrow_contract.address})
        finish_security_token_escrow(self.agent, {"address": escrow_contract.address}, _latest_security_escrow_id)
        # user1: 13000 trader: 17000

        bond_lock(self.trader, token, self.issuer["account_address"], 3000)
        # user1: 13000 trader: (hold: 14000, locked: 3000)

        bond_unlock(self.issuer, token, self.trader["account_address"], self.user1["account_address"], 2000)
        # user1: 15000 trader: (hold: 14000, locked: 1000)

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list)
        session.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        bond_set_transfer_approval_required(self.issuer, token, False)
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()
        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.hold_balance == 15000
        assert user1_record.locked_balance == 0
        assert trader_record.hold_balance == 14000
        assert trader_record.locked_balance == 1000

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list == target_token_holders_list.id))) == 2

    # <Normal_3>
    # StraightBond
    # Events
    # - ApplyForTransfer - pending
    # - Escrow - pending
    def test_normal_3(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issuer issues bond token.
        token = self.issue_token_bond(
            self.issuer, escrow_contract.address, personal_info_contract["address"], token_list_contract
        )
        self.listing_token(token["address"], session)

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetStraightBond", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        # Issuer transfers issued token to user1 and trader.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        transfer_token(token_contract, self.issuer["account_address"], self.trader["account_address"], 10000)
        transfer_token(token_contract, self.user1["account_address"], escrow_contract.address, 10000)
        # user1: 20000 trader: 10000

        bond_set_transfer_approval_required(self.issuer, token, True)
        bond_apply_for_transfer(self.user1, token, self.trader, 10000, "to user1#1")
        # user1: 20000 trader: 10000

        create_security_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            7000,
        )
        create_security_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            3000,
        )
        _latest_security_escrow_id = get_latest_security_escrow_id({"address": escrow_contract.address})
        finish_security_token_escrow(self.agent, {"address": escrow_contract.address}, _latest_security_escrow_id)
        approve_transfer_security_token_escrow(self.issuer, {"address": escrow_contract.address}, _latest_security_escrow_id, "")
        # user1: 17000 trader: 13000

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list)
        session.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        bond_set_transfer_approval_required(self.issuer, token, False)
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.hold_balance == 17000
        assert trader_record.hold_balance == 13000

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list == target_token_holders_list.id))) == 2

    # <Normal_4>
    # Share
    # Events
    # - Transfer
    # - Exchange
    #   - MakeOrder/CancelOrder/ForceCancelOrder/TakeOrder
    #   - CancelAgreement/ConfirmAgreement
    # - IssueFrom
    # - RedeemFrom
    # - Lock
    def test_normal_4(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        exchange = shared_contract["IbetShareExchange"]

        # Issuer issues share token.
        token = self.issue_token_share(self.issuer, exchange["address"], personal_info_contract["address"], token_list_contract)
        self.listing_token(token["address"], session)
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetShare", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        # Issuer transfers issued token to user1, trader and exchange.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        transfer_token(token_contract, self.issuer["account_address"], self.trader["account_address"], 10000)
        share_transfer_to_exchange(self.issuer, {"address": exchange["address"]}, token, 10000)
        # user1: 20000 trader: 10000

        share_transfer_to_exchange(self.user1, {"address": exchange["address"]}, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        cancel_order(self.user1, exchange, get_latest_orderid(exchange))
        # user1: 20000 trader: 10000

        share_transfer_to_exchange(self.user1, exchange, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        force_cancel_order(self.agent, exchange, get_latest_orderid(exchange))
        # user1: 20000 trader: 10000

        share_transfer_to_exchange(self.user1, exchange, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        _latest_order_id = get_latest_orderid(exchange)
        take_buy(self.trader, exchange, _latest_order_id, 10000)
        confirm_agreement(self.agent, exchange, _latest_order_id, get_latest_agreementid(exchange, _latest_order_id))
        # user1: 10000 trader: 20000

        share_issue_from(self.issuer, token, self.issuer["account_address"], 40000)
        share_redeem_from(self.issuer, token, self.trader["account_address"], 10000)
        # user1: 10000 trader: 10000

        share_issue_from(self.issuer, token, self.trader["account_address"], 30000)
        share_redeem_from(self.issuer, token, self.issuer["account_address"], 10000)
        # user1: 10000 trader: 40000

        share_lock(self.trader, token, self.issuer["account_address"], 3000)
        # user1: 10000 trader: (hold: 37000, locked: 3000)

        # Issuer issues other token.
        other_token = self.issue_token_share(
            self.issuer, exchange["address"], personal_info_contract["address"], token_list_contract
        )
        other_token_contract = Contract.get_contract("IbetShare", other_token["address"])
        transfer_token(other_token_contract, self.issuer["account_address"], self.user1["account_address"], 10000)
        transfer_token(other_token_contract, self.issuer["account_address"], self.trader["account_address"], 10000)
        share_transfer_to_exchange(self.user1, exchange, other_token, 10000)
        make_sell(self.user1, exchange, other_token, 10000, 100)
        _latest_order_id = get_latest_orderid(exchange)
        take_buy(self.trader, exchange, _latest_order_id, 10000)
        confirm_agreement(
            self.agent, exchange, _latest_order_id, get_latest_agreementid(exchange, _latest_order_id)
        )

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list)
        session.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.hold_balance == 10000
        assert user1_record.locked_balance == 0
        assert trader_record.hold_balance == 37000
        assert trader_record.locked_balance == 3000

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list == target_token_holders_list.id))) == 2

    # <Normal_5>
    # Share
    # Events
    # - ApplyForTransfer
    # - CancelForTransfer
    # - ApproveTransfer
    # - Escrow
    #   - CreateEscrow
    #   - FinishEscrow
    #   - ApproveTransfer
    # - Lock
    # - Unlock
    def test_normal_5(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issuer issues share token.
        token = self.issue_token_share(
            self.issuer, escrow_contract.address, personal_info_contract["address"], token_list_contract
        )
        self.listing_token(token["address"], session)

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetShare", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        share_transfer_to_exchange(self.user1, {"address": escrow_contract.address}, token, 10000)
        # user1: 20000 trader: 0

        # Issuer transfers issued token to user1 and trader.
        share_set_transfer_approval_required(self.issuer, token, True)
        share_apply_for_transfer(self.issuer, token, self.user1, 10000, "to user1#1")
        share_apply_for_transfer(self.issuer, token, self.trader, 10000, "to trader#1")

        share_cancel_transfer(self.issuer, token, 0, "to user1#1")
        share_approve_transfer(self.issuer, token, 1, "to trader#1")
        # user1: 20000 trader: 10000

        create_security_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            7000,
        )
        _latest_security_escrow_id = get_latest_security_escrow_id({"address": escrow_contract.address})
        finish_security_token_escrow(self.agent, {"address": escrow_contract.address}, _latest_security_escrow_id)
        approve_transfer_security_token_escrow(self.issuer, {"address": escrow_contract.address}, _latest_security_escrow_id, "")
        # user1: 13000 trader: 17000

        create_security_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            2000,
        )
        _latest_security_escrow_id = get_latest_security_escrow_id({"address": escrow_contract.address})
        finish_security_token_escrow(self.agent, {"address": escrow_contract.address}, _latest_security_escrow_id)
        # user1: 13000 trader: 17000

        share_lock(self.trader, token, self.issuer["account_address"], 3000)
        # user1: 13000 trader: (hold: 14000, locked: 3000)

        share_unlock(self.issuer, token, self.trader["account_address"], self.user1["account_address"], 2000)
        # user1: 15000 trader: (hold: 14000, locked: 1000)

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list)
        session.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        share_set_transfer_approval_required(self.issuer, token, False)
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.hold_balance == 15000
        assert user1_record.locked_balance == 0
        assert trader_record.hold_balance == 14000
        assert trader_record.locked_balance == 1000

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list == target_token_holders_list.id))) == 2

    # <Normal_6>
    # Share
    # Events
    # - ApplyForTransfer - pending
    # - Escrow - pending
    def test_normal_6(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issuer issues share token.
        token = self.issue_token_share(
            self.issuer, escrow_contract.address, personal_info_contract["address"], token_list_contract
        )
        self.listing_token(token["address"], session)

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetShare", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        # Issuer transfers issued token to user1 and trader.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        transfer_token(token_contract, self.issuer["account_address"], self.trader["account_address"], 10000)
        transfer_token(token_contract, self.user1["account_address"], escrow_contract.address, 10000)
        # user1: 20000 trader: 10000

        share_set_transfer_approval_required(self.issuer, token, True)
        share_apply_for_transfer(self.user1, token, self.trader, 10000, "to user1#1")
        # user1: 20000 trader: 10000

        create_security_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            7000,
        )
        create_security_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            3000,
        )
        _latest_security_escrow_id = get_latest_security_escrow_id({"address": escrow_contract.address})
        finish_security_token_escrow(self.agent, {"address": escrow_contract.address}, _latest_security_escrow_id)
        approve_transfer_security_token_escrow(self.issuer, {"address": escrow_contract.address}, _latest_security_escrow_id, "")
        # user1: 17000 trader: 13000

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list)
        session.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        share_set_transfer_approval_required(self.issuer, token, False)
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.hold_balance == 17000
        assert trader_record.hold_balance == 13000

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list == target_token_holders_list.id))) == 2

    # <Normal_7>
    # Coupon
    # Events
    # - Transfer
    # - Exchange
    #   - MakeOrder/CancelOrder/ForceCancelOrder/TakeOrder
    #   - CancelAgreement/ConfirmAgreement
    def test_normal_7(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        exchange = shared_contract["IbetCouponExchange"]

        # Issuer issues coupon token.
        token = self.issue_token_coupon(self.issuer, exchange["address"], token_list_contract)
        self.listing_token(token["address"], session)
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetCoupon", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        # Issuer transfers issued token to user1, trader and exchange.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        transfer_token(token_contract, self.issuer["account_address"], self.trader["account_address"], 10000)
        coupon_transfer_to_exchange(self.issuer, {"address": exchange["address"]}, token, 10000)
        # user1: 20000 trader: 10000

        coupon_transfer_to_exchange(self.user1, {"address": exchange["address"]}, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        cancel_order(self.user1, exchange, get_latest_orderid(exchange))
        # user1: 20000 trader: 10000

        coupon_transfer_to_exchange(self.user1, exchange, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        force_cancel_order(self.agent, exchange, get_latest_orderid(exchange))
        # user1: 20000 trader: 10000

        coupon_transfer_to_exchange(self.user1, exchange, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        _latest_order_id = get_latest_orderid(exchange)
        take_buy(self.trader, exchange, _latest_order_id, 10000)
        confirm_agreement(self.agent, exchange, _latest_order_id, get_latest_agreementid(exchange, _latest_order_id))
        # user1: 10000 trader: 20000

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list)
        session.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.hold_balance == 10000
        assert trader_record.hold_balance == 20000

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list == target_token_holders_list.id))) == 2

    # <Normal_8>
    # Coupon
    # Events
    # - Escrow
    #   - CreateEscrow
    #   - FinishEscrow
    def test_normal_8(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetEscrow"]

        # Issuer issues coupon token.
        token = self.issue_token_coupon(self.issuer, escrow_contract.address, token_list_contract)
        self.listing_token(token["address"], session)

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetCoupon", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        coupon_transfer_to_exchange(self.user1, {"address": escrow_contract.address}, token, 10000)
        # user1: 20000 trader: 0

        # Issuer transfers issued token to user1 and trader.

        create_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            7000,
        )
        _latest_escrow_id = get_latest_security_escrow_id({"address": escrow_contract.address})
        finish_token_escrow(self.agent, {"address": escrow_contract.address}, _latest_escrow_id)
        # user1: 13000 trader: 7000

        create_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            2000,
        )
        _latest_escrow_id = get_latest_security_escrow_id({"address": escrow_contract.address})
        finish_token_escrow(self.agent, {"address": escrow_contract.address}, _latest_escrow_id)
        # user1: 11000 trader: 9000

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list)
        session.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.hold_balance == 11000
        assert trader_record.hold_balance == 9000

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list == target_token_holders_list.id))) == 2

    # <Normal_9>
    # Coupon
    # Events
    # - Escrow - pending
    # - Consume
    def test_normal_9(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetEscrow"]

        # Issuer issues coupon token.
        token = self.issue_token_coupon(self.issuer, escrow_contract.address, token_list_contract)
        self.listing_token(token["address"], session)

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetCoupon", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        # Issuer transfers issued token to user1 and trader.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 10000)
        transfer_token(token_contract, self.issuer["account_address"], self.trader["account_address"], 10000)
        transfer_token(token_contract, self.user1["account_address"], escrow_contract.address, 10000)
        # user1: 10000 trader: 10000

        create_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            7000,
        )
        create_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            3000,
        )
        _latest_escrow_id = get_latest_escrow_id({"address": escrow_contract.address})
        finish_token_escrow(self.agent, {"address": escrow_contract.address}, _latest_escrow_id)
        # user1: 7000 trader: 13000

        consume_coupon_token(self.trader, token, 9000)
        # user1: 7000 trader: 4000

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list)
        session.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.hold_balance == 7000
        assert trader_record.hold_balance == 4000

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list == target_token_holders_list.id))) == 2

    # <Normal_10>
    # Membership
    # Events
    # - Transfer
    # - Exchange
    #   - MakeOrder/CancelOrder/ForceCancelOrder/TakeOrder
    #   - CancelAgreement/ConfirmAgreement
    def test_normal_10(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        exchange = shared_contract["IbetMembershipExchange"]

        # Issuer issues membership token.
        token = self.issue_token_membership(self.issuer, exchange["address"], token_list_contract)
        self.listing_token(token["address"], session)
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetMembership", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        # Issuer transfers issued token to user1, trader and exchange.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        transfer_token(token_contract, self.issuer["account_address"], self.trader["account_address"], 10000)
        membership_transfer_to_exchange(self.issuer, {"address": exchange["address"]}, token, 10000)
        # user1: 20000 trader: 10000

        membership_transfer_to_exchange(self.user1, {"address": exchange["address"]}, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        cancel_order(self.user1, exchange, get_latest_orderid(exchange))
        # user1: 20000 trader: 10000

        membership_transfer_to_exchange(self.user1, exchange, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        force_cancel_order(self.agent, exchange, get_latest_orderid(exchange))
        # user1: 20000 trader: 10000

        membership_transfer_to_exchange(self.user1, exchange, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        _latest_order_id = get_latest_orderid(exchange)
        take_buy(self.trader, exchange, _latest_order_id, 10000)
        confirm_agreement(self.agent, exchange, _latest_order_id, get_latest_agreementid(exchange, _latest_order_id))
        # user1: 10000 trader: 20000

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list)
        session.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        issuer_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.issuer["account_address"])
            .first()
        )
        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.hold_balance == 10000
        assert trader_record.hold_balance == 20000

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list == target_token_holders_list.id))) == 2

    # <Normal_11>
    # Membership
    # Events
    # - Escrow
    #   - CreateEscrow
    #   - FinishEscrow
    def test_normal_11(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetEscrow"]

        # Issuer issues membership token.
        token = self.issue_token_membership(self.issuer, escrow_contract.address, token_list_contract)
        self.listing_token(token["address"], session)

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetMembership", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        membership_transfer_to_exchange(self.user1, {"address": escrow_contract.address}, token, 10000)
        # user1: 20000 trader: 0

        # Issuer transfers issued token to user1 and trader.
        create_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            7000,
        )
        _latest_escrow_id = get_latest_security_escrow_id({"address": escrow_contract.address})
        finish_token_escrow(self.agent, {"address": escrow_contract.address}, _latest_escrow_id)

        create_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            2000,
        )
        _latest_escrow_id = get_latest_security_escrow_id({"address": escrow_contract.address})
        finish_token_escrow(self.agent, {"address": escrow_contract.address}, _latest_escrow_id)
        # user1: 11000 trader: 9000

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list)
        session.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.hold_balance == 11000
        assert trader_record.hold_balance == 9000

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list == target_token_holders_list.id))) == 2

    # <Normal_12>
    # Membership
    # Events
    # - Escrow - pending
    def test_normal_12(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetEscrow"]

        # Issuer issues membership token.
        token = self.issue_token_membership(self.issuer, escrow_contract.address, token_list_contract)
        self.listing_token(token["address"], session)

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetMembership", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        # Issuer transfers issued token to user1 and trader.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 10000)
        transfer_token(token_contract, self.issuer["account_address"], self.trader["account_address"], 10000)
        transfer_token(token_contract, self.user1["account_address"], escrow_contract.address, 10000)
        # user1: 10000 trader: 10000

        create_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            7000,
        )
        create_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            3000,
        )
        _latest_escrow_id = get_latest_escrow_id({"address": escrow_contract.address})
        finish_token_escrow(self.agent, {"address": escrow_contract.address}, _latest_escrow_id)
        # user1: 7000 trader: 13000

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list)
        session.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.hold_balance == 7000
        assert trader_record.hold_balance == 13000

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list == target_token_holders_list.id))) == 2

    # <Normal_13>
    # StraightBond
    # Use checkpoint.
    def test_normal_13(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        block_number: None,
    ):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]

        # Issuer issues bond token.
        token = self.issue_token_bond(
            self.issuer, exchange_contract["address"], personal_info_contract["address"], token_list_contract
        )
        self.listing_token(token["address"], session)
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetStraightBond", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        # Issuer transfers issued token to user1, trader and exchange.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        transfer_token(token_contract, self.issuer["account_address"], self.trader["account_address"], 10000)
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract["address"]}, token, 10000)
        # user1: 20000 trader: 10000

        # Insert collection record with above token and current block number
        target_token_holders_list1 = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list1)
        session.commit()
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list1.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list1.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.hold_balance == 20000
        assert trader_record.hold_balance == 10000

        bond_transfer_to_exchange(self.user1, {"address": exchange_contract["address"]}, token, 10000)
        make_sell(self.user1, exchange_contract, token, 10000, 100)
        cancel_order(self.user1, exchange_contract, get_latest_orderid(exchange_contract))
        # user1: 20000 trader: 10000

        bond_transfer_to_exchange(self.user1, exchange_contract, token, 10000)
        make_sell(self.user1, exchange_contract, token, 10000, 100)
        force_cancel_order(self.agent, exchange_contract, get_latest_orderid(exchange_contract))
        # user1: 20000 trader: 10000

        bond_transfer_to_exchange(self.user1, exchange_contract, token, 10000)
        make_sell(self.user1, exchange_contract, token, 10000, 100)
        _latest_order_id = get_latest_orderid(exchange_contract)
        take_buy(self.trader, exchange_contract, _latest_order_id, 10000)
        confirm_agreement(
            self.agent, exchange_contract, _latest_order_id, get_latest_agreementid(exchange_contract, _latest_order_id)
        )
        # user1: 10000 trader: 20000

        # Insert collection record with above token and current block number
        target_token_holders_list2 = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list2)
        session.commit()
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list2.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list2.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.hold_balance == 10000
        assert trader_record.hold_balance == 20000

        bond_transfer_to_exchange(self.user1, exchange_contract, token, 4000)
        make_buy(self.trader, exchange_contract, token, 4000, 100)
        _latest_order_id = get_latest_orderid(exchange_contract)
        take_sell(self.user1, exchange_contract, _latest_order_id, 4000)
        cancel_agreement(
            self.agent, exchange_contract, _latest_order_id, get_latest_agreementid(exchange_contract, _latest_order_id)
        )
        # user1: 10000 trader: 20000

        bond_transfer_to_exchange(self.user1, exchange_contract, token, 4000)
        make_buy(self.trader, exchange_contract, token, 4000, 100)
        _latest_order_id = get_latest_orderid(exchange_contract)
        take_sell(self.user1, exchange_contract, _latest_order_id, 4000)
        confirm_agreement(
            self.agent, exchange_contract, _latest_order_id, get_latest_agreementid(exchange_contract, _latest_order_id)
        )
        # user1: 6000 trader: 24000

        bond_issue_from(self.issuer, token, self.issuer["account_address"], 40000)
        bond_redeem_from(self.issuer, token, self.trader["account_address"], 10000)
        # user1: 6000 trader: 14000

        bond_issue_from(self.issuer, token, self.trader["account_address"], 30000)
        bond_redeem_from(self.issuer, token, self.issuer["account_address"], 10000)
        # user1: 6000 trader: 44000

        # Insert collection record with above token and current block number
        target_token_holders_list3 = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list3)
        session.commit()
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list3.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list == target_token_holders_list3.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.hold_balance == 6000
        assert trader_record.hold_balance == 44000

    # <Normal_14>
    # StraightBond
    # Jobs are queued and pending jobs are to be processed one by one.
    def test_normal_14(self, processor: Processor, shared_contract, session: Session, caplog, block_number: None):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]

        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()
        assert 2 == caplog.record_tuples.count((LOG.name, logging.DEBUG, f"There are no pending collect batch"))

        # Issuer issues bond token.
        token = self.issue_token_bond(
            self.issuer, exchange_contract["address"], personal_info_contract["address"], token_list_contract
        )
        self.listing_token(token["address"], session)
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetStraightBond", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        target_token_holders_list1 = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list1)
        session.commit()
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        transfer_token(token_contract, self.issuer["account_address"], self.trader["account_address"], 10000)
        target_token_holders_list2 = self.token_holders_list(token, web3.eth.block_number)
        session.add(target_token_holders_list2)
        session.commit()

        caplog.clear()
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, f"Token holder list({target_token_holders_list1.list_id}) status changes to be done."))
        assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, f"Token holder list({target_token_holders_list2.list_id}) status changes to be done."))
        assert 2 == caplog.record_tuples.count((LOG.name, logging.INFO, f"Collect job has been completed"))

    # <Normal_15>
    # When stored checkpoint is 9,999,999 and current block number is 19,999,999,
    # then processor should call "__process_all" method 10 times.
    def test_normal_15(self, processor: Processor, shared_contract, session: Session, caplog: pytest.LogCaptureFixture):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        exchange_contract = shared_contract["IbetStraightBondExchange"]
        current_block_number = 20000000 - 1
        checkpoint_block_number = 10000000 - 1

        token = self.issue_token_bond(
            self.issuer, exchange_contract["address"], personal_info_contract["address"], token_list_contract
        )
        self.listing_token(token["address"], session)
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        # Insert collection record with above token and checkpoint block number
        target_token_holders_list = self.token_holders_list(token, current_block_number)
        session.add(target_token_holders_list)
        completed_token_holders_list = self.token_holders_list(token, checkpoint_block_number, status=TokenHolderBatchStatus.DONE)
        session.add(completed_token_holders_list)
        session.commit()

        # Setting current block number to 19,999,999
        with (
            mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"])
        ):
            # Setting stored index to 9,999,999
            processor.collect()
            # Then processor call "__process_all" method 10 times.
            assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, f"process from=10000000, to=10999999"))
            assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, f"process from=11000000, to=11999999"))
            assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, f"process from=12000000, to=12999999"))
            assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, f"process from=13000000, to=13999999"))
            assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, f"process from=14000000, to=14999999"))
            assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, f"process from=15000000, to=15999999"))
            assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, f"process from=16000000, to=16999999"))
            assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, f"process from=17000000, to=17999999"))
            assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, f"process from=18000000, to=18999999"))
            assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, f"process from=19000000, to=19999999"))

            session.rollback()
            processed_list = session.query(TokenHoldersList).filter(TokenHoldersList.id == target_token_holders_list.id).first()
            assert processed_list.block_number == 19999999
            assert processed_list.batch_status == TokenHolderBatchStatus.DONE.value

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # There is no target token holders list id with batch_status PENDING.
    def test_error_1(self, processor: Processor, shared_contract, session: Session, caplog, block_number: None):
        token_list_contract = shared_contract["TokenList"]

        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        assert 1 == caplog.record_tuples.count((LOG.name, logging.DEBUG, f"There are no pending collect batch"))

    # <Error_2>
    # There is target token holders list id with batch_status PENDING.
    # And target token is not contained in "TokenList" contract.
    def test_error_2(self, processor: Processor, shared_contract, session: Session, caplog, block_number: None):
        token_list_contract = shared_contract["TokenList"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        # Insert collection definition with token address Zero
        target_token_holders_list = TokenHoldersList()
        target_token_holders_list.token_address = ZERO_ADDRESS
        target_token_holders_list.list_id = str(uuid.uuid4())
        target_token_holders_list.batch_status = TokenHolderBatchStatus.PENDING.value
        target_token_holders_list.block_number = 1000
        session.add(target_token_holders_list)
        session.commit()

        # Debug message should be shown that points out token contract must be listed.
        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()
        assert 1 == caplog.record_tuples.count((LOG.name, logging.DEBUG, f"Token contract must be listed to TokenList contract."))

        # Batch status of token holders list expects to be "ERROR"
        error_record_num = len(
            list(session.query(TokenHoldersList).filter(TokenHoldersList.batch_status == TokenHolderBatchStatus.FAILED.value))
        )
        assert error_record_num == 1

    # <Error_3>
    # Failed to get Logs because of ABIEventFunctionNotFound.
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=ABIEventFunctionNotFound()))
    def test_error_3(self, processor: Processor, shared_contract, session: Session, caplog, block_number: None):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issuer issues bond token.
        token = self.issue_token_bond(
            self.issuer, escrow_contract.address, personal_info_contract["address"], token_list_contract
        )
        self.listing_token(token["address"], session)

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetStraightBond", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        bond_transfer_to_exchange(self.user1, {"address": escrow_contract.address}, token, 10000)

        block_number = web3.eth.block_number
        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, block_number)
        session.add(target_token_holders_list)
        session.commit()

        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()
        _records: List[TokenHolder] = (
            session.query(TokenHolder).filter(TokenHolder.holder_list == target_token_holders_list.id).all()
        )
        assert len(_records) == 0

    # <Error_4>
    # Failed to get Logs because of blockchain(ServiceUnavailable).
    def test_error_4(self, processor: Processor, shared_contract, session: Session, caplog, block_number: None):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issuer issues bond token.
        token = self.issue_token_bond(
            self.issuer, escrow_contract.address, personal_info_contract["address"], token_list_contract
        )
        self.listing_token(token["address"], session)

        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetStraightBond", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        bond_transfer_to_exchange(self.user1, {"address": escrow_contract.address}, token, 10000)

        block_number = web3.eth.block_number
        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, block_number)
        session.add(target_token_holders_list)
        session.commit()

        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]), \
                mock.patch("web3.eth.Eth.get_code", side_effect=ServiceUnavailable()), \
                pytest.raises(ServiceUnavailable):
            processor.collect()

        _records: List[TokenHolder] = (
            session.query(TokenHolder).filter(TokenHolder.holder_list == target_token_holders_list.id).all()
        )
        assert len(_records) == 0

        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        bond_transfer_to_exchange(self.user1, {"address": escrow_contract.address}, token, 10000)

        block_number = web3.eth.block_number
        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, block_number)
        session.add(target_token_holders_list)
        session.commit()

        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]), \
                mock.patch("web3.eth.Eth.get_code", side_effect=ServiceUnavailable()), \
                pytest.raises(ServiceUnavailable):
            processor.collect()

        session.rollback()
        _records: List[TokenHolder] = (
            session.query(TokenHolder).filter(TokenHolder.holder_list == target_token_holders_list.id).all()
        )
        assert len(_records) == 0
