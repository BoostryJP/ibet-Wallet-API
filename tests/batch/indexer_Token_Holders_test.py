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
from typing import Type, List
from unittest import mock
from unittest.mock import MagicMock
import pytest
from sqlalchemy.orm import Session

from web3 import Web3
from web3.middleware import geth_poa_middleware

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app import config
from app.config import ZERO_ADDRESS
from app.contracts import Contract
from app.model.db import Listing, IDXPosition
from app.model.db.tokenholders import TokenHoldersList, BatchStatus, TokenHolder
from batch import (
    indexer_Position_Bond,
    indexer_Position_Share,
    indexer_Position_Membership,
    indexer_Position_Coupon,
)
from batch.indexer_Token_Holders import LOG, Processor
from batch.indexer_Position_Bond import Processor as BondIndexer
from batch.indexer_Position_Share import Processor as ShareIndexer
from batch.indexer_Position_Membership import Processor as MembershipIndexer
from batch.indexer_Position_Coupon import Processor as CouponIndexer
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
    bond_lock,
    bond_unlock,
    bond_authorize_lock_address,
    bond_issue_from,
    share_set_transfer_approval_required,
    bond_redeem_from,
    bond_set_transfer_approval_required,
    share_authorize_lock_address,
    share_lock,
    share_unlock,
    share_issue_from,
    share_redeem_from,
    share_apply_for_transfer,
    share_cancel_transfer,
    share_approve_transfer,
    finish_token_escrow,
    create_token_escrow,
    get_latest_escrow_id,
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    return Processor


@pytest.fixture(scope="function")
def processor(test_module, session):
    processor = test_module()
    return processor


@pytest.fixture(scope="session")
def bond_validator_module(shared_contract):
    indexer_Position_Bond.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    return BondIndexer


@pytest.fixture(scope="function")
def bond_position_indexer(bond_validator_module, session):
    bond_validator = bond_validator_module()
    bond_validator.initial_sync()
    return bond_validator


@pytest.fixture(scope="session")
def share_validator_module(shared_contract):
    indexer_Position_Share.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    return ShareIndexer


@pytest.fixture(scope="function")
def share_position_indexer(share_validator_module: Type[ShareIndexer]):
    share_validator = share_validator_module()
    share_validator.initial_sync()
    return share_validator


@pytest.fixture(scope="session")
def membership_validator_module(shared_contract):
    indexer_Position_Membership.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    return MembershipIndexer


@pytest.fixture(scope="function")
def membership_position_indexer(membership_validator_module: Type[MembershipIndexer]):
    membership_validator = membership_validator_module()
    membership_validator.initial_sync()
    return membership_validator


@pytest.fixture(scope="session")
def coupon_validator_module(shared_contract):
    indexer_Position_Coupon.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    return CouponIndexer


@pytest.fixture(scope="function")
def coupon_position_indexer(coupon_validator_module: Type[CouponIndexer]):
    coupon_validator = coupon_validator_module()
    coupon_validator.initial_sync()
    return coupon_validator


