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
from unittest.mock import ANY, MagicMock

from fastapi.testclient import TestClient
from web3 import Web3

from app import config


class TestEthereumJsonRpc:
    # Target API endpoint
    apiurl = "/Eth/RPC"

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    def test_normal_1(self, client: TestClient):
        resp = client.post(self.apiurl, json={"method": "eth_syncing", "params": []})

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {"jsonrpc": "2.0", "result": web3.eth.syncing}

    # Normal_2
    # method is not exists
    def test_normal_2(self, client: TestClient):
        resp = client.post(self.apiurl, json={"method": "eth_sync", "params": []})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "id": None,
            "jsonrpc": "2.0",
            "error": {
                "message": "The method eth_sync does not exist/is not available",
                "stack": ANY,
                "code": -32700,
            },
        }

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # Invalid Parameter
    # value_error.missing
    def test_error_1(self, client: TestClient):
        resp = client.post(self.apiurl, json={})

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "loc": ["body", "method"],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
                {
                    "loc": ["body", "params"],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
            ],
        }

    # Error_2
    # Invalid Parameter
    # method is not available
    def test_error_2(self, client: TestClient):
        resp = client.post(self.apiurl, json={"method": "invalid_method", "params": []})

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "loc": ["body", "method"],
                    "msg": "method:invalid_method is not available",
                    "type": "value_error",
                }
            ],
        }

    # Error_3
    # Service Unavailable
    def test_error_3(self, client: TestClient):
        with mock.patch("requests.post", MagicMock(side_effect=Exception())):
            resp = client.post(
                self.apiurl, json={"method": "eth_syncing", "params": []}
            )

        assert resp.status_code == 503
        assert resp.json()["meta"] == {
            "code": 503,
            "message": "Service Unavailable",
            "description": "Unable to connect to web3 provider",
        }
