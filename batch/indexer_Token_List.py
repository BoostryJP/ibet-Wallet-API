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
import hashlib
import json
import sys
import time

import aiohttp
from aiohttp import ClientTimeout
from eth_utils import to_checksum_address
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import REQUEST_TIMEOUT, TOKEN_LIST_SLEEP_INTERVAL, TOKEN_LIST_URL
from app.database import BatchAsyncSessionLocal
from app.errors import ServiceUnavailable
from app.model.db import TokenList
from batch import free_malloc, log

process_name = "INDEXER-TOKEN-LIST"
LOG = log.get_logger(process_name=process_name)


class Processor:
    """Processor for indexing token list"""

    def __init__(self):
        self.token_list_digest = None

    async def process(self):
        LOG.info("Syncing token list")

        # Get from TOKEN_LIST_URL
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    TOKEN_LIST_URL,
                    timeout=ClientTimeout(
                        connect=REQUEST_TIMEOUT[0], total=REQUEST_TIMEOUT[1]
                    ),
                ) as response:
                    if response.status != 200:
                        raise Exception(f"status code={response.status}")
                    token_list_json = await response.json()
        except Exception:
            LOG.exception("Failed to get token list")
            return

        # Check the difference from the previous cycle
        _resp_digest = hashlib.sha256(json.dumps(token_list_json).encode()).hexdigest()
        if _resp_digest == self.token_list_digest:
            LOG.info("Skip: There are no differences from the previous cycle")
            return
        else:
            self.token_list_digest = _resp_digest

        # Update DB data
        db_session = BatchAsyncSessionLocal()
        try:
            # Delete all token list from DB
            await db_session.execute(delete(TokenList))

            # Insert token list
            for i, token in enumerate(token_list_json):
                token_address = token.get("token_address", None)
                token_template = token.get("token_template", None)
                key_manager = token.get("key_manager", None)
                product_type = token.get("product_type", None)

                if (
                    not isinstance(token_address, str)
                    or not isinstance(token_template, str)
                    or not isinstance(key_manager, list)
                    or not isinstance(product_type, int)
                ):
                    LOG.notice(
                        f"Invalid type: token_address={token_address}, token_template={token_template}, key_manager={key_manager}, product_type={product_type}"
                    )
                    continue
                try:
                    token_address = to_checksum_address(token_address)
                except ValueError:
                    LOG.notice(
                        f"Invalid address: index={i} token_address={token_address}"
                    )
                    continue
                try:
                    await self.__sink_on_token_list(
                        db_session=db_session,
                        token_address=token_address,
                        token_template=token_template,
                        key_manager=key_manager,
                        product_type=product_type,
                    )
                except IntegrityError:
                    LOG.notice(
                        f"Duplicate address: index={i} token_address={token_address}"
                    )
                    continue

            await db_session.commit()
            await db_session.close()
        except Exception as e:
            await db_session.rollback()
            await db_session.close()
            raise e
        LOG.info("Sync job has been completed")

    @staticmethod
    async def __sink_on_token_list(
        db_session: AsyncSession,
        token_address: str,
        token_template: str,
        key_manager: list[str],
        product_type: int,
    ):
        _token_list = TokenList()
        _token_list.token_address = token_address
        _token_list.token_template = token_template
        _token_list.key_manager = key_manager
        _token_list.product_type = product_type
        await db_session.merge(_token_list)


async def main():
    LOG.info("Service started successfully")
    processor = Processor()
    while True:
        start_time = time.time()

        try:
            await processor.process()
        except ServiceUnavailable:
            LOG.notice("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:  # Unexpected errors
            LOG.exception("An exception occurred during event synchronization")

        elapsed_time = time.time() - start_time
        await asyncio.sleep(max(TOKEN_LIST_SLEEP_INTERVAL - elapsed_time, 0))
        free_malloc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
