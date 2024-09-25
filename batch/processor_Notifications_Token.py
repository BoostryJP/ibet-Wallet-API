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
from datetime import UTC, datetime
from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.contract import AsyncContract as Web3AsyncContract
from web3.exceptions import ABIEventNotFound
from web3.types import EventData

from app.config import (
    NOTIFICATION_PROCESS_INTERVAL,
    TOKEN_LIST_CONTRACT_ADDRESS,
    WORKER_COUNT,
)
from app.contracts import AsyncContract
from app.database import BatchAsyncSessionLocal
from app.errors import ServiceUnavailable
from app.model.db import (
    IDXTokenListItem,
    Listing,
    Notification,
    NotificationBlockNumber,
    NotificationType,
)
from app.utils.asyncio_utils import SemaphoreTaskGroup
from app.utils.company_list import CompanyList
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import log
from batch.lib.token_list import TokenList

LOG = log.get_logger(process_name="PROCESSOR-NOTIFICATIONS-TOKEN")

WORKER_COUNT = int(WORKER_COUNT)
NOTIFICATION_PROCESS_INTERVAL = int(NOTIFICATION_PROCESS_INTERVAL)

async_web3 = AsyncWeb3Wrapper()


# Get TokenList contract
list_contract = AsyncContract.get_contract(
    contract_name="TokenList", address=TOKEN_LIST_CONTRACT_ADDRESS
)
token_list = TokenList(list_contract)


# Watcher
class Watcher:
    contract_cache: dict[str, Web3AsyncContract] = {}

    def __init__(self, filter_name: str, filter_params: dict, notification_type: str):
        self.filter_name = filter_name
        self.filter_params = filter_params
        self.notification_type = notification_type

    @staticmethod
    def _gen_notification_id(entry, option_type=0):
        return "0x{:012x}{:06x}{:06x}{:02x}".format(
            entry["blockNumber"],
            entry["transactionIndex"],
            entry["logIndex"],
            option_type,
        )

    @staticmethod
    async def _gen_block_timestamp(entry):
        return datetime.fromtimestamp(
            (await async_web3.eth.get_block(entry["blockNumber"]))["timestamp"], UTC
        ).replace(tzinfo=None)

    @staticmethod
    async def _get_token_all_list(db_session: AsyncSession):
        _tokens = []
        registered_tokens: Sequence[IDXTokenListItem] = (
            await db_session.scalars(
                select(IDXTokenListItem).join(
                    Listing,
                    and_(Listing.token_address == IDXTokenListItem.token_address),
                )
            )
        ).all()
        for registered_token in registered_tokens:
            _tokens.append(
                {
                    "token": registered_token,
                    "token_type": registered_token.token_template,
                }
            )
        return _tokens

    async def db_merge(
        self,
        db_session: AsyncSession,
        token_contract: Web3AsyncContract,
        token_type: str,
        log_entries: list[EventData],
        token_owner_address: str,
    ):
        pass

    async def loop(self):
        start_time = time.time()
        db_session = BatchAsyncSessionLocal()

        try:
            # Get listed tokens
            _token_list = await self._get_token_all_list(db_session)
            latest_block_number = await async_web3.eth.block_number

            for _token in _token_list:
                # Get synchronized block number
                from_block_number = (
                    await self.__get_synchronized_block_number(
                        db_session=db_session,
                        contract_address=_token["token"].token_address,
                        notification_type=self.notification_type,
                    )
                    + 1
                )

                # Get the latest block number
                if from_block_number > latest_block_number:
                    LOG.info(f"<{self.__class__.__name__}> skip processing")
                    return

                # If the difference between the latest block number and fromBlock is 1,000,000 or more,
                # set toBlock to fromBlock + 999,999
                if latest_block_number - from_block_number >= 1000000:
                    to_block_number = from_block_number + 999999
                else:
                    to_block_number = latest_block_number

                # Get event logs
                try:
                    token_contract = self.contract_cache.get(
                        _token["token"].token_address, None
                    )
                    if token_contract is None:
                        token_contract = AsyncContract.get_contract(
                            contract_name=_token["token_type"],
                            address=_token["token"].token_address,
                        )
                        self.contract_cache[_token["token"].token_address] = (
                            token_contract
                        )
                    _event = getattr(token_contract.events, self.filter_name)
                    entries = await _event.get_logs(
                        from_block=from_block_number, to_block=to_block_number
                    )
                except ABIEventNotFound:  # Backward compatibility
                    entries = []
                except FileNotFoundError:
                    continue
                except Exception as err:  # If an Exception occurs, processing continues
                    LOG.error(err)
                    continue

                # Register notifications
                if len(entries) > 0:
                    await self.db_merge(
                        db_session=db_session,
                        token_contract=token_contract,
                        token_type=_token["token_type"],
                        log_entries=entries,
                        token_owner_address=_token["token"].owner_address,
                    )

                # Update synchronized block number
                await self.__set_synchronized_block_number(
                    db_session=db_session,
                    contract_address=_token["token"].token_address,
                    notification_type=self.notification_type,
                    block_number=to_block_number,
                )

                await db_session.commit()

        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        finally:
            await db_session.close()
            elapsed_time = time.time() - start_time
            LOG.info(
                "<{}> finished in {} secs".format(self.__class__.__name__, elapsed_time)
            )

    @staticmethod
    async def __get_synchronized_block_number(
        db_session: AsyncSession, contract_address: str, notification_type: str
    ):
        """Get latest synchronized blockNumber"""
        notification_block_number: NotificationBlockNumber | None = (
            await db_session.scalars(
                select(NotificationBlockNumber)
                .where(NotificationBlockNumber.notification_type == notification_type)
                .where(NotificationBlockNumber.contract_address == contract_address)
                .limit(1)
            )
        ).first()
        if notification_block_number is None:
            return -1
        else:
            return notification_block_number.latest_block_number

    @staticmethod
    async def __set_synchronized_block_number(
        db_session: AsyncSession,
        contract_address: str,
        notification_type: str,
        block_number: int,
    ):
        """Set latest synchronized blockNumber"""
        notification_block_number: NotificationBlockNumber | None = (
            await db_session.scalars(
                select(NotificationBlockNumber)
                .where(NotificationBlockNumber.notification_type == notification_type)
                .where(NotificationBlockNumber.contract_address == contract_address)
                .limit(1)
            )
        ).first()
        if notification_block_number is None:
            notification_block_number = NotificationBlockNumber()
        notification_block_number.notification_type = notification_type
        notification_block_number.contract_address = contract_address
        notification_block_number.latest_block_number = block_number
        await db_session.merge(notification_block_number)


