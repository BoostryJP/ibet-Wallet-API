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
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from app.model.db import IDXLockedPosition
from tests.types import SharedContract

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class TestTokenLockCount:
    """
    Test Case for token.LockCount
    """

    # テスト対象API
    apiurl = "/Token/Lock/Count"

    issuer_address = "0x0000000000000000000000000000000000000001"
    exchange_address = "0x0000000000000000000000000000000000000002"
    personal_info_address = "0x0000000000000000000000000000000000000003"

    token_1 = "0xE883a6F441Ad5682D37Df31d34fC012bcb07A741"
    token_2 = "0xE883A6f441AD5682D37df31d34FC012bcB07a742"
    token_3 = "0xe883a6f441AD5682d37dF31D34fc012bCB07A743"

    lock_1 = "0x52D0784B3460E206Ed69393AE1f9eD37941089E1"
    lock_2 = "0x52D0784B3460E206Ed69393aE1f9eD37941089E2"
    lock_3 = "0x52D0784B3460E206ed69393ae1F9Ed37941089e3"

    account_1 = "0x15d34aaf54267dB7d7c367839aAf71A00A2C6A61"
    account_2 = "0x15D34aaF54267DB7d7c367839Aaf71a00a2C6a62"
    account_3 = "0x15D34AAF54267Db7d7c367839aAf71a00A2C6a63"

    @staticmethod
    def create_idx_locked(
        session: Session,
        token_address: str,
        lock_address: str,
        account_address: str,
        value: int,
        created: datetime,
    ):
        # Issue token
        idx_locked = IDXLockedPosition()
        idx_locked.token_address = token_address
        idx_locked.lock_address = lock_address
        idx_locked.account_address = account_address
        idx_locked.value = value
        idx_locked.created = created
        session.add(idx_locked)
        session.commit()

    def setup_data(self, session: Session):
        token_address_list = [self.token_1, self.token_2, self.token_3]
        lock_address_list = [self.lock_1, self.lock_2, self.lock_3]
        account_address_list = [self.account_1, self.account_2, self.account_3]

        created = datetime(2023, 4, 12, 0, 0, 0)
        for value, (token_address, lock_address, account_address) in enumerate(
            itertools.product(
                token_address_list, lock_address_list, account_address_list
            )
        ):
            self.create_idx_locked(
                session=session,
                token_address=token_address,
                lock_address=lock_address,
                account_address=account_address,
                value=value + 1,
                created=created,
            )
            created += timedelta(minutes=1)
        for account_address in account_address_list:
            self.create_idx_locked(
                session=session,
                token_address="other_token_address",
                lock_address="lock_address",
                account_address=account_address,
                value=0,
                created=created,
            )
            created += timedelta(minutes=1)
        session.commit()

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1_1>
    # List all tokens
    def test_normal_1_1(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl,
            params={},
        )

        assumed_body = {"count": 27}

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_1_2>
    # List specific tokens with query
    def test_normal_1_2(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl,
            params={"token_address_list": [self.token_1, self.token_2]},
        )

        assumed_body = {"count": 18}

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_2>
    # Pagination
    def test_normal_2(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl,
            params={
                "token_address_list": [self.token_1],
                "offset": 1,
                "limit": 2,
            },
        )

        assumed_body = {"count": 9}

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_3>
    # Pagination(over offset)
    def test_normal_3(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl,
            params={"token_address_list": [self.token_1], "offset": 9},
        )

        assumed_body = {"count": 9}

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_4>
    # Filter(lock_address)
    def test_normal_4(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl,
            params={"lock_address": self.lock_1},
        )

        assumed_body = {"count": 9}

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_5>
    # Filter(account_address)
    def test_normal_5(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl,
            params={"account_address": self.account_1},
        )

        assumed_body = {"count": 9}

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body
