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
import threading
import time
from dataclasses import dataclass
from json.decoder import JSONDecodeError
from typing import Any, cast
from weakref import WeakKeyDictionary

from aiohttp import ClientError, ClientTimeout
from eth_typing import URI
from requests.exceptions import ConnectionError, HTTPError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from web3 import AsyncHTTPProvider, AsyncWeb3, HTTPProvider, Web3
from web3.eth import AsyncEth
from web3.geth import AsyncGeth
from web3.middleware import ExtraDataToPOAMiddleware
from web3.net import AsyncNet
from web3.types import RPCEndpoint, RPCResponse

from app import config, log
from app.database import async_engine, engine
from app.errors import ServiceUnavailable
from app.model.db import Node

LOG = log.get_logger()

thread_local = threading.local()

# Hashable timeout key for AsyncWeb3/provider caches.
AsyncWeb3TimeoutKey = tuple[Any, Any, Any, Any]

# Cache bucket for one scope, keyed by timeout.
AsyncWeb3CacheMap = dict[AsyncWeb3TimeoutKey, AsyncWeb3[Any]]


@dataclass
class ResolvedEndpointCache:
    endpoint_uri: URI
    expires_at: float


class Web3Wrapper:
    DEFAULT_TIMEOUT = 5

    def __init__(self, request_timeout: int = DEFAULT_TIMEOUT):
        if not config.UNIT_TEST_MODE:
            FailOverHTTPProvider.set_fail_over_mode(True)
        self.request_timeout = request_timeout

    @property
    def eth(self):
        web3 = self._get_web3(self.request_timeout)
        return web3.eth

    @property
    def geth(self):
        web3 = self._get_web3(self.request_timeout)
        return web3.geth

    @property
    def net(self):
        web3 = self._get_web3(self.request_timeout)
        return web3.net

    @staticmethod
    def _get_web3(request_timeout: int) -> Web3:
        # Get web3 for each thread because make to FailOverHTTPProvider thread-safe
        try:
            web3 = thread_local.web3
        except AttributeError:
            web3 = Web3(
                FailOverHTTPProvider(request_kwargs={"timeout": request_timeout})
            )
            web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            thread_local.web3 = web3

        return web3


class AsyncWeb3Wrapper:
    DEFAULT_TIMEOUT = 5

    def __init__(self, request_timeout: int | ClientTimeout = DEFAULT_TIMEOUT):
        if not config.UNIT_TEST_MODE:
            AsyncFailOverHTTPProvider.set_fail_over_mode(True)
        self.request_timeout = request_timeout

    @property
    def eth(self) -> AsyncEth:
        web3 = self.get_web3()
        return web3.eth

    @property
    def geth(self) -> AsyncGeth:
        web3 = self.get_web3()
        return web3.geth

    @property
    def net(self) -> AsyncNet:
        web3 = self.get_web3()
        return web3.net

    def get_web3(self) -> AsyncWeb3[Any]:
        return self._get_web3(self.request_timeout)

    @staticmethod
    def _normalize_async_timeout(
        request_timeout: int | ClientTimeout,
    ) -> ClientTimeout:
        """Normalize timeout to ClientTimeout."""
        if isinstance(request_timeout, ClientTimeout):
            return request_timeout
        return ClientTimeout(total=request_timeout)

    @classmethod
    def _get_web3(cls, request_timeout: int | ClientTimeout) -> AsyncWeb3[Any]:
        """Get AsyncWeb3 instance with fail-over support and timeout handling."""
        # Normalize plain integers before constructing the provider.
        timeout = cls._normalize_async_timeout(request_timeout)

        # Cache entries are separated by effective timeout settings.
        timeout_key: AsyncWeb3TimeoutKey = (
            timeout.total,
            timeout.connect,
            timeout.sock_connect,
            timeout.sock_read,
        )

        # Running loop for the current thread, if any.
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        # Without a running loop, fall back to a thread-local cache.
        if loop is None:
            try:
                # Reuse an AsyncWeb3 created earlier on this thread.
                async_web3_map = cast(
                    AsyncWeb3CacheMap,
                    thread_local.async_web3_without_loop,
                )
            except AttributeError:
                # Lazily initialize the fallback cache.
                async_web3_map: AsyncWeb3CacheMap = {}
                thread_local.async_web3_without_loop = async_web3_map

            async_web3 = async_web3_map.get(timeout_key)
            if async_web3 is None:
                # Create one provider per thread/timeout pair.
                async_web3 = cls._create_web3(timeout)
                async_web3_map[timeout_key] = async_web3
            return async_web3

        # With a running loop, scope AsyncWeb3 instances to that loop.
        try:
            async_web3_by_loop = cast(
                WeakKeyDictionary[asyncio.AbstractEventLoop, AsyncWeb3CacheMap],
                thread_local.async_web3_by_loop,
            )
        except AttributeError:
            # Weak keys let loop entries vanish when the loop is gone.
            async_web3_by_loop: WeakKeyDictionary[
                asyncio.AbstractEventLoop, AsyncWeb3CacheMap
            ] = WeakKeyDictionary()
            thread_local.async_web3_by_loop = async_web3_by_loop

        # Each loop keeps its own timeout-keyed sub-cache.
        loop_web3_map = async_web3_by_loop.setdefault(loop, cast(AsyncWeb3CacheMap, {}))
        async_web3 = loop_web3_map.get(timeout_key)
        if async_web3 is None:
            # Build and remember an AsyncWeb3 for this loop/timeout pair.
            async_web3 = cls._create_web3(timeout)
            loop_web3_map[timeout_key] = async_web3
        return async_web3

    @staticmethod
    def _create_web3(timeout: ClientTimeout) -> AsyncWeb3[Any]:
        async_web3 = AsyncWeb3(
            AsyncFailOverHTTPProvider(request_kwargs={"timeout": timeout})
        )
        async_web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        return async_web3


