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
from collections.abc import Sequence
from typing import cast

from eth_utils.address import to_checksum_address
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.types import BlockData, TxData

from app.config import WEB3_CHAINID
from app.database import BatchAsyncSessionLocal
from app.errors import ServiceUnavailable
from app.model.db import IDXBlockData, IDXBlockDataBlockNumber, IDXTxData
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import free_malloc, log

process_name = "INDEXER-BLOCK_TX_DATA"
LOG = log.get_logger(process_name=process_name)

async_web3 = AsyncWeb3Wrapper()


class Processor:
    """Processor for indexing Block and Transaction data"""

    @staticmethod
    def __get_db_session():
        return BatchAsyncSessionLocal()

    async def process(self):
        local_session = self.__get_db_session()
        try:
            latest_block = int(await async_web3.eth.block_number)
            from_block = (await self.__get_indexed_block_number(local_session)) + 1

            if from_block > latest_block:
                LOG.info("Skip process: from_block > latest_block")
                return

            LOG.info("Syncing from={}, to={}".format(from_block, latest_block))
            for block_number in range(from_block, latest_block + 1):
                block_data: BlockData = await async_web3.eth.get_block(
                    block_number, full_transactions=True
                )
                assert "number" in block_data
                assert "parentHash" in block_data
                assert "timestamp" in block_data
                assert "hash" in block_data

                # Synchronize block data
                block_model = IDXBlockData()
                block_model.number = block_data["number"]
                block_model.parent_hash = block_data["parentHash"].to_0x_hex()
                block_model.sha3_uncles = (
                    block_data["sha3Uncles"].to_0x_hex()
                    if "sha3Uncles" in block_data
                    else None
                )
                block_model.miner = block_data.get("miner")
                block_model.state_root = (
                    block_data["stateRoot"].to_0x_hex()
                    if "stateRoot" in block_data
                    else None
                )
                block_model.transactions_root = (
                    block_data["transactionsRoot"].to_0x_hex()
                    if "transactionsRoot" in block_data
                    else None
                )
                block_model.receipts_root = (
                    block_data["receiptsRoot"].to_0x_hex()
                    if "receiptsRoot" in block_data
                    else None
                )
                block_model.logs_bloom = (
                    block_data["logsBloom"].to_0x_hex()
                    if "logsBloom" in block_data
                    else None
                )
                block_model.difficulty = block_data.get("difficulty")
                block_model.gas_limit = block_data.get("gasLimit")
                block_model.gas_used = block_data.get("gasUsed")
                block_model.timestamp = block_data["timestamp"]
                block_model.proof_of_authority_data = (
                    block_data["proofOfAuthorityData"].to_0x_hex()
                    if "proofOfAuthorityData" in block_data
                    else None
                )
                block_model.mix_hash = (
                    block_data["mixHash"].to_0x_hex()
                    if "mixHash" in block_data
                    else None
                )
                block_model.nonce = (
                    block_data["nonce"].to_0x_hex() if "nonce" in block_data else None
                )
                block_model.hash = block_data["hash"].to_0x_hex()
                block_model.size = block_data.get("size")

                transactions = cast(
                    Sequence[TxData], block_data.get("transactions", [])
                )
                transaction_hash_list: list[str] = []

                for transaction in transactions:
                    assert "hash" in transaction
                    # Synchronize tx data
                    tx_model = IDXTxData()
                    tx_model.hash = transaction["hash"].to_0x_hex()
                    tx_model.block_hash = (
                        transaction["blockHash"].to_0x_hex()
                        if "blockHash" in transaction
                        else None
                    )
                    tx_model.block_number = transaction.get("blockNumber")
                    tx_model.transaction_index = transaction.get("transactionIndex")
                    tx_model.from_address = (
                        to_checksum_address(transaction["from"])
                        if "from" in transaction
                        else None
                    )
                    tx_model.to_address = (
                        to_checksum_address(transaction["to"])
                        if "to" in transaction and transaction["to"] is not None  # type: ignore to_address can be None
                        else None
                    )
                    tx_model.input = (
                        transaction["input"].to_0x_hex()
                        if "input" in transaction
                        else None
                    )
                    tx_model.gas = transaction.get("gas")
                    tx_model.gas_price = transaction.get("gasPrice")
                    tx_model.value = transaction.get("value")
                    tx_model.nonce = transaction.get("nonce")
                    local_session.add(tx_model)

                    transaction_hash_list.append(transaction["hash"].to_0x_hex())

                block_model.transactions = transaction_hash_list
                local_session.add(block_model)

                await self.__set_indexed_block_number(local_session, block_number)

                await local_session.commit()
        except Exception:
            await local_session.rollback()
            raise
        finally:
            await local_session.close()
        LOG.info("Sync job has been completed")

    @staticmethod
    async def __get_indexed_block_number(db_session: AsyncSession) -> int:
        indexed_block_number = (
            await db_session.scalars(
                select(IDXBlockDataBlockNumber)
                .where(IDXBlockDataBlockNumber.chain_id == WEB3_CHAINID)
                .limit(1)
            )
        ).first()
        if indexed_block_number is None:
            return -1
        else:
            assert indexed_block_number.latest_block_number is not None
            return indexed_block_number.latest_block_number

    @staticmethod
    async def __set_indexed_block_number(db_session: AsyncSession, block_number: int):
        indexed_block_number = IDXBlockDataBlockNumber()
        indexed_block_number.chain_id = WEB3_CHAINID
        indexed_block_number.latest_block_number = block_number
        await db_session.merge(indexed_block_number)


async def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            await processor.process()
        except ServiceUnavailable:
            LOG.notice("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An exception occurred during event synchronization")

        await asyncio.sleep(5)
        free_malloc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