class TestProcessor:
    issuer = eth_account["issuer"]
    user1 = eth_account["user1"]
    user2 = eth_account["user2"]
    trader = eth_account["trader"]
    agent = eth_account["agent"]

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
    def token_holders_list(token, block_number) -> TokenHoldersList:
        target_token_holders_list = TokenHoldersList()
        target_token_holders_list.list_id = str(uuid.uuid4())
        target_token_holders_list.token_address = token["address"]
        target_token_holders_list.batch_status = BatchStatus.PENDING.value
        target_token_holders_list.block_number = block_number
        return target_token_holders_list

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # StraightBond
    # Events
    # - Transfer
    # - Lock
    # - Unlock
    # - Exchange
    #   - MakeOrder
    #   - CancelOrder
    #   - ForceCancelOrder
    #   - TakeOrder
    #   - CancelAgreement
    #   - ConfirmAgreement
    # - IssueFrom
    # - RedeemFrom
    def test_normal_1(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        bond_position_indexer: BondIndexer,
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

        bond_authorize_lock_address(self.issuer, token, self.user1["account_address"], True)
        bond_authorize_lock_address(self.issuer, token, self.trader["account_address"], True)
        bond_lock(self.user1, token, self.trader["account_address"], 10000)
        bond_unlock(self.trader, token, self.user1["account_address"], self.user1["account_address"], 5000)

        bond_transfer_to_exchange(self.user1, {"address": exchange_contract["address"]}, token, 10000)
        make_sell(self.user1, exchange_contract, token, 10000, 100)
        cancel_order(self.user1, exchange_contract, get_latest_orderid(exchange_contract))

        bond_transfer_to_exchange(self.user1, exchange_contract, token, 10000)
        make_sell(self.user1, exchange_contract, token, 10000, 100)
        force_cancel_order(self.agent, exchange_contract, get_latest_orderid(exchange_contract))

        bond_transfer_to_exchange(self.user1, exchange_contract, token, 10000)
        make_sell(self.user1, exchange_contract, token, 10000, 100)
        _latest_order_id = get_latest_orderid(exchange_contract)
        take_buy(self.trader, exchange_contract, _latest_order_id, 10000)
        confirm_agreement(
            self.agent, exchange_contract, _latest_order_id, get_latest_agreementid(exchange_contract, _latest_order_id)
        )

        bond_transfer_to_exchange(self.user1, exchange_contract, token, 4000)
        make_buy(self.trader, exchange_contract, token, 4000, 100)
        _latest_order_id = get_latest_orderid(exchange_contract)
        take_sell(self.user1, exchange_contract, _latest_order_id, 4000)
        cancel_agreement(
            self.agent, exchange_contract, _latest_order_id, get_latest_agreementid(exchange_contract, _latest_order_id)
        )

        bond_transfer_to_exchange(self.user1, exchange_contract, token, 4000)
        make_buy(self.trader, exchange_contract, token, 4000, 100)
        _latest_order_id = get_latest_orderid(exchange_contract)
        take_sell(self.user1, exchange_contract, _latest_order_id, 4000)
        confirm_agreement(
            self.agent, exchange_contract, _latest_order_id, get_latest_agreementid(exchange_contract, _latest_order_id)
        )

        bond_issue_from(self.issuer, token, self.issuer["account_address"], 40000)
        bond_redeem_from(self.issuer, token, self.trader["account_address"], 10000)

        bond_issue_from(self.issuer, token, self.trader["account_address"], 30000)
        bond_redeem_from(self.issuer, token, self.issuer["account_address"], 10000)

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.blockNumber)
        session.add(target_token_holders_list)
        session.commit()
        bond_position_indexer.sync_new_logs()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.exchange_balance == 0
        assert user1_record.balance == 1000
        assert user1_record.exchange_commitment == 0
        assert user1_record.pending_transfer == 0

        assert trader_record.exchange_balance == 0
        assert trader_record.balance == 44000
        assert trader_record.exchange_commitment == 0
        assert trader_record.pending_transfer == 0

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list_id == target_token_holders_list.id))) == 2

        _user1_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == user1_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )
        _trader_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == trader_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )

        assert user1_record.balance == _user1_record_validator.balance
        assert user1_record.pending_transfer == _user1_record_validator.pending_transfer
        assert user1_record.exchange_balance == _user1_record_validator.exchange_balance
        assert user1_record.exchange_commitment == _user1_record_validator.exchange_commitment

        assert trader_record.balance == _trader_record_validator.balance
        assert trader_record.pending_transfer == _trader_record_validator.pending_transfer
        assert trader_record.exchange_balance == _trader_record_validator.exchange_balance
        assert trader_record.exchange_commitment == _trader_record_validator.exchange_commitment

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
    def test_normal_2(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        bond_position_indexer: BondIndexer,
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

        # Issuer transfers issued token to user1 and trader.
        bond_set_transfer_approval_required(self.issuer, token, True)
        bond_apply_for_transfer(self.issuer, token, self.user1, 10000, "to user1#1")
        bond_apply_for_transfer(self.issuer, token, self.trader, 10000, "to trader#1")

        bond_cancel_transfer(self.issuer, token, 0, "to user1#1")
        bond_approve_transfer(self.issuer, token, 1, "to trader#1")

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

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.blockNumber)
        session.add(target_token_holders_list)
        session.commit()

        bond_position_indexer.sync_new_logs()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        bond_set_transfer_approval_required(self.issuer, token, False)
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        processor.collect()
        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.exchange_balance == 1000
        assert user1_record.balance == 10000  # 20000
        assert user1_record.exchange_commitment == 2000
        assert user1_record.pending_transfer == 0

        assert trader_record.exchange_balance == 7000
        assert trader_record.balance == 10000
        assert trader_record.exchange_commitment == 0
        assert trader_record.pending_transfer == 0

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list_id == target_token_holders_list.id))) == 2

        _user1_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == user1_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )
        _trader_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == trader_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )

        assert user1_record.balance == _user1_record_validator.balance
        assert user1_record.pending_transfer == _user1_record_validator.pending_transfer
        assert user1_record.exchange_balance == _user1_record_validator.exchange_balance
        assert user1_record.exchange_commitment == _user1_record_validator.exchange_commitment

        assert trader_record.balance == _trader_record_validator.balance
        assert trader_record.pending_transfer == _trader_record_validator.pending_transfer
        assert trader_record.exchange_balance == _trader_record_validator.exchange_balance
        assert trader_record.exchange_commitment == _trader_record_validator.exchange_commitment

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
        bond_position_indexer: BondIndexer,
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

        bond_set_transfer_approval_required(self.issuer, token, True)
        bond_apply_for_transfer(self.user1, token, self.trader, 10000, "to user1#1")

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

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.blockNumber)
        session.add(target_token_holders_list)
        session.commit()

        bond_position_indexer.sync_new_logs()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        bond_set_transfer_approval_required(self.issuer, token, False)
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.exchange_balance == 0
        assert user1_record.balance == 0
        assert user1_record.exchange_commitment == 7000
        assert user1_record.pending_transfer == 10000

        assert trader_record.exchange_balance == 3000
        assert trader_record.balance == 10000
        assert trader_record.exchange_commitment == 0
        assert trader_record.pending_transfer == 0

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list_id == target_token_holders_list.id))) == 2

        _user1_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == user1_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )
        _trader_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == trader_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )

        assert user1_record.balance == _user1_record_validator.balance
        assert user1_record.pending_transfer == _user1_record_validator.pending_transfer
        assert user1_record.exchange_balance == _user1_record_validator.exchange_balance
        assert user1_record.exchange_commitment == _user1_record_validator.exchange_commitment

        assert trader_record.balance == _trader_record_validator.balance
        assert trader_record.pending_transfer == _trader_record_validator.pending_transfer
        assert trader_record.exchange_balance == _trader_record_validator.exchange_balance
        assert trader_record.exchange_commitment == _trader_record_validator.exchange_commitment

    # <Normal_4>
    # Share
    # Events
    # - Transfer
    # - Lock
    # - Unlock
    # - Exchange
    #   - MakeOrder
    #   - CancelOrder
    #   - ForceCancelOrder
    #   - TakeOrder
    #   - CancelAgreement
    #   - ConfirmAgreement
    # - IssueFrom
    # - RedeemFrom
    def test_normal_4(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        share_position_indexer: ShareIndexer,
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

        share_authorize_lock_address(self.issuer, token, self.user1["account_address"], True)
        share_authorize_lock_address(self.issuer, token, self.trader["account_address"], True)
        share_lock(self.user1, token, self.trader["account_address"], 10000)
        share_unlock(self.trader, token, self.user1["account_address"], self.user1["account_address"], 5000)

        share_transfer_to_exchange(self.user1, {"address": exchange["address"]}, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        cancel_order(self.user1, exchange, get_latest_orderid(exchange))
        share_transfer_to_exchange(self.user1, exchange, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        force_cancel_order(self.agent, exchange, get_latest_orderid(exchange))
        share_transfer_to_exchange(self.user1, exchange, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        _latest_order_id = get_latest_orderid(exchange)
        take_buy(self.trader, exchange, _latest_order_id, 10000)
        confirm_agreement(self.agent, exchange, _latest_order_id, get_latest_agreementid(exchange, _latest_order_id))

        share_issue_from(self.issuer, token, self.issuer["account_address"], 40000)
        share_redeem_from(self.issuer, token, self.trader["account_address"], 10000)

        share_issue_from(self.issuer, token, self.trader["account_address"], 30000)
        share_redeem_from(self.issuer, token, self.issuer["account_address"], 10000)

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.blockNumber)
        session.add(target_token_holders_list)
        session.commit()
        share_position_indexer.sync_new_logs()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.exchange_balance == 0
        assert user1_record.balance == 5000
        assert user1_record.exchange_commitment == 0
        assert user1_record.pending_transfer == 0

        assert trader_record.exchange_balance == 0
        assert trader_record.balance == 40000
        assert trader_record.exchange_commitment == 0
        assert trader_record.pending_transfer == 0

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list_id == target_token_holders_list.id))) == 2

        _user1_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == user1_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )
        _trader_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == trader_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )

        assert user1_record.balance == _user1_record_validator.balance
        assert user1_record.pending_transfer == _user1_record_validator.pending_transfer
        assert user1_record.exchange_balance == _user1_record_validator.exchange_balance
        assert user1_record.exchange_commitment == _user1_record_validator.exchange_commitment

        assert trader_record.balance == _trader_record_validator.balance
        assert trader_record.pending_transfer == _trader_record_validator.pending_transfer
        assert trader_record.exchange_balance == _trader_record_validator.exchange_balance
        assert trader_record.exchange_commitment == _trader_record_validator.exchange_commitment

    # <Normal 5>
    # Share
    # Events
    # - Transfer
    # - Lock
    # - Unlock
    # - Exchange
    #   - MakeOrder
    #   - CancelOrder
    #   - ForceCancelOrder
    #   - TakeOrder
    #   - CancelAgreement
    #   - ConfirmAgreement
    # - IssueFrom
    # - RedeemFrom
    def test_normal_5(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        share_position_indexer: ShareIndexer,
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

        # Issuer transfers issued token to user1 and trader.
        share_set_transfer_approval_required(self.issuer, token, True)
        share_apply_for_transfer(self.issuer, token, self.user1, 10000, "to user1#1")
        share_apply_for_transfer(self.issuer, token, self.trader, 10000, "to trader#1")

        share_cancel_transfer(self.issuer, token, 0, "to user1#1")
        share_approve_transfer(self.issuer, token, 1, "to trader#1")

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

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.blockNumber)
        session.add(target_token_holders_list)
        session.commit()

        share_position_indexer.sync_new_logs()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        share_set_transfer_approval_required(self.issuer, token, False)
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.exchange_balance == 1000
        assert user1_record.balance == 10000  # 20000
        assert user1_record.exchange_commitment == 2000
        assert user1_record.pending_transfer == 0

        assert trader_record.exchange_balance == 7000
        assert trader_record.balance == 10000
        assert trader_record.exchange_commitment == 0
        assert trader_record.pending_transfer == 0

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list_id == target_token_holders_list.id))) == 2

        _user1_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == user1_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )
        _trader_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == trader_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )

        assert user1_record.balance == _user1_record_validator.balance
        assert user1_record.pending_transfer == _user1_record_validator.pending_transfer
        assert user1_record.exchange_balance == _user1_record_validator.exchange_balance
        assert user1_record.exchange_commitment == _user1_record_validator.exchange_commitment

        assert trader_record.balance == _trader_record_validator.balance
        assert trader_record.pending_transfer == _trader_record_validator.pending_transfer
        assert trader_record.exchange_balance == _trader_record_validator.exchange_balance
        assert trader_record.exchange_commitment == _trader_record_validator.exchange_commitment

    # <Normal_6>
    # StraightBond
    # Events
    # - ApplyForTransfer - pending
    # - Escrow - pending
    def test_normal_6(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        share_position_indexer: ShareIndexer,
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

        share_set_transfer_approval_required(self.issuer, token, True)
        share_apply_for_transfer(self.user1, token, self.trader, 10000, "to user1#1")

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

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.blockNumber)
        session.add(target_token_holders_list)
        session.commit()

        share_position_indexer.sync_new_logs()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        share_set_transfer_approval_required(self.issuer, token, False)
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.exchange_balance == 0
        assert user1_record.balance == 0
        assert user1_record.exchange_commitment == 7000
        assert user1_record.pending_transfer == 10000

        assert trader_record.exchange_balance == 3000
        assert trader_record.balance == 10000
        assert trader_record.exchange_commitment == 0
        assert trader_record.pending_transfer == 0

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list_id == target_token_holders_list.id))) == 2

        _user1_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == user1_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )
        _trader_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == trader_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )

        assert user1_record.balance == _user1_record_validator.balance
        assert user1_record.exchange_balance == _user1_record_validator.exchange_balance
        assert user1_record.exchange_commitment == _user1_record_validator.exchange_commitment

        assert trader_record.balance == _trader_record_validator.balance
        assert trader_record.exchange_balance == _trader_record_validator.exchange_balance
        assert trader_record.exchange_commitment == _trader_record_validator.exchange_commitment

    # <Normal_7>
    # Coupon
    # Events
    # - Transfer
    # - Exchange
    #   - MakeOrder
    #   - CancelOrder
    #   - ForceCancelOrder
    #   - TakeOrder
    #   - CancelAgreement
    #   - ConfirmAgreement
    def test_normal_7(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        coupon_position_indexer: CouponIndexer,
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

        coupon_transfer_to_exchange(self.user1, {"address": exchange["address"]}, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        cancel_order(self.user1, exchange, get_latest_orderid(exchange))
        coupon_transfer_to_exchange(self.user1, exchange, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        force_cancel_order(self.agent, exchange, get_latest_orderid(exchange))
        coupon_transfer_to_exchange(self.user1, exchange, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        _latest_order_id = get_latest_orderid(exchange)
        take_buy(self.trader, exchange, _latest_order_id, 10000)
        confirm_agreement(self.agent, exchange, _latest_order_id, get_latest_agreementid(exchange, _latest_order_id))

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.blockNumber)
        session.add(target_token_holders_list)
        session.commit()
        coupon_position_indexer.sync_new_logs()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.exchange_balance == 0
        assert user1_record.balance == 10000
        assert user1_record.exchange_commitment == 0
        assert user1_record.pending_transfer == 0

        assert trader_record.exchange_balance == 0
        assert trader_record.balance == 20000
        assert trader_record.exchange_commitment == 0
        assert trader_record.pending_transfer == 0

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list_id == target_token_holders_list.id))) == 2

        _user1_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == user1_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )
        _trader_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == trader_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )

        assert user1_record.balance == _user1_record_validator.balance
        assert user1_record.exchange_balance == _user1_record_validator.exchange_balance
        assert user1_record.exchange_commitment == _user1_record_validator.exchange_commitment

        assert trader_record.balance == _trader_record_validator.balance
        assert trader_record.exchange_balance == _trader_record_validator.exchange_balance
        assert trader_record.exchange_commitment == _trader_record_validator.exchange_commitment

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
        coupon_position_indexer: CouponIndexer,
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

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.blockNumber)
        session.add(target_token_holders_list)
        session.commit()

        coupon_position_indexer.sync_new_logs()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.exchange_balance == 1000
        assert user1_record.balance == 10000
        assert user1_record.exchange_commitment == 0
        assert user1_record.pending_transfer == 0

        assert trader_record.exchange_balance == 9000
        assert trader_record.balance == 0
        assert trader_record.exchange_commitment == 0
        assert trader_record.pending_transfer == 0

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list_id == target_token_holders_list.id))) == 2

        _user1_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == user1_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )
        _trader_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == trader_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )

        assert user1_record.balance == _user1_record_validator.balance
        assert user1_record.exchange_balance == _user1_record_validator.exchange_balance
        assert user1_record.exchange_commitment == _user1_record_validator.exchange_commitment

        assert trader_record.balance == _trader_record_validator.balance
        assert trader_record.exchange_balance == _trader_record_validator.exchange_balance
        assert trader_record.exchange_commitment == _trader_record_validator.exchange_commitment

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
        coupon_position_indexer: CouponIndexer,
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

        consume_coupon_token(self.trader, token, 9000)
        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.blockNumber)
        session.add(target_token_holders_list)
        session.commit()

        coupon_position_indexer.sync_new_logs()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.exchange_balance == 0
        assert user1_record.balance == 0
        assert user1_record.exchange_commitment == 7000
        assert user1_record.pending_transfer == 0

        assert trader_record.exchange_balance == 3000
        assert trader_record.balance == 1000
        assert trader_record.exchange_commitment == 0
        assert trader_record.pending_transfer == 0

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list_id == target_token_holders_list.id))) == 2

        _user1_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == user1_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )
        _trader_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == trader_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )

        assert user1_record.balance == _user1_record_validator.balance
        assert user1_record.exchange_balance == _user1_record_validator.exchange_balance
        assert user1_record.exchange_commitment == _user1_record_validator.exchange_commitment

        assert trader_record.balance == _trader_record_validator.balance
        assert trader_record.exchange_balance == _trader_record_validator.exchange_balance
        assert trader_record.exchange_commitment == _trader_record_validator.exchange_commitment

    # <Normal_10>
    # Membership
    # Events
    # - Transfer
    # - Exchange
    #   - MakeOrder
    #   - CancelOrder
    #   - ForceCancelOrder
    #   - TakeOrder
    #   - CancelAgreement
    #   - ConfirmAgreement
    def test_normal_10(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        membership_position_indexer: MembershipIndexer,
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

        membership_transfer_to_exchange(self.user1, {"address": exchange["address"]}, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        cancel_order(self.user1, exchange, get_latest_orderid(exchange))
        membership_transfer_to_exchange(self.user1, exchange, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        force_cancel_order(self.agent, exchange, get_latest_orderid(exchange))
        membership_transfer_to_exchange(self.user1, exchange, token, 10000)
        make_sell(self.user1, exchange, token, 10000, 100)
        _latest_order_id = get_latest_orderid(exchange)
        take_buy(self.trader, exchange, _latest_order_id, 10000)
        confirm_agreement(self.agent, exchange, _latest_order_id, get_latest_agreementid(exchange, _latest_order_id))

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.blockNumber)
        session.add(target_token_holders_list)
        session.commit()
        membership_position_indexer.sync_new_logs()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        processor.collect()

        issuer_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.issuer["account_address"])
            .first()
        )
        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.exchange_balance == 0
        assert user1_record.balance == 10000
        assert user1_record.exchange_commitment == 0
        assert user1_record.pending_transfer == 0

        assert trader_record.exchange_balance == 0
        assert trader_record.balance == 20000
        assert trader_record.exchange_commitment == 0
        assert trader_record.pending_transfer == 0

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list_id == target_token_holders_list.id))) == 2

        _user1_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == user1_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )
        _trader_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == trader_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )

        assert user1_record.balance == _user1_record_validator.balance
        assert user1_record.exchange_balance == _user1_record_validator.exchange_balance
        assert user1_record.exchange_commitment == _user1_record_validator.exchange_commitment

        assert trader_record.balance == _trader_record_validator.balance
        assert trader_record.exchange_balance == _trader_record_validator.exchange_balance
        assert trader_record.exchange_commitment == _trader_record_validator.exchange_commitment

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
        membership_position_indexer: MembershipIndexer,
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

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.blockNumber)
        session.add(target_token_holders_list)
        session.commit()

        membership_position_indexer.sync_new_logs()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.exchange_balance == 1000
        assert user1_record.balance == 10000
        assert user1_record.exchange_commitment == 0
        assert user1_record.pending_transfer == 0

        assert trader_record.exchange_balance == 9000
        assert trader_record.balance == 0
        assert trader_record.exchange_commitment == 0
        assert trader_record.pending_transfer == 0

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list_id == target_token_holders_list.id))) == 2

        _user1_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == user1_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )
        _trader_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == trader_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )

        assert user1_record.balance == _user1_record_validator.balance
        assert user1_record.exchange_balance == _user1_record_validator.exchange_balance
        assert user1_record.exchange_commitment == _user1_record_validator.exchange_commitment

        assert trader_record.balance == _trader_record_validator.balance
        assert trader_record.exchange_balance == _trader_record_validator.exchange_balance
        assert trader_record.exchange_commitment == _trader_record_validator.exchange_commitment

    # <Normal_12>
    # Membership
    # Events
    # - Escrow - pending
    def test_normal_12(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        membership_position_indexer: MembershipIndexer,
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

        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, web3.eth.blockNumber)
        session.add(target_token_holders_list)
        session.commit()

        membership_position_indexer.sync_new_logs()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)

        # Then execute processor.
        processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        assert user1_record.exchange_balance == 0
        assert user1_record.balance == 0
        assert user1_record.exchange_commitment == 7000
        assert user1_record.pending_transfer == 0

        assert trader_record.exchange_balance == 3000
        assert trader_record.balance == 10000
        assert trader_record.exchange_commitment == 0
        assert trader_record.pending_transfer == 0

        assert len(list(session.query(TokenHolder).filter(TokenHolder.holder_list_id == target_token_holders_list.id))) == 2

        _user1_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == user1_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )
        _trader_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == trader_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )

        assert user1_record.balance == _user1_record_validator.balance
        assert user1_record.exchange_balance == _user1_record_validator.exchange_balance
        assert user1_record.exchange_commitment == _user1_record_validator.exchange_commitment

        assert trader_record.balance == _trader_record_validator.balance
        assert trader_record.exchange_balance == _trader_record_validator.exchange_balance
        assert trader_record.exchange_commitment == _trader_record_validator.exchange_commitment

    # <Normal_13>
    # StraightBond
    # Use checkpoint.
    def test_normal_13(
        self,
        processor: Processor,
        shared_contract,
        session: Session,
        bond_position_indexer: BondIndexer,
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

        bond_authorize_lock_address(self.issuer, token, self.user1["account_address"], True)
        bond_authorize_lock_address(self.issuer, token, self.trader["account_address"], True)
        bond_lock(self.user1, token, self.trader["account_address"], 10000)
        bond_unlock(self.trader, token, self.user1["account_address"], self.user1["account_address"], 5000)
        target_token_holders_list1 = self.token_holders_list(token, web3.eth.blockNumber)
        session.add(target_token_holders_list1)
        session.commit()
        bond_position_indexer.sync_new_logs()
        processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list1.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list1.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        _user1_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == user1_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )
        _trader_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == trader_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )

        assert user1_record.balance == _user1_record_validator.balance
        assert user1_record.pending_transfer == _user1_record_validator.pending_transfer
        assert user1_record.exchange_balance == _user1_record_validator.exchange_balance
        assert user1_record.exchange_commitment == _user1_record_validator.exchange_commitment

        assert trader_record.balance == _trader_record_validator.balance
        assert trader_record.pending_transfer == _trader_record_validator.pending_transfer
        assert trader_record.exchange_balance == _trader_record_validator.exchange_balance
        assert trader_record.exchange_commitment == _trader_record_validator.exchange_commitment

        bond_transfer_to_exchange(self.user1, {"address": exchange_contract["address"]}, token, 10000)
        make_sell(self.user1, exchange_contract, token, 10000, 100)
        cancel_order(self.user1, exchange_contract, get_latest_orderid(exchange_contract))
        bond_transfer_to_exchange(self.user1, exchange_contract, token, 10000)
        make_sell(self.user1, exchange_contract, token, 10000, 100)
        force_cancel_order(self.agent, exchange_contract, get_latest_orderid(exchange_contract))

        bond_transfer_to_exchange(self.user1, exchange_contract, token, 10000)
        make_sell(self.user1, exchange_contract, token, 10000, 100)
        _latest_order_id = get_latest_orderid(exchange_contract)
        take_buy(self.trader, exchange_contract, _latest_order_id, 10000)
        confirm_agreement(
            self.agent, exchange_contract, _latest_order_id, get_latest_agreementid(exchange_contract, _latest_order_id)
        )
        target_token_holders_list2 = self.token_holders_list(token, web3.eth.blockNumber)

        session.add(target_token_holders_list2)
        session.commit()
        bond_position_indexer.sync_new_logs()
        processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list2.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list2.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        _user1_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == user1_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )
        _trader_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == trader_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )

        assert user1_record.balance == _user1_record_validator.balance
        assert user1_record.pending_transfer == _user1_record_validator.pending_transfer
        assert user1_record.exchange_balance == _user1_record_validator.exchange_balance
        assert user1_record.exchange_commitment == _user1_record_validator.exchange_commitment

        assert trader_record.balance == _trader_record_validator.balance
        assert trader_record.pending_transfer == _trader_record_validator.pending_transfer
        assert trader_record.exchange_balance == _trader_record_validator.exchange_balance
        assert trader_record.exchange_commitment == _trader_record_validator.exchange_commitment

        bond_transfer_to_exchange(self.user1, exchange_contract, token, 4000)
        make_buy(self.trader, exchange_contract, token, 4000, 100)
        _latest_order_id = get_latest_orderid(exchange_contract)
        take_sell(self.user1, exchange_contract, _latest_order_id, 4000)
        cancel_agreement(
            self.agent, exchange_contract, _latest_order_id, get_latest_agreementid(exchange_contract, _latest_order_id)
        )

        bond_transfer_to_exchange(self.user1, exchange_contract, token, 4000)
        make_buy(self.trader, exchange_contract, token, 4000, 100)
        _latest_order_id = get_latest_orderid(exchange_contract)
        take_sell(self.user1, exchange_contract, _latest_order_id, 4000)
        confirm_agreement(
            self.agent, exchange_contract, _latest_order_id, get_latest_agreementid(exchange_contract, _latest_order_id)
        )

        bond_issue_from(self.issuer, token, self.issuer["account_address"], 40000)
        bond_redeem_from(self.issuer, token, self.trader["account_address"], 10000)

        bond_issue_from(self.issuer, token, self.trader["account_address"], 30000)
        bond_redeem_from(self.issuer, token, self.issuer["account_address"], 10000)
        target_token_holders_list3 = self.token_holders_list(token, web3.eth.blockNumber)
        session.add(target_token_holders_list3)
        session.commit()
        bond_position_indexer.sync_new_logs()
        processor.collect()

        user1_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list3.id)
            .filter(TokenHolder.account_address == self.user1["account_address"])
            .first()
        )
        trader_record: TokenHolder = (
            session.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == target_token_holders_list3.id)
            .filter(TokenHolder.account_address == self.trader["account_address"])
            .first()
        )

        _user1_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == user1_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )
        _trader_record_validator: IDXPosition = (
            session.query(IDXPosition)
            .filter(IDXPosition.account_address == trader_record.account_address)
            .order_by(IDXPosition.created)
            .first()
        )

        assert user1_record.balance == _user1_record_validator.balance
        assert user1_record.pending_transfer == _user1_record_validator.pending_transfer
        assert user1_record.exchange_balance == _user1_record_validator.exchange_balance
        assert user1_record.exchange_commitment == _user1_record_validator.exchange_commitment

        assert trader_record.balance == _trader_record_validator.balance
        assert trader_record.pending_transfer == _trader_record_validator.pending_transfer
        assert trader_record.exchange_balance == _trader_record_validator.exchange_balance
        assert trader_record.exchange_commitment == _trader_record_validator.exchange_commitment

    # <Normal_14>
    # StraightBond
    # Jobs are queued and pending jobs are to be processed one by one.
    def test_normal_14(self, processor: Processor, shared_contract, session: Session, caplog, block_number: None):
        processor.collect()
        LOG.addHandler(caplog.handler)
        with caplog.at_level(logging.DEBUG):
            processor.collect()
            assert f"There are no pending collect batch" in caplog.text

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

        target_token_holders_list1 = self.token_holders_list(token, web3.eth.blockNumber)
        session.add(target_token_holders_list1)
        session.commit()
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        transfer_token(token_contract, self.issuer["account_address"], self.trader["account_address"], 10000)
        target_token_holders_list2 = self.token_holders_list(token, web3.eth.blockNumber)
        session.add(target_token_holders_list2)
        session.commit()

        processor.collect()
        LOG.addHandler(caplog.handler)
        with caplog.at_level(logging.INFO):
            processor.collect()
        assert f"Token holder list({target_token_holders_list2.list_id}) status changes to be done." in caplog.text
        assert f"Collect job has been completed" in caplog.text

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # There is no target token holders list id with batch_status PENDING.
    def test_error_1(self, processor: Processor, shared_contract, session: Session, caplog, block_number: None):
        LOG.addHandler(caplog.handler)
        with caplog.at_level(logging.DEBUG):
            processor.collect()
        assert "There are no pending collect batch" in caplog.text
        assert "Collect job has been completed" in caplog.text

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
        target_token_holders_list.batch_status = BatchStatus.PENDING.value
        target_token_holders_list.block_number = 1000
        session.add(target_token_holders_list)
        session.commit()

        # Debug message should be shown that points out token contract must be listed.
        LOG.addHandler(caplog.handler)
        with caplog.at_level(logging.DEBUG):
            processor.collect()
        assert "Token contract must be listed to TokenList contract." in caplog.text
        assert f"Collect job has been completed" in caplog.text

        # Batch status of token holders list expects to be "ERROR"
        error_record_num = len(
            list(session.query(TokenHoldersList).filter(TokenHoldersList.batch_status == BatchStatus.FAILED.value))
        )
        assert error_record_num == 1

    # <Error_3>
    # Failed to get Logs from blockchain.
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
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

        block_number = web3.eth.blockNumber
        # Insert collection record with above token and current block number
        target_token_holders_list = self.token_holders_list(token, block_number)
        session.add(target_token_holders_list)
        session.commit()

        mock_lib = MagicMock()
        with mock.patch.object(Processor, "_Processor__sync_all", return_value=mock_lib) as __sync_all_mock:
            # Then execute processor.
            __sync_all_mock.return_value = None
            processor.collect()
            _records: List[TokenHolder] = (
                session.query(TokenHolder).filter(TokenHolder.holder_list_id == target_token_holders_list.id).all()
            )
            assert len(_records) == 0