class WatchTransfer(Watcher):
    """Watch Token Receive Event

    - Process for registering a notification when a token is received
    - Register a notification only if the account address (private key address) is the source of the transfer.
    """

    def __init__(self):
        super().__init__("Transfer", {}, NotificationType.TRANSFER)

    async def db_merge(
        self,
        db_session: AsyncSession,
        token_contract: Web3AsyncContract,
        token_type: str,
        log_entries: list[EventData],
        token_owner_address: str,
    ):
        company_list = await CompanyList.get()
        token_name = await AsyncContract.call_function(
            contract=token_contract, function_name="name", args=(), default_returns=""
        )
        for entry in log_entries:
            # If the contract address is the source of the transfer, skip the process
            if (
                await async_web3.eth.get_code(entry["args"]["from"])
            ).to_0x_hex() != "0x":
                continue

            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": token_type,
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = entry["args"]["to"]
            notification.block_timestamp = await self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            await db_session.merge(notification)


class WatchApplyForTransfer(Watcher):
    """Watch Token ApplyForTransfer Event

    - Process for registering a notification when application for transfer is submitted
    - Register a notification only if the account address (private key address) is the source of the transfer.
    """

    def __init__(self):
        super().__init__("ApplyForTransfer", {}, NotificationType.APPLY_FOR_TRANSFER)

    async def db_merge(
        self,
        db_session: AsyncSession,
        token_contract: Web3AsyncContract,
        token_type: str,
        log_entries: list[EventData],
        token_owner_address: str,
    ):
        company_list = await CompanyList.get()
        token_name = await AsyncContract.call_function(
            contract=token_contract, function_name="name", args=(), default_returns=""
        )
        for entry in log_entries:
            if not await token_list.is_registered(entry["address"]):
                continue

            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": token_type,
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = entry["args"]["to"]
            notification.block_timestamp = await self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            await db_session.merge(notification)


class WatchApproveTransfer(Watcher):
    """Watch Token ApproveTransfer Event

    - Process for registering a notification when application for transfer is approved
    - Register a notification only if the account address (private key address) is the source of the transfer.
    """

    def __init__(self):
        super().__init__("ApproveTransfer", {}, NotificationType.APPROVE_TRANSFER)

    async def db_merge(
        self,
        db_session: AsyncSession,
        token_contract: Web3AsyncContract,
        token_type: str,
        log_entries: list[EventData],
        token_owner_address: str,
    ):
        company_list = await CompanyList.get()
        token_name = await AsyncContract.call_function(
            contract=token_contract, function_name="name", args=(), default_returns=""
        )
        for entry in log_entries:
            if not await token_list.is_registered(entry["address"]):
                continue

            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": token_type,
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = entry["args"]["from"]
            notification.block_timestamp = await self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            await db_session.merge(notification)


class WatchCancelTransfer(Watcher):
    """Watch Token CancelTransfer Event

    - Process for registering a notification when application for transfer is canceled
    - Register a notification only if the account address (private key address) is the source of the transfer.
    """

    def __init__(self):
        super().__init__("CancelTransfer", {}, NotificationType.CANCEL_TRANSFER)

    async def db_merge(
        self,
        db_session: AsyncSession,
        token_contract: Web3AsyncContract,
        token_type: str,
        log_entries: list[EventData],
        token_owner_address: str,
    ):
        company_list = await CompanyList.get()
        token_name = await AsyncContract.call_function(
            contract=token_contract, function_name="name", args=(), default_returns=""
        )
        for entry in log_entries:
            if not await token_list.is_registered(entry["address"]):
                continue

            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": token_type,
            }
            notification = Notification()
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = entry["args"]["from"]
            notification.block_timestamp = await self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            await db_session.merge(notification)


# メイン処理
async def main():
    watchers = [
        WatchTransfer(),
        WatchApplyForTransfer(),
        WatchApproveTransfer(),
        WatchCancelTransfer(),
    ]

    LOG.info("Service started successfully")

    while True:
        start_time = time.time()

        try:
            tasks = await SemaphoreTaskGroup.run(
                *[watcher.loop() for watcher in watchers], max_concurrency=WORKER_COUNT
            )
            [task.result() for task in tasks]
        except ExceptionGroup as e:
            LOG.error(e)

        elapsed_time = time.time() - start_time
        LOG.info("<LOOP> finished in {} secs".format(elapsed_time))

        await asyncio.sleep(max(NOTIFICATION_PROCESS_INTERVAL - elapsed_time, 0))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
