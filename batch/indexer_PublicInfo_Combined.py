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
    COMPANY_LIST_LOCAL_MODE,
    COMPANY_LIST_SLEEP_INTERVAL,
    PUBLIC_ACCOUNT_LIST_SLEEP_INTERVAL,
    TOKEN_LIST_SLEEP_INTERVAL,
)
from app.errors import ServiceUnavailable
from batch import free_malloc, log
from batch.log import BatchLoggerAdapter
from batch.sub_indexers import (
    indexer_Company_List,
    indexer_PublicInfo_PublicAccountList,
    indexer_PublicInfo_TokenList,
)

process_name = "INDEXER-PUBLIC-INFO-COMBINED"
LOG: BatchLoggerAdapter = log.get_logger(process_name=process_name)


class IndexerProcessor(Protocol):
    def process(self) -> None: ...


@dataclass
class ScheduledProcessor:
    processor: IndexerProcessor
    child_logger: BatchLoggerAdapter
    interval_sec: int
    next_run_at: float = 0.0


async def run_processor(processor: IndexerProcessor, child_logger: BatchLoggerAdapter):
    try:
        with log.parent_process(process_name):
            processor.process()
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
            child_logger.exception("An exception occurred during processing")


async def main():
    LOG.info("Service started successfully")

    loop_interval_sec = 5

    processors: list[ScheduledProcessor] = [
        ScheduledProcessor(
            processor=indexer_PublicInfo_TokenList.Processor(),
            child_logger=indexer_PublicInfo_TokenList.LOG,
            interval_sec=TOKEN_LIST_SLEEP_INTERVAL,
        ),
        ScheduledProcessor(
            processor=indexer_PublicInfo_PublicAccountList.Processor(),
            child_logger=indexer_PublicInfo_PublicAccountList.LOG,
            interval_sec=PUBLIC_ACCOUNT_LIST_SLEEP_INTERVAL,
        ),
    ]

    if COMPANY_LIST_LOCAL_MODE:
        LOG.info("CompanyList processor is disabled by COMPANY_LIST_LOCAL_MODE")
    else:
        processors.append(
            ScheduledProcessor(
                processor=indexer_Company_List.Processor(),
                child_logger=indexer_Company_List.LOG,
                interval_sec=COMPANY_LIST_SLEEP_INTERVAL,
            )
        )
        LOG.info("CompanyList processor is enabled")

    now = time.time()
    for scheduled in processors:
        await run_processor(scheduled.processor, scheduled.child_logger)
        scheduled.next_run_at = now + scheduled.interval_sec

    while True:
        loop_start = time.time()

        for scheduled in processors:
            if loop_start >= scheduled.next_run_at:
                await run_processor(scheduled.processor, scheduled.child_logger)
                scheduled.next_run_at = time.time() + scheduled.interval_sec

        elapsed_time = time.time() - loop_start
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
