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
from typing import Any

from sqlalchemy import create_engine, delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import AsyncHTTPProvider, AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware, Web3Middleware
from web3.types import RPCEndpoint, RPCResponse

from app import config
from app.config import EXPECTED_BLOCKS_PER_SEC
from app.database import BatchAsyncSessionLocal
from app.model.db import Node
from batch import free_malloc, log

LOG = log.get_logger(process_name="PROCESSOR-BLOCK_SYNC_STATUS")

db_engine = create_engine(config.DATABASE_URL, echo=False, pool_pre_ping=True)


class Web3WrapperException(Exception):
    pass


class CustomWeb3ExceptionMiddleware(Web3Middleware):
    async def async_wrap_make_request(self, make_request):
        async def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
            METHODS = [
                "eth_blockNumber",
                "eth_getBlockByNumber",
                "eth_syncing",
            ]
            if method in METHODS:
                try:
                    return await make_request(method, params)
                except Exception as ex:
                    # Throw Web3WrapperException if an error occurred in Web3(connection error, timeout, etc),
                    # Web3WrapperException is handled in this module.
                    raise Web3WrapperException(ex)
            else:
                return await make_request(method, params)

        return middleware


class RingBuffer:
    def __init__(self, size, default=None):
        self._next = 0
        self._buffer = [default] * size

    def append(self, data):
        self._buffer[self._next] = data
        self._next = (self._next + 1) % len(self._buffer)

    def peek_oldest(self):
        return self._buffer[self._next]


