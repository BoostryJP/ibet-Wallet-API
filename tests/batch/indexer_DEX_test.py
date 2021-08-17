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
    IDXOrder,
    IDXAgreement,
    AgreementStatus,
    Listing
)
from tests.conftest import ibet_exchange_contract
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
    share_transfer_to_exchange,
    make_sell,
    take_buy,
    make_buy,
    take_sell,
    cancel_order,
    confirm_agreement,
    cancel_agreement
)
from tests.utils import PersonalInfoUtils
from batch import indexer_DEX

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="function")
def processor_factory(session, shared_contract):
    def _processor(bond=False, membership=False, coupon=False, share=False):

        # Create exchange contract for each test method.
        exchange_address = {
            "bond": None,
            "membership": None,
            "coupon": None,
            "share": None,
        }
        indexer_DEX.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = None
        indexer_DEX.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = None
        indexer_DEX.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = None
        indexer_DEX.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = None
        if bond is True:
            bond_exchange = ibet_exchange_contract(shared_contract["PaymentGateway"]["address"])
            indexer_DEX.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = bond_exchange["address"]
            exchange_address["bond"] = bond_exchange["address"]
        if membership is True:
            membership_exchange = ibet_exchange_contract(shared_contract["PaymentGateway"]["address"])
            indexer_DEX.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = membership_exchange["address"]
            exchange_address["membership"] = membership_exchange["address"]
        if coupon is True:
            coupon_exchange = ibet_exchange_contract(shared_contract["PaymentGateway"]["address"])
            indexer_DEX.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = coupon_exchange["address"]
            exchange_address["coupon"] = coupon_exchange["address"]
        if share is True:
            share_exchange = ibet_exchange_contract(shared_contract["PaymentGateway"]["address"])
            indexer_DEX.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = share_exchange["address"]
            exchange_address["share"] = share_exchange["address"]
        _sink = indexer_DEX.Sinks()
        _sink.register(indexer_DEX.DBSink(session))
        processor = indexer_DEX.Processor(_sink, session)
        processor.initial_sync()
        return processor, exchange_address

    return _processor


