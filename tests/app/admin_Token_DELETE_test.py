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

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.db import (
    ExecutableContract,
    IDXBondToken,
    IDXCouponToken,
    IDXMembershipToken,
    IDXShareToken,
    Listing,
)


class TestAdminTokenDELETE:
    # テスト対象API
    apiurl_base = "/Admin/Tokens/"

    @staticmethod
    def insert_Listing(session: Session, token: dict[str, Any]):
        listing = Listing()
        listing.token_address = token["token_address"]
        listing.is_public = token["is_public"]
        listing.max_holding_quantity = token["max_holding_quantity"]
        listing.max_sell_amount = token["max_sell_amount"]
        listing.owner_address = token["owner_address"]
        session.add(listing)

    @staticmethod
    def insert_ExecutableContract(session: Session, token: dict[str, Any]):
        executable_contract = ExecutableContract()
        executable_contract.contract_address = token["token_address"]
        session.add(executable_contract)

    @staticmethod
    def insert_IDXBondToken(session: Session, token: dict[str, Any]):
        idx_token = IDXBondToken()
        idx_token.token_address = token["token_address"]
        idx_token.token_template = "IbetStraightBond"
        idx_token.face_value_currency = ""
        idx_token.interest_payment_currency = ""
        idx_token.redemption_value_currency = ""
        idx_token.base_fx_rate = 0.0
        session.add(idx_token)

    @staticmethod
    def insert_IDXShareToken(session: Session, token: dict[str, Any]):
        idx_token = IDXShareToken()
        idx_token.token_address = token["token_address"]
        idx_token.token_template = "IbetShare"
        session.add(idx_token)

    @staticmethod
    def insert_IDXMembershipToken(session: Session, token: dict[str, Any]):
        idx_token = IDXMembershipToken()
        idx_token.token_address = token["token_address"]
        idx_token.token_template = "IbetMembership"
        session.add(idx_token)

    @staticmethod
    def insert_IDXCouponToken(session: Session, token: dict[str, Any]):
        idx_token = IDXCouponToken()
        idx_token.token_address = token["token_address"]
        idx_token.token_template = "IbetCoupon"
        session.add(idx_token)

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    # Bond
    def test_normal_1(self, client: TestClient, session: Session):
        token = {
            "token_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
            "owner_address": "0x56f63dc2351BeC560a429f0C646d64Ca718e11D6",
        }
        self.insert_Listing(session, token)
        self.insert_ExecutableContract(session, token)
        self.insert_IDXBondToken(session, token)
        session.commit()

        # Request target API
        apiurl = self.apiurl_base + str(token["token_address"])
        resp = client.delete(apiurl)

        # Assertion
        session.rollback()
        assert resp.status_code == 200
        assert resp.json() == {"data": {}, "meta": {"code": 200, "message": "OK"}}

        listing = session.scalars(
            select(Listing).where(Listing.token_address == token["token_address"])
        ).all()
        assert listing == []

        executable_contract = session.scalars(
            select(ExecutableContract).where(
                ExecutableContract.contract_address == token["token_address"]
            )
        ).all()
        assert executable_contract == []

        idx_token = session.scalars(
            select(IDXBondToken).where(
                IDXBondToken.token_address == token["token_address"]
            )
        ).all()
        assert idx_token == []

    # Normal_2
    # Share
    def test_normal_2(self, client: TestClient, session: Session):
        token = {
            "token_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
            "owner_address": "0x56f63dc2351BeC560a429f0C646d64Ca718e11D6",
        }
        self.insert_Listing(session, token)
        self.insert_ExecutableContract(session, token)
        self.insert_IDXShareToken(session, token)
        session.commit()

        # Request target API
        apiurl = self.apiurl_base + str(token["token_address"])
        resp = client.delete(apiurl)

        # Assertion
        session.rollback()
        assert resp.status_code == 200
        assert resp.json() == {"data": {}, "meta": {"code": 200, "message": "OK"}}

        listing = session.scalars(
            select(Listing).where(Listing.token_address == token["token_address"])
        ).all()
        assert listing == []

        executable_contract = session.scalars(
            select(ExecutableContract).where(
                ExecutableContract.contract_address == token["token_address"]
            )
        ).all()
        assert executable_contract == []

        idx_token = session.scalars(
            select(IDXShareToken).where(
                IDXShareToken.token_address == token["token_address"]
            )
        ).all()
        assert idx_token == []

    # Normal_3
    # Membership
    def test_normal_3(self, client: TestClient, session: Session):
        token = {
            "token_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
            "owner_address": "0x56f63dc2351BeC560a429f0C646d64Ca718e11D6",
        }
        self.insert_Listing(session, token)
        self.insert_ExecutableContract(session, token)
        self.insert_IDXMembershipToken(session, token)
        session.commit()

        # Request target API
        apiurl = self.apiurl_base + str(token["token_address"])
        resp = client.delete(apiurl)

        # Assertion
        session.rollback()
        assert resp.status_code == 200
        assert resp.json() == {"data": {}, "meta": {"code": 200, "message": "OK"}}

        listing = session.scalars(
            select(Listing).where(Listing.token_address == token["token_address"])
        ).all()
        assert listing == []

        executable_contract = session.scalars(
            select(ExecutableContract).where(
                ExecutableContract.contract_address == token["token_address"]
            )
        ).all()
        assert executable_contract == []

        idx_token = session.scalars(
            select(IDXMembershipToken).where(
                IDXMembershipToken.token_address == token["token_address"]
            )
        ).all()
        assert idx_token == []

    # Normal_4
    # Coupon
    def test_normal_4(self, client: TestClient, session: Session):
        token = {
            "token_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
            "owner_address": "0x56f63dc2351BeC560a429f0C646d64Ca718e11D6",
        }
        self.insert_Listing(session, token)
        self.insert_ExecutableContract(session, token)
        self.insert_IDXCouponToken(session, token)
        session.commit()

        # Request target API
        apiurl = self.apiurl_base + str(token["token_address"])
        resp = client.delete(apiurl)

        # Assertion
        session.rollback()
        assert resp.status_code == 200
        assert resp.json() == {"data": {}, "meta": {"code": 200, "message": "OK"}}

        listing = session.scalars(
            select(Listing).where(Listing.token_address == token["token_address"])
        ).all()
        assert listing == []

        executable_contract = session.scalars(
            select(ExecutableContract).where(
                ExecutableContract.contract_address == token["token_address"]
            )
        ).all()
        assert executable_contract == []

        idx_token = session.scalars(
            select(IDXCouponToken).where(
                IDXCouponToken.token_address == token["token_address"]
            )
        ).all()
        assert idx_token == []

    # Normal_5
    # Multiple token type(template)
    def test_normal_5(self, client: TestClient, session: Session):
        token = {
            "token_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
            "owner_address": "0x56f63dc2351BeC560a429f0C646d64Ca718e11D6",
        }
        self.insert_Listing(session, token)
        self.insert_ExecutableContract(session, token)
        self.insert_IDXBondToken(session, token)
        self.insert_IDXCouponToken(session, token)
        session.commit()

        # Request target API
        apiurl = self.apiurl_base + str(token["token_address"])
        resp = client.delete(apiurl)

        # Assertion
        session.rollback()
        assert resp.status_code == 200
        assert resp.json() == {"data": {}, "meta": {"code": 200, "message": "OK"}}

        listing = session.scalars(
            select(Listing).where(Listing.token_address == token["token_address"])
        ).all()
        assert listing == []

        executable_contract = session.scalars(
            select(ExecutableContract).where(
                ExecutableContract.contract_address == token["token_address"]
            )
        ).all()
        assert executable_contract == []

        idx_token = session.scalars(
            select(IDXBondToken).where(
                IDXBondToken.token_address == token["token_address"]
            )
        ).all()
        assert idx_token == []

        idx_token = session.scalars(
            select(IDXCouponToken).where(
                IDXCouponToken.token_address == token["token_address"]
            )
        ).all()
        assert idx_token == []
