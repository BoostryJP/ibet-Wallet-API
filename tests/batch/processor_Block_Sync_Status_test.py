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

import asyncio
from unittest import mock
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from app.model.db import Node
from batch.processor_Block_Sync_Status import Processor

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


@pytest_asyncio.fixture(scope="function")
async def processor():
    yield Processor()


@pytest.mark.order("first")
@pytest.mark.asyncio
class TestProcessor:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Run 1st: Normal state
    # Run 2nd: Abnormal state - Setting BLOCK_GENERATION_SPEED_THRESHOLD to 100% will trigger an error.
    # Run 3rd: Return to normal state
    # Run 4th: Abnormal state - An error occurs when the difference between highestBlock and currentBlock exceeds a threshold.
    # Run 5th: Return to normal state - Since the difference between highestBlock and currentBlock is within the threshold, no error occurs.
    async def test_normal_1(self, processor: Processor, async_session: AsyncSession):
        # Run 1st: Normal state
        await processor.initial_setup()
        await processor.process()
        await async_session.commit()

        _node = (await async_session.scalars(select(Node).limit(1))).first()
        assert _node is not None
        assert _node.id == 1
        assert _node.endpoint_uri == config.WEB3_HTTP_PROVIDER
        assert _node.priority == 0
        assert _node.is_synced == True

        # Run 2nd: Abnormal state
        # - Setting BLOCK_GENERATION_SPEED_THRESHOLD to 100% will trigger an error.
        await asyncio.sleep(config.BLOCK_SYNC_STATUS_SLEEP_INTERVAL)
        with mock.patch("app.config.BLOCK_GENERATION_SPEED_THRESHOLD", 100):
            await processor.process()
            await async_session.rollback()
            async_session.expire_all()

        _node = (await async_session.scalars(select(Node).limit(1))).first()
        assert _node is not None
        assert _node.is_synced == False

        # Run 3rd: Return to normal state
        await asyncio.sleep(config.BLOCK_SYNC_STATUS_SLEEP_INTERVAL)
        await processor.process()
        await async_session.rollback()
        async_session.expire_all()

        _node = (await async_session.scalars(select(Node).limit(1))).first()
        assert _node is not None
        assert _node.is_synced == True

        # Run 4th: Abnormal state
        # - An error occurs when the difference between highestBlock and currentBlock exceeds a threshold.
        await asyncio.sleep(config.BLOCK_SYNC_STATUS_SLEEP_INTERVAL)
        block_number = web3.eth.block_number
        is_syncing_mock = AsyncMock()
        is_syncing_mock.return_value = {
            "highestBlock": block_number,
            "currentBlock": block_number - 3,
        }
        with mock.patch("web3.eth.async_eth.AsyncEth.syncing", is_syncing_mock()):
            await processor.process()
            await async_session.rollback()
            async_session.expire_all()

        _node = (await async_session.scalars(select(Node).limit(1))).first()
        assert _node is not None
        assert _node.is_synced == False

        # Run 5th: Return to normal state
        # - Since the difference between highestBlock and currentBlock is within the threshold, no error occurs.
        await asyncio.sleep(config.BLOCK_SYNC_STATUS_SLEEP_INTERVAL)
        block_number = web3.eth.block_number
        is_syncing_mock = AsyncMock()
        is_syncing_mock.return_value = {
            "highestBlock": block_number,
            "currentBlock": block_number - 2,
        }
        with mock.patch("web3.eth.async_eth.AsyncEth.syncing", is_syncing_mock()):
            await processor.process()
            await async_session.rollback()
            async_session.expire_all()

        _node = (await async_session.scalars(select(Node).limit(1))).first()
        assert _node is not None
        assert _node.is_synced == True

    # <Normal_2>
    # Standby node is down to sync
    @mock.patch("app.config.WEB3_HTTP_PROVIDER_STANDBY", ["http://test1:1000"])
    async def test_normal_2(self, async_session: AsyncSession):
        processor = Processor()
        await processor.initial_setup()

        # pre assertion
        _node = (await async_session.scalars(select(Node).limit(1))).first()
        assert _node is not None
        assert _node.id == 1
        assert _node.endpoint_uri == "http://test1:1000"
        assert _node.priority == 1
        assert _node.is_synced == False

        # node sync(processing)
        provider = processor.node_info["http://test1:1000"]["web3"].manager.provider
        assert provider is not None
        org_value = getattr(provider, "endpoint_uri")
        assert isinstance(org_value, str)
        setattr(provider, "endpoint_uri", config.WEB3_HTTP_PROVIDER)
        await processor.process()
        await async_session.rollback()
        async_session.expire_all()
        setattr(provider, "endpoint_uri", org_value)

        # assertion
        _node = (
            await async_session.scalars(
                select(Node).where(Node.endpoint_uri == "http://test1:1000").limit(1)
            )
        ).first()
        assert _node is not None
        assert _node.is_synced == True

    # <Normal_3>
    # Delete old node data
    async def test_normal_3(self, async_session: AsyncSession):
        node = Node()
        node.id = 1
        node.endpoint_uri = "old_node"
        node.priority = 1
        node.is_synced = True
        async_session.add(node)
        await async_session.commit()

        processor = Processor()
        await processor.initial_setup()

        # assertion-1
        old_node = (
            await async_session.scalars(
                select(Node).where(
                    Node.endpoint_uri.not_in(list(config.WEB3_HTTP_PROVIDER))
                )
            )
        ).all()
        assert len(old_node) == 0

        # process
        await processor.process()
        await async_session.rollback()
        async_session.expire_all()

        # assertion-2
        new_node = (await async_session.scalars(select(Node).limit(1))).first()
        assert new_node is not None
        assert new_node.endpoint_uri == config.WEB3_HTTP_PROVIDER
        assert new_node.priority == 0
        assert new_node.is_synced == True

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # node down(initialize)
    @mock.patch(
        "app.config.WEB3_HTTP_PROVIDER_STANDBY",
        ["http://localhost:1000", "http://test2:2000"],
    )
    @mock.patch(
        "web3.providers.rpc.AsyncHTTPProvider.make_request",
        MagicMock(side_effect=Exception()),
    )
    async def test_error_1(self, async_session: AsyncSession):
        processor = Processor()
        await processor.initial_setup()

        # assertion
        _node_list = (await async_session.scalars(select(Node).order_by(Node.id))).all()
        assert len(_node_list) == 3
        _node = _node_list[0]
        assert _node.id == 1
        assert _node.endpoint_uri == config.WEB3_HTTP_PROVIDER
        assert _node.priority == 0
        assert _node.is_synced == False
        _node = _node_list[1]
        assert _node.id == 2
        assert _node.endpoint_uri == "http://localhost:1000"
        assert _node.priority == 1
        assert _node.is_synced == False
        _node = _node_list[2]
        assert _node.id == 3
        assert _node.endpoint_uri == "http://test2:2000"
        assert _node.priority == 1
        assert _node.is_synced == False

    # <Error_2>
    # node down(processing)
    async def test_error_2(self, processor: Processor, async_session: AsyncSession):
        await processor.initial_setup()
        await processor.process()

        # assertion
        _node = (await async_session.scalars(select(Node).limit(1))).first()
        assert _node is not None
        assert _node.id == 1
        assert _node.endpoint_uri == config.WEB3_HTTP_PROVIDER
        assert _node.priority == 0
        assert _node.is_synced == True

        # node down(processing)
        provider = processor.node_info[config.WEB3_HTTP_PROVIDER][
            "web3"
        ].manager.provider
        org_value = getattr(provider, "endpoint_uri", None)
        assert isinstance(org_value, str)
        setattr(provider, "endpoint_uri", "http://hogehoge")
        await processor.process()
        await async_session.rollback()
        async_session.expire_all()
        setattr(provider, "endpoint_uri", org_value)

        # assertion
        _node = (await async_session.scalars(select(Node).limit(1))).first()
        assert _node is not None
        assert _node.id == 1
        assert _node.endpoint_uri == config.WEB3_HTTP_PROVIDER
        assert _node.priority == 0
        assert _node.is_synced == False
