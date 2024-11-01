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

from datetime import UTC, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.model.db import IDXTransfer, IDXTransferSourceEventType, Listing


class TestTokenTransferHistorySearch:
    """
    Test Case for token.TransferHistory.Search
    """

    # テスト対象API
    apiurl_base = "/Token/{contract_address}/TransferHistory/Search"

    transaction_hash = (
        "0xc99116e27f0c40201a9e907ad5334f4477863269b90a94444d11a1bc9b9315e6"
    )
    token_address = "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740"
    from_address = "0xF13D2aCe101F1e4B55d96d66fBF18aD8a8aF22bF"
    to_address = "0x6431d02363FC69fFD9F69CAa4E05E96d4e79f3da"

    @staticmethod
    def insert_listing(session: Session, listing: dict):
        _listing = Listing()
        _listing.token_address = listing["token_address"]
        _listing.is_public = listing["is_public"]
        session.add(_listing)

    @staticmethod
    def insert_transfer_event(
        session: Session,
        transfer_event: dict,
        transfer_source_event: IDXTransferSourceEventType = IDXTransferSourceEventType.TRANSFER,
        transfer_event_data: dict | None = None,
        created: datetime | None = None,
    ):
        _transfer = IDXTransfer()
        _transfer.transaction_hash = transfer_event["transaction_hash"]
        _transfer.token_address = transfer_event["token_address"]
        _transfer.from_address = transfer_event["from_address"]
        _transfer.to_address = transfer_event["to_address"]
        _transfer.value = transfer_event["value"]
        _transfer.source_event = transfer_source_event.value
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
    # Transferイベントなし
    def test_normal_1(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={})

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 0,
            "offset": None,
            "limit": None,
            "total": 0,
        }
        assert resp.json()["data"]["transfer_history"] == assumed_body

    # Normal_2
    # Transferイベントあり：1件
    # offset=設定なし、 limit=設定なし
    def test_normal_2(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_event = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(session, transfer_event=transfer_event)

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 1,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 1
        assert data[0]["transaction_hash"] == transfer_event["transaction_hash"]
        assert data[0]["token_address"] == transfer_event["token_address"]
        assert data[0]["from_address"] == transfer_event["from_address"]
        assert data[0]["to_address"] == transfer_event["to_address"]
        assert data[0]["value"] == transfer_event["value"]

    # Normal_3_1
    # Transferイベントあり：2件
    def test_normal_3(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.to_address,
            "to_address": self.from_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 2,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 2
        assert data[0]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_1["token_address"]
        assert data[0]["from_address"] == transfer_event_1["from_address"]
        assert data[0]["to_address"] == transfer_event_1["to_address"]
        assert data[0]["value"] == transfer_event_1["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[0]["data"] is None
        assert data[0]["message"] is None

        assert data[1]["transaction_hash"] == transfer_event_2["transaction_hash"]
        assert data[1]["token_address"] == transfer_event_2["token_address"]
        assert data[1]["from_address"] == transfer_event_2["from_address"]
        assert data[1]["to_address"] == transfer_event_2["to_address"]
        assert data[1]["value"] == transfer_event_2["value"]
        assert data[1]["source_event"] == IDXTransferSourceEventType.UNLOCK.value
        assert data[1]["data"] == {"message": "force_unlock"}
        assert data[1]["message"] == "force_unlock"

    # Normal_3_2
    # Transferイベントあり：2件
    # Filter(source_event)
    def test_normal_3_2(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.to_address,
            "to_address": self.from_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl, json={"source_event": IDXTransferSourceEventType.UNLOCK.value}
        )

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 1

        assert data[0]["transaction_hash"] == transfer_event_2["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_2["token_address"]
        assert data[0]["from_address"] == transfer_event_2["from_address"]
        assert data[0]["to_address"] == transfer_event_2["to_address"]
        assert data[0]["value"] == transfer_event_2["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.UNLOCK.value
        assert data[0]["data"] == {"message": "force_unlock"}
        assert data[0]["message"] == "force_unlock"

    # Normal_3_3
    # Transferイベントあり：2件
    # Filter(data)
    def test_normal_3_3(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.to_address,
            "to_address": self.from_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"data": "force_unlock"})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 1

        assert data[0]["transaction_hash"] == transfer_event_2["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_2["token_address"]
        assert data[0]["from_address"] == transfer_event_2["from_address"]
        assert data[0]["to_address"] == transfer_event_2["to_address"]
        assert data[0]["value"] == transfer_event_2["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.UNLOCK.value
        assert data[0]["data"] == {"message": "force_unlock"}
        assert data[0]["message"] == "force_unlock"

    # Normal_3_4
    # Transferイベントあり：2件
    # Filter(account_address_list)
    def test_normal_3_4(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.to_address,
            "to_address": "other_address",
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"account_address_list": [self.from_address]})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 1,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 1

        assert data[0]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_1["token_address"]
        assert data[0]["from_address"] == transfer_event_1["from_address"]
        assert data[0]["to_address"] == transfer_event_1["to_address"]
        assert data[0]["value"] == transfer_event_1["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[0]["data"] is None
        assert data[0]["message"] is None

    # Normal_3_5_1
    # Transferイベントあり：2件
    # Filter(created_from)
    @pytest.mark.freeze_time(datetime(2023, 11, 6, 14, 0, 0, tzinfo=timezone.utc))
    @pytest.mark.parametrize(
        "created_from", ["2023-11-06T23:00:00+09:00", "2023-11-06T14:00:00+00:00"]
    )
    def test_normal_3_5_1(
        self, created_from: str, client: TestClient, session: Session
    ):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
            created=datetime.now(UTC).replace(tzinfo=None),
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
            created=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1),
        )
        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"created_from": created_from})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 1

        assert data[0]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_1["token_address"]
        assert data[0]["from_address"] == transfer_event_1["from_address"]
        assert data[0]["to_address"] == transfer_event_1["to_address"]
        assert data[0]["value"] == transfer_event_1["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[0]["data"] is None
        assert data[0]["message"] is None

    # Normal_3_5_2
    # Transferイベントあり：2件
    # Filter(created_to)
    @pytest.mark.freeze_time(datetime(2023, 11, 6, 14, 0, 0, tzinfo=timezone.utc))
    @pytest.mark.parametrize(
        "created_to", ["2023-11-06T23:00:00+09:00", "2023-11-06T14:00:00+00:00"]
    )
    def test_normal_3_5_2(self, created_to: str, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
            created=datetime.now(UTC).replace(tzinfo=None),
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
            created=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=1),
        )
        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"created_to": created_to})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 1

        assert data[0]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_1["token_address"]
        assert data[0]["from_address"] == transfer_event_1["from_address"]
        assert data[0]["to_address"] == transfer_event_1["to_address"]
        assert data[0]["value"] == transfer_event_1["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[0]["data"] is None
        assert data[0]["message"] is None

    # Normal_3_6_1
    # Transferイベントあり：2件
    # Filter(value_operator: =)
    def test_normal_3_6_1(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
            created=datetime.now(UTC).replace(tzinfo=None),
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
            created=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=1),
        )
        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"value_operator": 0, "value": 10})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 1

        assert data[0]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_1["token_address"]
        assert data[0]["from_address"] == transfer_event_1["from_address"]
        assert data[0]["to_address"] == transfer_event_1["to_address"]
        assert data[0]["value"] == transfer_event_1["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[0]["data"] is None
        assert data[0]["message"] is None

    # Normal_3_6_2
    # Transferイベントあり：2件
    # Filter(value_operator: >=)
    def test_normal_3_6_2(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
            created=datetime.now(UTC).replace(tzinfo=None),
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
            created=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=1),
        )
        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"value_operator": 1, "value": 15})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 1

        assert data[0]["transaction_hash"] == transfer_event_2["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_2["token_address"]
        assert data[0]["from_address"] == transfer_event_2["from_address"]
        assert data[0]["to_address"] == transfer_event_2["to_address"]
        assert data[0]["value"] == transfer_event_2["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.UNLOCK.value
        assert data[0]["data"] == {"message": "force_unlock"}
        assert data[0]["message"] == "force_unlock"

    # Normal_3_6_3
    # Transferイベントあり：2件
    # Filter(value_operator: <=)
    def test_normal_3_6_3(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
            created=datetime.now(UTC).replace(tzinfo=None),
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
            created=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=1),
        )
        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"value_operator": 2, "value": 10})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 1

        assert data[0]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_1["token_address"]
        assert data[0]["from_address"] == transfer_event_1["from_address"]
        assert data[0]["to_address"] == transfer_event_1["to_address"]
        assert data[0]["value"] == transfer_event_1["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[0]["data"] is None
        assert data[0]["message"] is None

    # Normal_3_7
    # Transferイベントあり：2件
    # Filter(transaction_hash)
    def test_normal_3_7(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": "other_transaction_hash",
            "token_address": self.token_address,
            "from_address": self.to_address,
            "to_address": self.from_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl, json={"transaction_hash": self.transaction_hash[0:5]}
        )

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 1

        assert data[0]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_1["token_address"]
        assert data[0]["from_address"] == transfer_event_1["from_address"]
        assert data[0]["to_address"] == transfer_event_1["to_address"]
        assert data[0]["value"] == transfer_event_1["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[0]["data"] is None
        assert data[0]["message"] is None

    # Normal_3_8
    # Transferイベントあり：2件
    # Filter(from_address)
    def test_normal_3_8(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": "other_from_address",
            "to_address": self.to_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"from_address": self.from_address[0:5]})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 1

        assert data[0]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_1["token_address"]
        assert data[0]["from_address"] == transfer_event_1["from_address"]
        assert data[0]["to_address"] == transfer_event_1["to_address"]
        assert data[0]["value"] == transfer_event_1["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[0]["data"] is None
        assert data[0]["message"] is None

    # Normal_3_9
    # Transferイベントあり：2件
    # Filter(to_address)
    def test_normal_3_9(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
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

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"to_address": self.to_address[0:5]})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 1

        assert data[0]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_1["token_address"]
        assert data[0]["from_address"] == transfer_event_1["from_address"]
        assert data[0]["to_address"] == transfer_event_1["to_address"]
        assert data[0]["value"] == transfer_event_1["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[0]["data"] is None
        assert data[0]["message"] is None

    # Normal_4_1_1
    # Transferイベントあり：2件
    # sort_order=from_account_address_list(asc)
    def test_normal_4_1_1(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": "0x0000000000000000000000000000000000000000",
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": "0x0000000000000000000000000000000000000001",
            "to_address": self.to_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        # ３件目
        transfer_event_3 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": "0x0000000000000000000000000000000000000002",
            "to_address": self.to_address,
            "value": 30,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_3,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={
                "account_address_list": [
                    "0x0000000000000000000000000000000000000001",
                    "0x0000000000000000000000000000000000000000",
                    "0x0000000000000000000000000000000000000004",
                    "0x0000000000000000000000000000000000000002",
                ],
                "sort_item": "from_account_address_list",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 3

        assert data[0]["transaction_hash"] == transfer_event_2["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_2["token_address"]
        assert data[0]["from_address"] == transfer_event_2["from_address"]
        assert data[0]["to_address"] == transfer_event_2["to_address"]
        assert data[0]["value"] == transfer_event_2["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.UNLOCK.value
        assert data[0]["data"] == {"message": "force_unlock"}
        assert data[0]["message"] == "force_unlock"

        assert data[1]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[1]["token_address"] == transfer_event_1["token_address"]
        assert data[1]["from_address"] == transfer_event_1["from_address"]
        assert data[1]["to_address"] == transfer_event_1["to_address"]
        assert data[1]["value"] == transfer_event_1["value"]
        assert data[1]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[1]["data"] is None
        assert data[1]["message"] is None

        assert data[2]["transaction_hash"] == transfer_event_3["transaction_hash"]
        assert data[2]["token_address"] == transfer_event_3["token_address"]
        assert data[2]["from_address"] == transfer_event_3["from_address"]
        assert data[2]["to_address"] == transfer_event_3["to_address"]
        assert data[2]["value"] == transfer_event_3["value"]
        assert data[2]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[2]["data"] is None
        assert data[2]["message"] is None

    # Normal_4_1_2
    # Transferイベントあり：2件
    # sort_order=from_account_address_list(desc)
    def test_normal_4_1_2(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": "0x0000000000000000000000000000000000000000",
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": "0x0000000000000000000000000000000000000001",
            "to_address": self.to_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        # ３件目
        transfer_event_3 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": "0x0000000000000000000000000000000000000002",
            "to_address": self.to_address,
            "value": 30,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_3,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={
                "account_address_list": [
                    "0x0000000000000000000000000000000000000001",
                    "0x0000000000000000000000000000000000000000",
                    "0x0000000000000000000000000000000000000004",
                    "0x0000000000000000000000000000000000000002",
                ],
                "sort_item": "from_account_address_list",
                "sort_order": 1,
            },
        )

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 3

        assert data[0]["transaction_hash"] == transfer_event_3["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_3["token_address"]
        assert data[0]["from_address"] == transfer_event_3["from_address"]
        assert data[0]["to_address"] == transfer_event_3["to_address"]
        assert data[0]["value"] == transfer_event_3["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[0]["data"] is None

        assert data[1]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[1]["token_address"] == transfer_event_1["token_address"]
        assert data[1]["from_address"] == transfer_event_1["from_address"]
        assert data[1]["to_address"] == transfer_event_1["to_address"]
        assert data[1]["value"] == transfer_event_1["value"]
        assert data[1]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[1]["data"] is None

        assert data[2]["transaction_hash"] == transfer_event_2["transaction_hash"]
        assert data[2]["token_address"] == transfer_event_2["token_address"]
        assert data[2]["from_address"] == transfer_event_2["from_address"]
        assert data[2]["to_address"] == transfer_event_2["to_address"]
        assert data[2]["value"] == transfer_event_2["value"]
        assert data[2]["source_event"] == IDXTransferSourceEventType.UNLOCK.value
        assert data[2]["data"] == {"message": "force_unlock"}

    # Normal_4_2_1
    # Transferイベントあり：2件
    # sort_order=to_account_address_list(asc)
    def test_normal_4_2_1(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000000",
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.to_address,
            "to_address": "0x0000000000000000000000000000000000000001",
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        # ３件目
        transfer_event_3 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000002",
            "value": 30,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_3,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={
                "account_address_list": [
                    "0x0000000000000000000000000000000000000001",
                    "0x0000000000000000000000000000000000000000",
                    "0x0000000000000000000000000000000000000004",
                    "0x0000000000000000000000000000000000000002",
                ],
                "sort_item": "to_account_address_list",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 3

        assert data[0]["transaction_hash"] == transfer_event_2["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_2["token_address"]
        assert data[0]["from_address"] == transfer_event_2["from_address"]
        assert data[0]["to_address"] == transfer_event_2["to_address"]
        assert data[0]["value"] == transfer_event_2["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.UNLOCK.value
        assert data[0]["data"] == {"message": "force_unlock"}

        assert data[1]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[1]["token_address"] == transfer_event_1["token_address"]
        assert data[1]["from_address"] == transfer_event_1["from_address"]
        assert data[1]["to_address"] == transfer_event_1["to_address"]
        assert data[1]["value"] == transfer_event_1["value"]
        assert data[1]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[1]["data"] is None

        assert data[2]["transaction_hash"] == transfer_event_3["transaction_hash"]
        assert data[2]["token_address"] == transfer_event_3["token_address"]
        assert data[2]["from_address"] == transfer_event_3["from_address"]
        assert data[2]["to_address"] == transfer_event_3["to_address"]
        assert data[2]["value"] == transfer_event_3["value"]
        assert data[2]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[2]["data"] is None

    # Normal_4_2_2
    # Transferイベントあり：2件
    # sort_order=to_account_address_list(desc)
    def test_normal_4_2_2(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000000",
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.to_address,
            "to_address": "0x0000000000000000000000000000000000000001",
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        # ３件目
        transfer_event_3 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000002",
            "value": 30,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_3,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={
                "account_address_list": [
                    "0x0000000000000000000000000000000000000001",
                    "0x0000000000000000000000000000000000000000",
                    "0x0000000000000000000000000000000000000004",
                    "0x0000000000000000000000000000000000000002",
                ],
                "sort_item": "to_account_address_list",
                "sort_order": 1,
            },
        )

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 3

        assert data[0]["transaction_hash"] == transfer_event_3["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_3["token_address"]
        assert data[0]["from_address"] == transfer_event_3["from_address"]
        assert data[0]["to_address"] == transfer_event_3["to_address"]
        assert data[0]["value"] == transfer_event_3["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[0]["data"] is None
        assert data[0]["message"] is None

        assert data[1]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[1]["token_address"] == transfer_event_1["token_address"]
        assert data[1]["from_address"] == transfer_event_1["from_address"]
        assert data[1]["to_address"] == transfer_event_1["to_address"]
        assert data[1]["value"] == transfer_event_1["value"]
        assert data[1]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[1]["data"] is None
        assert data[1]["message"] is None

        assert data[2]["transaction_hash"] == transfer_event_2["transaction_hash"]
        assert data[2]["token_address"] == transfer_event_2["token_address"]
        assert data[2]["from_address"] == transfer_event_2["from_address"]
        assert data[2]["to_address"] == transfer_event_2["to_address"]
        assert data[2]["value"] == transfer_event_2["value"]
        assert data[2]["source_event"] == IDXTransferSourceEventType.UNLOCK.value
        assert data[2]["data"] == {"message": "force_unlock"}
        assert data[2]["message"] == "force_unlock"

    # Normal_4_3
    # Transferイベントあり：2件
    # sort_order=from_address
    def test_normal_4_3(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000001",
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.to_address,
            "to_address": "0x0000000000000000000000000000000000000000",
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        # ３件目
        transfer_event_3 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000002",
            "value": 30,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_3,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"sort_item": "to_address", "sort_order": 1})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 3

        assert data[0]["transaction_hash"] == transfer_event_3["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_3["token_address"]
        assert data[0]["from_address"] == transfer_event_3["from_address"]
        assert data[0]["to_address"] == transfer_event_3["to_address"]
        assert data[0]["value"] == transfer_event_3["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[0]["data"] is None

        assert data[1]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[1]["token_address"] == transfer_event_1["token_address"]
        assert data[1]["from_address"] == transfer_event_1["from_address"]
        assert data[1]["to_address"] == transfer_event_1["to_address"]
        assert data[1]["value"] == transfer_event_1["value"]
        assert data[1]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[1]["data"] is None

        assert data[2]["transaction_hash"] == transfer_event_2["transaction_hash"]
        assert data[2]["token_address"] == transfer_event_2["token_address"]
        assert data[2]["from_address"] == transfer_event_2["from_address"]
        assert data[2]["to_address"] == transfer_event_2["to_address"]
        assert data[2]["value"] == transfer_event_2["value"]
        assert data[2]["source_event"] == IDXTransferSourceEventType.UNLOCK.value
        assert data[2]["data"] == {"message": "force_unlock"}

    # Normal_4_4
    # Transferイベントあり：2件
    # sort_order=from_address
    def test_normal_4_4(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": "0x0000000000000000000000000000000000000001",
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": "0x0000000000000000000000000000000000000000",
            "to_address": self.to_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        # ３件目
        transfer_event_3 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": "0x0000000000000000000000000000000000000002",
            "to_address": self.to_address,
            "value": 30,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_3,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"sort_item": "from_address", "sort_order": 1})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 3

        assert data[0]["transaction_hash"] == transfer_event_3["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_3["token_address"]
        assert data[0]["from_address"] == transfer_event_3["from_address"]
        assert data[0]["to_address"] == transfer_event_3["to_address"]
        assert data[0]["value"] == transfer_event_3["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[0]["data"] is None

        assert data[1]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[1]["token_address"] == transfer_event_1["token_address"]
        assert data[1]["from_address"] == transfer_event_1["from_address"]
        assert data[1]["to_address"] == transfer_event_1["to_address"]
        assert data[1]["value"] == transfer_event_1["value"]
        assert data[1]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[1]["data"] is None

        assert data[2]["transaction_hash"] == transfer_event_2["transaction_hash"]
        assert data[2]["token_address"] == transfer_event_2["token_address"]
        assert data[2]["from_address"] == transfer_event_2["from_address"]
        assert data[2]["to_address"] == transfer_event_2["to_address"]
        assert data[2]["value"] == transfer_event_2["value"]
        assert data[2]["source_event"] == IDXTransferSourceEventType.UNLOCK.value
        assert data[2]["data"] == {"message": "force_unlock"}

    # Normal_4_5
    # Transferイベントあり：2件
    # sort_order=created
    def test_normal_4_5(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
            created=datetime(2023, 11, 6, 20, 0, 0),
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
            created=datetime(2023, 11, 6, 20, 0, 1),
        )

        # ３件目
        transfer_event_3 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 30,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_3,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
            created=datetime(2023, 11, 6, 20, 0, 2),
        )

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"sort_item": "created", "sort_order": 1})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 3

        assert data[0]["transaction_hash"] == transfer_event_3["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_3["token_address"]
        assert data[0]["from_address"] == transfer_event_3["from_address"]
        assert data[0]["to_address"] == transfer_event_3["to_address"]
        assert data[0]["value"] == transfer_event_3["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[0]["data"] is None
        assert data[0]["message"] is None

        assert data[1]["transaction_hash"] == transfer_event_2["transaction_hash"]
        assert data[1]["token_address"] == transfer_event_2["token_address"]
        assert data[1]["from_address"] == transfer_event_2["from_address"]
        assert data[1]["to_address"] == transfer_event_2["to_address"]
        assert data[1]["value"] == transfer_event_2["value"]
        assert data[1]["source_event"] == IDXTransferSourceEventType.UNLOCK.value
        assert data[1]["data"] == {"message": "force_unlock"}
        assert data[1]["message"] == "force_unlock"

        assert data[2]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[2]["token_address"] == transfer_event_1["token_address"]
        assert data[2]["from_address"] == transfer_event_1["from_address"]
        assert data[2]["to_address"] == transfer_event_1["to_address"]
        assert data[2]["value"] == transfer_event_1["value"]
        assert data[2]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[2]["data"] is None
        assert data[2]["message"] is None

    # Normal_5_1
    # offset=1, limit=設定なし
    # Transferイベントあり：2件
    def test_normal_5_1(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.to_address,
            "to_address": self.from_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"offset": 1})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 2,
            "offset": 1,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 1

        assert data[0]["transaction_hash"] == transfer_event_2["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_2["token_address"]
        assert data[0]["from_address"] == transfer_event_2["from_address"]
        assert data[0]["to_address"] == transfer_event_2["to_address"]
        assert data[0]["value"] == transfer_event_2["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.UNLOCK.value
        assert data[0]["data"] == {"message": "force_unlock"}
        assert data[0]["message"] == "force_unlock"

    # Normal_5_2
    # offset=0, limit=設定なし
    # Transferイベントあり：2件
    def test_normal_5_2(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.to_address,
            "to_address": self.from_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"offset": 0})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 2,
            "offset": 0,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 2

        assert data[0]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_1["token_address"]
        assert data[0]["from_address"] == transfer_event_1["from_address"]
        assert data[0]["to_address"] == transfer_event_1["to_address"]
        assert data[0]["value"] == transfer_event_1["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[0]["data"] is None
        assert data[0]["message"] is None

        assert data[1]["transaction_hash"] == transfer_event_2["transaction_hash"]
        assert data[1]["token_address"] == transfer_event_2["token_address"]
        assert data[1]["from_address"] == transfer_event_2["from_address"]
        assert data[1]["to_address"] == transfer_event_2["to_address"]
        assert data[1]["value"] == transfer_event_2["value"]
        assert data[1]["source_event"] == IDXTransferSourceEventType.UNLOCK.value
        assert data[1]["data"] == {"message": "force_unlock"}
        assert data[1]["message"] == "force_unlock"

    # Normal_5_3
    # offset =設定なし, limit=1
    # Transferイベントあり：2件
    def test_normal_5_3(self, client: TestClient, session: Session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_1,
            transfer_source_event=IDXTransferSourceEventType.TRANSFER,
            transfer_event_data=None,
        )

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.to_address,
            "to_address": self.from_address,
            "value": 20,
        }
        self.insert_transfer_event(
            session=session,
            transfer_event=transfer_event_2,
            transfer_source_event=IDXTransferSourceEventType.UNLOCK,
            transfer_event_data={"message": "force_unlock"},
        )

        session.commit()

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"limit": 1})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 2,
            "offset": None,
            "limit": 1,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_history"]
        assert len(data) == 1

        assert data[0]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert data[0]["token_address"] == transfer_event_1["token_address"]
        assert data[0]["from_address"] == transfer_event_1["from_address"]
        assert data[0]["to_address"] == transfer_event_1["to_address"]
        assert data[0]["value"] == transfer_event_1["value"]
        assert data[0]["source_event"] == IDXTransferSourceEventType.TRANSFER.value
        assert data[0]["data"] is None
        assert data[0]["message"] is None

    ####################################################################
    # Error
    ####################################################################

    # Error_1
    # 無効なコントラクトアドレス
    # 400
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
    # 取扱していないトークン
    # 404
    def test_error_2(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={})

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": "token_address: " + self.token_address,
        }

    # Error_3_1
    # offset validation : String
    # 400
    def test_error_3_1(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"offset": "string"})

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": "string",
                    "loc": ["body", "offset"],
                    "msg": "Input should be a valid integer, unable to parse "
                    "string as an integer",
                    "type": "int_parsing",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_3_2
    # offset validation : 負値
    # 400
    def test_error_3_2(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"offset": -1})

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"ge": 0},
                    "input": -1,
                    "loc": ["body", "offset"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_3_3
    # offset validation : 小数
    # 400
    def test_error_3_3(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"offset": 1.5})

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": 1.5,
                    "loc": ["body", "offset"],
                    "msg": "Input should be a valid integer, got a number with a fractional part",
                    "type": "int_from_float",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_4_1
    # limit validation : String
    # 400
    def test_error_4_1(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"limit": "string"})

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": "string",
                    "loc": ["body", "limit"],
                    "msg": "Input should be a valid integer, unable to parse "
                    "string as an integer",
                    "type": "int_parsing",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_4_2
    # limit validation : 負値
    # 400
    def test_error_4_2(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"limit": -1})

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"ge": 0},
                    "input": -1,
                    "loc": ["body", "limit"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_4_3
    # limit validation : 小数
    # 400
    def test_error_4_3(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"limit": 1.5})

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": 1.5,
                    "loc": ["body", "limit"],
                    "msg": "Input should be a valid integer, got a number with a fractional part",
                    "type": "int_from_float",
                }
            ],
            "message": "Invalid Parameter",
        }
