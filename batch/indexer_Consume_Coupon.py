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
from datetime import datetime
from typing import Sequence
from zoneinfo import ZoneInfo

from eth_utils import to_checksum_address
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.exceptions import ABIEventFunctionNotFound

from app.config import TOKEN_LIST_CONTRACT_ADDRESS, TZ, ZERO_ADDRESS
from app.contracts import AsyncContract
from app.database import BatchAsyncSessionLocal
from app.errors import ServiceUnavailable
from app.model.db import IDXConsumeCoupon, Listing
from app.model.schema.base import TokenType
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import log

local_tz = ZoneInfo(TZ)

process_name = "INDEXER-CONSUME-COUPON"
LOG = log.get_logger(process_name=process_name)

async_web3 = AsyncWeb3Wrapper()


class Processor:
    """Processor for indexing coupon consumption events"""

    latest_block = 0

    def __init__(self):
        self.token_list = []

    @staticmethod
    def __get_db_session():
        return BatchAsyncSessionLocal()

    async def initial_sync(self):
        local_session = self.__get_db_session()
        latest_block_at_start = self.latest_block
        self.latest_block = await async_web3.eth.block_number
        try:
            await self.__get_token_list(local_session)

            # Synchronize 1,000,000 blocks each
            _to_block = 999999
            _from_block = 0
            if self.latest_block > 999999:
                while _to_block < self.latest_block:
                    await self.__sync_all(
                        db_session=local_session,
                        block_from=_from_block,
                        block_to=_to_block,
                    )
                    _to_block += 1000000
                    _from_block += 1000000
                await self.__sync_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=self.latest_block,
                )
            else:
                await self.__sync_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=self.latest_block,
                )
            await local_session.commit()
        except Exception as e:
            await local_session.rollback()
            self.latest_block = latest_block_at_start
            raise e
        finally:
            await local_session.close()
        LOG.info("Initial sync has been completed")

    async def sync_new_logs(self):
        local_session = self.__get_db_session()
        latest_block_at_start = self.latest_block
        try:
            await self.__get_token_list(local_session)

            blockTo = await async_web3.eth.block_number
            if blockTo == self.latest_block:
                return

            await self.__sync_all(
                db_session=local_session,
                block_from=self.latest_block + 1,
                block_to=blockTo,
            )
            self.latest_block = blockTo
            await local_session.commit()
        except Exception as e:
            await local_session.rollback()
            self.latest_block = latest_block_at_start
            raise e
        finally:
            await local_session.close()
        LOG.info("Sync job has been completed")

    async def __get_token_list(self, db_session: AsyncSession):
        self.token_list = []
        list_contract = AsyncContract.get_contract(
            contract_name="TokenList", address=TOKEN_LIST_CONTRACT_ADDRESS
        )
        listed_tokens: Sequence[Listing] = (
            await db_session.scalars(select(Listing))
        ).all()
        for listed_token in listed_tokens:
            token_info = await AsyncContract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(listed_token.token_address,),
                default_returns=(ZERO_ADDRESS, "", ZERO_ADDRESS),
            )
            if token_info[1] == TokenType.IbetCoupon:
                coupon_token_contract = AsyncContract.get_contract(
                    contract_name=TokenType.IbetCoupon,
                    address=listed_token.token_address,
                )
                self.token_list.append(coupon_token_contract)

    async def __sync_all(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        LOG.info("Syncing from={}, to={}".format(block_from, block_to))
        await self.__sync_consume(db_session, block_from, block_to)

    async def __sync_consume(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        for token in self.token_list:
            try:
                events = await token.events.Consume.get_logs(
                    fromBlock=block_from, toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                for event in events:
                    args = event["args"]
                    transaction_hash = event["transactionHash"].hex()
                    block_timestamp = datetime.utcfromtimestamp(
                        (await async_web3.eth.get_block(event["blockNumber"]))[
                            "timestamp"
                        ]
                    )
                    amount = args.get("value", 0)
                    consumer = args.get("consumer", ZERO_ADDRESS)
                    if amount > sys.maxsize:
                        pass
                    else:
                        if consumer != ZERO_ADDRESS:
                            await self.__sink_on_consume_coupon(
                                db_session=db_session,
                                transaction_hash=transaction_hash,
                                token_address=to_checksum_address(token.address),
                                account_address=consumer,
                                amount=amount,
                                block_timestamp=block_timestamp,
                            )
            except Exception as e:
                raise e

    @staticmethod
    async def __sink_on_consume_coupon(
        db_session: AsyncSession,
        transaction_hash: str,
        token_address: str,
        account_address: str,
        amount: int,
        block_timestamp: datetime,
    ):
        consume_coupon = (
            await db_session.scalars(
                select(IDXConsumeCoupon)
                .where(IDXConsumeCoupon.transaction_hash == transaction_hash)
                .where(IDXConsumeCoupon.token_address == token_address)
                .where(IDXConsumeCoupon.account_address == account_address)
                .limit(1)
            )
        ).first()
        if consume_coupon is None:
            LOG.debug(f"Consume: transaction_hash={transaction_hash}")
            consume_coupon = IDXConsumeCoupon()
            consume_coupon.transaction_hash = transaction_hash
            consume_coupon.token_address = token_address
            consume_coupon.account_address = account_address
            consume_coupon.amount = amount
            consume_coupon.block_timestamp = block_timestamp
            await db_session.merge(consume_coupon)


async def main():
    LOG.info("Service started successfully")
    processor = Processor()

    initial_synced_completed = False
    while not initial_synced_completed:
        try:
            await processor.initial_sync()
            initial_synced_completed = True
        except Exception:
            LOG.exception("Initial sync failed")

        await asyncio.sleep(10)

    while True:
        try:
            await processor.sync_new_logs()
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception("An exception occurred during event synchronization")

        await asyncio.sleep(10)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
