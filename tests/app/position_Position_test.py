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

from unittest import mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from app.model.db import (
    IDXLockedPosition,
    IDXPosition,
    IDXTransfer,
    IDXTransferSourceEventType,
    Listing,
)
from tests.account_config import eth_account
from tests.app.position_PositionCoupon_test import TestPositionCoupon
from tests.app.position_PositionMembership_test import TestPositionMembership
from tests.app.position_PositionShare_test import TestPositionShare
from tests.app.position_PositionStraightBond_test import TestPositionStraightBond

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class TestPosition:
    # Test API
    apiurl = "/Position/{account_address}"

    issuer = eth_account["issuer"]
    account_1 = eth_account["deployer"]
    account_2 = eth_account["trader"]
    zero_address = {"address": config.ZERO_ADDRESS}

    @staticmethod
    def create_idx_position(
        session: Session,
        token_address: str,
        account_address: str,
        balance: int | None = None,
        pending_transfer: int | None = None,
        exchange_balance: int | None = None,
        exchange_commitment: int | None = None,
    ):
        if (
            not balance
            and not exchange_balance
            and not exchange_commitment
            and not pending_transfer
        ):
            return
        idx_position = IDXPosition()
        idx_position.token_address = token_address
        idx_position.account_address = account_address
        if balance:
            idx_position.balance = balance
        if pending_transfer:
            idx_position.pending_transfer = pending_transfer
        if exchange_balance:
            idx_position.exchange_balance = exchange_balance
        if exchange_commitment:
            idx_position.exchange_commitment = exchange_commitment
        session.merge(idx_position)
        session.commit()
        pass

    @staticmethod
    def create_idx_locked_position(
        session: Session,
        token_address: str,
        lock_address: str,
        account_address: str,
        value: int,
    ):
        # Issue token
        idx_locked = IDXLockedPosition()
        idx_locked.token_address = token_address
        idx_locked.lock_address = lock_address
        idx_locked.account_address = account_address
        idx_locked.value = value
        session.add(idx_locked)
        session.commit()

    @staticmethod
    def list_token(token_address, session):
        listed_token = Listing()
        listed_token.token_address = token_address
        listed_token.is_public = True
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
        session.add(listed_token)

    @staticmethod
    def expected_bond_token():
        return {
            "company_name": "",
            "contact_information": "問い合わせ先",
            "face_value": 10000,
            "interest_payment_date1": "0101",
            "interest_payment_date10": "1001",
            "interest_payment_date11": "1101",
            "interest_payment_date12": "1201",
            "interest_payment_date2": "0201",
            "interest_payment_date3": "0301",
            "interest_payment_date4": "0401",
            "interest_payment_date5": "0501",
            "interest_payment_date6": "0601",
            "interest_payment_date7": "0701",
            "interest_payment_date8": "0801",
            "interest_payment_date9": "0901",
            "interest_rate": 0.0602,
            "is_offering": False,
            "is_redeemed": False,
            "max_holding_quantity": 1,
            "max_sell_amount": 1000,
            "memo": "メモ",
            "name": "テスト債券",
            "owner_address": TestPositionStraightBond.issuer["account_address"],
            "privacy_policy": "プライバシーポリシー",
            "purpose": "新商品の開発資金として利用。",
            "redemption_date": "20191231",
            "redemption_value": 10000,
            "return_amount": "商品券をプレゼント",
            "return_date": "20191231",
            "rsa_publickey": "",
            "status": True,
            "symbol": "BOND",
            "token_template": "IbetStraightBond",
            "total_supply": 1000000,
            "tradable_exchange": "0x0000000000000000000000000000000000000000",
            "transfer_approval_required": False,
            "transferable": True,
            "face_value_currency": "",
            "interest_payment_currency": "",
            "redemption_value_currency": "",
            "base_fx_rate": 0.0,
            "require_personal_info_registered": True,
        }

    @staticmethod
    def expected_share_token():
        return {
            "cancellation_date": "20200603",
            "company_name": "",
            "contact_information": "問い合わせ先",
            "dividend_information": {
                "dividend_payment_date": "20200502",
                "dividend_record_date": "20200401",
                "dividends": 1.01e-11,
            },
            "is_canceled": False,
            "is_offering": False,
            "issue_price": 1000,
            "max_holding_quantity": 1,
            "max_sell_amount": 1000,
            "memo": "メモ",
            "name": "テスト株式",
            "owner_address": TestPositionShare.issuer["account_address"],
            "principal_value": 1000,
            "privacy_policy": "プライバシーポリシー",
            "rsa_publickey": "",
            "status": True,
            "symbol": "SHARE",
            "token_template": "IbetShare",
            "total_supply": 1000000,
            "tradable_exchange": "0x0000000000000000000000000000000000000000",
            "transfer_approval_required": False,
            "transferable": True,
            "require_personal_info_registered": True,
        }

    @staticmethod
    def expected_coupon_token():
        return {
            "owner_address": TestPositionCoupon.issuer["account_address"],
            "company_name": "",
            "contact_information": "問い合わせ先",
            "details": "クーポン詳細",
            "expiration_date": "20191231",
            "image_url": [
                {"id": 1, "url": ""},
                {"id": 2, "url": ""},
                {"id": 3, "url": ""},
            ],
            "initial_offering_status": False,
            "max_holding_quantity": 1,
            "max_sell_amount": 1000,
            "memo": "クーポンメモ欄",
            "name": "テストクーポン",
            "privacy_policy": "プライバシーポリシー",
            "return_details": "リターン詳細",
            "rsa_publickey": "",
            "status": True,
            "symbol": "COUPON",
            "token_template": "IbetCoupon",
            "total_supply": 1000000,
            "tradable_exchange": "0x0000000000000000000000000000000000000000",
            "transferable": True,
        }

    @staticmethod
    def expected_membership_token():
        return {
            "owner_address": TestPositionMembership.issuer["account_address"],
            "company_name": "",
            "contact_information": "問い合わせ先",
            "details": "詳細",
            "expiration_date": "20191231",
            "image_url": [
                {"id": 1, "url": ""},
                {"id": 2, "url": ""},
                {"id": 3, "url": ""},
            ],
            "initial_offering_status": False,
            "max_holding_quantity": 1,
            "max_sell_amount": 1000,
            "memo": "メモ",
            "name": "テスト会員権",
            "privacy_policy": "プライバシーポリシー",
            "return_details": "リターン詳細",
            "rsa_publickey": "",
            "status": True,
            "symbol": "MEMBERSHIP",
            "token_template": "IbetMembership",
            "total_supply": 1000000,
            "tradable_exchange": "0x0000000000000000000000000000000000000000",
            "transferable": True,
        }

    def setup_bond(self, session: Session, shared_contract, index=0):
        personal_info_contract = shared_contract["PersonalInfo"]

        token_non_1 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 0, index, 1)
        token_non_2 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 0, index, 2)
        token_non_3 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 0, index, 3)
        token_non_4 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 0, index, 4)
        token_non_5 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 0, index, 5)
        token_non_6 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 0, index, 6)

        token_1 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 0, index, 1)
        token_2 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 0, index, 2)
        token_3 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 0, index, 3)
        token_4 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 0, index, 4)
        token_5 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 0, index, 5)

        # Prepare data
        self.create_idx_position(
            session,
            token_non_1,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_1, session)  # not target
        TestPositionStraightBond.create_idx_token(
            session,
            token_non_1,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )
        self.create_idx_position(
            session,
            token_non_2,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_2, session)  # not target
        TestPositionStraightBond.create_idx_token(
            session,
            token_non_2,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_1,
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_1, session)  # not target
        TestPositionStraightBond.create_idx_token(
            session,
            token_1,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_2,
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_2, session)  # not target
        TestPositionStraightBond.create_idx_token(
            session,
            token_2,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_non_3,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_3, session)  # not target
        TestPositionStraightBond.create_idx_token(
            session,
            token_non_3,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_non_4,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_4, session)  # not target
        TestPositionStraightBond.create_idx_token(
            session,
            token_non_4,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_3,
            self.account_1["account_address"],
            balance=999900,
            exchange_commitment=100,
        )
        self.list_token(token_3, session)  # not target
        TestPositionStraightBond.create_idx_token(
            session,
            token_3,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_4,
            self.account_1["account_address"],
            exchange_commitment=1000000,
        )
        self.list_token(token_4, session)
        TestPositionStraightBond.create_idx_token(
            session,
            token_4,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_non_5,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_5, session)  # not target
        TestPositionStraightBond.create_idx_token(
            session,
            token_non_5,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_non_6,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_6, session)  # not target
        TestPositionStraightBond.create_idx_token(
            session,
            token_non_6,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_locked_position(
            session,
            token_5,
            self.account_2["account_address"],
            self.account_1["account_address"],
            1000,
        )
        self.create_idx_locked_position(
            session,
            token_5,
            self.issuer["account_address"],
            self.account_1["account_address"],
            2000,
        )
        self.create_idx_locked_position(
            session,
            token_5,
            self.issuer["account_address"],
            self.account_2["account_address"],
            5000,
        )
        self.list_token(token_5, session)
        TestPositionStraightBond.create_idx_token(
            session,
            token_5,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

    def setup_share(self, session: Session, shared_contract, index=0):
        token_non_1 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 1, index, 1)
        token_non_2 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 1, index, 2)
        token_non_3 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 1, index, 3)
        token_non_4 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 1, index, 4)
        token_non_5 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 1, index, 5)
        token_non_6 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 1, index, 6)

        token_1 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 1, index, 1)
        token_2 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 1, index, 2)
        token_3 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 1, index, 3)
        token_4 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 1, index, 4)
        token_5 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 1, index, 5)
        token_6 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 1, index, 6)
        token_7 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 1, index, 7)

        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        self.create_idx_position(
            session,
            token_non_1,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_1, session)  # not target
        TestPositionShare.create_idx_token(
            session,
            token_non_1,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_non_2,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_2, session)  # not target
        TestPositionShare.create_idx_token(
            session,
            token_non_2,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session, token_1, self.account_1["account_address"], balance=1000000
        )
        self.list_token(token_1, session)  # not target
        TestPositionShare.create_idx_token(
            session,
            token_1,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session, token_2, self.account_1["account_address"], balance=1000000
        )
        self.list_token(token_2, session)  # not target
        TestPositionShare.create_idx_token(
            session,
            token_2,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_non_3,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_3, session)  # not target
        TestPositionShare.create_idx_token(
            session,
            token_non_3,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_non_4,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_4, session)  # not target
        TestPositionShare.create_idx_token(
            session,
            token_non_4,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_3,
            self.account_1["account_address"],
            balance=999900,
            pending_transfer=100,
        )
        self.list_token(token_3, session)  # not target
        TestPositionShare.create_idx_token(
            session,
            token_3,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_4,
            self.account_1["account_address"],
            pending_transfer=1000000,
        )
        self.list_token(token_4, session)
        TestPositionShare.create_idx_token(
            session,
            token_4,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_5,
            self.account_1["account_address"],
            balance=999900,
            exchange_commitment=100,
        )
        self.list_token(token_5, session)
        TestPositionShare.create_idx_token(
            session,
            token_5,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_6,
            self.account_1["account_address"],
            exchange_commitment=1000000,
        )
        self.list_token(token_6, session)
        TestPositionShare.create_idx_token(
            session,
            token_6,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_non_5,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_5, session)  # not target
        TestPositionShare.create_idx_token(
            session,
            token_non_5,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_position(
            session,
            token_non_6,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_6, session)  # not target
        TestPositionShare.create_idx_token(
            session,
            token_non_6,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        self.create_idx_locked_position(
            session,
            token_7,
            self.account_2["account_address"],
            self.account_1["account_address"],
            1000,
        )
        self.create_idx_locked_position(
            session,
            token_7,
            self.issuer["account_address"],
            self.account_1["account_address"],
            2000,
        )
        self.create_idx_locked_position(
            session,
            token_7,
            self.issuer["account_address"],
            self.account_2["account_address"],
            5000,
        )
        self.list_token(token_7, session)
        TestPositionShare.create_idx_token(
            session,
            token_7,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

    def setup_coupon(self, session: Session, shared_contract, index=0):
        token_non_1 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 2, index, 1)
        token_non_2 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 2, index, 2)
        token_non_3 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 2, index, 3)
        token_non_4 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 2, index, 4)
        token_non_5 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 2, index, 5)
        token_non_6 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 2, index, 6)
        token_non_7 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 2, index, 7)
        token_non_8 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 2, index, 8)
        token_non_9 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 2, index, 9)

        token_1 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 2, index, 1)
        token_2 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 2, index, 2)
        token_3 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 2, index, 3)
        token_4 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 2, index, 4)
        token_5 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 2, index, 5)
        token_6 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 2, index, 6)
        token_7 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 2, index, 7)

        # Prepare data
        self.create_idx_position(
            session,
            token_non_1,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_1, session)  # not target
        TestPositionCoupon.create_idx_token(session, token_non_1, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_non_2,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_2, session)  # not target
        TestPositionCoupon.create_idx_token(session, token_non_2, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_1,
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_1, session)
        TestPositionCoupon.create_idx_token(session, token_1, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_2,
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_2, session)
        TestPositionCoupon.create_idx_token(session, token_2, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_non_3,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_3, session)  # not target
        TestPositionCoupon.create_idx_token(session, token_non_3, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_non_4,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_4, session)  # not target
        TestPositionCoupon.create_idx_token(session, token_non_4, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_3,
            self.account_1["account_address"],
            balance=999900,
            exchange_commitment=100,
        )
        self.list_token(token_3, session)
        TestPositionCoupon.create_idx_token(session, token_3, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_4,
            self.account_1["account_address"],
            exchange_commitment=1000000,
        )
        self.list_token(token_4, session)
        TestPositionCoupon.create_idx_token(session, token_4, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_non_5,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_5, session)  # not target
        TestPositionCoupon.create_idx_token(session, token_non_5, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_non_6,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_6, session)  # not target
        TestPositionCoupon.create_idx_token(session, token_non_6, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_5,
            self.account_1["account_address"],
            balance=999900,
        )
        TestPositionCoupon.create_idx_consume(
            session, token_5, self.account_1["account_address"], 80
        )
        TestPositionCoupon.create_idx_consume(
            session, token_5, self.account_1["account_address"], 20
        )
        self.list_token(token_5, session)
        TestPositionCoupon.create_idx_token(session, token_5, config.ZERO_ADDRESS)

        TestPositionCoupon.create_idx_consume(
            session, token_6, self.account_1["account_address"], 800000
        )
        TestPositionCoupon.create_idx_consume(
            session, token_6, self.account_1["account_address"], 200000
        )
        self.list_token(token_6, session)
        TestPositionCoupon.create_idx_token(session, token_6, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_non_7,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_7, session)  # not target
        TestPositionCoupon.create_idx_token(session, token_non_7, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_non_8,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_8, session)  # not target
        TestPositionCoupon.create_idx_token(session, token_non_8, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_7,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_7, session)
        TestPositionCoupon.create_idx_token(session, token_7, config.ZERO_ADDRESS)

        idx_transfer = IDXTransfer()
        idx_transfer.transaction_hash = "tx1"
        idx_transfer.token_address = token_7
        idx_transfer.from_address = self.issuer["account_address"]
        idx_transfer.to_address = self.account_1["account_address"]
        idx_transfer.value = 100000
        idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
        session.add(idx_transfer)

        self.create_idx_position(
            session,
            token_non_9,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_9, session)  # not target
        TestPositionCoupon.create_idx_token(session, token_non_9, config.ZERO_ADDRESS)

    def setup_membership(self, session: Session, shared_contract, index=0):
        token_non_1 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 3, index, 1)
        token_non_2 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 3, index, 2)
        token_non_3 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 3, index, 3)
        token_non_4 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 3, index, 4)
        token_non_5 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 3, index, 5)
        token_non_6 = "0x{:010x}{:010x}{:010x}{:010x}".format(9999999999, 3, index, 6)

        token_1 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 3, index, 1)
        token_2 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 3, index, 2)
        token_3 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 3, index, 3)
        token_4 = "0x{:010x}{:010x}{:010x}{:010x}".format(0, 3, index, 4)

        # Prepare data
        self.create_idx_position(
            session,
            token_non_1,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_1, session)  # not target
        TestPositionMembership.create_idx_token(
            session, token_non_1, config.ZERO_ADDRESS
        )

        self.create_idx_position(
            session,
            token_non_2,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_2, session)  # not target
        TestPositionMembership.create_idx_token(
            session, token_non_2, config.ZERO_ADDRESS
        )

        self.create_idx_position(
            session,
            token_1,
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_1, session)
        TestPositionMembership.create_idx_token(session, token_1, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_2,
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_2, session)
        TestPositionMembership.create_idx_token(session, token_2, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_non_3,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_3, session)  # not target
        TestPositionMembership.create_idx_token(
            session, token_non_3, config.ZERO_ADDRESS
        )

        self.create_idx_position(
            session,
            token_non_4,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_4, session)  # not target
        TestPositionMembership.create_idx_token(
            session, token_non_4, config.ZERO_ADDRESS
        )

        self.create_idx_position(
            session,
            token_3,
            self.account_1["account_address"],
            balance=999900,
            exchange_commitment=100,
        )
        self.list_token(token_3, session)
        TestPositionMembership.create_idx_token(session, token_3, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_4,
            self.account_1["account_address"],
            exchange_commitment=1000000,
        )
        self.list_token(token_4, session)
        TestPositionMembership.create_idx_token(session, token_4, config.ZERO_ADDRESS)

        self.create_idx_position(
            session,
            token_non_5,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_5, session)  # not target
        TestPositionMembership.create_idx_token(
            session, token_non_5, config.ZERO_ADDRESS
        )

        self.create_idx_position(
            session,
            token_non_6,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non_6, session)  # not target
        TestPositionMembership.create_idx_token(
            session, token_non_6, config.ZERO_ADDRESS
        )

    def setup_data(self, session: Session, shared_contract, index=0):
        # StraightBond
        self.setup_bond(session=session, shared_contract=shared_contract, index=index)
        # Share
        self.setup_share(session=session, shared_contract=shared_contract, index=index)
        # Coupon
        self.setup_coupon(session=session, shared_contract=shared_contract, index=index)
        # Membership
        self.setup_membership(
            session=session, shared_contract=shared_contract, index=index
        )

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # List all positions
    def test_normal_1(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = True
        config.SHARE_TOKEN_ENABLED = True
        config.COUPON_TOKEN_ENABLED = True
        config.MEMBERSHIP_TOKEN_ENABLED = True

        token_list_contract = shared_contract["TokenList"]
        self.setup_data(session=session, shared_contract=shared_contract, index=0)

        with mock.patch("app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract):
            # Request target API
            resp = client.get(
                self.apiurl.format(account_address=self.account_1["account_address"]),
                params={},
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "result_set": {
                "count": 22,
                "offset": None,
                "limit": None,
                "total": 22,
            },
            "positions": [
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000001",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000002",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
                {
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000003",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000004",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 3000,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000005",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000001",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000002",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 100,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000003",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 1000000,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000004",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000005",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                    "locked": 0,
                    "pending_transfer": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000006",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 3000,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000007",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 0,
                    "token": {
                        "token_address": "0x0000000000000000000200000000000000000001",
                        **self.expected_coupon_token(),
                    },
                },
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 0,
                    "token": {
                        "token_address": "0x0000000000000000000200000000000000000002",
                        **self.expected_coupon_token(),
                    },
                },
                {
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                    "used": 0,
                    "token": {
                        "token_address": "0x0000000000000000000200000000000000000003",
                        **self.expected_coupon_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                    "used": 0,
                    "token": {
                        "token_address": "0x0000000000000000000200000000000000000004",
                        **self.expected_coupon_token(),
                    },
                },
                {
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 100,
                    "token": {
                        "token_address": "0x0000000000000000000200000000000000000005",
                        **self.expected_coupon_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 1000000,
                    "token": {
                        **self.expected_coupon_token(),
                        "token_address": "0x0000000000000000000200000000000000000006",
                    },
                },
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "token": {
                        "token_address": "0x0000000000000000000300000000000000000001",
                        **self.expected_membership_token(),
                    },
                },
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "token": {
                        "token_address": "0x0000000000000000000300000000000000000002",
                        **self.expected_membership_token(),
                    },
                },
                {
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                    "token": {
                        "token_address": "0x0000000000000000000300000000000000000003",
                        **self.expected_membership_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                    "token": {
                        "token_address": "0x0000000000000000000300000000000000000004",
                        **self.expected_membership_token(),
                    },
                },
            ],
        }

    # <Normal_2>
    # List bond positions
    @pytest.mark.parametrize("query_filter", [True, False])
    def test_normal_2(
        self, query_filter, client: TestClient, session: Session, shared_contract
    ):
        token_list_contract = shared_contract["TokenList"]
        self.setup_data(session=session, shared_contract=shared_contract, index=0)

        if query_filter:
            config.BOND_TOKEN_ENABLED = True
            config.SHARE_TOKEN_ENABLED = True
            config.COUPON_TOKEN_ENABLED = True
            config.MEMBERSHIP_TOKEN_ENABLED = True

            with mock.patch(
                "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract
            ):
                # Request target API
                resp = client.get(
                    self.apiurl.format(
                        account_address=self.account_1["account_address"]
                    ),
                    params={"token_type_list": ["IbetStraightBond"]},
                )
        else:
            config.BOND_TOKEN_ENABLED = True
            config.SHARE_TOKEN_ENABLED = False
            config.COUPON_TOKEN_ENABLED = False
            config.MEMBERSHIP_TOKEN_ENABLED = False

            with mock.patch(
                "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract
            ):
                # Request target API
                resp = client.get(
                    self.apiurl.format(
                        account_address=self.account_1["account_address"]
                    ),
                    params={},
                )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "result_set": {
                "count": 5,
                "offset": None,
                "limit": None,
                "total": 5,
            },
            "positions": [
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000001",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000002",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
                {
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000003",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000004",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 3000,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000005",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
            ],
        }

    # <Normal_3>
    # List share positions
    @pytest.mark.parametrize("query_filter", [True, False])
    def test_normal_3(
        self, query_filter, client: TestClient, session: Session, shared_contract
    ):
        token_list_contract = shared_contract["TokenList"]
        self.setup_data(session=session, shared_contract=shared_contract, index=0)

        if query_filter:
            config.BOND_TOKEN_ENABLED = True
            config.SHARE_TOKEN_ENABLED = True
            config.COUPON_TOKEN_ENABLED = True
            config.MEMBERSHIP_TOKEN_ENABLED = True

            with mock.patch(
                "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract
            ):
                # Request target API
                resp = client.get(
                    self.apiurl.format(
                        account_address=self.account_1["account_address"]
                    ),
                    params={"token_type_list": ["IbetShare"]},
                )
        else:
            config.BOND_TOKEN_ENABLED = False
            config.SHARE_TOKEN_ENABLED = True
            config.COUPON_TOKEN_ENABLED = False
            config.MEMBERSHIP_TOKEN_ENABLED = False

            with mock.patch(
                "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract
            ):
                # Request target API
                resp = client.get(
                    self.apiurl.format(
                        account_address=self.account_1["account_address"]
                    ),
                    params={},
                )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "result_set": {
                "count": 7,
                "offset": None,
                "limit": None,
                "total": 7,
            },
            "positions": [
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000001",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000002",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 100,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000003",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 1000000,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000004",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000005",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                    "locked": 0,
                    "pending_transfer": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000006",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 3000,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000007",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
            ],
        }

    # <Normal_4>
    # List coupon positions
    @pytest.mark.parametrize("query_filter", [True, False])
    def test_normal_4(
        self, query_filter, client: TestClient, session: Session, shared_contract
    ):
        token_list_contract = shared_contract["TokenList"]
        self.setup_data(session=session, shared_contract=shared_contract, index=0)

        if query_filter:
            config.BOND_TOKEN_ENABLED = True
            config.SHARE_TOKEN_ENABLED = True
            config.COUPON_TOKEN_ENABLED = True
            config.MEMBERSHIP_TOKEN_ENABLED = True

            with mock.patch(
                "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract
            ):
                # Request target API
                resp = client.get(
                    self.apiurl.format(
                        account_address=self.account_1["account_address"]
                    ),
                    params={"token_type_list": ["IbetCoupon"]},
                )
        else:
            config.BOND_TOKEN_ENABLED = False
            config.SHARE_TOKEN_ENABLED = False
            config.COUPON_TOKEN_ENABLED = True
            config.MEMBERSHIP_TOKEN_ENABLED = False

            with mock.patch(
                "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract
            ):
                # Request target API
                resp = client.get(
                    self.apiurl.format(
                        account_address=self.account_1["account_address"]
                    ),
                    params={},
                )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "result_set": {
                "count": 6,
                "offset": None,
                "limit": None,
                "total": 6,
            },
            "positions": [
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 0,
                    "token": {
                        "token_address": "0x0000000000000000000200000000000000000001",
                        **self.expected_coupon_token(),
                    },
                },
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 0,
                    "token": {
                        "token_address": "0x0000000000000000000200000000000000000002",
                        **self.expected_coupon_token(),
                    },
                },
                {
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                    "used": 0,
                    "token": {
                        "token_address": "0x0000000000000000000200000000000000000003",
                        **self.expected_coupon_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                    "used": 0,
                    "token": {
                        "token_address": "0x0000000000000000000200000000000000000004",
                        **self.expected_coupon_token(),
                    },
                },
                {
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 100,
                    "token": {
                        "token_address": "0x0000000000000000000200000000000000000005",
                        **self.expected_coupon_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 1000000,
                    "token": {
                        **self.expected_coupon_token(),
                        "token_address": "0x0000000000000000000200000000000000000006",
                    },
                },
            ],
        }

    # <Normal_5>
    # List membership positions
    @pytest.mark.parametrize("query_filter", [True, False])
    def test_normal_5(
        self, query_filter, client: TestClient, session: Session, shared_contract
    ):
        token_list_contract = shared_contract["TokenList"]
        self.setup_data(session=session, shared_contract=shared_contract, index=0)

        if query_filter:
            config.BOND_TOKEN_ENABLED = True
            config.SHARE_TOKEN_ENABLED = True
            config.COUPON_TOKEN_ENABLED = True
            config.MEMBERSHIP_TOKEN_ENABLED = True

            with mock.patch(
                "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract
            ):
                # Request target API
                resp = client.get(
                    self.apiurl.format(
                        account_address=self.account_1["account_address"]
                    ),
                    params={"token_type_list": ["IbetMembership"]},
                )
        else:
            config.BOND_TOKEN_ENABLED = False
            config.SHARE_TOKEN_ENABLED = False
            config.COUPON_TOKEN_ENABLED = False
            config.MEMBERSHIP_TOKEN_ENABLED = True

            with mock.patch(
                "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract
            ):
                # Request target API
                resp = client.get(
                    self.apiurl.format(
                        account_address=self.account_1["account_address"]
                    ),
                    params={},
                )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "result_set": {
                "count": 4,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "positions": [
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "token": {
                        "token_address": "0x0000000000000000000300000000000000000001",
                        **self.expected_membership_token(),
                    },
                },
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "token": {
                        "token_address": "0x0000000000000000000300000000000000000002",
                        **self.expected_membership_token(),
                    },
                },
                {
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                    "token": {
                        "token_address": "0x0000000000000000000300000000000000000003",
                        **self.expected_membership_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                    "token": {
                        "token_address": "0x0000000000000000000300000000000000000004",
                        **self.expected_membership_token(),
                    },
                },
            ],
        }

    # <Normal_6>
    # List multiple token type positions
    @pytest.mark.parametrize("query_filter", [True, False])
    def test_normal_6(
        self, query_filter, client: TestClient, session: Session, shared_contract
    ):
        token_list_contract = shared_contract["TokenList"]
        self.setup_data(session=session, shared_contract=shared_contract, index=0)

        if query_filter:
            config.BOND_TOKEN_ENABLED = True
            config.SHARE_TOKEN_ENABLED = True
            config.COUPON_TOKEN_ENABLED = False
            config.MEMBERSHIP_TOKEN_ENABLED = False

            with (
                mock.patch(
                    "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract
                ),
                mock.patch("app.config.BOND_TOKEN_ENABLED", True),
                mock.patch("app.config.SHARE_TOKEN_ENABLED", True),
            ):
                # Request target API
                resp = client.get(
                    self.apiurl.format(
                        account_address=self.account_1["account_address"]
                    ),
                    params={},
                )
        else:
            config.BOND_TOKEN_ENABLED = True
            config.SHARE_TOKEN_ENABLED = True
            config.COUPON_TOKEN_ENABLED = True
            config.MEMBERSHIP_TOKEN_ENABLED = True

            with mock.patch(
                "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract
            ):
                # Request target API
                resp = client.get(
                    self.apiurl.format(
                        account_address=self.account_1["account_address"]
                    ),
                    params={"token_type_list": ["IbetStraightBond", "IbetShare"]},
                )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "result_set": {
                "count": 12,
                "offset": None,
                "limit": None,
                "total": 12,
            },
            "positions": [
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000001",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000002",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
                {
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000003",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000004",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 3000,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000005",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000001",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000002",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 100,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000003",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 1000000,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000004",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000005",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                    "locked": 0,
                    "pending_transfer": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000006",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 3000,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000007",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
            ],
        }

    # <Normal_7>
    # Pagination
    def test_normal_7(self, client: TestClient, session: Session, shared_contract):
        token_list_contract = shared_contract["TokenList"]
        self.setup_data(session=session, shared_contract=shared_contract, index=0)

        config.BOND_TOKEN_ENABLED = True
        config.SHARE_TOKEN_ENABLED = True
        config.COUPON_TOKEN_ENABLED = True
        config.MEMBERSHIP_TOKEN_ENABLED = True

        with mock.patch("app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract):
            # Request target API
            resp = client.get(
                self.apiurl.format(account_address=self.account_1["account_address"]),
                params={"offset": 3, "limit": 5},
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "result_set": {
                "count": 22,
                "offset": 3,
                "limit": 5,
                "total": 22,
            },
            "positions": [
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000004",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
                {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 3000,
                    "token": {
                        "token_address": "0x0000000000000000000000000000000000000005",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_bond_token(),
                    },
                },
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000001",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000002",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
                {
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 100,
                    "locked": 0,
                    "token": {
                        "token_address": "0x0000000000000000000100000000000000000003",
                        "personal_info_address": shared_contract["PersonalInfo"][
                            "address"
                        ],
                        **self.expected_share_token(),
                    },
                },
            ],
        }

    # <Normal_8>
    # Pagination(over offset)
    def test_normal_8(self, client: TestClient, session: Session, shared_contract):
        token_list_contract = shared_contract["TokenList"]
        self.setup_data(session=session, shared_contract=shared_contract, index=0)

        config.BOND_TOKEN_ENABLED = True
        config.SHARE_TOKEN_ENABLED = True
        config.COUPON_TOKEN_ENABLED = True
        config.MEMBERSHIP_TOKEN_ENABLED = True

        with mock.patch("app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract):
            # Request target API
            resp = client.get(
                self.apiurl.format(account_address=self.account_1["account_address"]),
                params={"offset": 22, "limit": 1},
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "result_set": {
                "count": 22,
                "offset": 22,
                "limit": 1,
                "total": 22,
            },
            "positions": [],
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # ParameterError: offset/limit(minus value)
    def test_error_1(self, client: TestClient, session: Session):
        # Request target API
        resp = client.get(
            self.apiurl.format(account_address=self.account_1["account_address"]),
            params={
                "offset": -1,
                "limit": -1,
            },
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"ge": 0},
                    "input": "-1",
                    "loc": ["query", "offset"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
                {
                    "ctx": {"ge": 0},
                    "input": "-1",
                    "loc": ["query", "limit"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
            ],
            "message": "Invalid Parameter",
        }

    # <Error_2>
    # ParameterError: offset/limit(not int), include_token_details(not bool)
    def test_error_2(self, client: TestClient, session: Session):
        # Request target API
        resp = client.get(
            self.apiurl.format(account_address=self.account_1["account_address"]),
            params={
                "offset": "test",
                "limit": "test",
            },
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": "test",
                    "loc": ["query", "offset"],
                    "msg": "Input should be a valid integer, unable to parse "
                    "string as an integer",
                    "type": "int_parsing",
                },
                {
                    "input": "test",
                    "loc": ["query", "limit"],
                    "msg": "Input should be a valid integer, unable to parse "
                    "string as an integer",
                    "type": "int_parsing",
                },
            ],
            "message": "Invalid Parameter",
        }
