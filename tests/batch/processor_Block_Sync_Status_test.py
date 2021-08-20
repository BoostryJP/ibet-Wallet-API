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
import pytest
from unittest import mock
from unittest.mock import MagicMock

from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.model import Node
from batch import processor_Block_Sync_Status

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="function")
def watcher_factory(session):
    def _watcher(cls_name):
        cls = getattr(processor_Block_Sync_Status, cls_name)
        watcher = cls()
        return watcher

    return _watcher


class TestWatchBlockSyncState:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Working
    def test_normal_1(self, watcher_factory, session):
        watcher = watcher_factory("WatchBlockSyncState")

        # Run target process
        next_block_number = watcher.history.peekOldest()["block_number"] + 10000
        with mock.patch("web3.eth.Eth.blockNumber", next_block_number):
            watcher.loop()

        # Assertion
        _node = session.query(Node).first()
        assert _node.id == 1
        assert _node.is_synced is True

    # <Normal_2>
    # Working(1 block late)
    def test_normal_2(self, watcher_factory, session):
        watcher = watcher_factory("WatchBlockSyncState")

        # Run target process
        block_number = watcher.history.peekOldest()["block_number"]
        next_block_number = block_number + 10000
        with mock.patch("web3.eth.Eth.syncing", {"highestBlock": block_number, "currentBlock": block_number - 1}), \
             mock.patch("web3.eth.Eth.blockNumber", next_block_number):
            watcher.loop()

        # Assertion
        _node = session.query(Node).first()
        assert _node.id == 1
        assert _node.is_synced is True

    # <Normal_3>
    # Not Sync(now syncing)
    def test_normal_3(self, watcher_factory, session):
        watcher = watcher_factory("WatchBlockSyncState")

        # Run target process
        block_number = watcher.history.peekOldest()["block_number"]
        with mock.patch("web3.eth.Eth.syncing", {"highestBlock": block_number, "currentBlock": block_number - 2}):
            watcher.loop()

        # Assertion
        _node = session.query(Node).first()
        assert _node.id == 1
        assert _node.is_synced is False

    # <Normal_4>
    # Not Sync(block late)
    def test_normal_4(self, watcher_factory, session):
        watcher = watcher_factory("WatchBlockSyncState")

        # Run target process
        next_block_number = watcher.history.peekOldest()["block_number"] - 10000
        with mock.patch("web3.eth.Eth.blockNumber", next_block_number):
            watcher.loop()

        # Assertion
        _node = session.query(Node).first()
        assert _node.id == 1
        assert _node.is_synced is False

    # <Normal_5>
    # Working -> Working
    def test_normal_5(self, watcher_factory, session):
        watcher = watcher_factory("WatchBlockSyncState")

        # Prepare Data
        _node = Node()
        _node.is_synced = True
        session.add(_node)

        # Run target process
        next_block_number = watcher.history.peekOldest()["block_number"] + 10000
        with mock.patch("web3.eth.Eth.blockNumber", next_block_number):
            watcher.loop()

        # Assertion
        _node = session.query(Node).first()
        assert _node.id == 1
        assert _node.is_synced is True

    # <Normal_6>
    # Working -> Not Sync
    def test_normal_6(self, watcher_factory, session):
        watcher = watcher_factory("WatchBlockSyncState")

        # Prepare Data
        _node = Node()
        _node.is_synced = True
        session.add(_node)

        # Run target process
        next_block_number = watcher.history.peekOldest()["block_number"] - 10000
        with mock.patch("web3.eth.Eth.blockNumber", next_block_number):
            watcher.loop()

        # Assertion
        _node = session.query(Node).first()
        assert _node.id == 1
        assert _node.is_synced is False

    # <Normal_7>
    # Not Sync -> Working
    def test_normal_7(self, watcher_factory, session):
        watcher = watcher_factory("WatchBlockSyncState")

        # Prepare Data
        _node = Node()
        _node.is_synced = False
        session.add(_node)

        # Run target process
        next_block_number = watcher.history.peekOldest()["block_number"] + 10000
        with mock.patch("web3.eth.Eth.blockNumber", next_block_number):
            watcher.loop()

        # Assertion
        _node = session.query(Node).first()
        assert _node.id == 1
        assert _node.is_synced is True

    # <Normal_8>
    # Not Sync -> Not Sync
    def test_normal_8(self, watcher_factory, session):
        watcher = watcher_factory("WatchBlockSyncState")

        # Prepare Data
        _node = Node()
        _node.is_synced = False
        session.add(_node)

        # Run target process
        next_block_number = watcher.history.peekOldest()["block_number"] - 10000
        with mock.patch("web3.eth.Eth.blockNumber", next_block_number):
            watcher.loop()

        # Assertion
        _node = session.query(Node).first()
        assert _node.id == 1
        assert _node.is_synced is False

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Error occur
    def test_error_1(self, watcher_factory, session):
        watcher = watcher_factory("WatchBlockSyncState")

        # Run target process
        with mock.patch("web3.eth.Eth.blockNumber", MagicMock(side_effect=Exception())):
            watcher.loop()

        # Assertion
        _node = session.query(Node).first()
        assert _node is None
