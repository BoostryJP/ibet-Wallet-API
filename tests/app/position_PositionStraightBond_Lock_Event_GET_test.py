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
    IDXLock,
    IDXUnlock
)
from app.model.schema import LockHistoryCategory


class TestPositionStraightBondLockEvent:
    """
    Test Case for position.StraightBond.Lock.Event
    """

    # テスト対象API
    apiurl_base = "/Position/{account_address}/StraightBond/Lock/Event"

    token_1 = "0xE883a6F441Ad5682D37Df31d34fC012bcb07A741"
    token_2 = "0xE883A6f441AD5682D37df31d34FC012bcB07a742"

    lock_1 = "0x52D0784B3460E206Ed69393AE1f9eD37941089E1"
    lock_2 = "0x52D0784B3460E206Ed69393aE1f9eD37941089E2"

    recipient_1 = "0xb95fE0B4b44B79062452e0599Ca341CFe2913101"
    recipient_2 = "0xB95fe0B4B44B79062452e0599cA341CfE2913102"

    account_1 = "0x15d34aaf54267dB7d7c367839aAf71A00A2C6A61"
    account_2 = "0x15D34aaF54267DB7d7c367839Aaf71a00a2C6a62"

    transaction_hash = "0xc99116e27f0c40201a9e907ad5334f4477863269b90a94444d11a1bc9b9315e6"

    @staticmethod
    def insert_listing(session: Session, token_address: str):
        _listing = Listing()
        _listing.token_address = token_address
        _listing.is_public = True
        session.add(_listing)

    @staticmethod
    def create_idx_lock_event(
        session: Session, transaction_hash: str, block_number: int, token_address: str, lock_address: str,
        account_address: str, value: int
    ):
        _lock = IDXLock()
        _lock.transaction_hash = transaction_hash
        _lock.block_number = block_number
        _lock.token_address = token_address
        _lock.lock_address = lock_address
        _lock.account_address = account_address
        _lock.value = value
        _lock.data = {
            "message": f"{value}"
        }
        _lock.block_timestamp = datetime.now()
        session.add(_lock)

    @staticmethod
    def create_idx_unlock_event(
        session: Session, transaction_hash: str, block_number: int, token_address: str, lock_address: str,
        account_address: str, recipient_address: str ,value: int
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

    def setup_data(self, session: Session, token_address: str):
        self.insert_listing(session=session, token_address=token_address)

        lock_address_list = [self.lock_1, self.lock_2]
        account_address_list = [self.account_1, self.account_2]
        recipient_address_list = [self.recipient_1, self.recipient_2]

        for value, (lock_address, account_address) in enumerate(
            itertools.product(lock_address_list, account_address_list)
        ):
            self.create_idx_lock_event(
                session=session,
                transaction_hash=self.transaction_hash,
                block_number=value+1,
                token_address=token_address,
                lock_address=lock_address,
                account_address=account_address,
                value=value+1
            )

        for value, (account_address, (lock_address, recipient_address)) in enumerate(
            itertools.product(account_address_list, zip(lock_address_list, recipient_address_list))
        ):
            self.create_idx_unlock_event(
                session=session,
                transaction_hash=self.transaction_hash,
                block_number=value+1,
                token_address=token_address,
                lock_address=lock_address,
                account_address=account_address,
                recipient_address=recipient_address,
                value=value+1
            )

    ####################################################################
    # Normal
    ####################################################################

    # Normal_1
    # List all Events
    def test_normal_1(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session, token_address=self.token_1)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={}
        )

        assumed_body = [
            {
                "token_address": self.token_1, "lock_address": self.lock_2,
                "account_address": self.account_1, "recipient_address": self.recipient_2,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "2"}, "value": 2,
                "history_category": LockHistoryCategory.Unlock,
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": self.recipient_1,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Unlock
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_2,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "3"}, "value": 3,
                "history_category": LockHistoryCategory.Lock,
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Lock
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 4,
            "offset": None,
            "limit": None,
            "total": 4
        }
        assert resp.json()["data"]["lock_history"] == assumed_body

    # Normal_2
    # Pagination
    def test_normal_2(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session, token_address=self.token_1)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "offset": 3,
                "limit": 1
            }
        )

        assumed_body = [
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Lock
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 4,
            "offset": 3,
            "limit": 1,
            "total": 4
        }
        assert resp.json()["data"]["lock_history"] == assumed_body

    # Normal_3
    # Pagination(over offset)
    def test_normal_3(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session, token_address=self.token_1)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "offset": 4
            }
        )

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 4,
            "offset": 4,
            "limit": None,
            "total": 4
        }
        assert resp.json()["data"]["lock_history"] == assumed_body

    # Normal_4_1
    # Filter(token_address)
    def test_normal_4_1(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session, token_address=self.token_1)
        self.setup_data(session=session, token_address=self.token_2)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "token_address": self.token_1
            }
        )

        assumed_body = [
            {
                "token_address": self.token_1, "lock_address": self.lock_2,
                "account_address": self.account_1, "recipient_address": self.recipient_2,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "2"}, "value": 2,
                "history_category": LockHistoryCategory.Unlock,
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": self.recipient_1,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Unlock
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_2,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "3"}, "value": 3,
                "history_category": LockHistoryCategory.Lock,
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Lock
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 4,
            "offset": None,
            "limit": None,
            "total": 8
        }
        assert resp.json()["data"]["lock_history"] == assumed_body

    # Normal_4_2
    # Filter(lock_address)
    def test_normal_4_2(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session, token_address=self.token_1)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "lock_address": self.lock_1
            }
        )

        assumed_body = [
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": self.recipient_1,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Unlock
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Lock
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 2,
            "offset": None,
            "limit": None,
            "total": 4
        }
        assert resp.json()["data"]["lock_history"] == assumed_body

    # Normal_4_3
    # Filter(recipient_address)
    def test_normal_4_3(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session, token_address=self.token_1)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "recipient_address": self.recipient_1
            }
        )

        assumed_body = [
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": self.recipient_1,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Unlock
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 4
        }
        assert resp.json()["data"]["lock_history"] == assumed_body

    # Normal_4_4
    # Filter(category=Lock)
    def test_normal_4_4(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session, token_address=self.token_1)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "category": LockHistoryCategory.Lock.value,
                "lock_address": self.lock_1
            }
        )

        assumed_body = [
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Lock
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 2
        }
        assert resp.json()["data"]["lock_history"] == assumed_body

    # Normal_4_6
    # Filter(category=Unlock)
    def test_normal_4_6(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session, token_address=self.token_1)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "category": LockHistoryCategory.Unlock.value,
                "offset": 1
            }
        )

        assumed_body = [
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": self.recipient_1,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Unlock
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 2,
            "offset": 1,
            "limit": None,
            "total": 2
        }
        assert resp.json()["data"]["lock_history"] == assumed_body

    # Normal_4_7
    # Filter(data)
    def test_normal_4_7(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session, token_address=self.token_1)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "data": "1"
            }
        )

        assumed_body = [
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": self.recipient_1,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Unlock
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Lock
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 2,
            "offset": None,
            "limit": None,
            "total": 4
        }
        assert resp.json()["data"]["lock_history"] == assumed_body

    # Normal_5_1
    # Sort(token_address)
    def test_normal_5_1(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session, token_address=self.token_1)
        self.setup_data(session=session, token_address=self.token_2)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "sort_item": "token_address",
                "sort_order": 0
            }
        )

        assumed_body = [
            {
                "token_address": self.token_1, "lock_address": self.lock_2,
                "account_address": self.account_1, "recipient_address": self.recipient_2,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "2"}, "value": 2,
                "history_category": LockHistoryCategory.Unlock,
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": self.recipient_1,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Unlock
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_2,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "3"}, "value": 3,
                "history_category": LockHistoryCategory.Lock,
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Lock
            },
            {
                "token_address": self.token_2, "lock_address": self.lock_2,
                "account_address": self.account_1, "recipient_address": self.recipient_2,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "2"}, "value": 2,
                "history_category": LockHistoryCategory.Unlock,
            },
            {
                "token_address": self.token_2, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": self.recipient_1,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Unlock
            },
            {
                "token_address": self.token_2, "lock_address": self.lock_2,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "3"}, "value": 3,
                "history_category": LockHistoryCategory.Lock,
            },
            {
                "token_address": self.token_2, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Lock
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 8,
            "offset": None,
            "limit": None,
            "total": 8
        }
        assert resp.json()["data"]["lock_history"] == assumed_body

    # Normal_5_2
    # Sort(lock_address)
    def test_normal_5_2(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session, token_address=self.token_1)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "sort_item": "lock_address",
                "sort_order": 0
            }
        )

        assumed_body = [
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": self.recipient_1,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Unlock
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Lock
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_2,
                "account_address": self.account_1, "recipient_address": self.recipient_2,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "2"}, "value": 2,
                "history_category": LockHistoryCategory.Unlock,
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_2,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "3"}, "value": 3,
                "history_category": LockHistoryCategory.Lock,
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 4,
            "offset": None,
            "limit": None,
            "total": 4
        }
        assert resp.json()["data"]["lock_history"] == assumed_body

    # Normal_5_3
    # Sort(recipient_address)
    def test_normal_5_3(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session, token_address=self.token_1)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "sort_item": "recipient_address",
                "sort_order": 0
            }
        )

        assumed_body = [
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": self.recipient_1,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Unlock
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_2,
                "account_address": self.account_1, "recipient_address": self.recipient_2,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "2"}, "value": 2,
                "history_category": LockHistoryCategory.Unlock,
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_2,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "3"}, "value": 3,
                "history_category": LockHistoryCategory.Lock,
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Lock
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 4,
            "offset": None,
            "limit": None,
            "total": 4
        }
        assert resp.json()["data"]["lock_history"] == assumed_body

    # Normal_5_5
    # Sort(value)
    def test_normal_5_5(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session, token_address=self.token_1)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "sort_item": "value",
                "sort_order": 0
            }
        )

        assumed_body = [
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": self.recipient_1,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Unlock
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Lock
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_2,
                "account_address": self.account_1, "recipient_address": self.recipient_2,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "2"}, "value": 2,
                "history_category": LockHistoryCategory.Unlock,
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_2,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "3"}, "value": 3,
                "history_category": LockHistoryCategory.Lock,
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 4,
            "offset": None,
            "limit": None,
            "total": 4
        }
        assert resp.json()["data"]["lock_history"] == assumed_body

    # Normal_5_6
    # Sort(block_timestamp)
    def test_normal_5_6(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session=session, token_address=self.token_1)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "sort_item": "block_timestamp",
                "sort_order": 0
            }
        )

        assumed_body = [
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Lock
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_2,
                "account_address": self.account_1, "recipient_address": None,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "3"}, "value": 3,
                "history_category": LockHistoryCategory.Lock,
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_1,
                "account_address": self.account_1, "recipient_address": self.recipient_1,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "1"}, "value": 1,
                "history_category": LockHistoryCategory.Unlock
            },
            {
                "token_address": self.token_1, "lock_address": self.lock_2,
                "account_address": self.account_1, "recipient_address": self.recipient_2,
                "block_timestamp": ANY, "transaction_hash": self.transaction_hash,
                "data": {"message": "2"}, "value": 2,
                "history_category": LockHistoryCategory.Unlock,
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["result_set"] == {
            "count": 4,
            "offset": None,
            "limit": None,
            "total": 4
        }
        assert resp.json()["data"]["lock_history"] == assumed_body

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # ParameterError: invalid account_address
    def test_error_1(self, client: TestClient, session: Session):

        # Request target API
        resp = client.get(
            self.apiurl_base.format(account_address="invalid"),
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "invalid account_address"
        }

    # <Error_2>
    # ParameterError: offset/limit(minus value)
    def test_error_2(self, client: TestClient, session: Session):

        # Request target API
        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "offset": -1,
                "limit": -1,
            }
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"limit_value": 0},
                    "loc": ["query", "offset"],
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge"
                },
                {
                    "ctx": {"limit_value": 0},
                    "loc": ["query", "limit"],
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge"
                }
            ],
            "message": "Invalid Parameter"
        }

    # <Error_3>
    # ParameterError: offset/limit(not int), include_token_details(not bool)
    def test_error_3(self, client: TestClient, session: Session):

        # Request target API
        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "offset": "test",
                "limit": "test",
            }
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "loc": ["query", "offset"],
                    "msg": "value is not a valid integer",
                    "type": "type_error.integer"
                },
                {
                    "loc": ["query", "limit"],
                    "msg": "value is not a valid integer",
                    "type": "type_error.integer"
                }
            ],
            "message": "Invalid Parameter"
        }
