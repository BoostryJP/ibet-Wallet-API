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

from unittest import mock
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3

from app import config
from app.model.db import Node


class TestEthereumJsonRpc:
    # Target API endpoint
    apiurl = "/Eth/RPC"

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    def test_normal_1(self, client: TestClient, session: Session):
        node_1 = Node()
        node_1.is_synced = False
        node_1.endpoint_uri = ""
        node_1.priority = 0
        session.add(node_1)

        node_2 = Node()
        node_2.is_synced = True
        node_2.endpoint_uri = config.WEB3_HTTP_PROVIDER
        node_2.priority = 1
        session.add(node_2)

        session.commit()

        # Request target API
        resp = client.post(self.apiurl, json={"method": "eth_syncing", "params": []})

        # Assertion
        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "id": 1,
            "jsonrpc": "2.0",
            "result": web3.eth.syncing,
        }

    # Normal_2
    # method is not exists
    def test_normal_2(self, client: TestClient, session: Session):
        node_1 = Node()
        node_1.is_synced = True
        node_1.endpoint_uri = config.WEB3_HTTP_PROVIDER
        node_1.priority = 1
        session.add(node_1)

        session.commit()

        # Request target API
        resp = client.post(self.apiurl, json={"method": "eth_sync", "params": []})

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32004,
                "message": "Method eth_sync is not supported",
                "data": {
                    "message": "Method eth_sync is not supported",
                    "data": {"method": "eth_sync", "params": []},
                },
            },
        }

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # Invalid Parameter
    # value_error.missing
    def test_error_1(self, client: TestClient):
        # Request target API
        resp = client.post(self.apiurl, json={})

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "input": {},
                    "loc": ["body", "method"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": {},
                    "loc": ["body", "params"],
                    "msg": "Field required",
                    "type": "missing",
                },
            ],
        }

    # Error_2
    # Invalid Parameter
    # method is not available
    def test_error_2(self, client: TestClient):
        # Request target API
        resp = client.post(self.apiurl, json={"method": "invalid_method", "params": []})

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "ctx": {"error": {}},
                    "input": "invalid_method",
                    "loc": ["body", "method"],
                    "msg": "Value error, The method invalid_method is not available",
                    "type": "value_error",
                }
            ],
        }

    # Error_3_1
    # Service Unavailable
    def test_error_3_1(self, client: TestClient, session: Session):
        node_1 = Node()
        node_1.is_synced = True
        node_1.endpoint_uri = config.WEB3_HTTP_PROVIDER
        node_1.priority = 1
        session.add(node_1)

        session.commit()

        # Request target API
        with mock.patch("httpx.AsyncClient.post", MagicMock(side_effect=Exception())):
            resp = client.post(
                self.apiurl, json={"method": "eth_syncing", "params": []}
            )

        # Assertion
        assert resp.status_code == 503
        assert resp.json()["meta"] == {
            "code": 503,
            "message": "Service Unavailable",
            "description": "Unable to connect to web3 provider",
        }

    # Error_3_2
    # Service Unavailable
    # No web3 providers available
    def test_error_3_2(self, client: TestClient, session: Session):
        # Request target API
        resp = client.post(self.apiurl, json={"method": "eth_syncing", "params": []})

        # Assertion
        assert resp.status_code == 503
        assert resp.json()["meta"] == {
            "code": 503,
            "message": "Service Unavailable",
            "description": "No web3 providers available",
        }
