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
import os
import sys
import time
from typing import Sequence

import httpx
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

import log

from app.config import CHAT_WEBHOOK_URL
from app.database import BatchAsyncSessionLocal
from app.model.db import ChatWebhook

LOG = log.get_logger(process_name="PROCESSOR-SEND-CHAT-WEBHOOK")


class Processor:
    async def process(self):
        db_session = BatchAsyncSessionLocal()
        try:
            hook_list: Sequence[ChatWebhook] = (
                await db_session.scalars(select(ChatWebhook))
            ).all()
            if len(hook_list) > 0:
                LOG.info("Process start")

                for hook in hook_list:
                    try:
                        async with httpx.AsyncClient() as client:
                            await client.post(CHAT_WEBHOOK_URL, json=hook.message)
                    except Exception:
                        LOG.exception("Failed to send chat webhook")
                    finally:
                        # Delete the message regardless of the status code of the response.
                        await db_session.delete(hook)
                        await db_session.commit()
                LOG.info("Process end")
        finally:
            await db_session.close()


async def main():
    LOG.info("Service started successfully")
    processor = Processor()
    while True:
        start_time = time.time()
        try:
            await processor.process()
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception(ex)

        elapsed_time = time.time() - start_time
        await asyncio.sleep(max(30 - elapsed_time, 0))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
