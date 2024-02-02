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

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import TZ
from app.model.db import AccountTag, IDXTransferApproval, Listing

UTC = timezone(timedelta(hours=0), "UTC")
local_tz = ZoneInfo(TZ)


class TestTokenTransferApprovalHistory:
    """
    Test Case for token.TransferApprovalHistory
    """

    # test target API
    apiurl_base = "/Token/{contract_address}/TransferApprovalHistory"

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

        session.commit()

        # request target API
        query_string = ""
        resp = client.get(
            self.apiurl_base.format(contract_address=self.token_address),
            params=query_string,
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

        session.commit()

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = ""
        resp = client.get(apiurl, params=query_string)

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

        session.commit()

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = ""
        resp = client.get(apiurl, params=query_string)

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

    # Normal_2_3_1
    # Filter (account_tag: from_address)
    def test_normal_2_3_1(self, client: TestClient, session: Session):
        # データ準備：Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # データ準備：AccountTag
        account_tag = AccountTag()
        account_tag.account_address = self.from_address
        account_tag.account_tag = "test_tag"
        session.add(account_tag)
        session.commit()

        # データ準備；IDXTransferApproval
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

        session.commit()

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.get(apiurl, params={"account_tag": "test_tag"})

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

    # Normal_2_3_2
    # Filter (account_tag: to_address)
    def test_normal_2_3_2(self, client: TestClient, session: Session):
        # データ準備：Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # データ準備：AccountTag
        account_tag = AccountTag()
        account_tag.account_address = self.to_address
        account_tag.account_tag = "test_tag"
        session.add(account_tag)
        session.commit()

        # データ準備；IDXTransferApproval
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

        session.commit()

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.get(apiurl, params={"account_tag": "test_tag"})

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

    # Normal_2_3_3
    # Filter (account_tag: ヒットしない)
    def test_normal_2_3_3(self, client: TestClient, session: Session):
        # データ準備：Listing
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # データ準備；IDXTransferApproval
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

        session.commit()

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.get(apiurl, params={"account_tag": "test_tag"})

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        assert resp.json()["data"]["result_set"] == {
            "count": 0,
            "offset": None,
            "limit": None,
            "total": 0,
        }
        data = resp.json()["data"]["transfer_approval_history"]
        assert len(data) == 0

    # Normal_3_1
    # Data exists (value_operator: =)
    # offset=設定なし、 limit=設定なし
    def test_normal_3_1(self, client: TestClient, session: Session):
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

        session.commit()

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.get(
            apiurl,
            params={"value": 10, "value_operator": 0},
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

    # Normal_3_2
    # Data exists (value_operator: >=)
    # offset=設定なし、 limit=設定なし
    def test_normal_3_2(self, client: TestClient, session: Session):
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

        session.commit()

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.get(
            apiurl,
            params={"value": 20, "value_operator": 1},
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

    # Normal_3_3
    # Data exists (value_operator: <=)
    # offset=設定なし、 limit=設定なし
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

        session.commit()

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.get(
            apiurl,
            params={"value": 10, "value_operator": 2},
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

    # Normal_4_1
    # Data exists (from address)
    # offset=設定なし、 limit=設定なし
    def test_normal_4_1(self, client: TestClient, session: Session):
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
            "from_address": "other_from_address",
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

        session.commit()

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.get(apiurl, params={"from_address": self.from_address[0:5]})

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

    # Normal_4_2
    # Data exists (to address)
    # offset=設定なし、 limit=設定なし
    def test_normal_4_2(self, client: TestClient, session: Session):
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
            "from_address": self.from_address,
            "to_address": "other_to_address",
            "value": 10,
            "application_datetime": datetime.utcnow(),
            "application_blocktimestamp": datetime.utcnow(),
            "approval_datetime": datetime.utcnow(),
            "approval_blocktimestamp": datetime.utcnow(),
            "cancelled": False,
            "transfer_approved": True,
        }
        self.insert_transfer_approval(session, transfer_approval=transfer_approval_2)

        session.commit()

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        resp = client.get(apiurl, params={"to_address": self.to_address[0:5]})

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

    # Normal_5_1
    # Data exists
    # offset=1、 limit=設定なし
    def test_normal_5_1(self, client: TestClient, session: Session):
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

        session.commit()

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = "offset=1"
        resp = client.get(apiurl, params=query_string)

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

    # Normal_5_2
    # Data exists
    # offset=2、 limit=2
    def test_normal_5_2(self, client: TestClient, session: Session):
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

        session.commit()

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = "offset=2&limit=2"
        resp = client.get(apiurl, params=query_string)

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

    # Normal_5_3
    # Data exists
    # offset=設定なし、 limit=2
    def test_normal_5_3(self, client: TestClient, session: Session):
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

        session.commit()

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = "limit=1"
        resp = client.get(apiurl, params=query_string)

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

    # Normal_5_4
    # Data exists
    # offset=設定なし、 limit=0
    def test_normal_5_4(self, client: TestClient, session: Session):
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

        session.commit()

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = "limit=0"
        resp = client.get(apiurl, params=query_string)

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
        query_string = ""
        resp = client.get(apiurl, params=query_string)

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
        query_string = ""
        resp = client.get(apiurl, params=query_string)

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
        query_string = "offset=string"
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": "string",
                    "loc": ["query", "offset"],
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
        query_string = "offset=-1"
        resp = client.get(apiurl, params=query_string)

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
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_3_3
    # offset validation : 小数
    # 400
    def test_error_3_3(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = "offset=1.5"
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": "1.5",
                    "loc": ["query", "offset"],
                    "msg": "Input should be a valid integer, unable to parse "
                    "string as an integer",
                    "type": "int_parsing",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_4_1
    # limit validation : String
    # 400
    def test_error_4_1(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = "limit=string"
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": "string",
                    "loc": ["query", "limit"],
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
        query_string = "limit=-1"
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"ge": 0},
                    "input": "-1",
                    "loc": ["query", "limit"],
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
        query_string = "limit=1.5"
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": "1.5",
                    "loc": ["query", "limit"],
                    "msg": "Input should be a valid integer, unable to parse "
                    "string as an integer",
                    "type": "int_parsing",
                }
            ],
            "message": "Invalid Parameter",
        }