class FailOverHTTPProvider(HTTPProvider):
    fail_over_mode = False  # If False, use only the default(primary) provider

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.endpoint_uri: URI | None = None
        self._resolved_endpoint_cache: ResolvedEndpointCache | None = None
        self._resolved_endpoint_lock = threading.Lock()

    @staticmethod
    def _get_cache_ttl() -> float:
        return max(float(config.WEB3_REQUEST_WAIT_TIME), 1.0)

    def _get_cached_endpoint_uri(self) -> URI | None:
        with self._resolved_endpoint_lock:
            cache = self._resolved_endpoint_cache
            if cache is None:
                return None
            if cache.expires_at <= time.monotonic():
                self._resolved_endpoint_cache = None
                return None
            return cache.endpoint_uri

    def _set_cached_endpoint_uri(self, endpoint_uri: URI) -> None:
        with self._resolved_endpoint_lock:
            self._resolved_endpoint_cache = ResolvedEndpointCache(
                endpoint_uri=endpoint_uri,
                expires_at=time.monotonic() + self._get_cache_ttl(),
            )

    def _clear_cached_endpoint_uri(self) -> None:
        with self._resolved_endpoint_lock:
            self._resolved_endpoint_cache = None

    def _resolve_endpoint_uri(self) -> URI | None:
        db_session = Session(autocommit=False, autoflush=True, bind=engine)
        try:
            if db_session.scalars(select(Node).limit(1)).first() is None:
                endpoint_uri = URI(config.WEB3_HTTP_PROVIDER)
                self._set_cached_endpoint_uri(endpoint_uri)
                return endpoint_uri

            _node = db_session.scalars(
                select(Node)
                .where(Node.is_synced == True)
                .order_by(Node.priority)
                .order_by(Node.id)
                .limit(1)
            ).first()
            if _node is None:
                return None
            assert _node.endpoint_uri is not None
            endpoint_uri = URI(_node.endpoint_uri)
            self._set_cached_endpoint_uri(endpoint_uri)
            return endpoint_uri
        finally:
            db_session.close()

    def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        if FailOverHTTPProvider.fail_over_mode is True:
            cached_endpoint_uri = self._get_cached_endpoint_uri()
            if cached_endpoint_uri is not None:
                self.endpoint_uri = cached_endpoint_uri
                try:
                    return super().make_request(method, params)
                except ConnectionError, JSONDecodeError, HTTPError:
                    self._clear_cached_endpoint_uri()
                    LOG.notice(
                        f"Retry web3 request due to connection fail: method={method}, params={params}"
                    )

            counter = 0
            while counter <= config.WEB3_REQUEST_RETRY_COUNT:
                endpoint_uri = self._resolve_endpoint_uri()
                if endpoint_uri is None:
                    counter += 1
                    if counter <= config.WEB3_REQUEST_RETRY_COUNT:
                        time.sleep(config.WEB3_REQUEST_WAIT_TIME)
                        continue
                    raise ServiceUnavailable("Block synchronization is down")

                self.endpoint_uri = endpoint_uri
                try:
                    return super().make_request(method, params)
                except ConnectionError, JSONDecodeError, HTTPError:
                    # NOTE:
                    #  JSONDecodeError will be raised if a request is sent
                    #  while Quorum is terminating.
                    self._clear_cached_endpoint_uri()
                    LOG.notice(
                        f"Retry web3 request due to connection fail: method={method}, params={params}"
                    )
                    counter += 1
                    if counter <= config.WEB3_REQUEST_RETRY_COUNT:
                        time.sleep(config.WEB3_REQUEST_WAIT_TIME)
                        continue
            raise ServiceUnavailable("Block synchronization is down")

        self.endpoint_uri = URI(config.WEB3_HTTP_PROVIDER)
        return super().make_request(method, params)

    @staticmethod
    def set_fail_over_mode(use_fail_over: bool):
        FailOverHTTPProvider.fail_over_mode = use_fail_over


