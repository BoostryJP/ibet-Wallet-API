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
from typing import Protocol

from sqlalchemy.exc import SQLAlchemyError

from app.config import SHARE_TOKEN_ENABLED
from app.errors import ServiceUnavailable
from batch import free_malloc, log
from batch.log import BatchLoggerAdapter
from batch.sub_indexers import (
    indexer_Transfer,
    indexer_TransferApproval,
)

process_name = "INDEXER-TRANSFER-COMBINED"
LOG: BatchLoggerAdapter = log.get_logger(process_name=process_name)


class IndexerProcessor(Protocol):
    async def sync_new_logs(self) -> None: ...


async def main():
    """Main function for the combined Transfer indexer."""

    LOG.info("Service started successfully")

    loop_interval_sec = 5

    processors: list[tuple[IndexerProcessor, BatchLoggerAdapter]] = [
        (indexer_Transfer.Processor(), indexer_Transfer.LOG),
    ]

    if SHARE_TOKEN_ENABLED:
        processors.append(
            (indexer_TransferApproval.Processor(), indexer_TransferApproval.LOG)
        )
        LOG.info("TransferApproval processor is enabled")
    else:
        LOG.info("TransferApproval processor is disabled")

    # Initial sync (retry until each processor succeeds once)
    for processor, child_logger in processors:
        initialized = False
        while not initialized:
            start_time = time.time()
            try:
                with log.parent_process(process_name):
                    await processor.sync_new_logs()
                    initialized = True
                    child_logger.info("Initial sync succeeded")
            except Exception:
                with log.parent_process(process_name):
                    child_logger.exception("Initial sync failed")

            elapsed_time = time.time() - start_time
            await asyncio.sleep(max(loop_interval_sec - elapsed_time, 0))

    # Main loop
    while True:
        start_time = time.time()

        for processor, child_logger in processors:
            try:
                with log.parent_process(process_name):
                    await processor.sync_new_logs()
                    child_logger.debug("Processed")
            except ServiceUnavailable:
                with log.parent_process(process_name):
                    child_logger.notice("An external service was unavailable")
            except SQLAlchemyError as sa_err:
                with log.parent_process(process_name):
                    child_logger.error(
                        f"A database error has occurred: code={sa_err.code}\n{sa_err}"
                    )
            except Exception:
                with log.parent_process(process_name):
                    child_logger.exception(
                        "An exception occurred during event synchronization"
                    )

        elapsed_time = time.time() - start_time
        time_to_sleep = max(loop_interval_sec - elapsed_time, 0)
        if time_to_sleep == 0:
            LOG.notice("Processing is delayed")
        await asyncio.sleep(time_to_sleep)
        free_malloc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
