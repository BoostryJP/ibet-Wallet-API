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
import os
import sys
import time
from typing import Any, Callable

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session
)
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.types import (
    RPCEndpoint,
    RPCResponse
)

path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(path)

from app import config
from app.model.db import Node
import log

LOG = log.get_logger(process_name="PROCESSOR-BLOCK_SYNC_STATUS")

engine = create_engine(config.DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)


class Web3WrapperException(Exception):
    pass


def web3_exception_handler_middleware(
        make_request: Callable[[RPCEndpoint, Any], Any], w3: "Web3"
) -> Callable[[RPCEndpoint, Any], RPCResponse]:
    METHODS = [
        "eth_blockNumber",
        "eth_getBlockByNumber",
        "eth_syncing",
    ]

    def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
        if method in METHODS:
            try:
                return make_request(method, params)
            except Exception as ex:
                # Throw Web3WrapperException if an error occurred in Web3(connection error, timeout, etc),
                # Web3WrapperException is handled in this module.
                raise Web3WrapperException(ex)
        else:
            return make_request(method, params)

    return middleware


# Average block generation interval
EXPECTED_BLOCKS_PER_SEC = 1


class Sinks:
    def __init__(self):
        self.sinks = []

    def register(self, sink):
        self.sinks.append(sink)

    def on_node(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_node(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_node(self, endpoint_uri: str, priority: int, is_synced: bool):
        _node = self.db.query(Node).filter(Node.endpoint_uri == endpoint_uri).first()
        if _node is not None:
            _node.is_synced = is_synced
            self.db.merge(_node)
        else:
            _node = Node()
            _node.endpoint_uri = endpoint_uri
            _node.priority = priority
            _node.is_synced = is_synced
            self.db.add(_node)

    def flush(self):
        self.db.commit()


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
    def __init__(self, sink, db):
        self.sink = sink
        self.db = db
        self.node_info = {}

        self.__set_node_info(endpoint_uri=config.WEB3_HTTP_PROVIDER, priority=0)
        for endpoint_uri in config.WEB3_HTTP_PROVIDER_STANDBY:
            self.__set_node_info(endpoint_uri=endpoint_uri, priority=1)
        self.sink.flush()

    def process(self):
        for endpoint_uri in self.node_info.keys():
            try:
                self.__process(endpoint_uri=endpoint_uri)
            except Web3WrapperException:
                self.__web3_errors(endpoint_uri=endpoint_uri)
                LOG.error(f"Node connection failed: {endpoint_uri}")

    def __set_node_info(self, endpoint_uri: str, priority: int):
        self.node_info[endpoint_uri] = {
            "priority": priority
        }

        web3 = Web3(Web3.HTTPProvider(endpoint_uri))
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        web3.middleware_onion.add(web3_exception_handler_middleware)
        self.node_info[endpoint_uri]["web3"] = web3

        # Get block number
        try:
            # NOTE: Immediately after the processing, the monitoring data is not retained,
            #       so the past block number is acquired.
            block = web3.eth.get_block(max(web3.eth.blockNumber - config.BLOCK_SYNC_STATUS_CALC_PERIOD, 0))
        except Web3WrapperException:
            self.__web3_errors(endpoint_uri=endpoint_uri)
            LOG.error(f"Node connection failed: {endpoint_uri}")
            block = {
                "timestamp": time.time(),
                "number": 0
            }

        data = {
            "time": block["timestamp"],
            "block_number": block["number"]
        }
        history = RingBuffer(config.BLOCK_SYNC_STATUS_CALC_PERIOD, data)
        self.node_info[endpoint_uri]["history"] = history

    def __process(self, endpoint_uri: str):
        is_synced = True
        errors = []
        priority = self.node_info[endpoint_uri]["priority"]
        web3 = self.node_info[endpoint_uri]["web3"]
        history = self.node_info[endpoint_uri]["history"]

        # Check sync to other node
        syncing = web3.eth.syncing
        if syncing:
            remaining_blocks = syncing["highestBlock"] - syncing["currentBlock"]
            if remaining_blocks > config.BLOCK_SYNC_REMAINING_THRESHOLD:
                is_synced = False
                errors.append(f"highestBlock={syncing['highestBlock']}, currentBlock={syncing['currentBlock']}")

        # Check increased block number
        data = {
            "time": time.time(),
            "block_number": web3.eth.blockNumber
        }
        old_data = history.peek_oldest()
        elapsed_time = data["time"] - old_data["time"]
        generated_block_count = data["block_number"] - old_data["block_number"]
        generated_block_count_threshold = \
            (elapsed_time / EXPECTED_BLOCKS_PER_SEC) * \
            (config.BLOCK_GENERATION_SPEED_THRESHOLD / 100)  # count of block generation theoretical value
        if generated_block_count < generated_block_count_threshold:
            is_synced = False
            errors.append(f"{generated_block_count} blocks in {int(elapsed_time)} sec")
        history.append(data)

        # Update database
        _node = self.db.query(Node).filter(Node.endpoint_uri == endpoint_uri).first()
        status_changed = False if _node is not None and _node.is_synced == is_synced else True
        self.sink.on_node(endpoint_uri=endpoint_uri, priority=priority, is_synced=is_synced)

        # Output logs
        if status_changed:
            if is_synced:
                LOG.info(f"{endpoint_uri} Block synchronization is working")
            else:
                LOG.error(f"{endpoint_uri} Block synchronization is down: %s", errors)
        else:
            if not is_synced:
                # If the same previous processing status, log output with WARING level.
                LOG.warning(f"{endpoint_uri} Block synchronization is down: %s", errors)

        self.sink.flush()

    def __web3_errors(self, endpoint_uri: str):
        try:
            priority = self.node_info[endpoint_uri]["priority"]
            self.sink.on_node(endpoint_uri=endpoint_uri, priority=priority, is_synced=False)
            self.sink.flush()
        except Exception as ex:
            # Unexpected errors(DB error, etc)
            LOG.exception(ex)


_sink = Sinks()
_sink.register(DBSink(db_session))
processor = Processor(sink=_sink, db=db_session)


def main():
    LOG.info("Service started successfully")

    while True:
        start_time = time.time()

        try:
            processor.process()
            LOG.debug("Processed")
        except Exception as ex:
            # Unexpected errors(DB error, etc)
            LOG.exception(ex)

        elapsed_time = time.time() - start_time
        time.sleep(max(config.BLOCK_SYNC_STATUS_SLEEP_INTERVAL - elapsed_time, 0))


if __name__ == "__main__":
    main()