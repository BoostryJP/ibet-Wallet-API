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

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import ANY

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.model.db import AccountTag, IDXTransfer, IDXTransferSourceEventType, Listing


class TestAllTokenTransferHistory:
    """
    Test Case for token.ListAllTransferHistory
    """

    # テスト対象API
    apiurl = "/Token/TransferHistory"

    transaction_hash = (
        "0xc99116e27f0c40201a9e907ad5334f4477863269b90a94444d11a1bc9b9315e6"
    )
    token_address = "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740"

    account_address_1 = "0xF13D2aCe101F1e4B55d96d66fBF18aD8a8aF22bF"
    account_address_2 = "0x6431d02363FC69fFD9F69CAa4E05E96d4e79f3da"

    @staticmethod
    def insert_listing(session: Session, listing: dict[str, Any]):
        _listing = Listing()
        _listing.token_address = listing["token_address"]
        _listing.is_public = listing["is_public"]
        session.add(_listing)

    @staticmethod
    def insert_transfer_event(
        session: Session,
        transfer_event: dict[str, Any],
        transfer_source_event: IDXTransferSourceEventType = IDXTransferSourceEventType.TRANSFER,
        transfer_event_data: dict[str, Any] | None = None,
        created: datetime | None = None,
    ):
        _transfer = IDXTransfer()
        _transfer.transaction_hash = transfer_event["transaction_hash"]
        _transfer.token_address = transfer_event["token_address"]
        _transfer.from_address = transfer_event["from_address"]
        _transfer.to_address = transfer_event["to_address"]
        _transfer.value = transfer_event["value"]
        _transfer.source_event = transfer_source_event
        _transfer.data = transfer_event_data
        _transfer.message = (
            transfer_event_data.get("message")
            if transfer_event_data is not None
            else None
        )
        if created is not None:
            _transfer.created = created
        session.add(_transfer)

    ####################################################################
    # Normal
    ####################################################################

    # Normal_1
    # # No Transfer Event
    def test_normal_1(self, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        session.commit()

        # Call the target API
        resp = client.get(self.apiurl, params={})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 0, "offset": None, "limit": None, "total": 0},
            "transfer_history": [],
        }

    # Normal_2
    # Transfer event exists: 1 case
    # offset: not set, limit: not set
    def test_normal_2(self, client: TestClient, session: Session):
        # Prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_event = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 10,
        }
        self.insert_transfer_event(session, transfer_event=transfer_event)

        session.commit()

        # Call the target API
        resp = client.get(self.apiurl, params={})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 1},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_1,
                    "to_address": self.account_address_2,
                    "value": 10,
                    "data": None,
                    "message": None,
                    "created": ANY,
                    "source_event": "Transfer",
                }
            ],
        }

    # Normal_3
    # Transfer event exists: 2 cases
    def test_normal_3(self, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data: IDXTransfer
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        # Call the target API
        resp = client.get(self.apiurl, params={})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_1,
                    "to_address": self.account_address_2,
                    "value": 10,
                    "data": None,
                    "message": None,
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                },
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_1,
                    "to_address": self.account_address_2,
                    "value": 20,
                    "data": {"message": "force_unlock"},
                    "message": "force_unlock",
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.UNLOCK,
                },
            ],
        }

    # Normal_4_1_1
    # Filter
    # - account_tag: from_address
    def test_normal_4_1_1(self, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data: AccountTag
        account_tag = AccountTag()
        account_tag.account_address = self.account_address_1
        account_tag.account_tag = "test_tag"
        session.add(account_tag)
        session.commit()

        # Prepare data: IDXTransfer
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,  # match
            "to_address": self.account_address_2,  # not match
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_2,  # not match
            "to_address": self.account_address_2,  # not match
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        # Call the target API
        resp = client.get(self.apiurl, params={"account_tag": "test_tag"})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 1},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_1,
                    "to_address": self.account_address_2,
                    "value": 10,
                    "data": None,
                    "message": None,
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                }
            ],
        }

    # Normal_4_1_2
    # Filter
    # - account_tag: to_address
    def test_normal_4_1_2(self, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data: AccountTag
        account_tag = AccountTag()
        account_tag.account_address = self.account_address_1
        account_tag.account_tag = "test_tag"
        session.add(account_tag)
        session.commit()

        # Prepare data: IDXTransfer
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_2,  # not match
            "to_address": self.account_address_2,  # not match
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_2,  # not match
            "to_address": self.account_address_1,  # match
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        # Call the target API
        resp = client.get(self.apiurl, params={"account_tag": "test_tag"})

        # 検証
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 1},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_2,
                    "to_address": self.account_address_1,
                    "value": 20,
                    "data": {"message": "force_unlock"},
                    "message": "force_unlock",
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.UNLOCK,
                },
            ],
        }

    # Normal_4_2
    # Filter
    # - source_event
    def test_normal_4_2(self, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data: IDXTransfer
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_2,
            "to_address": self.account_address_1,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        # Call the target API
        resp = client.get(
            self.apiurl, params={"source_event": IDXTransferSourceEventType.UNLOCK}
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_2,
                    "to_address": self.account_address_1,
                    "value": 20,
                    "data": {"message": "force_unlock"},
                    "message": "force_unlock",
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.UNLOCK,
                }
            ],
        }

    # Normal_4_3
    # Filter
    # - data
    def test_normal_4_3(self, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data: IDXTransfer
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_2,
            "to_address": self.account_address_1,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        # Call the target API
        resp = client.get(self.apiurl, params={"data": "force_unlock"})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_2,
                    "to_address": self.account_address_1,
                    "value": 20,
                    "data": {"message": "force_unlock"},
                    "message": "force_unlock",
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.UNLOCK,
                }
            ],
        }

    # Normal_4_4_1
    # Filter
    # - value
    # - value_operator: =
    def test_normal_4_4_1(self, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data: IDXTransfer
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )
        session.commit()

        # Call the target API
        resp = client.get(self.apiurl, params={"value_operator": 0, "value": 10})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_1,
                    "to_address": self.account_address_2,
                    "value": 10,
                    "data": None,
                    "message": None,
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                }
            ],
        }

    # Normal_4_4_2
    # Filter
    # - value
    # - value_operator: >=
    def test_normal_4_4_2(self, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data: IDXTransfer
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )
        session.commit()

        # Call the target API
        resp = client.get(self.apiurl, params={"value_operator": 1, "value": 15})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_1,
                    "to_address": self.account_address_2,
                    "value": 20,
                    "data": {"message": "force_unlock"},
                    "message": "force_unlock",
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.UNLOCK,
                }
            ],
        }

    # Normal_4_4_3
    # Filter
    # - value
    # - value_operator: <=
    def test_normal_4_4_3(self, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data: IDXTransfer
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )
        session.commit()

        # Call the target API
        resp = client.get(self.apiurl, params={"value_operator": 2, "value": 10})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_1,
                    "to_address": self.account_address_2,
                    "value": 10,
                    "data": None,
                    "message": None,
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                }
            ],
        }

    # Normal_4_5
    # Filter
    # - token_address
    def test_normal_4_5(self, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)
        listing = {
            "token_address": "other_token_address",
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data: IDXTransfer
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": "other_token_address",
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )
        session.commit()

        # Call the target API
        resp = client.get(
            self.apiurl, params={"token_address": self.token_address[0:5]}
        )  # Partial match

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_1,
                    "to_address": self.account_address_2,
                    "value": 10,
                    "data": None,
                    "message": None,
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                }
            ],
        }

    # Normal_4_6
    # Filter
    # - transaction_hash
    def test_normal_4_6(self, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data: IDXTransfer
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        transfer_event_2 = {
            "transaction_hash": "other_transaction_hash",
            "token_address": self.token_address,
            "from_address": self.account_address_2,
            "to_address": self.account_address_1,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        # Call the target API
        resp = client.get(
            self.apiurl, params={"transaction_hash": self.transaction_hash[0:5]}
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_1,
                    "to_address": self.account_address_2,
                    "value": 10,
                    "data": None,
                    "message": None,
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                }
            ],
        }

    # Normal_4_7
    # Filter
    # - from_address
    def test_normal_4_7(self, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data: IDXTransfer
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": "other_from_address",
            "to_address": self.account_address_1,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        # Call the target API
        resp = client.get(
            self.apiurl, params={"from_address": self.account_address_1[0:5]}
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_1,
                    "to_address": self.account_address_2,
                    "value": 10,
                    "data": None,
                    "message": None,
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                }
            ],
        }

    # Normal_4_8
    # Filter
    # - to_address
    def test_normal_4_8(self, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data: IDXTransfer
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": "other_to_address",
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        # Call the target API
        resp = client.get(
            self.apiurl, params={"to_address": self.account_address_2[0:5]}
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_1,
                    "to_address": self.account_address_2,
                    "value": 10,
                    "data": None,
                    "message": None,
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                }
            ],
        }

    # Normal_4_9
    # Filter
    # - created_from
    @pytest.mark.parametrize(
        "created_from", ["2023-11-06T23:00:00+09:00", "2023-11-06T14:00:00+00:00"]
    )
    def test_normal_4_9(self, created_from: str, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data: IDXTransfer
        base_time = datetime(2023, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
            created=base_time,
        )
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
            created=base_time - timedelta(seconds=1),
        )

        session.commit()

        # Call the target API
        resp = client.get(self.apiurl, params={"created_from": created_from})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_1,
                    "to_address": self.account_address_2,
                    "value": 10,
                    "data": None,
                    "message": None,
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                }
            ],
        }

    # Normal_4_10
    # Filter
    # - created_to
    @pytest.mark.parametrize(
        "created_to", ["2023-11-06T23:00:00+09:00", "2023-11-06T14:00:00+00:00"]
    )
    def test_normal_4_10(self, created_to: str, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data: IDXTransfer
        base_time = datetime(2023, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
            created=base_time,
        )
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
            created=base_time + timedelta(seconds=1),
        )

        session.commit()

        # Call the target API
        resp = client.get(self.apiurl, params={"created_to": created_to})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_1,
                    "to_address": self.account_address_2,
                    "value": 10,
                    "data": None,
                    "message": None,
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                }
            ],
        }

    # Normal_5_1
    # Pagination
    # offset: 1, limit: not set
    def test_normal_5_1(self, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data: IDXTransfer
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_2,
            "to_address": self.account_address_1,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        # Call the target API
        resp = client.get(self.apiurl, params={"offset": 1})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 2, "offset": 1, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_2,
                    "to_address": self.account_address_1,
                    "value": 20,
                    "data": {"message": "force_unlock"},
                    "message": "force_unlock",
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.UNLOCK,
                }
            ],
        }

    # Normal_5_2
    # offset: not set, limit: 1
    def test_normal_5_2(self, client: TestClient, session: Session):
        # Prepare data: Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # Prepare data: IDXTransfer
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_1,
            "to_address": self.account_address_2,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.account_address_2,
            "to_address": self.account_address_1,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        # Call the target API
        resp = client.get(self.apiurl, params={"limit": 1})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 2, "offset": None, "limit": 1, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.transaction_hash,
                    "token_address": self.token_address,
                    "from_address": self.account_address_1,
                    "to_address": self.account_address_2,
                    "value": 10,
                    "data": None,
                    "message": None,
                    "created": ANY,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                }
            ],
        }

    ####################################################################
    # Error
    ####################################################################

    # Error_1
    # Invalid Parameter Error
    # - invalid offset/limit value
    def test_error_1(self, client: TestClient, session: Session):
        # Call the target API
        resp = client.get(
            self.apiurl,
            params={
                "offset": -1,
                "limit": -1,
            },
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "greater_than_equal",
                    "loc": ["query", "offset"],
                    "msg": "Input should be greater than or equal to 0",
                    "input": "-1",
                    "ctx": {"ge": 0},
                },
                {
                    "type": "greater_than_equal",
                    "loc": ["query", "limit"],
                    "msg": "Input should be greater than or equal to 0",
                    "input": "-1",
                    "ctx": {"ge": 0},
                },
            ],
        }
