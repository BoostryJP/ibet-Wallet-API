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

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.model.db import IDXLockedPosition, IDXPosition, Listing
from tests.account_config import eth_account


class TestTokenTokenHoldersSearch:
    """
    Test Case for token.TokenHolders.Search
    """

    # Target API endpoint
    apiurl_base = "/Token/{contract_address}/Holders/Search"

    token_address = "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740"
    account_address_1 = "0x52D0784B3460E206ed69393AE1f9ed37941089eC"
    account_address_2 = "0x52D0784B3460E206ED69393ae1f9Ed37941089eD"
    account_address_3 = "0x52d0784b3460e206ed69393aE1F9Ed37941089Ee"
    account_address_4 = "0x52d0784b3460E206ED69393AE1F9eD37941089Ef"
    issuer_address = "0x02D0784B3460E206ED69393ae1f9Ed37941089eD"

    lock_address_1 = eth_account["user1"]["account_address"]
    lock_address_2 = eth_account["user2"]["account_address"]

    @staticmethod
    def insert_listing(session, listing: dict):
        _listing = Listing()
        _listing.token_address = listing["token_address"]
        _listing.is_public = listing["is_public"]
        _listing.owner_address = TestTokenTokenHoldersSearch.issuer_address
        session.add(_listing)
        session.commit()

    @staticmethod
    def insert_position(session, position: dict):
        _position = IDXPosition()
        _position.token_address = position["token_address"]
        _position.account_address = position["account_address"]
        _position.balance = position.get("balance")  # nullable
        _position.pending_transfer = position.get("pending_transfer")  # nullable
        _position.exchange_balance = position.get("exchange_balance")  # nullable
        _position.exchange_commitment = position.get("exchange_commitment")  # nullable
        if "created" in position:
            _position.created = position.get("created")
        session.add(_position)
        session.commit()

    @staticmethod
    def insert_locked_position(
        session: Session, locked_position: dict, zero_position=False
    ):
        idx_locked = IDXLockedPosition()
        idx_locked.token_address = locked_position["token_address"]
        idx_locked.lock_address = locked_position["lock_address"]
        idx_locked.account_address = locked_position["account_address"]
        idx_locked.value = locked_position["value"]
        session.add(idx_locked)
        if zero_position is True:
            _position = IDXPosition()
            _position.token_address = locked_position["token_address"]
            _position.account_address = locked_position["account_address"]
            _position.balance = 0
            _position.pending_transfer = 0
            _position.exchange_balance = 0
            _position.exchange_commitment = 0
            session.add(_position)
        session.commit()

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
        resp = client.post(apiurl, json={})

        # Assertion
        assumed_body = {
            "result_set": {"offset": None, "limit": None, "total": 0, "count": 0},
            "token_holder_list": [],
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_2_1
    # Data exists
    def test_normal_2_1(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        other_listing = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "is_public": True,
        }
        self.insert_listing(session, listing=other_listing)

        # Prepare data (position)
        position_1 = {
            "token_address": self.token_address,
            "account_address": self.account_address_1,
            "balance": 10,
            "exchange_balance": 10,
            "pending_transfer": 5,
            "exchange_commitment": 5,
            "created": datetime(2023, 4, 13, 0, 0, 0),
        }
        self.insert_position(session, position_1)
        position_2 = {
            "token_address": self.token_address,
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 10,
            "exchange_commitment": 10,
            "created": datetime(2023, 4, 14, 0, 0, 0),
        }
        self.insert_position(session, position_2)

        # Prepare data (other token position)
        other_position_1 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_1,
            "balance": 0,
            "exchange_balance": 0,
            "pending_transfer": 0,
            "exchange_commitment": 0,
            "created": datetime(2023, 4, 15, 0, 0, 0),
        }
        self.insert_position(session, other_position_1)
        other_position_2 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 10,
            "exchange_commitment": 10,
            "created": datetime(2023, 4, 16, 0, 0, 0),
        }
        self.insert_position(session, other_position_2)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={})

        # Assertion
        assumed_body = {
            "result_set": {"offset": None, "limit": None, "total": 2, "count": 2},
            "token_holder_list": [
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_2,
                    "amount": 20,
                    "pending_transfer": 10,
                    "exchange_balance": 20,
                    "exchange_commitment": 10,
                    "locked": 0,
                },
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_1,
                    "amount": 10,
                    "pending_transfer": 5,
                    "exchange_balance": 10,
                    "exchange_commitment": 5,
                    "locked": 0,
                },
            ],
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_2_2
    # Data exists: locked position
    def test_normal_2_2(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        other_listing = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "is_public": True,
        }
        self.insert_listing(session, listing=other_listing)

        # Prepare data (position)
        position_1 = {
            "token_address": self.token_address,
            "account_address": self.account_address_1,
            "balance": 0,
            "exchange_balance": 0,
            "pending_transfer": 0,
            "exchange_commitment": 0,
            "created": datetime(2023, 4, 13, 0, 0, 0),
        }
        self.insert_position(session, position_1)
        position_2 = {
            "token_address": self.token_address,
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 10,
            "exchange_commitment": 10,
            "created": datetime(2023, 4, 14, 0, 0, 0),
        }
        self.insert_position(session, position_2)

        # Prepare data (other token position)
        other_position_1 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_1,
            "balance": 0,
            "exchange_balance": 0,
            "pending_transfer": 0,
            "exchange_commitment": 0,
            "created": datetime(2023, 4, 15, 0, 0, 0),
        }
        self.insert_position(session, other_position_1)
        other_position_2 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 10,
            "exchange_commitment": 10,
            "created": datetime(2023, 4, 16, 0, 0, 0),
        }
        self.insert_position(session, other_position_2)

        # Prepare data (locked position)
        locked_position_1 = {
            "token_address": self.token_address,
            "lock_address": self.lock_address_1,
            "account_address": self.account_address_1,
            "value": 1,
        }
        self.insert_locked_position(session, locked_position_1)
        locked_position_2 = {
            "token_address": self.token_address,
            "lock_address": self.lock_address_2,
            "account_address": self.account_address_1,
            "value": 1,
        }
        self.insert_locked_position(session, locked_position_2)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={})

        # Assertion
        assumed_body = {
            "result_set": {"offset": None, "limit": None, "total": 2, "count": 2},
            "token_holder_list": [
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_2,
                    "amount": 20,
                    "pending_transfer": 10,
                    "exchange_balance": 20,
                    "exchange_commitment": 10,
                    "locked": 0,
                },
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_1,
                    "amount": 0,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": 2,
                },
            ],
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

        other_listing = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "is_public": True,
        }
        self.insert_listing(session, listing=other_listing)

        # Prepare data (balance = 0)
        position_1 = {
            "token_address": self.token_address,
            "account_address": self.account_address_1,
            "balance": 0,
        }
        self.insert_position(session, position=position_1)

        # Prepare data (pending_transfer = 0)
        position_2 = {
            "token_address": self.token_address,
            "account_address": self.account_address_2,
            "pending_transfer": 0,
        }
        self.insert_position(session, position=position_2)

        # Prepare data (exchange_balance = 0)
        position_3 = {
            "token_address": self.token_address,
            "account_address": self.account_address_3,
            "exchange_balance": 0,
        }
        self.insert_position(session, position=position_3)

        # Prepare data (exchange_commitment = 0)
        position_4 = {
            "token_address": self.token_address,
            "account_address": self.account_address_4,
            "exchange_commitment": 0,
        }
        self.insert_position(session, position=position_4)

        # Prepare data (other token position)
        other_position_1 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_1,
            "balance": 0,
            "exchange_balance": 0,
            "pending_transfer": 0,
            "exchange_commitment": 0,
        }
        self.insert_position(session, other_position_1)
        other_position_2 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 10,
            "exchange_commitment": 10,
        }
        self.insert_position(session, other_position_2)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={})

        assumed_body = {
            "result_set": {"offset": None, "limit": None, "total": 0, "count": 0},
            "token_holder_list": [],
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_4_1
    # Filter with exclude_issuer
    def test_normal_4(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        other_listing = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "is_public": True,
        }
        self.insert_listing(session, listing=other_listing)

        # Prepare data (balance > 0)
        position_1 = {
            "token_address": self.token_address,
            "account_address": self.account_address_1,
            "balance": 10,
            "exchange_balance": 10,
        }
        self.insert_position(session, position=position_1)

        # Prepare data (pending_transfer > 0 and account_address=issuer)
        position_2 = {
            "token_address": self.token_address,
            "account_address": self.issuer_address,
            "pending_transfer": 5,
        }
        self.insert_position(session, position=position_2)

        # Prepare data (other token position)
        other_position_1 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_1,
            "balance": 0,
            "exchange_balance": 0,
            "pending_transfer": 0,
            "exchange_commitment": 0,
        }
        self.insert_position(session, other_position_1)
        other_position_2 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 10,
            "exchange_commitment": 10,
        }
        self.insert_position(session, other_position_2)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"exclude_owner": True})

        # Assertion
        assumed_body = {
            "result_set": {"offset": None, "limit": None, "total": 2, "count": 1},
            "token_holder_list": [
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_1,
                    "amount": 10,
                    "pending_transfer": 0,
                    "exchange_balance": 10,
                    "exchange_commitment": 0,
                    "locked": 0,
                }
            ],
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_4_2
    # Filter with account_address_list
    def test_normal_4_2(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        other_listing = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "is_public": True,
        }
        self.insert_listing(session, listing=other_listing)

        # Prepare data (balance > 0)
        position_1 = {
            "token_address": self.token_address,
            "account_address": self.account_address_1,
            "balance": 10,
            "exchange_balance": 10,
        }
        self.insert_position(session, position=position_1)

        # Prepare data (pending_transfer > 0 and account_address=issuer)
        position_2 = {
            "token_address": self.token_address,
            "account_address": self.issuer_address,
            "pending_transfer": 5,
        }
        self.insert_position(session, position=position_2)

        # Prepare data (balance > 0)
        position_3 = {
            "token_address": self.token_address,
            "account_address": self.account_address_2,
            "balance": 10,
            "exchange_balance": 10,
        }
        self.insert_position(session, position=position_3)

        # Prepare data (locked position)
        locked_position_1 = {
            "token_address": self.token_address,
            "lock_address": self.lock_address_1,
            "account_address": self.account_address_3,
            "value": 1,
        }
        self.insert_locked_position(session, locked_position_1, zero_position=True)
        locked_position_2 = {
            "token_address": self.token_address,
            "lock_address": self.lock_address_2,
            "account_address": self.account_address_4,
            "value": 1,
        }
        self.insert_locked_position(session, locked_position_2, zero_position=True)

        # Prepare data (other token position)
        other_position_1 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_1,
            "balance": 0,
            "exchange_balance": 0,
            "pending_transfer": 0,
            "exchange_commitment": 0,
        }
        self.insert_position(session, other_position_1)
        other_position_2 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 10,
            "exchange_commitment": 10,
        }
        self.insert_position(session, other_position_2)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={
                "exclude_owner": True,
                "account_address_list": [
                    self.account_address_2,
                    self.account_address_3,
                    self.account_address_4,
                ],
            },
        )

        # Assertion
        assumed_body = {
            "result_set": {"offset": None, "limit": None, "total": 3, "count": 3},
            "token_holder_list": [
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_4,
                    "amount": 0,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": 1,
                },
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_3,
                    "amount": 0,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": 1,
                },
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_2,
                    "amount": 10,
                    "pending_transfer": 0,
                    "exchange_balance": 10,
                    "exchange_commitment": 0,
                    "locked": 0,
                },
            ],
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_4_3
    # Filter with equal filter
    @pytest.mark.parametrize(
        "query_filter",
        [
            "amount",
            "pending_transfer",
            "exchange_balance",
            "exchange_commitment",
            "locked",
        ],
    )
    def test_normal_4_3(self, query_filter: str, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        other_listing = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "is_public": True,
        }
        self.insert_listing(session, listing=other_listing)

        # Prepare data (position)
        position_1 = {
            "token_address": self.token_address,
            "account_address": self.account_address_1,
            "balance": 1,
            "exchange_balance": 1,
            "pending_transfer": 1,
            "exchange_commitment": 1,
            "created": datetime(2023, 4, 13, 0, 0, 0),
        }
        self.insert_position(session, position_1)
        position_2 = {
            "token_address": self.token_address,
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 20,
            "exchange_commitment": 20,
            "created": datetime(2023, 4, 14, 0, 0, 0),
        }
        self.insert_position(session, position_2)

        # Prepare data (other token position)
        other_position_1 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_1,
            "balance": 0,
            "exchange_balance": 0,
            "pending_transfer": 0,
            "exchange_commitment": 0,
            "created": datetime(2023, 4, 15, 0, 0, 0),
        }
        self.insert_position(session, other_position_1)
        other_position_2 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 10,
            "exchange_commitment": 10,
            "created": datetime(2023, 4, 16, 0, 0, 0),
        }
        self.insert_position(session, other_position_2)

        # Prepare data (locked position)
        locked_position_1 = {
            "token_address": self.token_address,
            "lock_address": self.lock_address_1,
            "account_address": self.account_address_1,
            "value": 1,
        }
        self.insert_locked_position(session, locked_position_1)
        locked_position_2 = {
            "token_address": self.token_address,
            "lock_address": self.lock_address_2,
            "account_address": self.account_address_2,
            "value": 20,
        }
        self.insert_locked_position(session, locked_position_2)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl, json={query_filter: 20, query_filter + "_operator": 0}
        )

        # Assertion
        assumed_body = {
            "result_set": {"offset": None, "limit": None, "total": 2, "count": 1},
            "token_holder_list": [
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_2,
                    "amount": 20,
                    "pending_transfer": 20,
                    "exchange_balance": 20,
                    "exchange_commitment": 20,
                    "locked": 20,
                },
            ],
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_4_4
    # Filter with greater than equal filter
    @pytest.mark.parametrize(
        "query_filter",
        [
            "amount",
            "pending_transfer",
            "exchange_balance",
            "exchange_commitment",
            "locked",
        ],
    )
    def test_normal_4_4(self, query_filter: str, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        other_listing = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "is_public": True,
        }
        self.insert_listing(session, listing=other_listing)

        # Prepare data (position)
        position_1 = {
            "token_address": self.token_address,
            "account_address": self.account_address_1,
            "balance": 1,
            "exchange_balance": 1,
            "pending_transfer": 1,
            "exchange_commitment": 1,
            "created": datetime(2023, 4, 13, 0, 0, 0),
        }
        self.insert_position(session, position_1)
        position_2 = {
            "token_address": self.token_address,
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 20,
            "exchange_commitment": 20,
            "created": datetime(2023, 4, 14, 0, 0, 0),
        }
        self.insert_position(session, position_2)

        # Prepare data (other token position)
        other_position_1 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_1,
            "balance": 0,
            "exchange_balance": 0,
            "pending_transfer": 0,
            "exchange_commitment": 0,
            "created": datetime(2023, 4, 15, 0, 0, 0),
        }
        self.insert_position(session, other_position_1)
        other_position_2 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 10,
            "exchange_commitment": 10,
            "created": datetime(2023, 4, 16, 0, 0, 0),
        }
        self.insert_position(session, other_position_2)

        # Prepare data (locked position)
        locked_position_1 = {
            "token_address": self.token_address,
            "lock_address": self.lock_address_1,
            "account_address": self.account_address_1,
            "value": 1,
        }
        self.insert_locked_position(session, locked_position_1)
        locked_position_2 = {
            "token_address": self.token_address,
            "lock_address": self.lock_address_2,
            "account_address": self.account_address_2,
            "value": 20,
        }
        self.insert_locked_position(session, locked_position_2)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl, json={query_filter: 20, query_filter + "_operator": 1}
        )

        # Assertion
        assumed_body = {
            "result_set": {"offset": None, "limit": None, "total": 2, "count": 1},
            "token_holder_list": [
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_2,
                    "amount": 20,
                    "pending_transfer": 20,
                    "exchange_balance": 20,
                    "exchange_commitment": 20,
                    "locked": 20,
                },
            ],
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_4_5
    # Filter with less than equal filter
    @pytest.mark.parametrize(
        "query_filter",
        [
            "amount",
            "pending_transfer",
            "exchange_balance",
            "exchange_commitment",
            "locked",
        ],
    )
    def test_normal_4_5(self, query_filter: str, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        other_listing = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "is_public": True,
        }
        self.insert_listing(session, listing=other_listing)

        # Prepare data (position)
        position_1 = {
            "token_address": self.token_address,
            "account_address": self.account_address_1,
            "balance": 1,
            "exchange_balance": 1,
            "pending_transfer": 1,
            "exchange_commitment": 1,
            "created": datetime(2023, 4, 13, 0, 0, 0),
        }
        self.insert_position(session, position_1)
        position_2 = {
            "token_address": self.token_address,
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 20,
            "exchange_commitment": 20,
            "created": datetime(2023, 4, 14, 0, 0, 0),
        }
        self.insert_position(session, position_2)

        # Prepare data (other token position)
        other_position_1 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_1,
            "balance": 0,
            "exchange_balance": 0,
            "pending_transfer": 0,
            "exchange_commitment": 0,
            "created": datetime(2023, 4, 15, 0, 0, 0),
        }
        self.insert_position(session, other_position_1)
        other_position_2 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 10,
            "exchange_commitment": 10,
            "created": datetime(2023, 4, 16, 0, 0, 0),
        }
        self.insert_position(session, other_position_2)

        # Prepare data (locked position)
        locked_position_1 = {
            "token_address": self.token_address,
            "lock_address": self.lock_address_1,
            "account_address": self.account_address_1,
            "value": 1,
        }
        self.insert_locked_position(session, locked_position_1)
        locked_position_2 = {
            "token_address": self.token_address,
            "lock_address": self.lock_address_2,
            "account_address": self.account_address_2,
            "value": 20,
        }
        self.insert_locked_position(session, locked_position_2)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl, json={query_filter: 19, query_filter + "_operator": 2}
        )

        # Assertion
        assumed_body = {
            "result_set": {"offset": None, "limit": None, "total": 2, "count": 1},
            "token_holder_list": [
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_1,
                    "amount": 1,
                    "pending_transfer": 1,
                    "exchange_balance": 1,
                    "exchange_commitment": 1,
                    "locked": 1,
                },
            ],
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_5_1
    # Sort with account_address_list
    def test_normal_5_1(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        other_listing = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "is_public": True,
        }
        self.insert_listing(session, listing=other_listing)

        # Prepare data (balance > 0)
        position_1 = {
            "token_address": self.token_address,
            "account_address": self.account_address_1,
            "balance": 10,
            "exchange_balance": 10,
        }
        self.insert_position(session, position=position_1)

        # Prepare data (pending_transfer > 0 and account_address=issuer)
        position_2 = {
            "token_address": self.token_address,
            "account_address": self.issuer_address,
            "pending_transfer": 5,
        }
        self.insert_position(session, position=position_2)

        # Prepare data (balance > 0)
        position_3 = {
            "token_address": self.token_address,
            "account_address": self.account_address_2,
            "balance": 10,
            "exchange_balance": 10,
        }
        self.insert_position(session, position=position_3)

        # Prepare data (locked position)
        locked_position_1 = {
            "token_address": self.token_address,
            "lock_address": self.lock_address_1,
            "account_address": self.account_address_3,
            "value": 1,
        }
        self.insert_locked_position(session, locked_position_1, zero_position=True)
        locked_position_2 = {
            "token_address": self.token_address,
            "lock_address": self.lock_address_2,
            "account_address": self.account_address_4,
            "value": 1,
        }
        self.insert_locked_position(session, locked_position_2, zero_position=True)

        # Prepare data (other token position)
        other_position_1 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_1,
            "balance": 0,
            "exchange_balance": 0,
            "pending_transfer": 0,
            "exchange_commitment": 0,
        }
        self.insert_position(session, other_position_1)
        other_position_2 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 10,
            "exchange_commitment": 10,
        }
        self.insert_position(session, other_position_2)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={
                "sort_item": "account_address_list",
                "sort_order": 0,
                "account_address_list": [
                    self.account_address_4,
                    "not_exist_address",
                    self.account_address_2,
                    self.account_address_3,
                ],
            },
        )

        # Assertion
        assumed_body = {
            "result_set": {"offset": None, "limit": None, "total": 3, "count": 3},
            "token_holder_list": [
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_4,
                    "amount": 0,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": 1,
                },
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_2,
                    "amount": 10,
                    "pending_transfer": 0,
                    "exchange_balance": 10,
                    "exchange_commitment": 0,
                    "locked": 0,
                },
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_3,
                    "amount": 0,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": 1,
                },
            ],
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_5_2
    # Sort with amount/pending_transfer/exchange_balance/exchange_commitment/locked
    @pytest.mark.parametrize(
        "sort_item",
        [
            "amount",
            "pending_transfer",
            "exchange_balance",
            "exchange_commitment",
            "locked",
        ],
    )
    def test_normal_5_2(self, sort_item: str, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        other_listing = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "is_public": True,
        }
        self.insert_listing(session, listing=other_listing)

        # Prepare data (position)
        position_1 = {
            "token_address": self.token_address,
            "account_address": self.account_address_1,
            "balance": 1,
            "exchange_balance": 1,
            "pending_transfer": 1,
            "exchange_commitment": 1,
            "created": datetime(2023, 4, 13, 0, 0, 0),
        }
        self.insert_position(session, position_1)
        position_2 = {
            "token_address": self.token_address,
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 20,
            "exchange_commitment": 20,
            "created": datetime(2023, 4, 14, 0, 0, 0),
        }
        self.insert_position(session, position_2)

        # Prepare data (other token position)
        other_position_1 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_1,
            "balance": 0,
            "exchange_balance": 0,
            "pending_transfer": 0,
            "exchange_commitment": 0,
            "created": datetime(2023, 4, 15, 0, 0, 0),
        }
        self.insert_position(session, other_position_1)
        other_position_2 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 10,
            "exchange_commitment": 10,
            "created": datetime(2023, 4, 16, 0, 0, 0),
        }
        self.insert_position(session, other_position_2)

        # Prepare data (locked position)
        locked_position_1 = {
            "token_address": self.token_address,
            "lock_address": self.lock_address_1,
            "account_address": self.account_address_1,
            "value": 1,
        }
        self.insert_locked_position(session, locked_position_1)
        locked_position_2 = {
            "token_address": self.token_address,
            "lock_address": self.lock_address_2,
            "account_address": self.account_address_2,
            "value": 20,
        }
        self.insert_locked_position(session, locked_position_2)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"sort_item": sort_item, "sort_order": 0})

        # Assertion
        assumed_body = {
            "result_set": {"offset": None, "limit": None, "total": 2, "count": 2},
            "token_holder_list": [
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_1,
                    "amount": 1,
                    "pending_transfer": 1,
                    "exchange_balance": 1,
                    "exchange_commitment": 1,
                    "locked": 1,
                },
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_2,
                    "amount": 20,
                    "pending_transfer": 20,
                    "exchange_balance": 20,
                    "exchange_commitment": 20,
                    "locked": 20,
                },
            ],
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_6_1
    # Pagination: offset
    def test_normal_6_1(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        other_listing = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "is_public": True,
        }
        self.insert_listing(session, listing=other_listing)

        # Prepare data (balance > 0)
        position_1 = {
            "token_address": self.token_address,
            "account_address": self.account_address_1,
            "balance": 10,
            "exchange_balance": 10,
        }
        self.insert_position(session, position=position_1)

        # Prepare data (pending_transfer > 0 and account_address=issuer)
        position_2 = {
            "token_address": self.token_address,
            "account_address": self.issuer_address,
            "pending_transfer": 5,
        }
        self.insert_position(session, position=position_2)

        # Prepare data (pending_transfer > 0 and account_address=issuer)
        position_3 = {
            "token_address": self.token_address,
            "account_address": self.account_address_2,
            "balance": 5,
        }
        self.insert_position(session, position=position_3)

        # Prepare data (other token position)
        other_position_1 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_1,
            "balance": 0,
            "exchange_balance": 0,
            "pending_transfer": 0,
            "exchange_commitment": 0,
        }
        self.insert_position(session, other_position_1)
        other_position_2 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 10,
            "exchange_commitment": 10,
        }
        self.insert_position(session, other_position_2)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"exclude_owner": True, "offset": 1})

        # Assertion
        assumed_body = {
            "result_set": {"offset": 1, "limit": None, "total": 3, "count": 2},
            "token_holder_list": [
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_1,
                    "amount": 10,
                    "pending_transfer": 0,
                    "exchange_balance": 10,
                    "exchange_commitment": 0,
                    "locked": 0,
                }
            ],
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_6_2
    # Pagination: limit
    def test_normal_6_2(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        other_listing = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "is_public": True,
        }
        self.insert_listing(session, listing=other_listing)

        # Prepare data (balance > 0)
        position_1 = {
            "token_address": self.token_address,
            "account_address": self.account_address_1,
            "balance": 10,
            "exchange_balance": 10,
        }
        self.insert_position(session, position=position_1)

        # Prepare data (pending_transfer > 0 and account_address=issuer)
        position_2 = {
            "token_address": self.token_address,
            "account_address": self.issuer_address,
            "pending_transfer": 5,
        }
        self.insert_position(session, position=position_2)

        # Prepare data (pending_transfer > 0 and account_address=issuer)
        position_3 = {
            "token_address": self.token_address,
            "account_address": self.account_address_2,
            "balance": 5,
        }
        self.insert_position(session, position=position_3)

        # Prepare data (other token position)
        other_position_1 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_1,
            "balance": 0,
            "exchange_balance": 0,
            "pending_transfer": 0,
            "exchange_commitment": 0,
        }
        self.insert_position(session, other_position_1)
        other_position_2 = {
            "token_address": "0x55126b4e2a868E7519C32aA3945e7298d768975b",
            "account_address": self.account_address_2,
            "balance": 20,
            "exchange_balance": 20,
            "pending_transfer": 10,
            "exchange_commitment": 10,
        }
        self.insert_position(session, other_position_2)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"exclude_owner": True, "limit": 1})

        # Assertion
        assumed_body = {
            "result_set": {"offset": None, "limit": 1, "total": 3, "count": 2},
            "token_holder_list": [
                {
                    "token_address": self.token_address,
                    "account_address": self.account_address_2,
                    "amount": 5,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": 0,
                }
            ],
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
        resp = client.post(apiurl, json={})

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["path", "token_address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": "0xabcd",
                    "ctx": {"error": {}},
                }
            ],
        }

    # Error_2
    # 404: Data Not Exists Error
    # token is not listed
    def test_error_2(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={})

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": "token_address: " + self.token_address,
        }
