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

from typing import cast

import pytest
from aiohttp import ClientError
from eth_typing import URI
from requests.exceptions import ConnectionError
from web3 import AsyncHTTPProvider, HTTPProvider
from web3.types import RPCEndpoint, RPCResponse

from app.utils import web3_utils


# Verify that the FailOverHTTPProvider reuses the cached endpoint URI for multiple requests
# when in fail-over mode and the cache is valid.
def test_failover_http_provider_reuses_cached_endpoint(
    monkeypatch: pytest.MonkeyPatch,
):
    provider = web3_utils.FailOverHTTPProvider("http://127.0.0.1:8545")
    monkeypatch.setattr(web3_utils.FailOverHTTPProvider, "fail_over_mode", True)
    monkeypatch.setattr(provider, "_get_cache_ttl", lambda: 60.0)

    resolve_calls: list[URI] = []

    def fake_resolve() -> URI:
        endpoint = URI("http://cached-node")
        resolve_calls.append(endpoint)
        provider._set_cached_endpoint_uri(endpoint)  # type: ignore[attr-defined]
        return endpoint

    def fake_make_request(
        self: HTTPProvider, method: RPCEndpoint, params: object
    ) -> RPCResponse:
        return {"result": cast(str, provider.endpoint_uri)}

    monkeypatch.setattr(provider, "_resolve_endpoint_uri", fake_resolve)
    monkeypatch.setattr(HTTPProvider, "make_request", fake_make_request)

    first = provider.make_request(RPCEndpoint("eth_chainId"), [])
    second = provider.make_request(RPCEndpoint("eth_chainId"), [])

    assert first == {"result": "http://cached-node"}
    assert second == {"result": "http://cached-node"}
    assert len(resolve_calls) == 1


# Verify that if the cached endpoint fails,
# the FailOverHTTPProvider will attempt to resolve a new endpoint and update the cache accordingly.
def test_failover_http_provider_invalidates_cache_on_request_error(
    monkeypatch: pytest.MonkeyPatch,
):
    provider = web3_utils.FailOverHTTPProvider("http://127.0.0.1:8545")
    monkeypatch.setattr(web3_utils.FailOverHTTPProvider, "fail_over_mode", True)
    monkeypatch.setattr(provider, "_get_cache_ttl", lambda: 60.0)
    provider._set_cached_endpoint_uri(URI("http://stale-node"))  # type: ignore[attr-defined]

    resolve_calls: list[URI] = []
    call_count = 0

    def fake_resolve() -> URI:
        endpoint = URI("http://fresh-node")
        resolve_calls.append(endpoint)
        provider._set_cached_endpoint_uri(endpoint)  # type: ignore[attr-defined]
        return endpoint

    def fake_make_request(
        self: HTTPProvider, method: RPCEndpoint, params: object
    ) -> RPCResponse:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("connection failed")
        return {"result": cast(str, provider.endpoint_uri)}

    monkeypatch.setattr(provider, "_resolve_endpoint_uri", fake_resolve)
    monkeypatch.setattr(HTTPProvider, "make_request", fake_make_request)

    result = provider.make_request(RPCEndpoint("eth_chainId"), [])

    assert result == {"result": "http://fresh-node"}
    assert len(resolve_calls) == 1


# Verify that the AsyncFailOverHTTPProvider reuses the cached endpoint URI for multiple requests
# when in fail-over mode and the cache is valid.
@pytest.mark.asyncio
async def test_async_failover_http_provider_reuses_cached_endpoint(
    monkeypatch: pytest.MonkeyPatch,
):
    provider = web3_utils.AsyncFailOverHTTPProvider("http://127.0.0.1:8545")
    monkeypatch.setattr(web3_utils.AsyncFailOverHTTPProvider, "fail_over_mode", True)
    monkeypatch.setattr(provider, "_get_cache_ttl", lambda: 60.0)

    resolve_calls: list[URI] = []

    async def fake_resolve() -> URI:
        endpoint = URI("http://cached-node")
        resolve_calls.append(endpoint)
        await provider._set_cached_endpoint_uri(endpoint)  # type: ignore[attr-defined]
        return endpoint

    async def fake_make_request(
        self: AsyncHTTPProvider, method: RPCEndpoint, params: object
    ) -> RPCResponse:
        return {"result": cast(str, provider.endpoint_uri)}

    monkeypatch.setattr(provider, "_resolve_endpoint_uri", fake_resolve)
    monkeypatch.setattr(AsyncHTTPProvider, "make_request", fake_make_request)

    first = await provider.make_request(RPCEndpoint("eth_chainId"), [])
    second = await provider.make_request(RPCEndpoint("eth_chainId"), [])

    assert first == {"result": "http://cached-node"}
    assert second == {"result": "http://cached-node"}
    assert len(resolve_calls) == 1


# Verify that if the cached endpoint fails,
# the AsyncFailOverHTTPProvider will attempt to resolve a new endpoint and update the cache accordingly.
@pytest.mark.asyncio
async def test_async_failover_http_provider_invalidates_cache_on_request_error(
    monkeypatch: pytest.MonkeyPatch,
):
    provider = web3_utils.AsyncFailOverHTTPProvider("http://127.0.0.1:8545")
    monkeypatch.setattr(web3_utils.AsyncFailOverHTTPProvider, "fail_over_mode", True)
    monkeypatch.setattr(provider, "_get_cache_ttl", lambda: 60.0)
    await provider._set_cached_endpoint_uri(URI("http://stale-node"))  # type: ignore[attr-defined]

    resolve_calls: list[URI] = []
    call_count = 0

    async def fake_resolve() -> URI:
        endpoint = URI("http://fresh-node")
        resolve_calls.append(endpoint)
        await provider._set_cached_endpoint_uri(endpoint)  # type: ignore[attr-defined]
        return endpoint

    async def fake_make_request(
        self: AsyncHTTPProvider, method: RPCEndpoint, params: object
    ) -> RPCResponse:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ClientError("connection failed")
        return {"result": cast(str, provider.endpoint_uri)}

    monkeypatch.setattr(provider, "_resolve_endpoint_uri", fake_resolve)
    monkeypatch.setattr(AsyncHTTPProvider, "make_request", fake_make_request)

    result = await provider.make_request(RPCEndpoint("eth_chainId"), [])

    assert result == {"result": "http://fresh-node"}
    assert len(resolve_calls) == 1
