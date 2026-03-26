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

from sqlalchemy.exc import SQLAlchemyError

from app.config import (
    BOND_TOKEN_ENABLED,
    COUPON_TOKEN_ENABLED,
    MEMBERSHIP_TOKEN_ENABLED,
    SHARE_TOKEN_ENABLED,
)
from app.errors import ServiceUnavailable
from batch import free_malloc, log
from batch.log import BatchLoggerAdapter

process_name = "INDEXER-POSITION-COMBINED"
LOG: BatchLoggerAdapter = log.get_logger(process_name=process_name)


class IndexerProcessor(Protocol):
    async def sync_new_logs(self) -> None: ...


@dataclass
class ScheduledProcessor:
    processor: IndexerProcessor
    child_logger: BatchLoggerAdapter
    interval_sec: int
    next_run_at: float = 0.0
    current_task: asyncio.Task[None] | None = None
    delayed_logged: bool = False


async def run_processor(scheduled: ScheduledProcessor):
    """Run the processor and handle exceptions"""

    try:
        with log.parent_process(process_name):
            await scheduled.processor.sync_new_logs()
            scheduled.child_logger.debug("Processed")
    except ServiceUnavailable:
        with log.parent_process(process_name):
            scheduled.child_logger.notice("An external service was unavailable")
    except SQLAlchemyError as sa_err:
        with log.parent_process(process_name):
            scheduled.child_logger.error(
                f"A database error has occurred: code={sa_err.code}\n{sa_err}"
            )
    except Exception:
        with log.parent_process(process_name):
            scheduled.child_logger.exception(
                "An exception occurred during event synchronization"
            )


async def main():
    """Main function for the combined Position indexer."""

    LOG.info("Service started successfully")

    loop_interval_sec = 10

    processors: list[ScheduledProcessor] = []

    # Add sub-indexers based on enabled features
    if SHARE_TOKEN_ENABLED:
        from batch.sub_indexers import indexer_Position_Share

        processors.append(
            ScheduledProcessor(
                processor=indexer_Position_Share.Processor(),
                child_logger=indexer_Position_Share.LOG,
                interval_sec=loop_interval_sec,
            )
        )
        LOG.info("PositionShare processor is enabled")
    else:
        LOG.info("PositionShare processor is disabled")

    if BOND_TOKEN_ENABLED:
        from batch.sub_indexers import indexer_Position_Bond

        processors.append(
            ScheduledProcessor(
                processor=indexer_Position_Bond.Processor(),
                child_logger=indexer_Position_Bond.LOG,
                interval_sec=loop_interval_sec,
            )
        )
        LOG.info("PositionBond processor is enabled")
    else:
        LOG.info("PositionBond processor is disabled")

    if MEMBERSHIP_TOKEN_ENABLED:
        from batch.sub_indexers import indexer_Position_Membership

        processors.append(
            ScheduledProcessor(
                processor=indexer_Position_Membership.Processor(),
                child_logger=indexer_Position_Membership.LOG,
                interval_sec=loop_interval_sec,
            )
        )
        LOG.info("PositionMembership processor is enabled")
    else:
        LOG.info("PositionMembership processor is disabled")

    if COUPON_TOKEN_ENABLED:
        from batch.sub_indexers import (
            indexer_Consume_Coupon,
            indexer_Position_Coupon,
        )

        processors.append(
            ScheduledProcessor(
                processor=indexer_Position_Coupon.Processor(),
                child_logger=indexer_Position_Coupon.LOG,
                interval_sec=loop_interval_sec,
            )
        )
        processors.append(
            ScheduledProcessor(
                processor=indexer_Consume_Coupon.Processor(),
                child_logger=indexer_Consume_Coupon.LOG,
                interval_sec=loop_interval_sec,
            )
        )
        LOG.info("PositionCoupon processor is enabled")
    else:
        LOG.info("PositionCoupon processor is disabled")

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
                    scheduled.child_logger.notice(
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
