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
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import TZ
from app.model.db import IDXTransferApproval, Listing

UTC = timezone(timedelta(hours=0), "UTC")
local_tz = ZoneInfo(TZ)


class TestTokenTransferApprovalHistorySearch:
    """
    Test Case for token.TransferApprovalHistory.Search
    """

    # test target API
    apiurl_base = "/Token/{contract_address}/TransferApprovalHistory/Search"

    token_address = "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740"
    exchange_address = "0x4Dd3E334ea551402482003bbf72031b366155B0A"
    application_id = 123
    from_address = "0xF13D2aCe101F1e4B55d96d66fBF18aD8a8aF22bF"
    to_address = "0x6431d02363FC69fFD9F69CAa4E05E96d4e79f3da"

    @staticmethod
    def insert_listing(session, listing: dict):
        _listing = Listing()
        _listing.token_address = listing["token_address"]
        _listing.is_public = listing["is_public"]
        session.add(_listing)

    @staticmethod
    def insert_transfer_approval(session, transfer_approval: dict):
        _transfer_approval = IDXTransferApproval()
        _transfer_approval.token_address = transfer_approval["token_address"]
        _transfer_approval.exchange_address = transfer_approval.get("exchange_address")
        _transfer_approval.application_id = transfer_approval["application_id"]
        _transfer_approval.from_address = transfer_approval["from_address"]
        _transfer_approval.to_address = transfer_approval["to_address"]
        _transfer_approval.value = transfer_approval.get("value")  # nullable
        _transfer_approval.application_datetime = transfer_approval.get(
            "application_datetime"
        )  # nullable
        _transfer_approval.application_blocktimestamp = transfer_approval.get(
            "application_blocktimestamp"
        )  # nullable
        _transfer_approval.approval_datetime = transfer_approval.get(
            "approval_datetime"
        )  # nullable
        _transfer_approval.approval_blocktimestamp = transfer_approval.get(
            "approval_blocktimestamp"
        )  # nullable
        _transfer_approval.cancelled = transfer_approval.get("cancelled")
        _transfer_approval.transfer_approved = transfer_approval.get(
            "transfer_approved"
        )
        session.add(_transfer_approval)

    ####################################################################
    # Normal
    ####################################################################

    # Normal_1
    # No data
    def test_normal_1(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # request target API
        resp = client.post(
            self.apiurl_base.format(contract_address=self.token_address),
            json={},
        )

        # assertion
        assumed_body = {
            "result_set": {"count": 0, "offset": None, "limit": None, "total": 0},
            "transfer_approval_history": [],
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # Normal_2_1
    # Data exists
    # offset=設定なし、 limit=設定なし
    def test_normal_2_1(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        before_datetime = (
            datetime.utcnow()
            .replace(tzinfo=UTC)
            .astimezone(local_tz)
            .strftime("%Y/%m/%d %H:%M:%S.%f")
        )
        time.sleep(1)

        for i in range(2, -1, -1):
            transfer_approval = {
                "token_address": self.token_address,
                "application_id": i,
                "from_address": self.from_address,
                "to_address": self.to_address,
                "value": 10,
                "application_datetime": datetime.utcnow(),
                "application_blocktimestamp": datetime.utcnow(),
                "approval_datetime": datetime.utcnow(),
                "approval_blocktimestamp": datetime.utcnow(),
                "cancelled": False,
                "transfer_approved": True,
            }
            self.insert_transfer_approval(session, transfer_approval=transfer_approval)

        time.sleep(1)
        after_datetime = (
            datetime.utcnow()
            .replace(tzinfo=UTC)
            .astimezone(local_tz)
            .strftime("%Y/%m/%d %H:%M:%S.%f")
        )

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_approval_history"]
        for i, item in enumerate(data):
            assert item["token_address"] == self.token_address
            assert item["exchange_address"] is None
            assert item["application_id"] == i
            assert item["from_address"] == self.from_address
            assert item["to_address"] == self.to_address
            assert before_datetime < item["application_datetime"] < after_datetime
            assert before_datetime < item["application_blocktimestamp"] < after_datetime
            assert before_datetime < item["approval_datetime"] < after_datetime
            assert before_datetime < item["approval_blocktimestamp"] < after_datetime
            assert item["cancelled"] is False
            assert item["transfer_approved"] is True

    # Normal_2_2
    # Data exists (exchange events)
    # offset=設定なし、 limit=設定なし
    def test_normal_2_2(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        before_datetime = (
            datetime.utcnow()
            .replace(tzinfo=UTC)
            .astimezone(local_tz)
            .strftime("%Y/%m/%d %H:%M:%S.%f")
        )
        time.sleep(1)

        for i in range(2, -1, -1):
            transfer_approval = {
                "token_address": self.token_address,
                "exchange_address": self.exchange_address,
                "application_id": i,
                "from_address": self.from_address,
                "to_address": self.to_address,
                "value": 10,
                "application_datetime": datetime.utcnow(),
                "application_blocktimestamp": datetime.utcnow(),
                "approval_datetime": datetime.utcnow(),
                "approval_blocktimestamp": datetime.utcnow(),
                "cancelled": False,
                "transfer_approved": True,
            }
            self.insert_transfer_approval(session, transfer_approval=transfer_approval)

        time.sleep(1)
        after_datetime = (
            datetime.utcnow()
            .replace(tzinfo=UTC)
            .astimezone(local_tz)
            .strftime("%Y/%m/%d %H:%M:%S.%f")
        )

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_approval_history"]
        for i, item in enumerate(data):
            assert item["token_address"] == self.token_address
            assert item["exchange_address"] == self.exchange_address
            assert item["application_id"] == i
            assert item["from_address"] == self.from_address
            assert item["to_address"] == self.to_address
            assert before_datetime < item["application_datetime"] < after_datetime
            assert before_datetime < item["application_blocktimestamp"] < after_datetime
            assert before_datetime < item["approval_datetime"] < after_datetime
            assert before_datetime < item["approval_blocktimestamp"] < after_datetime
            assert item["cancelled"] is False
            assert item["transfer_approved"] is True

    # Normal_2_3
    # Data exists (account address list)
    # offset=設定なし、 limit=設定なし
    def test_normal_2_3(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": "other_address",
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={"account_address_list": [self.from_address]},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 1,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 1
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == self.to_address
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

    # Normal_2_4_1
    # Data exists (application datetime from)
    # offset=設定なし、 limit=設定なし
    @pytest.mark.freeze_time(datetime(2023, 11, 6, 14, 0, 0, tzinfo=timezone.utc))
    @pytest.mark.parametrize(
        "application_datetime_from",
        ["2023-11-06T23:00:00+09:00", "2023-11-06T14:00:00+00:00"],
    )
    def test_normal_2_4_1(
        self, application_datetime_from: str, client: TestClient, session: Session
    ):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow() - timedelta(seconds=1),
            "application_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "approval_datetime": datetime.utcnow() - timedelta(seconds=1),
            "approval_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={"application_datetime_from": application_datetime_from},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 2
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == self.to_address
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

    # Normal_2_4_2
    # Data exists (application datetime to)
    # offset=設定なし、 limit=設定なし
    @pytest.mark.freeze_time(datetime(2023, 11, 6, 14, 0, 0, tzinfo=timezone.utc))
    @pytest.mark.parametrize(
        "application_datetime_from",
        ["2023-11-06T22:59:59+09:00", "2023-11-06T13:59:59+00:00"],
    )
    def test_normal_2_4_2(
        self, application_datetime_from: str, client: TestClient, session: Session
    ):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow() - timedelta(seconds=1),
            "application_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "approval_datetime": datetime.utcnow() - timedelta(seconds=1),
            "approval_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={"application_datetime_to": application_datetime_from},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 1
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == self.to_address
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

    # Normal_2_5_1
    # Data exists (application block timestamp from)
    # offset=設定なし、 limit=設定なし
    @pytest.mark.freeze_time(datetime(2023, 11, 6, 14, 0, 0, tzinfo=timezone.utc))
    @pytest.mark.parametrize(
        "application_blocktimestamp_from",
        ["2023-11-06T23:00:00+09:00", "2023-11-06T14:00:00+00:00"],
    )
    def test_normal_2_5_1(
        self, application_blocktimestamp_from: str, client: TestClient, session: Session
    ):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow() - timedelta(seconds=1),
            "application_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "approval_datetime": datetime.utcnow() - timedelta(seconds=1),
            "approval_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={"application_blocktimestamp_from": application_blocktimestamp_from},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 2
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == self.to_address
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

    # Normal_2_5_2
    # Data exists (application block timestamp to)
    # offset=設定なし、 limit=設定なし
    @pytest.mark.freeze_time(datetime(2023, 11, 6, 14, 0, 0, tzinfo=timezone.utc))
    @pytest.mark.parametrize(
        "application_blocktimestamp_to",
        ["2023-11-06T22:59:59+09:00", "2023-11-06T13:59:59+00:00"],
    )
    def test_normal_2_5_2(
        self, application_blocktimestamp_to: str, client: TestClient, session: Session
    ):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow() - timedelta(seconds=1),
            "application_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "approval_datetime": datetime.utcnow() - timedelta(seconds=1),
            "approval_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={"application_blocktimestamp_to": application_blocktimestamp_to},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 1
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == self.to_address
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

    # Normal_2_6_1
    # Data exists (application datetime from)
    # offset=設定なし、 limit=設定なし
    @pytest.mark.freeze_time(datetime(2023, 11, 6, 14, 0, 0, tzinfo=timezone.utc))
    @pytest.mark.parametrize(
        "approval_datetime_from",
        ["2023-11-06T23:00:00+09:00", "2023-11-06T14:00:00+00:00"],
    )
    def test_normal_2_6_1(
        self, approval_datetime_from: str, client: TestClient, session: Session
    ):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow() - timedelta(seconds=1),
            "application_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "approval_datetime": datetime.utcnow() - timedelta(seconds=1),
            "approval_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={"approval_datetime_from": approval_datetime_from},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 2
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == self.to_address
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

    # Normal_2_6_2
    # Data exists (application datetime to)
    # offset=設定なし、 limit=設定なし
    @pytest.mark.freeze_time(datetime(2023, 11, 6, 14, 0, 0, tzinfo=timezone.utc))
    @pytest.mark.parametrize(
        "approval_datetime_from",
        ["2023-11-06T22:59:59+09:00", "2023-11-06T13:59:59+00:00"],
    )
    def test_normal_2_6_2(
        self, approval_datetime_from: str, client: TestClient, session: Session
    ):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow() - timedelta(seconds=1),
            "application_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "approval_datetime": datetime.utcnow() - timedelta(seconds=1),
            "approval_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={"approval_datetime_to": approval_datetime_from},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 1
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == self.to_address
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

    # Normal_2_7_1
    # Data exists (application block timestamp from)
    # offset=設定なし、 limit=設定なし
    @pytest.mark.freeze_time(datetime(2023, 11, 6, 14, 0, 0, tzinfo=timezone.utc))
    @pytest.mark.parametrize(
        "approval_blocktimestamp_from",
        ["2023-11-06T23:00:00+09:00", "2023-11-06T14:00:00+00:00"],
    )
    def test_normal_2_7_1(
        self, approval_blocktimestamp_from: str, client: TestClient, session: Session
    ):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow() - timedelta(seconds=1),
            "application_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "approval_datetime": datetime.utcnow() - timedelta(seconds=1),
            "approval_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={"approval_blocktimestamp_from": approval_blocktimestamp_from},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 2
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == self.to_address
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

    # Normal_2_7_2
    # Data exists (application block timestamp to)
    # offset=設定なし、 limit=設定なし
    @pytest.mark.freeze_time(datetime(2023, 11, 6, 14, 0, 0, tzinfo=timezone.utc))
    @pytest.mark.parametrize(
        "approval_blocktimestamp_to",
        ["2023-11-06T22:59:59+09:00", "2023-11-06T13:59:59+00:00"],
    )
    def test_normal_2_7_2(
        self, approval_blocktimestamp_to: str, client: TestClient, session: Session
    ):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow() - timedelta(seconds=1),
            "application_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "approval_datetime": datetime.utcnow() - timedelta(seconds=1),
            "approval_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={"approval_blocktimestamp_to": approval_blocktimestamp_to},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 1
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == self.to_address
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

    # Normal_2_8_1
    # Data exists (value_operator: =)
    # offset=設定なし、 limit=設定なし
    def test_normal_2_8_1(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 20,
            "application_datetime": datetime.utcnow() - timedelta(seconds=1),
            "application_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "approval_datetime": datetime.utcnow() - timedelta(seconds=1),
            "approval_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={"value": 10, "value_operator": 0},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 2
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == self.to_address
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

    # Normal_2_8_2
    # Data exists (value_operator: >=)
    # offset=設定なし、 limit=設定なし
    def test_normal_2_8_2(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 20,
            "application_datetime": datetime.utcnow() - timedelta(seconds=1),
            "application_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "approval_datetime": datetime.utcnow() - timedelta(seconds=1),
            "approval_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={"value": 20, "value_operator": 1},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 1
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == self.to_address
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

    # Normal_2_8_3
    # Data exists (value_operator: <=)
    # offset=設定なし、 limit=設定なし
    def test_normal_2_8_3(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 20,
            "application_datetime": datetime.utcnow() - timedelta(seconds=1),
            "application_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "approval_datetime": datetime.utcnow() - timedelta(seconds=1),
            "approval_blocktimestamp": datetime.utcnow() - timedelta(seconds=1),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={"value": 10, "value_operator": 2},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 2
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == self.to_address
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

    # Normal_3_1_1
    # sort_order=from_account_address_list(asc)
    def test_normal_3_1_1(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": "0x0000000000000000000000000000000000000001",
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": "0x0000000000000000000000000000000000000002",
            "to_address": self.to_address,
            "value": 20,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        transfer_approval_3 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 3,
            "from_address": "0x0000000000000000000000000000000000000003",
            "to_address": self.to_address,
            "value": 30,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_3)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={
                "account_address_list": [
                    "0x0000000000000000000000000000000000000001",
                    "0x0000000000000000000000000000000000000002",
                    "0x0000000000000000000000000000000000000004",
                    "0x0000000000000000000000000000000000000003",
                ],
                "sort_item": "from_account_address_list",
                "sort_order": 1,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 1
        assert data[0]["from_address"] == "0x0000000000000000000000000000000000000001"
        assert data[0]["to_address"] == self.to_address
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

        assert data[1]["token_address"] == self.token_address
        assert data[1]["exchange_address"] == self.exchange_address
        assert data[1]["application_id"] == 2
        assert data[1]["from_address"] == "0x0000000000000000000000000000000000000002"
        assert data[1]["to_address"] == self.to_address
        assert data[1]["cancelled"] is False
        assert data[1]["transfer_approved"] is True

        assert data[2]["token_address"] == self.token_address
        assert data[2]["exchange_address"] == self.exchange_address
        assert data[2]["application_id"] == 3
        assert data[2]["from_address"] == "0x0000000000000000000000000000000000000003"
        assert data[2]["to_address"] == self.to_address
        assert data[2]["cancelled"] is False
        assert data[2]["transfer_approved"] is True

    # Normal_3_1_2
    # sort_order=from_account_address_list(desc)
    def test_normal_3_1_2(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": "0x0000000000000000000000000000000000000001",
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": "0x0000000000000000000000000000000000000002",
            "to_address": self.to_address,
            "value": 20,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        transfer_approval_3 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 3,
            "from_address": "0x0000000000000000000000000000000000000003",
            "to_address": self.to_address,
            "value": 30,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_3)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={
                "account_address_list": [
                    "0x0000000000000000000000000000000000000003",
                    "0x0000000000000000000000000000000000000004",
                    "0x0000000000000000000000000000000000000002",
                    "0x0000000000000000000000000000000000000001",
                ],
                "sort_item": "from_account_address_list",
                "sort_order": 0,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 1
        assert data[0]["from_address"] == "0x0000000000000000000000000000000000000001"
        assert data[0]["to_address"] == self.to_address
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

        assert data[1]["token_address"] == self.token_address
        assert data[1]["exchange_address"] == self.exchange_address
        assert data[1]["application_id"] == 2
        assert data[1]["from_address"] == "0x0000000000000000000000000000000000000002"
        assert data[1]["to_address"] == self.to_address
        assert data[1]["cancelled"] is False
        assert data[1]["transfer_approved"] is True

        assert data[2]["token_address"] == self.token_address
        assert data[2]["exchange_address"] == self.exchange_address
        assert data[2]["application_id"] == 3
        assert data[2]["from_address"] == "0x0000000000000000000000000000000000000003"
        assert data[2]["to_address"] == self.to_address
        assert data[2]["cancelled"] is False
        assert data[2]["transfer_approved"] is True

    # Normal_3_2_1
    # sort_order=to_account_address_list(asc)
    def test_normal_3_2_1(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000001",
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000002",
            "value": 20,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        transfer_approval_3 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 3,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000003",
            "value": 30,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_3)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={
                "account_address_list": [
                    "0x0000000000000000000000000000000000000003",
                    "0x0000000000000000000000000000000000000004",
                    "0x0000000000000000000000000000000000000002",
                    "0x0000000000000000000000000000000000000001",
                ],
                "sort_item": "to_account_address_list",
                "sort_order": 0,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 1
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == "0x0000000000000000000000000000000000000001"
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

        assert data[1]["token_address"] == self.token_address
        assert data[1]["exchange_address"] == self.exchange_address
        assert data[1]["application_id"] == 2
        assert data[1]["from_address"] == self.from_address
        assert data[1]["to_address"] == "0x0000000000000000000000000000000000000002"
        assert data[1]["cancelled"] is False
        assert data[1]["transfer_approved"] is True

        assert data[2]["token_address"] == self.token_address
        assert data[2]["exchange_address"] == self.exchange_address
        assert data[2]["application_id"] == 3
        assert data[2]["from_address"] == self.from_address
        assert data[2]["to_address"] == "0x0000000000000000000000000000000000000003"
        assert data[2]["cancelled"] is False
        assert data[2]["transfer_approved"] is True

    # Normal_3_2_2
    # sort_order=to_account_address_list(asc)
    def test_normal_3_2_2(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000001",
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000002",
            "value": 20,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        transfer_approval_3 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 3,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000003",
            "value": 30,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_3)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={
                "account_address_list": [
                    "0x0000000000000000000000000000000000000001",
                    "0x0000000000000000000000000000000000000004",
                    "0x0000000000000000000000000000000000000002",
                    "0x0000000000000000000000000000000000000003",
                ],
                "sort_item": "to_account_address_list",
                "sort_order": 1,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 1
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == "0x0000000000000000000000000000000000000001"
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

        assert data[1]["token_address"] == self.token_address
        assert data[1]["exchange_address"] == self.exchange_address
        assert data[1]["application_id"] == 2
        assert data[1]["from_address"] == self.from_address
        assert data[1]["to_address"] == "0x0000000000000000000000000000000000000002"
        assert data[1]["cancelled"] is False
        assert data[1]["transfer_approved"] is True

        assert data[2]["token_address"] == self.token_address
        assert data[2]["exchange_address"] == self.exchange_address
        assert data[2]["application_id"] == 3
        assert data[2]["from_address"] == self.from_address
        assert data[2]["to_address"] == "0x0000000000000000000000000000000000000003"
        assert data[2]["cancelled"] is False
        assert data[2]["transfer_approved"] is True

    # Normal_3_3
    # sort_order=from_address
    def test_normal_3_3(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": "0x0000000000000000000000000000000000000001",
            "to_address": self.to_address,
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": "0x0000000000000000000000000000000000000002",
            "to_address": self.to_address,
            "value": 20,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        transfer_approval_3 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 3,
            "from_address": "0x0000000000000000000000000000000000000003",
            "to_address": self.to_address,
            "value": 30,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_3)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={"sort_item": "from_address", "sort_order": 0},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 1
        assert data[0]["from_address"] == "0x0000000000000000000000000000000000000001"
        assert data[0]["to_address"] == self.to_address
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

        assert data[1]["token_address"] == self.token_address
        assert data[1]["exchange_address"] == self.exchange_address
        assert data[1]["application_id"] == 2
        assert data[1]["from_address"] == "0x0000000000000000000000000000000000000002"
        assert data[1]["to_address"] == self.to_address
        assert data[1]["cancelled"] is False
        assert data[1]["transfer_approved"] is True

        assert data[2]["token_address"] == self.token_address
        assert data[2]["exchange_address"] == self.exchange_address
        assert data[2]["application_id"] == 3
        assert data[2]["from_address"] == "0x0000000000000000000000000000000000000003"
        assert data[2]["to_address"] == self.to_address
        assert data[2]["cancelled"] is False
        assert data[2]["transfer_approved"] is True

    # Normal_3_4
    # sort_order=to_address
    def test_normal_3_4(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000001",
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000002",
            "value": 20,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        transfer_approval_3 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 3,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000003",
            "value": 30,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_3)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={
                "sort_item": "to_address",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 1
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == "0x0000000000000000000000000000000000000001"
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

        assert data[1]["token_address"] == self.token_address
        assert data[1]["exchange_address"] == self.exchange_address
        assert data[1]["application_id"] == 2
        assert data[1]["from_address"] == self.from_address
        assert data[1]["to_address"] == "0x0000000000000000000000000000000000000002"
        assert data[1]["cancelled"] is False
        assert data[1]["transfer_approved"] is True

        assert data[2]["token_address"] == self.token_address
        assert data[2]["exchange_address"] == self.exchange_address
        assert data[2]["application_id"] == 3
        assert data[2]["from_address"] == self.from_address
        assert data[2]["to_address"] == "0x0000000000000000000000000000000000000003"
        assert data[2]["cancelled"] is False
        assert data[2]["transfer_approved"] is True

    # Normal_3_5
    # sort_order=datetime
    @pytest.mark.parametrize(
        "sort_item",
        [
            "application_datetime",
            "application_blocktimestamp",
            "approval_datetime",
            "approval_blocktimestamp",
        ],
    )
    def test_normal_3_5(self, sort_item: str, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000001",
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000002",
            "value": 20,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        transfer_approval_3 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 3,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000003",
            "value": 30,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_3)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={
                "sort_item": sort_item,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 1
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == "0x0000000000000000000000000000000000000001"
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

        assert data[1]["token_address"] == self.token_address
        assert data[1]["exchange_address"] == self.exchange_address
        assert data[1]["application_id"] == 2
        assert data[1]["from_address"] == self.from_address
        assert data[1]["to_address"] == "0x0000000000000000000000000000000000000002"
        assert data[1]["cancelled"] is False
        assert data[1]["transfer_approved"] is True

        assert data[2]["token_address"] == self.token_address
        assert data[2]["exchange_address"] == self.exchange_address
        assert data[2]["application_id"] == 3
        assert data[2]["from_address"] == self.from_address
        assert data[2]["to_address"] == "0x0000000000000000000000000000000000000003"
        assert data[2]["cancelled"] is False
        assert data[2]["transfer_approved"] is True

    # Normal_3_6
    # sort_order=cancelled
    def test_normal_3_6(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_approval_1 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 1,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000001",
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": None,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_1)

        transfer_approval_2 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 2,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000002",
            "value": 20,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": None,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        transfer_approval_3 = {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": 3,
            "from_address": self.from_address,
            "to_address": "0x0000000000000000000000000000000000000003",
            "value": 30,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": True,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_3)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(
            apiurl,
            json={
                "sort_item": "cancelled",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_approval_history"]

        assert data[0]["token_address"] == self.token_address
        assert data[0]["exchange_address"] == self.exchange_address
        assert data[0]["application_id"] == 1
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == "0x0000000000000000000000000000000000000001"
        assert data[0]["cancelled"] is None
        assert data[0]["transfer_approved"] is True

        assert data[1]["token_address"] == self.token_address
        assert data[1]["exchange_address"] == self.exchange_address
        assert data[1]["application_id"] == 2
        assert data[1]["from_address"] == self.from_address
        assert data[1]["to_address"] == "0x0000000000000000000000000000000000000002"
        assert data[1]["cancelled"] is None
        assert data[1]["transfer_approved"] is True

        assert data[2]["token_address"] == self.token_address
        assert data[2]["exchange_address"] == self.exchange_address
        assert data[2]["application_id"] == 3
        assert data[2]["from_address"] == self.from_address
        assert data[2]["to_address"] == "0x0000000000000000000000000000000000000003"
        assert data[2]["cancelled"] is True
        assert data[2]["transfer_approved"] is True

    # Normal_4_1
    # Data exists
    # offset=1、 limit=設定なし
    def test_normal_4_1(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        before_datetime = (
            datetime.utcnow()
            .replace(tzinfo=UTC)
            .astimezone(local_tz)
            .strftime("%Y/%m/%d %H:%M:%S.%f")
        )
        time.sleep(1)

        for i in range(2, -1, -1):
            transfer_approval = {
                "token_address": self.token_address,
                "application_id": i,
                "from_address": self.from_address,
                "to_address": self.to_address,
                "value": 10,
                "application_datetime": datetime.utcnow(),
                "application_blocktimestamp": datetime.utcnow(),
                "approval_datetime": datetime.utcnow(),
                "approval_blocktimestamp": datetime.utcnow(),
                "cancelled": False,
                "transfer_approved": True,
            }
            self.insert_transfer_approval(session, transfer_approval=transfer_approval)

        time.sleep(1)
        after_datetime = (
            datetime.utcnow()
            .replace(tzinfo=UTC)
            .astimezone(local_tz)
            .strftime("%Y/%m/%d %H:%M:%S.%f")
        )

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"offset": 1})

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": 1,
            "limit": None,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_approval_history"]
        assert len(data) == 2
        for i, item in enumerate(data):
            assert item["token_address"] == self.token_address
            assert item["application_id"] == i + 1
            assert item["from_address"] == self.from_address
            assert item["to_address"] == self.to_address
            assert before_datetime < item["application_datetime"] < after_datetime
            assert before_datetime < item["application_blocktimestamp"] < after_datetime
            assert before_datetime < item["approval_datetime"] < after_datetime
            assert before_datetime < item["approval_blocktimestamp"] < after_datetime
            assert item["cancelled"] is False
            assert item["transfer_approved"] is True

    # Normal_4_2
    # Data exists
    # offset=2、 limit=2
    def test_normal_4_2(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        before_datetime = (
            datetime.utcnow()
            .replace(tzinfo=UTC)
            .astimezone(local_tz)
            .strftime("%Y/%m/%d %H:%M:%S.%f")
        )
        time.sleep(1)

        for i in range(2, -1, -1):
            transfer_approval = {
                "token_address": self.token_address,
                "application_id": i,
                "from_address": self.from_address,
                "to_address": self.to_address,
                "value": 10,
                "application_datetime": datetime.utcnow(),
                "application_blocktimestamp": datetime.utcnow(),
                "approval_datetime": datetime.utcnow(),
                "approval_blocktimestamp": datetime.utcnow(),
                "cancelled": False,
                "transfer_approved": True,
            }
            self.insert_transfer_approval(session, transfer_approval=transfer_approval)

        time.sleep(1)
        after_datetime = (
            datetime.utcnow()
            .replace(tzinfo=UTC)
            .astimezone(local_tz)
            .strftime("%Y/%m/%d %H:%M:%S.%f")
        )

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"offset": 2, "limit": 2})

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": 2,
            "limit": 2,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_approval_history"]
        assert len(data) == 1
        assert data[0]["token_address"] == self.token_address
        assert data[0]["application_id"] == 2
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == self.to_address
        assert before_datetime < data[0]["application_datetime"] < after_datetime
        assert before_datetime < data[0]["application_blocktimestamp"] < after_datetime
        assert before_datetime < data[0]["approval_datetime"] < after_datetime
        assert before_datetime < data[0]["approval_blocktimestamp"] < after_datetime
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

    # Normal_4_3
    # Data exists
    # offset=設定なし、 limit=2
    def test_normal_4_3(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        before_datetime = (
            datetime.utcnow()
            .replace(tzinfo=UTC)
            .astimezone(local_tz)
            .strftime("%Y/%m/%d %H:%M:%S.%f")
        )
        time.sleep(1)

        for i in range(2, -1, -1):
            transfer_approval = {
                "token_address": self.token_address,
                "application_id": i,
                "from_address": self.from_address,
                "to_address": self.to_address,
                "value": 10,
                "application_datetime": datetime.utcnow(),
                "application_blocktimestamp": datetime.utcnow(),
                "approval_datetime": datetime.utcnow(),
                "approval_blocktimestamp": datetime.utcnow(),
                "cancelled": False,
                "transfer_approved": True,
            }
            self.insert_transfer_approval(session, transfer_approval=transfer_approval)

        time.sleep(1)
        after_datetime = (
            datetime.utcnow()
            .replace(tzinfo=UTC)
            .astimezone(local_tz)
            .strftime("%Y/%m/%d %H:%M:%S.%f")
        )

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"limit": 1})

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": 1,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_approval_history"]
        assert len(data) == 1
        assert data[0]["token_address"] == self.token_address
        assert data[0]["application_id"] == 0
        assert data[0]["from_address"] == self.from_address
        assert data[0]["to_address"] == self.to_address
        assert before_datetime < data[0]["application_datetime"] < after_datetime
        assert before_datetime < data[0]["application_blocktimestamp"] < after_datetime
        assert before_datetime < data[0]["approval_datetime"] < after_datetime
        assert before_datetime < data[0]["approval_blocktimestamp"] < after_datetime
        assert data[0]["cancelled"] is False
        assert data[0]["transfer_approved"] is True

    # Normal_4_3
    # Data exists
    # offset=設定なし、 limit=0
    def test_normal_4_4(self, client: TestClient, session: Session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        for i in range(2, -1, -1):
            transfer_approval = {
                "token_address": self.token_address,
                "application_id": i,
                "from_address": self.from_address,
                "to_address": self.to_address,
                "value": 10,
                "application_datetime": datetime.utcnow(),
                "application_blocktimestamp": datetime.utcnow(),
                "approval_datetime": datetime.utcnow(),
                "approval_blocktimestamp": datetime.utcnow(),
                "cancelled": False,
                "transfer_approved": True,
            }
            self.insert_transfer_approval(session, transfer_approval=transfer_approval)

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.post(apiurl, json={"limit": 0})

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": 0,
            "total": 3,
        }
        data = resp.json()["data"]["transfer_approval_history"]
        assert len(data) == 0

    ####################################################################
    # Error
    ####################################################################

    # Error_1
    # 無効なコントラクトアドレス
    # 400
    def test_error_1(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(contract_address="0xabcd")
        resp = client.post(
            apiurl,
            json={},
        )

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
        resp = client.post(
            apiurl,
            json={},
        )

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
                    "msg": "Input should be a valid integer, got a number with a "
                    "fractional part",
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
                    "msg": "Input should be a valid integer, got a number with a "
                    "fractional part",
                    "type": "int_from_float",
                }
            ],
            "message": "Invalid Parameter",
        }
