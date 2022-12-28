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
import itertools
from datetime import datetime
from unittest.mock import ANY
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.model.db import (
    Listing,
    IDXUnlock
)


class TestTokenUnlock:
    """
    Test Case for token.Unlock
    """

    # テスト対象API
    apiurl_base = "/Token/{token_address}/Unlock"

    token_1 = "0xE883a6F441Ad5682D37Df31d34fC012bcb07A741"
    token_2 = "0xE883A6f441AD5682D37df31d34FC012bcB07a742"
    token_3 = "0xe883a6f441AD5682d37dF31D34fc012bCB07A743"
    token_4 = "0xe883A6F441AD5682d37dF31d34fc012BcB07a744"

    lock_1 = "0x52D0784B3460E206ED69393ae1f9Ed37941089e1"
    lock_2 = "0x52D0784B3460E206ED69393ae1f9Ed37941089e2"
    lock_3 = "0x52D0784B3460E206ED69393ae1f9Ed37941089e3"

    account_1 = "0x15d34aaf54267db7d7c367839aaf71a00a2c6a61"
    account_2 = "0x15d34aaf54267db7d7c367839aaf71a00a2c6a62"
    account_3 = "0x15d34aaf54267db7d7c367839aaf71a00a2c6a63"

    recipient_address = "0x8E42d0884fEa12EF68D834a9349d8E76049117ac"

    transaction_hash = "0xc99116e27f0c40201a9e907ad5334f4477863269b90a94444d11a1bc9b9315e6"

    @staticmethod
    def insert_listing(session: Session, token_address: str):
        _listing = Listing()
        _listing.token_address = token_address
        _listing.is_public = True
        session.add(_listing)

    @staticmethod
    def create_idx_unlock_event(
        session: Session, transaction_hash: str, block_number: int, token_address: str, lock_address: str,
        account_address: str, recipient_address: str, value: int
    ):
        _unlock = IDXUnlock()
        _unlock.transaction_hash = transaction_hash
        _unlock.block_number = block_number
        _unlock.token_address = token_address
        _unlock.lock_address = lock_address
        _unlock.account_address = account_address
        _unlock.recipient_address = recipient_address
        _unlock.value = value
        _unlock.data = {
            "message": f"{value}"
        }
        _unlock.block_timestamp = datetime.now()
        session.add(_unlock)

    def setup_data(self, session: Session):
        self.insert_listing(session=session, token_address=self.token_1)
        self.insert_listing(session=session, token_address=self.token_2)
        self.insert_listing(session=session, token_address=self.token_3)
        self.insert_listing(session=session, token_address=self.token_4)

        token_address_list = [self.token_1, self.token_2, self.token_3]
        lock_address_list = [self.lock_1, self.lock_2, self.lock_3]
        account_address_list = [self.account_1, self.account_2, self.account_3]
        for value, (token_address, lock_address, account_address) in enumerate(itertools.product(token_address_list, lock_address_list, account_address_list)):
            self.create_idx_unlock_event(
                session=session,
                transaction_hash=self.transaction_hash,
                block_number=value+1,
                token_address=token_address,
                lock_address=lock_address,
                account_address=account_address,
                recipient_address=self.recipient_address,
                value=value+1
            )

    ####################################################################
    # Normal
    ####################################################################

    # Normal_1
    # List all Events
    def test_normal_1(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session)

        apiurl = self.apiurl_base.format(token_address=self.token_3)
        resp = client.get(
            apiurl,
            params={}
        )

        assumed_body = [
            {
                "account_address": self.account_3, "block_timestamp": ANY, "data": {"message": "27"}, "value": 27,
                "lock_address": self.lock_3, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
                
            },
            {
                "account_address": self.account_2, "block_timestamp": ANY, "data": {"message": "26"}, "value": 26,
                "lock_address": self.lock_3, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "25"}, "value": 25,
                "lock_address": self.lock_3, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_3, "block_timestamp": ANY, "data": {"message": "24"}, "value": 24,
                "lock_address": self.lock_2, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_2, "block_timestamp": ANY, "data": {"message": "23"}, "value": 23,
                "lock_address": self.lock_2, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "22"}, "value": 22,
                "lock_address": self.lock_2, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_3, "block_timestamp": ANY, "data": {"message": "21"}, "value": 21,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_2, "block_timestamp": ANY, "data": {"message": "20"}, "value": 20,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "19"}, "value": 19,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 9,
            "offset": None,
            "limit": None,
            "total": 9
        }
        assert resp.json()["data"]["unlock_events"] == assumed_body

    # Normal_2
    # Pagination
    def test_normal_2(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session)

        apiurl = self.apiurl_base.format(token_address=self.token_3)
        resp = client.get(
            apiurl,
            params={
                "offset": 3,
                "limit": 5
            }
        )

        assumed_body = [
            {
                "account_address": self.account_3, "block_timestamp": ANY, "data": {"message": "24"}, "value": 24,
                "lock_address": self.lock_2, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_2, "block_timestamp": ANY, "data": {"message": "23"}, "value": 23,
                "lock_address": self.lock_2, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "22"}, "value": 22,
                "lock_address": self.lock_2, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_3, "block_timestamp": ANY, "data": {"message": "21"}, "value": 21,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_2, "block_timestamp": ANY, "data": {"message": "20"}, "value": 20,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 9,
            "offset": 3,
            "limit": 5,
            "total": 9
        }
        assert resp.json()["data"]["unlock_events"] == assumed_body

    # Normal_3
    # Pagination(over offset)
    def test_normal_3(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session)

        apiurl = self.apiurl_base.format(token_address=self.token_3)
        resp = client.get(
            apiurl,
            params={
                "offset": 9
            }
        )

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 9,
            "offset": 9,
            "limit": None,
            "total": 9
        }
        assert resp.json()["data"]["unlock_events"] == []

    # Normal_4_1
    # Filter(lock_address)
    def test_normal_4_1(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session)

        apiurl = self.apiurl_base.format(token_address=self.token_3)
        resp = client.get(
            apiurl,
            params={
                "lock_address": self.lock_1
            }
        )

        assumed_body = [
            {
                "account_address": self.account_3, "block_timestamp": ANY, "data": {"message": "21"}, "value": 21,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_2, "block_timestamp": ANY, "data": {"message": "20"}, "value": 20,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "19"}, "value": 19,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 9
        }
        assert resp.json()["data"]["unlock_events"] == assumed_body

    # Normal_4_2
    # Filter(account_address)
    def test_normal_4_2(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session)

        apiurl = self.apiurl_base.format(token_address=self.token_3)
        resp = client.get(
            apiurl,
            params={
                "account_address": self.account_1
            }
        )

        assumed_body = [
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "25"}, "value": 25,
                "lock_address": self.lock_3, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "22"}, "value": 22,
                "lock_address": self.lock_2, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "19"}, "value": 19,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 9
        }
        assert resp.json()["data"]["unlock_events"] == assumed_body

    # Normal_4_3
    # Filter(account_address)
    def test_normal_4_3(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session)

        apiurl = self.apiurl_base.format(token_address=self.token_3)
        resp = client.get(
            apiurl,
            params={
                "data": "1"
            }
        )

        assumed_body = [
            {
                "account_address": self.account_3, "block_timestamp": ANY, "data": {"message": "21"}, "value": 21,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "19"}, "value": 19,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 2,
            "offset": None,
            "limit": None,
            "total": 9
        }
        assert resp.json()["data"]["unlock_events"] == assumed_body

    # Normal_5_1
    # Sort(lock_address)
    def test_normal_5_1(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session)

        apiurl = self.apiurl_base.format(token_address=self.token_3)
        resp = client.get(
            apiurl,
            params={
                "sort_item": "lock_address"
            }
        )

        assumed_body = [
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "25"}, "value": 25,
                "lock_address": self.lock_3, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_2, "block_timestamp": ANY, "data": {"message": "26"}, "value": 26,
                "lock_address": self.lock_3, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_3, "block_timestamp": ANY, "data": {"message": "27"}, "value": 27,
                "lock_address": self.lock_3, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "22"}, "value": 22,
                "lock_address": self.lock_2, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_2, "block_timestamp": ANY, "data": {"message": "23"}, "value": 23,
                "lock_address": self.lock_2, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_3, "block_timestamp": ANY, "data": {"message": "24"}, "value": 24,
                "lock_address": self.lock_2, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "19"}, "value": 19,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_2, "block_timestamp": ANY, "data": {"message": "20"}, "value": 20,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_3, "block_timestamp": ANY, "data": {"message": "21"}, "value": 21,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 9,
            "offset": None,
            "limit": None,
            "total": 9
        }
        assert resp.json()["data"]["unlock_events"] == assumed_body

    # Normal_5_2
    # Sort(account_address)
    def test_normal_5_2(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session)

        apiurl = self.apiurl_base.format(token_address=self.token_3)
        resp = client.get(
            apiurl,
            params={
                "sort_item": "account_address",
                "sort_order": 0,
            }
        )

        assumed_body = [
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "19"}, "value": 19,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "22"}, "value": 22,
                "lock_address": self.lock_2, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "25"}, "value": 25,
                "lock_address": self.lock_3, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_2, "block_timestamp": ANY, "data": {"message": "20"}, "value": 20,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_2, "block_timestamp": ANY, "data": {"message": "23"}, "value": 23,
                "lock_address": self.lock_2, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_2, "block_timestamp": ANY, "data": {"message": "26"}, "value": 26,
                "lock_address": self.lock_3, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_3, "block_timestamp": ANY, "data": {"message": "21"}, "value": 21,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_3, "block_timestamp": ANY, "data": {"message": "24"}, "value": 24,
                "lock_address": self.lock_2, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_3, "block_timestamp": ANY, "data": {"message": "27"}, "value": 27,
                "lock_address": self.lock_3, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 9,
            "offset": None,
            "limit": None,
            "total": 9
        }
        assert resp.json()["data"]["unlock_events"] == assumed_body

    # Normal_5_3
    # Sort(value)
    def test_normal_5_3(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session)

        apiurl = self.apiurl_base.format(token_address=self.token_3)
        resp = client.get(
            apiurl,
            params={
                "sort_item": "value",
                "sort_order": 1,
            }
        )

        assumed_body = [
            {
                "account_address": self.account_3, "block_timestamp": ANY, "data": {"message": "27"}, "value": 27,
                "lock_address": self.lock_3, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_2, "block_timestamp": ANY, "data": {"message": "26"}, "value": 26,
                "lock_address": self.lock_3, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "25"}, "value": 25,
                "lock_address": self.lock_3, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_3, "block_timestamp": ANY, "data": {"message": "24"}, "value": 24,
                "lock_address": self.lock_2, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_2, "block_timestamp": ANY, "data": {"message": "23"}, "value": 23,
                "lock_address": self.lock_2, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "22"}, "value": 22,
                "lock_address": self.lock_2, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_3, "block_timestamp": ANY, "data": {"message": "21"}, "value": 21,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_2, "block_timestamp": ANY, "data": {"message": "20"}, "value": 20,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            },
            {
                "account_address": self.account_1, "block_timestamp": ANY, "data": {"message": "19"}, "value": 19,
                "lock_address": self.lock_1, "token_address": self.token_3, "transaction_hash": self.transaction_hash, 
                "recipient_address": self.recipient_address
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 9,
            "offset": None,
            "limit": None,
            "total": 9
        }
        assert resp.json()["data"]["unlock_events"] == assumed_body

    ####################################################################
    # Error
    ####################################################################

    # Error_1
    # Invalid contract address
    # 400
    def test_error_1(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(token_address="0xabcd")
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "invalid contract_address"
        }

    # Error_2
    # Not Found in listing
    # 404
    def test_error_2(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(token_address=self.token_4)
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": "contract_address: " + self.token_4
        }
