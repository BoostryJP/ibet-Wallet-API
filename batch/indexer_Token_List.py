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
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.exceptions import ABIEventFunctionNotFound

from app import config
from app.contracts import AsyncContract
from app.database import BatchAsyncSessionLocal
from app.errors import ServiceUnavailable
from app.model.db import IDXTokenListBlockNumber, IDXTokenListItem
from app.model.schema.base import TokenType
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import log

process_name = "INDEXER-TOKEN-LIST"
LOG = log.get_logger(process_name=process_name)

async_web3 = AsyncWeb3Wrapper()


class Processor:
    """Processor for indexing TokenList events"""

    def __init__(self):
        self.token_list_contract = AsyncContract.get_contract(
            contract_name="TokenList", address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )
        self.available_token_template_list = [
            TokenType.IbetStraightBond,
            TokenType.IbetShare,
            TokenType.IbetMembership,
            TokenType.IbetCoupon,
        ]

    @staticmethod
    def __get_db_session():
        return BatchAsyncSessionLocal()

    async def process(self):
        local_session = self.__get_db_session()
        try:
            latest_block = await async_web3.eth.block_number
            _from_block = (
                await self.__get_idx_token_list_block_number(
                    db_session=local_session,
                    contract_address=config.TOKEN_LIST_CONTRACT_ADDRESS,
                )
                + 1
            )
            _to_block = 999999 + _from_block
            if latest_block > _to_block:
                while _to_block < latest_block:
                    await self.__sync_all(
                        db_session=local_session,
                        block_from=_from_block,
                        block_to=_to_block,
                    )
                    _from_block += 1000000
                    _to_block += 1000000
                await self.__sync_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=latest_block,
                )
            else:
                if _from_block > latest_block:
                    return
                await self.__sync_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=latest_block,
                )
            await self.__set_idx_token_list_block_number(
                db_session=local_session,
                contract_address=config.TOKEN_LIST_CONTRACT_ADDRESS,
                block_number=latest_block,
            )
            await local_session.commit()
        except Exception:
            await local_session.rollback()
            raise
        finally:
            await local_session.close()
        LOG.info("Sync job has been completed")

    async def __sync_all(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        LOG.info("Syncing from={}, to={}".format(block_from, block_to))
        await self.__sync_register(db_session, block_from, block_to)

    async def __sync_register(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Sync Register Events

        :param db_session: ORM session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            events = await self.token_list_contract.events.Register.get_logs(
                fromBlock=block_from, toBlock=block_to
            )
        except ABIEventFunctionNotFound:
            events = []
        try:
            for _event in events:
                token_address = _event["args"].get("token_address")
                token_template = _event["args"].get("token_template")
                owner_address = _event["args"].get("owner_address")
                await self.__sink_on_token_info(
                    db_session=db_session,
                    token_address=token_address,
                    token_template=token_template,
                    owner_address=owner_address,
                )
        except Exception as e:
            raise e

    async def __sink_on_token_info(
        self,
        db_session: AsyncSession,
        token_address: str,
        token_template: str,
        owner_address: str,
    ):
        """Update Token Info item in DB

        :param db_session: ORM session
        :param token_address: token address
        :param token_template: token template
        :param owner_address: owner address
        :return: None
        """
        if token_template not in self.available_token_template_list:
            return
        idx_token_list: Optional[IDXTokenListItem] = (
            await db_session.scalars(
                select(IDXTokenListItem)
                .where(IDXTokenListItem.token_address == token_address)
                .limit(1)
            )
        ).first()
        if idx_token_list is not None:
            idx_token_list.token_template = token_template
            idx_token_list.owner_address = owner_address
            await db_session.merge(idx_token_list)
        else:
            idx_token_list = IDXTokenListItem()
            idx_token_list.token_address = token_address
            idx_token_list.token_template = token_template
            idx_token_list.owner_address = owner_address
            db_session.add(idx_token_list)

    @staticmethod
    async def __get_idx_token_list_block_number(
        db_session: AsyncSession, contract_address: str
    ):
        """Get token list index for Share"""
        _idx_token_list_block_number = (
            await db_session.scalars(
                select(IDXTokenListBlockNumber)
                .where(IDXTokenListBlockNumber.contract_address == contract_address)
                .limit(1)
            )
        ).first()
        if _idx_token_list_block_number is None:
            return -1
        else:
            return _idx_token_list_block_number.latest_block_number

    @staticmethod
    async def __set_idx_token_list_block_number(
        db_session: AsyncSession, contract_address: str, block_number: int
    ):
        """Get token list index for Share"""
        _idx_token_list_block_number = (
            await db_session.scalars(
                select(IDXTokenListBlockNumber)
                .where(IDXTokenListBlockNumber.contract_address == contract_address)
                .limit(1)
            )
        ).first()
        if _idx_token_list_block_number is None:
            _idx_token_list_block_number = IDXTokenListBlockNumber()
        _idx_token_list_block_number.latest_block_number = block_number
        _idx_token_list_block_number.contract_address = contract_address
        await db_session.merge(_idx_token_list_block_number)


async def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            await processor.process()
            LOG.debug("Processed")
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An exception occurred during event synchronization")

        await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
