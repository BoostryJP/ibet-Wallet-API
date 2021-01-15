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

from app.model.node import Node


class TestNodeInfoBlockSyncStatus:
    # テスト対象API
    apiurl = '/v2/NodeInfo/BlockSyncStatus'

    @staticmethod
    def insert_node_data(session, is_synced):
        node = Node()
        node.is_synced = is_synced
        session.add(node)

    # ＜正常系1＞
    # ブロック同期正常
    def test_normal_1(self, client, session):
        TestNodeInfoBlockSyncStatus.insert_node_data(session, is_synced=True)

        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == {
            "is_synced": True
        }

    # ＜正常系2＞
    # ブロック同期停止
    def test_normal_2(self, client, session):
        TestNodeInfoBlockSyncStatus.insert_node_data(session, is_synced=False)

        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == {
            "is_synced": False
        }
