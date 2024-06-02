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

import requests
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3

from app import config
from app.model.db import Node

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))


class TestNodeInfoBlockSyncStatus:
    # target api
    apiurl = "/NodeInfo/BlockSyncStatus"

    @staticmethod
    def insert_node_data(
        session, is_synced, endpoint_uri=config.WEB3_HTTP_PROVIDER, priority=0
    ):
        node = Node()
        node.is_synced = is_synced
        node.endpoint_uri = endpoint_uri
        node.priority = priority
        session.add(node)
        session.commit()

    ##################################################
    # Normal
    ##################################################

    # Normal_1
    # Node is synced
    def test_normal_1(self, client: TestClient, session: Session):
        with mock.patch(
            "app.utils.web3_utils.AsyncFailOverHTTPProvider.fail_over_mode", True
        ):
            # prepare test data
            self.insert_node_data(
                session, is_synced=False, endpoint_uri="http://localhost:8546"
            )
            self.insert_node_data(
                session,
                is_synced=True,
                endpoint_uri=config.WEB3_HTTP_PROVIDER,
                priority=1,
            )

            # request target api
            resp = client.get(self.apiurl)

        # assertion
        latest_block_number = web3.eth.block_number
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "is_synced": True,
            "latest_block_number": latest_block_number,
        }

    # Normal_2
    # Node is not synced
    def test_normal_2(self, client: TestClient, session: Session):
        with mock.patch(
            "app.utils.web3_utils.AsyncFailOverHTTPProvider.fail_over_mode", True
        ):
            # prepare test data
            self.insert_node_data(session, is_synced=False)
            self.insert_node_data(
                session,
                is_synced=False,
                endpoint_uri="http://localhost:8546",
                priority=1,
            )

            # request target api
            resp = client.get(self.apiurl)

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {"is_synced": False, "latest_block_number": None}

    ##################################################
    # Error
    ##################################################

    # Error_1
    @mock.patch(
        "web3.AsyncWeb3.AsyncHTTPProvider.make_request",
        MagicMock(side_effect=requests.exceptions.ReadTimeout()),
    )
    def test_error_1(self, client: TestClient, session: Session):
        # prepare test data
        self.insert_node_data(
            session, is_synced=False, endpoint_uri="http://localhost:8546"
        )
        self.insert_node_data(
            session,
            is_synced=True,
            endpoint_uri=config.WEB3_HTTP_PROVIDER,
            priority=1,
        )

        # request target api
        resp = client.get(self.apiurl)

        # assertion
        assert resp.status_code == 503
        assert resp.json()["meta"] == {
            "code": 503,
            "message": "Service Unavailable",
            "description": "Temporarily unable to connect to web3 provider",
        }