class AsyncFailOverHTTPProvider(AsyncHTTPProvider):
    fail_over_mode = False  # If False, use only the default(primary) provider

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.endpoint_uri: URI | None = None
        self._resolved_endpoint_cache: ResolvedEndpointCache | None = None
        self._resolved_endpoint_lock = asyncio.Lock()

    @staticmethod
    def _get_cache_ttl() -> float:
        return max(float(config.WEB3_REQUEST_WAIT_TIME), 1.0)

    async def _get_cached_endpoint_uri(self) -> URI | None:
        async with self._resolved_endpoint_lock:
            cache = self._resolved_endpoint_cache
            if cache is None:
                return None
            if cache.expires_at <= time.monotonic():
                self._resolved_endpoint_cache = None
                return None
            return cache.endpoint_uri

    async def _set_cached_endpoint_uri(self, endpoint_uri: URI) -> None:
        async with self._resolved_endpoint_lock:
            self._resolved_endpoint_cache = ResolvedEndpointCache(
                endpoint_uri=endpoint_uri,
                expires_at=time.monotonic() + self._get_cache_ttl(),
            )

    async def _clear_cached_endpoint_uri(self) -> None:
        async with self._resolved_endpoint_lock:
            self._resolved_endpoint_cache = None

    async def _resolve_endpoint_uri(self) -> URI | None:
        db_session = AsyncSession(autocommit=False, autoflush=True, bind=async_engine)
        try:
            if (await db_session.scalars(select(Node).limit(1))).first() is None:
                endpoint_uri = URI(config.WEB3_HTTP_PROVIDER)
                await self._set_cached_endpoint_uri(endpoint_uri)
                return endpoint_uri

            _node = (
                await db_session.scalars(
                    select(Node)
                    .where(Node.is_synced == True)
                    .order_by(Node.priority)
                    .order_by(Node.id)
                    .limit(1)
                )
            ).first()
            if _node is None:
                return None
            assert _node.endpoint_uri is not None
            endpoint_uri = URI(_node.endpoint_uri)
            await self._set_cached_endpoint_uri(endpoint_uri)
            return endpoint_uri
        finally:
            await db_session.close()

    async def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        if AsyncFailOverHTTPProvider.fail_over_mode is True:
            cached_endpoint_uri = await self._get_cached_endpoint_uri()
            if cached_endpoint_uri is not None:
                self.endpoint_uri = cached_endpoint_uri
                try:
                    return await super().make_request(method, params)
                except ClientError, JSONDecodeError:
                    await self._clear_cached_endpoint_uri()
                    LOG.notice(
                        f"Retry web3 request due to connection fail: method={method}, params={params}"
                    )

            counter = 0
            while counter <= config.WEB3_REQUEST_RETRY_COUNT:
                endpoint_uri = await self._resolve_endpoint_uri()
                if endpoint_uri is None:
                    counter += 1
                    if counter <= config.WEB3_REQUEST_RETRY_COUNT:
                        await asyncio.sleep(config.WEB3_REQUEST_WAIT_TIME)
                        continue
                    raise ServiceUnavailable("Block synchronization is down")

                self.endpoint_uri = endpoint_uri
                try:
                    return await super().make_request(method, params)
                except ClientError, JSONDecodeError:
                    # NOTE:
                    #  JSONDecodeError will be raised if a request is sent
                    #  while Quorum is terminating.
                    await self._clear_cached_endpoint_uri()
                    LOG.notice(
                        f"Retry web3 request due to connection fail: method={method}, params={params}"
                    )
                    counter += 1
                    if counter <= config.WEB3_REQUEST_RETRY_COUNT:
                        await asyncio.sleep(config.WEB3_REQUEST_WAIT_TIME)
                        continue
            raise ServiceUnavailable("Block synchronization is down")

        self.endpoint_uri = URI(config.WEB3_HTTP_PROVIDER)
        return await super().make_request(method, params)

    @staticmethod
    def set_fail_over_mode(use_fail_over: bool):
        AsyncFailOverHTTPProvider.fail_over_mode = use_fail_over
