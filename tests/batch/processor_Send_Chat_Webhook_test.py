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

import json
import logging
from unittest import mock
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.model.db import ChatWebhook
from batch.processor_Send_Chat_Webhook import LOG, Processor


@pytest.fixture(scope="function")
def processor():
    return Processor()


@pytest.fixture(scope="function")
def caplog(caplog: pytest.LogCaptureFixture):
    LOG = logging.getLogger("ibet_wallet_batch")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield caplog
    LOG.propagate = False
    LOG.setLevel(default_log_level)


@pytest.mark.asyncio
class TestProcessorSendChatWebhook:
    # Normal_1
    # No unsent hook exists
    async def test_normal_1(self, processor, async_session, caplog):
        # Run processor
        with mock.patch(
            "aiohttp.client.ClientSession.post", AsyncMock(side_effect=None)
        ):
            await processor.process()
            await async_session.commit()

        # Assertion
        assert 0 == caplog.record_tuples.count((LOG.name, logging.INFO, "Process end"))

    # Normal_2
    # Unsent hook exists
    async def test_normal_2(self, processor, async_session, caplog):
        # Prepare data
        hook = ChatWebhook()
        hook.message = json.dumps({"title": "test_title1", "text": "test_text"})
        async_session.add(hook)
        hook = ChatWebhook()
        hook.message = json.dumps({"title": "test_title2", "text": "test_text"})
        async_session.add(hook)
        await async_session.commit()

        # Run processor
        with mock.patch(
            "aiohttp.client.ClientSession.post", AsyncMock(side_effect=None)
        ):
            await processor.process()
            await async_session.commit()

        # Assertion
        assert len((await async_session.scalars(select(ChatWebhook))).all()) == 0

        assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, "Process end"))

    # Normal_3
    # Fail to send message -> Skip
    async def test_normal_3(self, processor, async_session, caplog):
        # Prepare data
        hook = ChatWebhook()
        hook.message = json.dumps({"title": "test_title", "text": "test_text"})
        async_session.add(hook)
        await async_session.commit()

        # Run processor
        with mock.patch(
            "aiohttp.client.ClientSession.post", AsyncMock(side_effect=Exception())
        ):
            await processor.process()
            await async_session.commit()

        # Assertion
        assert len((await async_session.scalars(select(ChatWebhook))).all()) == 0

        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.ERROR, "Failed to send chat webhook")
        )

        assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, "Process end"))

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # SQLAlchemyError
    async def test_error_1(self, processor, async_session, caplog):
        # Prepare data
        hook = ChatWebhook()
        hook.message = json.dumps({"title": "test_title", "text": "test_text"})
        async_session.add(hook)
        await async_session.commit()

        # Run processor
        with (
            mock.patch(
                "aiohttp.client.ClientSession.post", AsyncMock(side_effect=None)
            ),
            mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()),
            pytest.raises(SQLAlchemyError),
        ):
            await processor.process()
            await async_session.commit()

        # Assertion
        assert len((await async_session.scalars(select(ChatWebhook))).all()) == 1

        assert 0 == caplog.record_tuples.count((LOG.name, logging.INFO, "Process end"))
