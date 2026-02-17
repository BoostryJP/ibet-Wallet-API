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
import logging
from collections.abc import Awaitable, Callable, Generator
from unittest import mock
from unittest.mock import AsyncMock, MagicMock

import pytest

from batch.indexer_Transfer_Combined import ScheduledProcessor, main, run_processor


@pytest.fixture(scope="function")
def main_func() -> Generator[Callable[[], Awaitable[None]], None, None]:
    logger = logging.getLogger("ibet_wallet_batch")
    default_log_level = logger.level
    logger.setLevel(logging.DEBUG)
    logger.propagate = True
    yield main
    logger.propagate = False
    logger.setLevel(default_log_level)


# Verify that both processors are scheduled independently and run even if one takes a long time
@pytest.mark.asyncio
async def test_main_schedules_processors_independently(
    main_func: Callable[[], Awaitable[None]],
) -> None:
    async def long_sync() -> None:
        await asyncio.sleep(5.0)  # Simulate long processing time

    transfer_processor = MagicMock()
    transfer_processor.sync_new_logs = AsyncMock(side_effect=long_sync)

    transfer_approval_processor = MagicMock()
    transfer_approval_processor.sync_new_logs = AsyncMock()

    with (
        mock.patch("app.config.SHARE_TOKEN_ENABLED", True),
        mock.patch(
            "batch.indexer_Transfer_Combined.SHARE_TOKEN_ENABLED",
            True,
        ),
        mock.patch(
            "batch.indexer_Transfer_Combined.indexer_Transfer.Processor",
            return_value=transfer_processor,
        ),
        mock.patch(
            "batch.indexer_Transfer_Combined.indexer_TransferApproval.Processor",
            return_value=transfer_approval_processor,
        ),
        pytest.raises(asyncio.TimeoutError),
    ):
        await asyncio.wait_for(main_func(), timeout=0.05)

    assert transfer_processor.sync_new_logs.await_count == 1
    assert transfer_approval_processor.sync_new_logs.await_count == 1


# Verify that run_processor handles unexpected exceptions
@pytest.mark.asyncio
async def test_run_processor_handles_unexpected_error() -> None:
    processor = MagicMock()
    processor.sync_new_logs = AsyncMock(side_effect=Exception("unexpected error"))
    scheduled = ScheduledProcessor(
        processor=processor,
        child_logger=MagicMock(),
        interval_sec=1,
    )

    await run_processor(scheduled)

    assert processor.sync_new_logs.await_count == 1
