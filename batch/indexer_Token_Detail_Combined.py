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
import sys
import time
from dataclasses import dataclass
from typing import Protocol

from app import config
from batch import free_malloc, log
from batch.sub_indexers.indexer_Token_Detail import (
    Processor as TokenDetailProcessor,
    process_name as token_detail_process_name,
)
from batch.sub_indexers.indexer_Token_Detail_ShortTerm import (
    Processor as TokenDetailShortTermProcessor,
    process_name as token_detail_short_term_process_name,
)

process_name = "INDEXER-TOKEN-DETAIL-COMBINED"
LOG = log.get_logger(process_name=process_name)


class IndexerProcessor(Protocol):
    async def process(self) -> None: ...


@dataclass
class ScheduledProcessor:
    process_name: str
    processor: IndexerProcessor
    interval_sec: int
    next_run_at: float = 0.0
    current_task: asyncio.Task[None] | None = None
    delayed_logged: bool = False


async def run_processor(scheduled: ScheduledProcessor):
    """Run the processor and handle exceptions"""

    child_logger = log.get_logger(process_name=scheduled.process_name)
    try:
        with log.parent_process(process_name):
            await scheduled.processor.process()
            child_logger.debug("Processed")
    except Exception:
        with log.parent_process(process_name):
            child_logger.exception("An exception occurred during processing")


async def main():
    """Main function to run the combined token detail processors"""

    LOG.info("Service started successfully")

    loop_interval_sec = 1

    # Initialize scheduled processors
    processors: list[ScheduledProcessor] = [
        ScheduledProcessor(
            process_name=token_detail_process_name,
            processor=TokenDetailProcessor(),
            interval_sec=config.TOKEN_CACHE_REFRESH_INTERVAL,
        ),
        ScheduledProcessor(
            process_name=token_detail_short_term_process_name,
            processor=TokenDetailShortTermProcessor(),
            interval_sec=config.TOKEN_SHORT_TERM_CACHE_REFRESH_INTERVAL,
        ),
    ]

    # Set initial next run time to now for all processors
    now = time.time()
    for scheduled in processors:
        scheduled.next_run_at = now

    # Main loop to run processors at their scheduled intervals
    while True:
        loop_start = time.time()

        for scheduled in processors:
            # Await the current task if it's done, to catch any exceptions
            current_task = scheduled.current_task
            if current_task is not None and current_task.done():
                await current_task
                scheduled.current_task = None
                scheduled.delayed_logged = False

            # Detect delay when the processor is still running beyond its next scheduled run time.
            if (
                current_task is not None
                and not current_task.done()
                and loop_start >= scheduled.next_run_at
                and not scheduled.delayed_logged
            ):
                with log.parent_process(process_name):
                    child_logger = log.get_logger(process_name=scheduled.process_name)
                    child_logger.notice(
                        "Processing is delayed: processing time exceeded the configured interval"
                    )
                    scheduled.delayed_logged = True

            # Schedule the next run if it's time and there's no current task running
            if loop_start >= scheduled.next_run_at and scheduled.current_task is None:
                scheduled.current_task = asyncio.create_task(run_processor(scheduled))
                scheduled.next_run_at = time.time() + scheduled.interval_sec

        elapsed_time = time.time() - loop_start
        time_to_sleep = max(loop_interval_sec - elapsed_time, 0)

        await asyncio.sleep(time_to_sleep)
        free_malloc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
