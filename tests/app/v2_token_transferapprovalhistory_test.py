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
from datetime import (
    datetime,
    timezone,
    timedelta
)

from app.model.db import (
    Listing,
    IDXTransferApproval
)

UTC = timezone(timedelta(hours=0), "UTC")
JST = timezone(timedelta(hours=+9), "JST")


class TestV2TransferApprovalHistory:
    """
    Test Case for v2.token.TransferApprovalHistory
    """

    # test target API
    apiurl_base = "/v2/Token/{contract_address}/TransferApprovalHistory"

    token_address = "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740"
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
        _transfer_approval.application_id = transfer_approval["application_id"]
        _transfer_approval.from_address = transfer_approval["from_address"]
        _transfer_approval.to_address = transfer_approval["to_address"]
        _transfer_approval.value = transfer_approval.get("value")  # nullable
        _transfer_approval.application_datetime = transfer_approval.get("application_datetime")  # nullable
        _transfer_approval.application_blocktimestamp = transfer_approval.get("application_blocktimestamp")  # nullable
        _transfer_approval.approval_datetime = transfer_approval.get("approval_datetime")  # nullable
        _transfer_approval.approval_blocktimestamp = transfer_approval.get("approval_blocktimestamp")  # nullable
        _transfer_approval.cancelled = transfer_approval.get("cancelled")
        session.add(_transfer_approval)

    ####################################################################
    # Normal
    ####################################################################

    # Normal_1
    # No data
    def test_normal_1(self, client, session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # request target API
        query_string = ""
        resp = client.simulate_get(
            self.apiurl_base.format(contract_address=self.token_address),
            query_string=query_string
        )

        # assertion
        assumed_body = {
            "result_set": {
                "count": 0,
                "offset": None,
                "limit": None,
                "total": 0
            },
            "transfer_approval_history": []
        }
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert resp.json["data"] == assumed_body

    # Normal_2
    # Data exists
    # offset=設定なし、 limit=設定なし
    def test_normal_2(self, client, session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        before_datetime = datetime.utcnow().\
            replace(tzinfo=UTC).\
            astimezone(JST).\
            strftime("%Y/%m/%d %H:%M:%S.%f")
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
                "cancelled": False
            }
            self.insert_transfer_approval(
                session,
                transfer_approval=transfer_approval
            )

        time.sleep(1)
        after_datetime = datetime.utcnow().\
            replace(tzinfo=UTC).\
            astimezone(JST).\
            strftime("%Y/%m/%d %H:%M:%S.%f")

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        # assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}

        assert resp.json["data"]["result_set"] == {
                "count": 3,
                "offset": None,
                "limit": None,
                "total": 3
        }
        data = resp.json["data"]["transfer_approval_history"]
        for i, item in enumerate(data):
            assert item["token_address"] == self.token_address
            assert item["application_id"] == i
            assert item["from_address"] == self.from_address
            assert item["to_address"] == self.to_address
            assert before_datetime < item["application_datetime"] < after_datetime
            assert before_datetime < item["application_blocktimestamp"] < after_datetime
            assert before_datetime < item["approval_datetime"] < after_datetime
            assert before_datetime < item["approval_blocktimestamp"] < after_datetime
            assert item["cancelled"] is False

    # Normal_3
    # Data exists
    # offset=1、 limit=設定なし
    def test_normal_3(self, client, session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        before_datetime = datetime.utcnow(). \
            replace(tzinfo=UTC). \
            astimezone(JST). \
            strftime("%Y/%m/%d %H:%M:%S.%f")
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
                "cancelled": False
            }
            self.insert_transfer_approval(
                session,
                transfer_approval=transfer_approval
            )

        time.sleep(1)
        after_datetime = datetime.utcnow(). \
            replace(tzinfo=UTC). \
            astimezone(JST). \
            strftime("%Y/%m/%d %H:%M:%S.%f")

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = "offset=1"
        resp = client.simulate_get(apiurl, query_string=query_string)

        # assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert resp.json["data"]["result_set"] == {
            "count": 3,
            "offset": 1,
            "limit": None,
            "total": 3
        }
        data = resp.json["data"]["transfer_approval_history"]
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

    # Normal_4
    # Data exists
    # offset=2、 limit=2
    def test_normal_4(self, client, session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        before_datetime = datetime.utcnow(). \
            replace(tzinfo=UTC). \
            astimezone(JST). \
            strftime("%Y/%m/%d %H:%M:%S.%f")
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
                "cancelled": False
            }
            self.insert_transfer_approval(
                session,
                transfer_approval=transfer_approval
            )

        time.sleep(1)
        after_datetime = datetime.utcnow(). \
            replace(tzinfo=UTC). \
            astimezone(JST). \
            strftime("%Y/%m/%d %H:%M:%S.%f")

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = "offset=2&limit=2"
        resp = client.simulate_get(apiurl, query_string=query_string)

        # assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert resp.json["data"]["result_set"] == {
            "count": 3,
            "offset": 2,
            "limit": 2,
            "total": 3
        }
        data = resp.json["data"]["transfer_approval_history"]
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

    # Normal_5
    # Data exists
    # offset=設定なし、 limit=2
    def test_normal_5(self, client, session):
        # prepare data
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        before_datetime = datetime.utcnow(). \
            replace(tzinfo=UTC). \
            astimezone(JST). \
            strftime("%Y/%m/%d %H:%M:%S.%f")
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
                "cancelled": False
            }
            self.insert_transfer_approval(
                session,
                transfer_approval=transfer_approval
            )

        time.sleep(1)
        after_datetime = datetime.utcnow(). \
            replace(tzinfo=UTC). \
            astimezone(JST). \
            strftime("%Y/%m/%d %H:%M:%S.%f")

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = "limit=1"
        resp = client.simulate_get(apiurl, query_string=query_string)

        # assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert resp.json["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": 1,
            "total": 3
        }
        data = resp.json["data"]["transfer_approval_history"]
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

    # Normal_6
    # Data exists
    # offset=設定なし、 limit=0
    def test_normal_6(self, client, session):
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
                "cancelled": False
            }
            self.insert_transfer_approval(
                session,
                transfer_approval=transfer_approval
            )

        # request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = "limit=0"
        resp = client.simulate_get(apiurl, query_string=query_string)

        # assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert resp.json["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": 0,
            "total": 3
        }
        data = resp.json["data"]["transfer_approval_history"]
        assert len(data) == 0

    ####################################################################
    # Error
    ####################################################################

    # Error_1
    # 無効なコントラクトアドレス
    # 400
    def test_error_1(self, client, session):
        apiurl = self.apiurl_base.format(contract_address="0xabcd")
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "invalid contract_address"
        }

    # Error_2
    # 取扱していないトークン
    # 404
    def test_error_2(self, client, session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": "contract_address: " + self.token_address
        }

    # Error_3_1
    # offset validation : String
    # 400
    def test_error_3_1(self, client, session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = "offset=string"
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'offset': [
                    "field 'offset' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # Error_3_2
    # offset validation : 負値
    # 400
    def test_error_3_2(self, client, session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = "offset=-1"
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'offset': 'min value is 0'}
        }

    # Error_3_3
    # offset validation : 小数
    # 400
    def test_error_3_3(self, client, session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = "offset=1.5"
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'offset': [
                    "field 'offset' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # Error_4_1
    # limit validation : String
    # 400
    def test_error_4_1(self, client, session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = "limit=string"
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'limit': [
                    "field 'limit' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # Error_4_2
    # limit validation : 負値
    # 400
    def test_error_4_2(self, client, session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = "limit=-1"
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'limit': 'min value is 0'}
        }

    # Error_4_3
    # limit validation : 小数
    # 400
    def test_error_4_3(self, client, session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = "limit=1.5"
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'limit': [
                    "field 'limit' could not be coerced",
                    'must be of integer type'
                ]
            }
        }
