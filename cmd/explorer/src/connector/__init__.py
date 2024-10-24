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

from typing import Any

from aiohttp import ClientSession
from cache import AsyncTTL

from app.model.schema import (
    BlockDataDetail,
    BlockDataListResponse,
    GetBlockSyncStatusResponse,
    ListBlockDataQuery,
    ListTxDataQuery,
    TxDataDetail,
    TxDataListResponse,
)


class ApiNotEnabledException(Exception):
    pass


async def health_check(url: str, session: ClientSession) -> None:
    async with session.get(url=f"{url}/") as resp:
        await resp.json()


@AsyncTTL(time_to_live=10, skip_args=1)
async def get_node_info(session: ClientSession, url: str) -> GetBlockSyncStatusResponse:
    async with session.get(url=f"{url}/NodeInfo/BlockSyncStatus") as resp:
        data = await resp.json()
        return GetBlockSyncStatusResponse.model_validate(data.get("data"))


def dict_factory(x: list[tuple[str, Any]]):
    return {k: v for (k, v) in x if v is not None}


@AsyncTTL(time_to_live=3600, skip_args=1)
async def list_block_data(
    session: ClientSession, url: str, query: ListBlockDataQuery
) -> BlockDataListResponse:
    async with session.get(
        url=f"{url}/NodeInfo/BlockData", params=query.model_dump_json()
    ) as resp:
        data = await resp.json()
        if resp.status == 404:
            raise ApiNotEnabledException(data)
        return BlockDataListResponse.model_validate(data.get("data"))


@AsyncTTL(time_to_live=3600, skip_args=1)
async def get_block_data(
    session: ClientSession, url: str, block_number: int
) -> BlockDataDetail:
    async with session.get(url=f"{url}/NodeInfo/BlockData/{block_number}") as resp:
        data = await resp.json()
        return BlockDataDetail.model_validate(data.get("data"))


@AsyncTTL(time_to_live=3600, skip_args=1)
async def list_tx_data(
    session: ClientSession, url: str, query: ListTxDataQuery
) -> TxDataListResponse:
    async with session.get(
        url=f"{url}/NodeInfo/TxData", params=query.model_dump_json()
    ) as resp:
        data = await resp.json()
        return TxDataListResponse.model_validate(data.get("data"))


@AsyncTTL(time_to_live=3600, skip_args=1)
async def get_tx_data(session: ClientSession, url: str, tx_hash: str) -> TxDataDetail:
    async with session.get(url=f"{url}/NodeInfo/TxData/{tx_hash}") as resp:
        data = await resp.json()
        return TxDataDetail.model_validate(data.get("data"))