class Processor:
    def __init__(self):
        self.node_info = {}

    async def initial_setup(self):
        local_session = self.__get_db_session()
        try:
            # Delete old node data
            valid_endpoint_uri_list = [
                config.WEB3_HTTP_PROVIDER
            ] + config.WEB3_HTTP_PROVIDER_STANDBY
            await self.__delete_old_node(
                db_session=local_session,
                valid_endpoint_uri_list=valid_endpoint_uri_list,
            )
            # Initial setting
            await self.__set_node_info(
                db_session=local_session,
                endpoint_uri=config.WEB3_HTTP_PROVIDER,
                priority=0,
            )
            for endpoint_uri in config.WEB3_HTTP_PROVIDER_STANDBY:
                await self.__set_node_info(
                    db_session=local_session, endpoint_uri=endpoint_uri, priority=1
                )
            await local_session.commit()
        finally:
            await local_session.close()

    @staticmethod
    def __get_db_session() -> AsyncSession:
        return BatchAsyncSessionLocal()

    async def process(self):
        local_session = self.__get_db_session()
        try:
            for endpoint_uri in self.node_info.keys():
                try:
                    await self.__process(
                        db_session=local_session, endpoint_uri=endpoint_uri
                    )
                except Web3WrapperException:
                    await self.__web3_errors(
                        db_session=local_session, endpoint_uri=endpoint_uri
                    )
                    LOG.exception(f"Node connection failed: {endpoint_uri}")
                await local_session.commit()
        finally:
            await local_session.close()

    async def __set_node_info(
        self, db_session: AsyncSession, endpoint_uri: str, priority: int
    ):
        self.node_info[endpoint_uri] = {"priority": priority}

        web3 = AsyncWeb3(
            AsyncHTTPProvider(
                endpoint_uri,
                # Disabled retry logic explicitly
                exception_retry_configuration=None,
            ),
        )
        web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        web3.middleware_onion.add(CustomWeb3ExceptionMiddleware)
        self.node_info[endpoint_uri]["web3"] = web3

        # Get block number
        try:
            # NOTE: Immediately after the processing, the monitoring data is not retained,
            #       so the past block number is acquired.
            block = await web3.eth.get_block(
                max(
                    (await web3.eth.block_number)
                    - config.BLOCK_SYNC_STATUS_CALC_PERIOD,
                    0,
                )
            )
        except Web3WrapperException:
            await self.__web3_errors(db_session=db_session, endpoint_uri=endpoint_uri)
            LOG.error(f"Node connection failed: {endpoint_uri}")
            block = {"timestamp": time.time(), "number": 0}

        data = {"time": block["timestamp"], "block_number": block["number"]}
        history = RingBuffer(config.BLOCK_SYNC_STATUS_CALC_PERIOD, data)
        self.node_info[endpoint_uri]["history"] = history

    async def __process(self, db_session: AsyncSession, endpoint_uri: str):
        is_synced = True
        errors = []
        priority = self.node_info[endpoint_uri]["priority"]
        web3 = self.node_info[endpoint_uri]["web3"]
        history = self.node_info[endpoint_uri]["history"]

        # Check sync to other node
        syncing = await web3.eth.syncing
        if syncing:
            remaining_blocks = syncing["highestBlock"] - syncing["currentBlock"]
            if remaining_blocks > config.BLOCK_SYNC_REMAINING_THRESHOLD:
                is_synced = False
                errors.append(
                    f"highestBlock={syncing['highestBlock']}, currentBlock={syncing['currentBlock']}"
                )

        # Check increased block number
        data = {"time": time.time(), "block_number": await web3.eth.block_number}
        old_data = history.peek_oldest()
        elapsed_time = data["time"] - old_data["time"]
        generated_block_count = data["block_number"] - old_data["block_number"]
        generated_block_count_threshold = (elapsed_time * EXPECTED_BLOCKS_PER_SEC) * (
            config.BLOCK_GENERATION_SPEED_THRESHOLD / 100
        )  # count of block generation theoretical value
        if generated_block_count < generated_block_count_threshold:
            is_synced = False
            errors.append(f"{generated_block_count} blocks in {int(elapsed_time)} sec")
        history.append(data)

        # Update database
        _node = (
            await db_session.scalars(
                select(Node).where(Node.endpoint_uri == endpoint_uri).limit(1)
            )
        ).first()
        status_changed = (
            False if _node is not None and _node.is_synced == is_synced else True
        )
        await self.__sink_on_node(
            db_session=db_session,
            endpoint_uri=endpoint_uri,
            priority=priority,
            is_synced=is_synced,
        )

        # Output logs
        if status_changed:
            if is_synced:
                LOG.info(f"{endpoint_uri} Block synchronization is working")
            else:
                LOG.error(f"{endpoint_uri} Block synchronization is down: %s", errors)
        else:
            if not is_synced:
                # If the same previous processing status, log output with WARING level.
                LOG.notice(f"{endpoint_uri} Block synchronization is down: %s", errors)

    async def __web3_errors(self, db_session: AsyncSession, endpoint_uri: str):
        try:
            priority = self.node_info[endpoint_uri]["priority"]
            await self.__sink_on_node(
                db_session=db_session,
                endpoint_uri=endpoint_uri,
                priority=priority,
                is_synced=False,
            )
        except Exception as ex:
            # Unexpected errors(DB error, etc)
            LOG.exception(ex)

    @staticmethod
    async def __delete_old_node(
        db_session: AsyncSession, valid_endpoint_uri_list: list[str]
    ):
        await db_session.execute(
            delete(Node).where(Node.endpoint_uri.not_in(valid_endpoint_uri_list))
        )

    @staticmethod
    async def __sink_on_node(
        db_session: AsyncSession, endpoint_uri: str, priority: int, is_synced: bool
    ):
        _node = (
            await db_session.scalars(
                select(Node).where(Node.endpoint_uri == endpoint_uri).limit(1)
            )
        ).first()
        if _node is not None:
            _node.is_synced = is_synced
            await db_session.merge(_node)
        else:
            _node = Node()
            _node.endpoint_uri = endpoint_uri
            _node.priority = priority
            _node.is_synced = is_synced
            db_session.add(_node)


async def main():
    LOG.info("Service started successfully")
    processor = Processor()
    await processor.initial_setup()
    while True:
        start_time = time.time()

        try:
            await processor.process()
            LOG.debug("Processed")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:  # Unexpected errors
            LOG.exception(ex)

        elapsed_time = time.time() - start_time
        await asyncio.sleep(
            max(config.BLOCK_SYNC_STATUS_SLEEP_INTERVAL - elapsed_time, 0)
        )
        free_malloc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
