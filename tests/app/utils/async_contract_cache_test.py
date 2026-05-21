import asyncio
from typing import Any, cast

import pytest
from aiohttp import ClientTimeout
from web3 import AsyncHTTPProvider, AsyncWeb3

from app.contracts import contract as contract_module
from app.utils.web3_utils import AsyncWeb3Wrapper


def test_async_web3_wrapper_normalizes_timeout_to_client_timeout():
    """
    Test that AsyncWeb3Wrapper normalizes timeout to ClientTimeout.
    """

    loop = asyncio.new_event_loop()
    wrapper = AsyncWeb3Wrapper(5)

    try:
        async_web3 = loop.run_until_complete(_get_web3(wrapper))
    finally:
        loop.close()

    timeout = cast(Any, async_web3.provider)._request_kwargs["timeout"]
    assert isinstance(timeout, ClientTimeout)
    assert timeout.total == 5


def test_async_web3_wrapper_scopes_web3_by_event_loop():
    """
    Test that AsyncWeb3Wrapper scopes AsyncWeb3 instances by event loop.
    """

    wrapper = AsyncWeb3Wrapper()
    loops: list[asyncio.AbstractEventLoop] = []

    def get_web3_for_new_loop() -> AsyncWeb3[AsyncHTTPProvider]:
        loop = asyncio.new_event_loop()
        loops.append(loop)
        return loop.run_until_complete(_get_web3(wrapper))

    async_web3_1 = get_web3_for_new_loop()
    async_web3_2 = get_web3_for_new_loop()

    try:
        assert async_web3_1 is not async_web3_2
    finally:
        for loop in loops:
            loop.close()


def test_async_contract_factory_cache_is_scoped_by_async_web3(
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Test that AsyncContract factory cache is scoped by AsyncWeb3 instance.
    """

    web3_1 = AsyncWeb3(AsyncHTTPProvider("http://127.0.0.1:8545"))
    web3_2 = AsyncWeb3(AsyncHTTPProvider("http://127.0.0.1:8545"))

    contract_module.AsyncContract.cache.clear()
    contract_module.AsyncContract.factory_map.clear()
    contract_module.AsyncContract.cache["TestContract"] = {"abi": []}

    monkeypatch.setattr(contract_module.async_web3, "get_web3", lambda: web3_1)
    contract_1 = contract_module.AsyncContract.get_contract(
        "TestContract", "0x0000000000000000000000000000000000000001"
    )

    monkeypatch.setattr(contract_module.async_web3, "get_web3", lambda: web3_2)
    contract_2 = contract_module.AsyncContract.get_contract(
        "TestContract", "0x0000000000000000000000000000000000000002"
    )

    try:
        assert cast(Any, contract_1).w3 is web3_1
        assert cast(Any, contract_2).w3 is web3_2
        assert len(contract_module.AsyncContract.factory_map) == 2
        assert len(contract_module.AsyncContract.factory_map[web3_1]) == 1
        assert len(contract_module.AsyncContract.factory_map[web3_2]) == 1
    finally:
        contract_module.AsyncContract.cache.clear()
        contract_module.AsyncContract.factory_map.clear()


async def _get_web3(wrapper: AsyncWeb3Wrapper) -> AsyncWeb3[AsyncHTTPProvider]:
    return wrapper.get_web3()
