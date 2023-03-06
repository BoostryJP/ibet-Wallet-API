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

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.model.db import IDXLockedPosition
from app import config

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestPositionStraightBondLock:
    """
    Test Case for position.StraightBond.Lock
    """

    # テスト対象API
    apiurl_base = "/Position/{account_address}/StraightBond/Lock"

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
    def create_idx_locked(session: Session,
                          token_address: str,
                          lock_address: str,
                          account_address: str,
                          value: int):
        # Issue token
        idx_locked = IDXLockedPosition()
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
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1)
        )

        assumed_body = {
            "result_set": {
                "count": 9,
                "offset": None,
                "limit": None,
                "total": 9
            },
            "locked_positions": [
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

    # <Normal_1_2>
    # List specific tokens with query
    def test_normal_1_2(self, client: TestClient, session: Session):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "token_address_list": [
                    self.token_1,
                    self.token_2
                ]
            }
        )

        assumed_body = {
            "result_set": {
                "count": 6,
                "offset": None,
                "limit": None,
                "total": 6
            },
            "locked_positions": [
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_1, "value": 1},
                {"token_address": self.token_1, "lock_address": self.lock_2, "account_address": self.account_1, "value": 4},
                {"token_address": self.token_1, "lock_address": self.lock_3, "account_address": self.account_1, "value": 7},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_1, "value": 10},
                {"token_address": self.token_2, "lock_address": self.lock_2, "account_address": self.account_1, "value": 13},
                {"token_address": self.token_2, "lock_address": self.lock_3, "account_address": self.account_1, "value": 16}
            ]
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_2>
    # Pagination
    def test_normal_2(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "token_address_list": [
                    self.token_1
                ],
                "offset": 1,
                "limit": 2
            }
        )

        assumed_body = {
            "result_set": {
                "count": 3,
                "offset": 1,
                "limit": 2,
                "total": 3
            },
            "locked_positions": [
                {"token_address": self.token_1, "lock_address": self.lock_2, "account_address": self.account_1, "value": 4},
                {"token_address": self.token_1, "lock_address": self.lock_3, "account_address": self.account_1, "value": 7}
            ]
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_3>
    # Pagination(over offset)
    def test_normal_3(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "token_address_list": [
                    self.token_1
                ],
                "offset": 9
            }
        )

        assumed_body = {
            "result_set": {
                "count": 3,
                "offset": 9,
                "limit": None,
                "total": 3
            },
            "locked_positions": []
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_4>
    # Filter(lock_address)
    def test_normal_4(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "lock_address": self.lock_1
            }
        )

        assumed_body = {
            "result_set": {
                "count": 3,
                "offset": None,
                "limit": None,
                "total": 9
            },
            "locked_positions": [
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_1, "value": 1},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_1, "value": 10},
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_1, "value": 19}
            ]
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_5_1>
    # Sort(token_address)
    def test_normal_5_1(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "sort_order": 1,
                "sort_item": "token_address"
            }
        )

        assumed_body = {
            "result_set": {
                "count": 9,
                "offset": None,
                "limit": None,
                "total": 9
            },
            "locked_positions": [
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
    def test_normal_5_2(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "sort_order": 0,
                "sort_item": "lock_address"
            }
        )

        assumed_body = {
            "result_set": {
                "count": 9,
                "offset": None,
                "limit": None,
                "total": 9
            },
            "locked_positions": [
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
    def test_normal_5_3(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "lock_address": self.lock_1,
                "sort_order": 0,
                "sort_item": "account_address"
            }
        )

        assumed_body = {
            "result_set": {
                "count": 3,
                "offset": None,
                "limit": None,
                "total": 9
            },
            "locked_positions": [
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_1, "value": 1},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_1, "value": 10},
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_1, "value": 19}
            ]
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_5_4>
    # Sort(value)
    def test_normal_5_4(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "lock_address": self.lock_1,
                "sort_order": 1,
                "sort_item": "value"
            }
        )

        assumed_body = {
            "result_set": {
                "count": 3,
                "offset": None,
                "limit": None,
                "total": 9
            },
            "locked_positions": [
                {"token_address": self.token_3, "lock_address": self.lock_1, "account_address": self.account_1, "value": 19},
                {"token_address": self.token_2, "lock_address": self.lock_1, "account_address": self.account_1, "value": 10},
                {"token_address": self.token_1, "lock_address": self.lock_1, "account_address": self.account_1, "value": 1},
            ]
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # ParameterError: invalid account_address
    def test_error_1(self, client: TestClient, session: Session):
        config.BOND_TOKEN_ENABLED = True

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
        config.BOND_TOKEN_ENABLED = True

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
        config.BOND_TOKEN_ENABLED = True

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

    # <Error_4>
    # Not Supported
    def test_error_4(self, client: TestClient, session: Session):
        config.BOND_TOKEN_ENABLED = False

        # Request target API
        resp = client.get(
            self.apiurl_base.format(account_address="some_address"),
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /Position/some_address/StraightBond/Lock'
        }
