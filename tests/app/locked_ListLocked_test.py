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
import pytest

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.model.db import IDXLocked
from app import config
from batch import indexer_Token_Detail
from batch.indexer_Token_Detail import Processor

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    indexer_Token_Detail.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    return indexer_Token_Detail


@pytest.fixture(scope="function")
def processor(test_module, session):
    processor = test_module.Processor()
    return processor


class TestTokenStraightBondTokens:
    """
    Test Case for locked
    """

    # テスト対象API
    apiurl = "/Locked"

    token_1 = "0xe883A6f441Ad5682d37DF31d34fc012bcB07A741"
    token_2 = "0xe883A6f441Ad5682d37DF31d34fc012bcB07A742"
    token_3 = "0xe883A6f441Ad5682d37DF31d34fc012bcB07A743"

    lock_1 = "0x52D0784B3460E206ED69393ae1f9Ed37941089e1"
    lock_2 = "0x52D0784B3460E206ED69393ae1f9Ed37941089e2"
    lock_3 = "0x52D0784B3460E206ED69393ae1f9Ed37941089e3"

    account_1 = "0x15d34aaf54267db7d7c367839aaf71a00a2c6a61"
    account_2 = "0x15d34aaf54267db7d7c367839aaf71a00a2c6a62"
    account_3 = "0x15d34aaf54267db7d7c367839aaf71a00a2c6a63"

    @staticmethod
    def create_idx_locked(session: Session,
                          token_address: str,
                          lock_address: str,
                          account_address: str,
                          value: int):
        # Issue token
        idx_locked = IDXLocked()
        idx_locked.token_address = token_address
        idx_locked.lock_address = lock_address
        idx_locked.account_address = account_address
        idx_locked.value = value
        session.add(idx_locked)
        session.commit()

    def setup_data(self, session: Session):
        token_address_list = [self.token_1, self.token_2, self.token_3]
        lock_address_list = [self.lock_1, self.lock_2, self.lock_3]
        account_address_list = [self.account_1, self.account_2, self.account_3]
        for value, (token_address, lock_address, account_address) in enumerate(itertools.product(token_address_list, lock_address_list, account_address_list)):
            self.create_idx_locked(
                session=session,
                token_address=token_address,
                lock_address=lock_address,
                account_address=account_address,
                value=value+1
            )

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1_1>
    # List all tokens
    def test_normal_1_1(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl
        )

        assumed_body = {
            "result_set": {
                "count": 27,
                "offset": None,
                "limit": None,
                "total": 27
            },
            "locked_list": [
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_1, "value": 1},
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_2, "value": 2},
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_3, "value": 3},
                {"token_address": self.token_1, "lock_address": self.lock_2, "account_address": self.account_1, "value": 4},
                {"token_address": self.token_1, "lock_address": self.lock_2, "account_address": self.account_2, "value": 5},
                {"token_address": self.token_1, "lock_address": self.lock_2, "account_address": self.account_3, "value": 6},
                {"token_address": self.token_1, "lock_address": self.lock_3, "account_address": self.account_1, "value": 7},
                {"token_address": self.token_1, "lock_address": self.lock_3, "account_address": self.account_2, "value": 8},
                {"token_address": self.token_1, "lock_address": self.lock_3, "account_address": self.account_3, "value": 9},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_1, "value": 10},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_2, "value": 11},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_3, "value": 12},
                {"token_address": self.token_2, "lock_address": self.lock_2, "account_address": self.account_1, "value": 13},
                {"token_address": self.token_2, "lock_address": self.lock_2, "account_address": self.account_2, "value": 14},
                {"token_address": self.token_2, "lock_address": self.lock_2, "account_address": self.account_3, "value": 15},
                {"token_address": self.token_2, "lock_address": self.lock_3, "account_address": self.account_1, "value": 16},
                {"token_address": self.token_2, "lock_address": self.lock_3, "account_address": self.account_2, "value": 17},
                {"token_address": self.token_2, "lock_address": self.lock_3, "account_address": self.account_3, "value": 18},
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_1, "value": 19},
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_2, "value": 20},
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_3, "value": 21},
                {"token_address": self.token_3, "lock_address": self.lock_2, "account_address": self.account_1, "value": 22},
                {"token_address": self.token_3, "lock_address": self.lock_2, "account_address": self.account_2, "value": 23},
                {"token_address": self.token_3, "lock_address": self.lock_2, "account_address": self.account_3, "value": 24},
                {"token_address": self.token_3, "lock_address": self.lock_3, "account_address": self.account_1, "value": 25},
                {"token_address": self.token_3, "lock_address": self.lock_3, "account_address": self.account_2, "value": 26},
                {"token_address": self.token_3, "lock_address": self.lock_3, "account_address": self.account_3, "value": 27},
            ]
        }

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
            params={
                "token_address_list": [
                    self.token_1,
                    self.token_2
                ]
            }
        )

        assumed_body = {
            "result_set": {
                "count": 18,
                "offset": None,
                "limit": None,
                "total": 18
            },
            "locked_list": [
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_1, "value": 1},
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_2, "value": 2},
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_3, "value": 3},
                {"token_address": self.token_1, "lock_address": self.lock_2, "account_address": self.account_1, "value": 4},
                {"token_address": self.token_1, "lock_address": self.lock_2, "account_address": self.account_2, "value": 5},
                {"token_address": self.token_1, "lock_address": self.lock_2, "account_address": self.account_3, "value": 6},
                {"token_address": self.token_1, "lock_address": self.lock_3, "account_address": self.account_1, "value": 7},
                {"token_address": self.token_1, "lock_address": self.lock_3, "account_address": self.account_2, "value": 8},
                {"token_address": self.token_1, "lock_address": self.lock_3, "account_address": self.account_3, "value": 9},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_1, "value": 10},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_2, "value": 11},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_3, "value": 12},
                {"token_address": self.token_2, "lock_address": self.lock_2, "account_address": self.account_1, "value": 13},
                {"token_address": self.token_2, "lock_address": self.lock_2, "account_address": self.account_2, "value": 14},
                {"token_address": self.token_2, "lock_address": self.lock_2, "account_address": self.account_3, "value": 15},
                {"token_address": self.token_2, "lock_address": self.lock_3, "account_address": self.account_1, "value": 16},
                {"token_address": self.token_2, "lock_address": self.lock_3, "account_address": self.account_2, "value": 17},
                {"token_address": self.token_2, "lock_address": self.lock_3, "account_address": self.account_3, "value": 18}
            ]
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_2>
    # Pagination
    def test_normal_2(self, client: TestClient, session: Session, shared_contract, processor: Processor):
        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl,
            params={
                "token_address_list": [
                    self.token_1
                ],
                "offset": 3,
                "limit": 5
            }
        )

        assumed_body = {
            "result_set": {
                "count": 9,
                "offset": 3,
                "limit": 5,
                "total": 9
            },
            "locked_list": [
                {"token_address": self.token_1, "lock_address": self.lock_2, "account_address": self.account_1, "value": 4},
                {"token_address": self.token_1, "lock_address": self.lock_2, "account_address": self.account_2, "value": 5},
                {"token_address": self.token_1, "lock_address": self.lock_2, "account_address": self.account_3, "value": 6},
                {"token_address": self.token_1, "lock_address": self.lock_3, "account_address": self.account_1, "value": 7},
                {"token_address": self.token_1, "lock_address": self.lock_3, "account_address": self.account_2, "value": 8}
            ]
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_3>
    # Pagination(over offset)
    def test_normal_3(self, client: TestClient, session: Session, shared_contract, processor: Processor):
        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl,
            params={
                "token_address_list": [
                    self.token_1
                ],
                "offset": 9
            }
        )

        assumed_body = {
            "result_set": {
                "count": 9,
                "offset": 9,
                "limit": None,
                "total": 9
            },
            "locked_list": []
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_4_1>
    # Filter(lock_address)
    def test_normal_4_1(self, client: TestClient, session: Session, shared_contract, processor: Processor):
        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl,
            params={
                "lock_address": self.lock_1
            }
        )

        assumed_body = {
            "result_set": {
                "count": 9,
                "offset": None,
                "limit": None,
                "total": 27
            },
            "locked_list": [
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_1, "value": 1},
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_2, "value": 2},
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_3, "value": 3},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_1, "value": 10},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_2, "value": 11},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_3, "value": 12},
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_1, "value": 19},
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_2, "value": 20},
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_3, "value": 21}
            ]
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_4_2>
    # Filter(account_address)
    def test_normal_4_2(self, client: TestClient, session: Session):
        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl,
            params={
                "account_address": self.account_1
            }
        )

        assumed_body = {
            "result_set": {
                "count": 9,
                "offset": None,
                "limit": None,
                "total": 27
            },
            "locked_list": [
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_1, "value": 1},
                {"token_address": self.token_1, "lock_address": self.lock_2, "account_address": self.account_1, "value": 4},
                {"token_address": self.token_1, "lock_address": self.lock_3, "account_address": self.account_1, "value": 7},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_1, "value": 10},
                {"token_address": self.token_2, "lock_address": self.lock_2, "account_address": self.account_1, "value": 13},
                {"token_address": self.token_2, "lock_address": self.lock_3, "account_address": self.account_1, "value": 16},
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_1, "value": 19},
                {"token_address": self.token_3, "lock_address": self.lock_2, "account_address": self.account_1, "value": 22},
                {"token_address": self.token_3, "lock_address": self.lock_3, "account_address": self.account_1, "value": 25}
            ]
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_5_1>
    # Sort(token_address)
    def test_normal_5_1(self, client: TestClient, session: Session, shared_contract, processor: Processor):
        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl,
            params={
                "account_address": self.account_1,
                "sort_order": 1,
                "sort_item": "token_address"
            }
        )

        assumed_body = {
            "result_set": {
                "count": 9,
                "offset": None,
                "limit": None,
                "total": 27
            },
            "locked_list": [
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_1, "value": 19},
                {"token_address": self.token_3, "lock_address": self.lock_2, "account_address": self.account_1, "value": 22},
                {"token_address": self.token_3, "lock_address": self.lock_3, "account_address": self.account_1, "value": 25},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_1, "value": 10},
                {"token_address": self.token_2, "lock_address": self.lock_2, "account_address": self.account_1, "value": 13},
                {"token_address": self.token_2, "lock_address": self.lock_3, "account_address": self.account_1, "value": 16},
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_1, "value": 1},
                {"token_address": self.token_1, "lock_address": self.lock_2, "account_address": self.account_1, "value": 4},
                {"token_address": self.token_1, "lock_address": self.lock_3, "account_address": self.account_1, "value": 7},
            ]
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_5_2>
    # Sort(lock_address)
    def test_normal_5_2(self, client: TestClient, session: Session, shared_contract, processor: Processor):
        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl,
            params={
                "account_address": self.account_1,
                "sort_order": 0,
                "sort_item": "lock_address"
            }
        )

        assumed_body = {
            "result_set": {
                "count": 9,
                "offset": None,
                "limit": None,
                "total": 27
            },
            "locked_list": [
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_1, "value": 1},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_1, "value": 10},
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_1, "value": 19},
                {"token_address": self.token_1, "lock_address": self.lock_2, "account_address": self.account_1, "value": 4},
                {"token_address": self.token_2, "lock_address": self.lock_2, "account_address": self.account_1, "value": 13},
                {"token_address": self.token_3, "lock_address": self.lock_2, "account_address": self.account_1, "value": 22},
                {"token_address": self.token_1, "lock_address": self.lock_3, "account_address": self.account_1, "value": 7},
                {"token_address": self.token_2, "lock_address": self.lock_3, "account_address": self.account_1, "value": 16},
                {"token_address": self.token_3, "lock_address": self.lock_3, "account_address": self.account_1, "value": 25},
            ]
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_5_3>
    # Sort(account_address)
    def test_normal_5_3(self, client: TestClient, session: Session, shared_contract, processor: Processor):
        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl,
            params={
                "lock_address": self.lock_1,
                "sort_order": 0,
                "sort_item": "account_address"
            }
        )

        assumed_body = {
            "result_set": {
                "count": 9,
                "offset": None,
                "limit": None,
                "total": 27
            },
            "locked_list": [
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_1, "value": 1},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_1, "value": 10},
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_1, "value": 19},
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_2, "value": 2},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_2, "value": 11},
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_2, "value": 20},
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_3, "value": 3},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_3, "value": 12},
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_3, "value": 21},
            ]
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_5_4>
    # Sort(account_address)
    def test_normal_5_4(self, client: TestClient, session: Session, shared_contract, processor: Processor):
        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl,
            params={
                "lock_address": self.lock_1,
                "sort_order": 1,
                "sort_item": "value"
            }
        )

        assumed_body = {
            "result_set": {
                "count": 9,
                "offset": None,
                "limit": None,
                "total": 27
            },
            "locked_list": [
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_3, "value": 21},
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_2, "value": 20},
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_1, "value": 19},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_3, "value": 12},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_2, "value": 11},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_1, "value": 10},
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_3, "value": 3},
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_2, "value": 2},
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_1, "value": 1},
            ]
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body
