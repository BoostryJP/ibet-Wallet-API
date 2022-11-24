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
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.model.db import (
    IDXPosition,
    Listing
)


class TestTokenTokenHoldersCount:
    """
    Test Case for token.TokenHoldersCount
    """

    # Target API endpoint
    apiurl_base = "/Token/{contract_address}/Holders/Count"

    token_address = "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740"
    account_address = "0x52D0784B3460E206ED69393ae1f9Ed37941089eD"
    issuer_address = "0x02D0784B3460E206ED69393ae1f9Ed37941089eD"

    @staticmethod
    def insert_listing(session, listing: dict):
        _listing = Listing()
        _listing.token_address = listing["token_address"]
        _listing.is_public = listing["is_public"]
        _listing.owner_address = TestTokenTokenHoldersCount.issuer_address

        session.add(_listing)

    @staticmethod
    def insert_position(session, position: dict):
        _position = IDXPosition()
        _position.token_address = position["token_address"]
        _position.account_address = position["account_address"]
        _position.balance = position.get("balance")  # nullable
        _position.pending_transfer = position.get(
            "pending_transfer")  # nullable
        _position.exchange_balance = position.get(
            "exchange_balance")  # nullable
        _position.exchange_commitment = position.get(
            "exchange_commitment")  # nullable
        session.add(_position)

    ####################################################################
    # Normal
    ####################################################################

    # Normal_1
    # No data
    def test_normal_1(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        # Assertion
        assumed_body = {
            "count": 0
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_2
    # Data exists
    def test_normal_2(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data (balance > 0)
        position_1 = {
            "token_address": self.token_address,
            "account_address": self.account_address,
            "balance": 10,
            "exchange_balance": 10,
        }
        self.insert_position(session, position=position_1)

        # Prepare data (pending_transfer > 0)
        position_2 = {
            "token_address": self.token_address,
            "account_address": self.account_address,
            "pending_transfer": 5
        }
        self.insert_position(session, position=position_2)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        # Assertion
        assumed_body = {
            "count": 2
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_3
    # balance = 0 , pending_transfer = 0, exchange_balance = 0, exchange_commitment = 0
    def test_normal_3(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data (balance = 0)
        position_1 = {
            "token_address": self.token_address,
            "account_address": self.account_address,
            "balance": 0
        }
        self.insert_position(session, position=position_1)

        # Prepare data (pending_transfer = 0)
        position_2 = {
            "token_address": self.token_address,
            "account_address": self.account_address,
            "pending_transfer": 0
        }
        self.insert_position(session, position=position_2)

        # Prepare data (exchange_balance = 0)
        position_3 = {
            "token_address": self.token_address,
            "account_address": self.account_address,
            "exchange_balance": 0
        }
        self.insert_position(session, position=position_3)

        # Prepare data (exchange_commitment = 0)
        position_4 = {
            "token_address": self.token_address,
            "account_address": self.account_address,
            "exchange_commitment": 0
        }
        self.insert_position(session, position=position_4)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assumed_body = {
            "count": 0
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_4
    # Filter with exclude_issuer
    def test_normal_4(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data (balance > 0)
        position_1 = {
            "token_address": self.token_address,
            "account_address": self.account_address,
            "balance": 10,
            "exchange_balance": 10,
        }
        self.insert_position(session, position=position_1)

        # Prepare data (pending_transfer > 0 and account_address=issuer)
        position_2 = {
            "token_address": self.token_address,
            "account_address": self.issuer_address,
            "pending_transfer": 5
        }
        self.insert_position(session, position=position_2)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query = {
            "exclude_owner": True
        }
        resp = client.get(apiurl, params=query)

        # Assertion
        assumed_body = {
            "count": 1
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    ####################################################################
    # Error
    ####################################################################

    # Error_1
    # 400: Invalid Parameter Error
    # Invalid contract address
    def test_error_1(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(contract_address="0xabcd")
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "invalid contract_address"
        }

    # Error_2
    # 404: Data Not Exists Error
    # token is not listed
    def test_error_2(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": "contract_address: " + self.token_address
        }