class TestProcessor:
    issuer = eth_account["issuer"]
    agent = eth_account["agent"]
    trader = eth_account["trader"]

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
    def issue_token_membership(issuer, exchange_contract_address, token_list):
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

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # StraightBondExchange
    # - Create Order
    def test_normal_1(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(bond=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["bond"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = self.issue_token_bond(
            self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)
        self.listing_token(token["address"], session)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)
        block_number = web3.eth.blockNumber

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 1
        block = web3.eth.getBlock(block_number)
        _order = _order_list[0]
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is False
        assert _order.price == 100
        assert _order.amount == 1000000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is False
        assert _order.order_timestamp is not None
        _agreement_list = session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        assert len(_agreement_list) == 0

    # <Normal_2>
    # StraightBondExchange
    # - Create Order
    # - Cancel Order
    def test_normal_2(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(bond=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["bond"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = self.issue_token_bond(
            self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)
        self.listing_token(token["address"], session)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)
        block_number = web3.eth.blockNumber

        # Cancel Order
        cancel_order(self.issuer, {"address": exchange_contract_address}, 1)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 1
        block = web3.eth.getBlock(block_number)
        _order = _order_list[0]
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is False
        assert _order.price == 100
        assert _order.amount == 1000000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is True
        assert _order.order_timestamp is not None
        _agreement_list = session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        assert len(_agreement_list) == 0

    # <Normal_3>
    # StraightBondExchange
    # - Create Order
    # - Order Agreement(Take buy)
    def test_normal_3(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(bond=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["bond"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = self.issue_token_bond(
            self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)
        self.listing_token(token["address"], session)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)
        block_number = web3.eth.blockNumber

        # Order Agreement(Take buy)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 2000)
        block_number2 = web3.eth.blockNumber

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 1
        block = web3.eth.getBlock(block_number)
        _order = _order_list[0]
        assert _order.id == 1
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is False
        assert _order.price == 100
        assert _order.amount == 1000000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is False
        assert _order.order_timestamp is not None
        _agreement_list = session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        assert len(_agreement_list) == 1
        block2 = web3.eth.getBlock(block_number2)
        _agreement = _agreement_list[0]
        assert _agreement.transaction_hash == block2["transactions"][0].hex()
        assert _agreement.exchange_address == exchange_contract_address
        assert _agreement.order_id == 1
        assert _agreement.agreement_id == 1
        assert _agreement.unique_order_id == f"{exchange_contract_address}_1"
        assert _agreement.buyer_address == self.trader["account_address"]
        assert _agreement.seller_address == self.issuer["account_address"]
        assert _agreement.counterpart_address == self.trader["account_address"]
        assert _agreement.amount == 2000
        assert _agreement.status == AgreementStatus.PENDING.value
        assert _agreement.agreement_timestamp is not None
        assert _agreement.settlement_timestamp is None

    # <Normal_4>
    # StraightBondExchange
    # - Create Order
    # - Order Agreement(Take sell)
    def test_normal_4(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(bond=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["bond"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = self.issue_token_bond(
            self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)
        self.listing_token(token["address"], session)

        PersonalInfoUtils.register(
            self.trader["account_address"], personal_info_contract_address, self.issuer["account_address"])
        bond_transfer_to_exchange(self.issuer, {"address": self.trader["account_address"]}, token, 3000)

        # Create Order
        make_buy(self.issuer, {"address": exchange_contract_address}, token, 4000, 100)
        block_number = web3.eth.blockNumber

        # Order Agreement(Take sell)
        bond_transfer_to_exchange(self.trader, {"address": exchange_contract_address}, token, 3000)
        take_sell(self.trader, {"address": exchange_contract_address}, 1, 3000)
        block_number2 = web3.eth.blockNumber

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 1
        block = web3.eth.getBlock(block_number)
        _order = _order_list[0]
        assert _order.id == 1
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is True
        assert _order.price == 100
        assert _order.amount == 4000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is False
        assert _order.order_timestamp is not None
        _agreement_list = session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        assert len(_agreement_list) == 1
        block2 = web3.eth.getBlock(block_number2)
        _agreement = _agreement_list[0]
        assert _agreement.transaction_hash == block2["transactions"][0].hex()
        assert _agreement.exchange_address == exchange_contract_address
        assert _agreement.order_id == 1
        assert _agreement.agreement_id == 1
        assert _agreement.unique_order_id == f"{exchange_contract_address}_1"
        assert _agreement.buyer_address == self.issuer["account_address"]
        assert _agreement.seller_address == self.trader["account_address"]
        assert _agreement.counterpart_address == self.trader["account_address"]
        assert _agreement.amount == 3000
        assert _agreement.status == AgreementStatus.PENDING.value
        assert _agreement.agreement_timestamp is not None
        assert _agreement.settlement_timestamp is None

    # <Normal_5>
    # StraightBondExchange
    # - Create Order
    # - Order Agreement
    # - Confirm Agreement
    def test_normal_5(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(bond=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["bond"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = self.issue_token_bond(
            self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)
        self.listing_token(token["address"], session)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)
        block_number = web3.eth.blockNumber

        # Order Agreement(Take buy)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 2000)
        block_number2 = web3.eth.blockNumber

        # Confirm Agreement
        confirm_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)
        block_number3 = web3.eth.blockNumber

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 1
        block = web3.eth.getBlock(block_number)
        _order = _order_list[0]
        assert _order.id == 1
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is False
        assert _order.price == 100
        assert _order.amount == 1000000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is False
        assert _order.order_timestamp is not None
        _agreement_list = session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        assert len(_agreement_list) == 1
        block2 = web3.eth.getBlock(block_number2)
        block3 = web3.eth.getBlock(block_number3)
        _agreement = _agreement_list[0]
        assert _agreement.transaction_hash == block2["transactions"][0].hex()
        assert _agreement.exchange_address == exchange_contract_address
        assert _agreement.order_id == 1
        assert _agreement.agreement_id == 1
        assert _agreement.unique_order_id == f"{exchange_contract_address}_1"
        assert _agreement.buyer_address == self.trader["account_address"]
        assert _agreement.seller_address == self.issuer["account_address"]
        assert _agreement.counterpart_address == self.trader["account_address"]
        assert _agreement.amount == 2000
        assert _agreement.status == AgreementStatus.DONE.value
        assert _agreement.agreement_timestamp is not None
        assert _agreement.settlement_timestamp is not None

    # <Normal_6>
    # StraightBondExchange
    # - Create Order
    # - Order Agreement
    # - Cancel Agreement
    def test_normal_6(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(bond=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["bond"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = self.issue_token_bond(
            self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)
        self.listing_token(token["address"], session)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)
        block_number = web3.eth.blockNumber

        # Order Agreement(Take buy)
        take_buy(self.trader, {"address": exchange_contract_address}, 1, 2000)
        block_number2 = web3.eth.blockNumber

        # Cancel Agreement
        cancel_agreement(self.agent, {"address": exchange_contract_address}, 1, 1)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 1
        block = web3.eth.getBlock(block_number)
        _order = _order_list[0]
        assert _order.id == 1
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is False
        assert _order.price == 100
        assert _order.amount == 1000000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is False
        assert _order.order_timestamp is not None
        _agreement_list = session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        assert len(_agreement_list) == 1
        block2 = web3.eth.getBlock(block_number2)
        _agreement = _agreement_list[0]
        assert _agreement.transaction_hash == block2["transactions"][0].hex()
        assert _agreement.exchange_address == exchange_contract_address
        assert _agreement.order_id == 1
        assert _agreement.agreement_id == 1
        assert _agreement.unique_order_id == f"{exchange_contract_address}_1"
        assert _agreement.buyer_address == self.trader["account_address"]
        assert _agreement.seller_address == self.issuer["account_address"]
        assert _agreement.counterpart_address == self.trader["account_address"]
        assert _agreement.amount == 2000
        assert _agreement.status == AgreementStatus.CANCELED.value
        assert _agreement.agreement_timestamp is not None
        assert _agreement.settlement_timestamp is None

    # <Normal_7>
    # MembershipExchange, CouponExchange, ShareExchange
    # - Create Order
    # - Order Agreement
    # - Confirm Agreement
    def test_normal_7(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(membership=True, coupon=True, share=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        membership_exchange_contract_address = exchange_address["membership"]
        coupon_exchange_contract_address = exchange_address["coupon"]
        share_exchange_contract_address = exchange_address["share"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        membership_token = self.issue_token_membership(
            self.issuer, membership_exchange_contract_address, token_list_contract)
        self.listing_token(membership_token["address"], session)
        coupon_token = self.issue_token_coupon(
            self.issuer, coupon_exchange_contract_address, token_list_contract)
        self.listing_token(coupon_token["address"], session)
        share_token = self.issue_token_share(
            self.issuer, share_exchange_contract_address, personal_info_contract_address, token_list_contract)
        self.listing_token(share_token["address"], session)

        # Create Order
        membership_transfer_to_exchange(
            self.issuer, {"address": membership_exchange_contract_address}, membership_token, 900000)
        make_sell(self.issuer, {"address": membership_exchange_contract_address}, membership_token, 900000, 100)
        membership_block_number = web3.eth.blockNumber
        transfer_coupon_token(
            self.issuer, coupon_token, coupon_exchange_contract_address, 800000)
        make_sell(self.issuer, {"address": coupon_exchange_contract_address}, coupon_token, 800000, 200)
        coupon_block_number = web3.eth.blockNumber
        share_transfer_to_exchange(
            self.issuer, {"address": share_exchange_contract_address}, share_token, 700000)
        make_sell(self.issuer, {"address": share_exchange_contract_address}, share_token, 700000, 300)
        share_block_number = web3.eth.blockNumber

        # Order Agreement(Take buy)
        take_buy(self.trader, {"address": membership_exchange_contract_address}, 1, 1000)
        membership_block_number2 = web3.eth.blockNumber
        take_buy(self.trader, {"address": coupon_exchange_contract_address}, 1, 2000)
        coupon_block_number2 = web3.eth.blockNumber
        take_buy(self.trader, {"address": share_exchange_contract_address}, 1, 3000)
        share_block_number2 = web3.eth.blockNumber

        # Confirm Agreement
        confirm_agreement(self.agent, {"address": membership_exchange_contract_address}, 1, 1)
        membership_block_number3 = web3.eth.blockNumber
        confirm_agreement(self.agent, {"address": coupon_exchange_contract_address}, 1, 1)
        coupon_block_number3 = web3.eth.blockNumber
        confirm_agreement(self.agent, {"address": share_exchange_contract_address}, 1, 1)
        share_block_number3 = web3.eth.blockNumber

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 3
        block = web3.eth.getBlock(membership_block_number)
        _order = _order_list[0]
        assert _order.id == 1
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == membership_token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{membership_exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is False
        assert _order.price == 100
        assert _order.amount == 900000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is False
        assert _order.order_timestamp is not None
        block = web3.eth.getBlock(coupon_block_number)
        _order = _order_list[1]
        assert _order.id == 2
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == coupon_token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{coupon_exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is False
        assert _order.price == 200
        assert _order.amount == 800000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is False
        assert _order.order_timestamp is not None
        block = web3.eth.getBlock(share_block_number)
        _order = _order_list[2]
        assert _order.id == 3
        assert _order.transaction_hash == block["transactions"][0].hex()
        assert _order.token_address == share_token["address"]
        assert _order.order_id == 1
        assert _order.unique_order_id == f"{share_exchange_contract_address}_1"
        assert _order.account_address == self.issuer["account_address"]
        assert _order.counterpart_address == ""
        assert _order.is_buy is False
        assert _order.price == 300
        assert _order.amount == 700000
        assert _order.agent_address == self.agent["account_address"]
        assert _order.is_cancelled is False
        assert _order.order_timestamp is not None
        _agreement_list = session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        assert len(_agreement_list) == 3
        block2 = web3.eth.getBlock(membership_block_number2)
        block3 = web3.eth.getBlock(membership_block_number3)
        _agreement = _agreement_list[0]
        assert _agreement.transaction_hash == block2["transactions"][0].hex()
        assert _agreement.exchange_address == membership_exchange_contract_address
        assert _agreement.order_id == 1
        assert _agreement.agreement_id == 1
        assert _agreement.unique_order_id == f"{membership_exchange_contract_address}_1"
        assert _agreement.buyer_address == self.trader["account_address"]
        assert _agreement.seller_address == self.issuer["account_address"]
        assert _agreement.counterpart_address == self.trader["account_address"]
        assert _agreement.amount == 1000
        assert _agreement.status == AgreementStatus.DONE.value
        assert _agreement.agreement_timestamp is not None
        assert _agreement.settlement_timestamp is not None
        block2 = web3.eth.getBlock(coupon_block_number2)
        block3 = web3.eth.getBlock(coupon_block_number3)
        _agreement = _agreement_list[1]
        assert _agreement.transaction_hash == block2["transactions"][0].hex()
        assert _agreement.exchange_address == coupon_exchange_contract_address
        assert _agreement.order_id == 1
        assert _agreement.agreement_id == 1
        assert _agreement.unique_order_id == f"{coupon_exchange_contract_address}_1"
        assert _agreement.buyer_address == self.trader["account_address"]
        assert _agreement.seller_address == self.issuer["account_address"]
        assert _agreement.counterpart_address == self.trader["account_address"]
        assert _agreement.amount == 2000
        assert _agreement.status == AgreementStatus.DONE.value
        assert _agreement.agreement_timestamp is not None
        assert _agreement.settlement_timestamp is not None
        block2 = web3.eth.getBlock(share_block_number2)
        block3 = web3.eth.getBlock(share_block_number3)
        _agreement = _agreement_list[2]
        assert _agreement.transaction_hash == block2["transactions"][0].hex()
        assert _agreement.exchange_address == share_exchange_contract_address
        assert _agreement.order_id == 1
        assert _agreement.agreement_id == 1
        assert _agreement.unique_order_id == f"{share_exchange_contract_address}_1"
        assert _agreement.buyer_address == self.trader["account_address"]
        assert _agreement.seller_address == self.issuer["account_address"]
        assert _agreement.counterpart_address == self.trader["account_address"]
        assert _agreement.amount == 3000
        assert _agreement.status == AgreementStatus.DONE.value
        assert _agreement.agreement_timestamp is not None
        assert _agreement.settlement_timestamp is not None

    # <Normal_8>
    # Not Listing Token
    def test_normal_8(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(bond=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["bond"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = self.issue_token_bond(
            self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 0
        _agreement_list = session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        assert len(_agreement_list) == 0

    # <Normal_9>
    # Unset Exchange Address
    def test_normal_9(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory()

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        membership_token = self.issue_token_membership(
            self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(membership_token["address"], session)
        coupon_token = self.issue_token_coupon(
            self.issuer, config.ZERO_ADDRESS, token_list_contract)
        self.listing_token(coupon_token["address"], session)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 0
        _agreement_list = session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        assert len(_agreement_list) == 0

    # <Normal_10>
    # Blockchain Not Proceed
    def test_normal_10(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory()

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 0
        _agreement_list = session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        assert len(_agreement_list) == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, processor_factory, shared_contract, session):
        processor, exchange_address = processor_factory(bond=True)

        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        exchange_contract_address = exchange_address["bond"]
        personal_info_contract_address = shared_contract["PersonalInfo"]["address"]
        token = self.issue_token_bond(
            self.issuer, exchange_contract_address, personal_info_contract_address, token_list_contract)
        self.listing_token(token["address"], session)

        # Create Order
        bond_transfer_to_exchange(self.issuer, {"address": exchange_contract_address}, token, 1000000)
        make_sell(self.issuer, {"address": exchange_contract_address}, token, 1000000, 100)

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _order_list = session.query(IDXOrder).order_by(IDXOrder.created).all()
        assert len(_order_list) == 0
        _agreement_list = session.query(IDXAgreement).order_by(IDXAgreement.created).all()
        assert len(_agreement_list) == 0
