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

from batch.indexer_Token_Detail_Combined import (
    ScheduledProcessor,
    main,
    run_processor,
)


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
async def test_main_schedules_both_processors_independently(
    main_func: Callable[[], Awaitable[None]],
) -> None:
    async def long_process():
        await asyncio.sleep(5.0)  # Simulate long processing time

    token_detail_processor = MagicMock()
    token_detail_processor.process = AsyncMock(side_effect=long_process)

    short_term_processor = MagicMock()
    short_term_processor.process = AsyncMock()

    token_list_event_processor = MagicMock()
    token_list_event_processor.process = AsyncMock()

    with (
        mock.patch(
            "batch.indexer_Token_Detail_Combined.TokenListEventProcessor",
            return_value=token_list_event_processor,
        ),
        mock.patch(
            "batch.indexer_Token_Detail_Combined.TokenDetailProcessor",
            return_value=token_detail_processor,
        ),
        mock.patch(
            "batch.indexer_Token_Detail_Combined.TokenDetailShortTermProcessor",
            return_value=short_term_processor,
        ),
        mock.patch(
            "batch.indexer_Token_Detail_Combined.config.TOKEN_CACHE_REFRESH_INTERVAL",
            9999,
        ),
        mock.patch(
            "batch.indexer_Token_Detail_Combined.config.TOKEN_SHORT_TERM_CACHE_REFRESH_INTERVAL",
            9999,
        ),
        mock.patch("batch.indexer_Token_Detail_Combined.config.TOKEN_CACHE", True),
        pytest.raises(asyncio.TimeoutError),
    ):
        await asyncio.wait_for(main_func(), timeout=0.05)

    assert token_list_event_processor.process.await_count == 1
    assert token_detail_processor.process.await_count == 1
    assert short_term_processor.process.await_count == 1


@pytest.mark.asyncio
async def test_main_runs_only_token_list_event_when_token_cache_disabled(
    main_func: Callable[[], Awaitable[None]],
) -> None:
    token_list_event_processor = MagicMock()
    token_list_event_processor.process = AsyncMock()

    token_detail_processor = MagicMock()
    token_detail_processor.process = AsyncMock()

    short_term_processor = MagicMock()
    short_term_processor.process = AsyncMock()

    with (
        mock.patch(
            "batch.indexer_Token_Detail_Combined.TokenListEventProcessor",
            return_value=token_list_event_processor,
        ),
        mock.patch(
            "batch.indexer_Token_Detail_Combined.TokenDetailProcessor",
            return_value=token_detail_processor,
        ),
        mock.patch(
            "batch.indexer_Token_Detail_Combined.TokenDetailShortTermProcessor",
            return_value=short_term_processor,
        ),
        mock.patch("batch.indexer_Token_Detail_Combined.config.TOKEN_CACHE", False),
        pytest.raises(asyncio.TimeoutError),
    ):
        await asyncio.wait_for(main_func(), timeout=0.05)

    assert token_list_event_processor.process.await_count == 1
    assert token_detail_processor.process.await_count == 0
    assert short_term_processor.process.await_count == 0


# Verify that run_processor handles unexpected exceptions
@pytest.mark.asyncio
async def test_run_processor_handles_unexpected_error() -> None:
    process_name = "INDEXER-TOKEN-DETAIL-MOCK"
    processor = MagicMock()
    processor.process = AsyncMock(side_effect=Exception("unexpected error"))
    scheduled = ScheduledProcessor(
        process_name=process_name,
        processor=processor,
        interval_sec=1,
    )

    await run_processor(scheduled)

    assert processor.process.await_count == 1
