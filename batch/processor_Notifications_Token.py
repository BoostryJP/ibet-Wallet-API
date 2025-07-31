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
from web3 import Web3
from web3.contract import AsyncContract as Web3AsyncContract
from web3.exceptions import (
    ABIEventNotFound,
)
from web3.types import EventData

from app.config import (
    NOTIFICATION_PROCESS_INTERVAL,
    TOKEN_LIST_CONTRACT_ADDRESS,
    WORKER_COUNT,
)
from app.contracts import AsyncContract
from app.database import BatchAsyncSessionLocal
from app.errors import ServiceUnavailable
from app.model.blockchain import BondToken, CouponToken, MembershipToken, ShareToken
from app.model.db import (
    IDXTokenListRegister,
    Listing,
    Notification,
    NotificationAttributeValue,
    NotificationBlockNumber,
    NotificationType,
)
from app.model.schema.base import TokenType
from app.utils.asyncio_utils import SemaphoreTaskGroup
from app.utils.company_list import CompanyList
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import free_malloc, log
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


# EventWatcher
class EventWatcher:
    contract_cache: dict[str, Web3AsyncContract] = {}

    def __init__(
        self,
        filter_name: str,
        filter_params: dict,
        notification_type: str,
        token_type_list: list[TokenType] = None,
        skip_past_data_on_initial_sync: bool = False,
    ):
        if token_type_list is None:
            token_type_list = list([])
        self.filter_name = filter_name
        self.filter_params = filter_params
        self.notification_type = notification_type
        self.token_type_list = token_type_list
        self.skip_past_data_on_initial_sync = skip_past_data_on_initial_sync

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
    async def _get_token_all_list(
        db_session: AsyncSession, token_type_list: list[TokenType]
    ):
        _tokens = []

        stmt = select(IDXTokenListRegister).join(
            Listing,
            and_(Listing.token_address == IDXTokenListRegister.token_address),
        )
        if len(token_type_list) != 0:
            stmt = stmt.where(IDXTokenListRegister.token_template.in_(token_type_list))
        registered_tokens: Sequence[IDXTokenListRegister] = (
            await db_session.scalars(stmt)
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
            _token_list = await self._get_token_all_list(
                db_session, self.token_type_list
            )
            latest_block_number = await async_web3.eth.block_number

            for _token in _token_list:
                # Get synchronized block number
                from_block_number = (
                    await self.__get_synchronized_block_number(
                        db_session=db_session,
                        contract_address=_token["token"].token_address,
                        notification_type=self.notification_type,
                        latest_block_number=latest_block_number,
                        skip_past_data_on_initial_sync=self.skip_past_data_on_initial_sync,
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
            LOG.notice("An external service was unavailable")
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
        db_session: AsyncSession,
        contract_address: str,
        notification_type: str,
        latest_block_number: int,
        skip_past_data_on_initial_sync: bool,
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
            if skip_past_data_on_initial_sync is True:
                return latest_block_number - 1
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


class WatchTransfer(EventWatcher):
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
            notification.notification_category = "event_log"
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = entry["args"]["to"]
            notification.block_timestamp = await self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            await db_session.merge(notification)


class WatchApplyForTransfer(EventWatcher):
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
            notification.notification_category = "event_log"
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = entry["args"]["to"]
            notification.block_timestamp = await self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            await db_session.merge(notification)


class WatchApproveTransfer(EventWatcher):
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
            notification.notification_category = "event_log"
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = entry["args"]["from"]
            notification.block_timestamp = await self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            await db_session.merge(notification)


class WatchCancelTransfer(EventWatcher):
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
            notification.notification_category = "event_log"
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = entry["args"]["from"]
            notification.block_timestamp = await self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            await db_session.merge(notification)


class WatchForceLock(EventWatcher):
    """Watch ForceLock Event

    - Process for registering a notification when a token is forcibly locked.
    """

    def __init__(self):
        super().__init__("ForceLock", {}, NotificationType.FORCE_LOCK)

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
            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": token_type,
            }
            notification = Notification()
            notification.notification_category = "event_log"
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = entry["args"]["accountAddress"]
            notification.block_timestamp = await self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            await db_session.merge(notification)


class WatchForceUnlock(EventWatcher):
    """Watch ForceUnlock Event

    - Process for registering a notification when a token is forcibly unlocked.
    """

    def __init__(self):
        super().__init__("ForceUnlock", {}, NotificationType.FORCE_UNLOCK)

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
            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": token_type,
            }
            notification = Notification()
            notification.notification_category = "event_log"
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = entry["args"]["accountAddress"]
            notification.block_timestamp = await self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            await db_session.merge(notification)


class WatchChangeToRedeemed(EventWatcher):
    """Watch ChangeToRedeemed Event for Bond Token

    - Process for registering a notification when a token status is changed to redeemed.
    """

    def __init__(self):
        super().__init__(
            filter_name="ChangeToRedeemed",
            filter_params={},
            notification_type=NotificationType.CHANGE_TO_REDEEMED,
            token_type_list=[TokenType.IbetStraightBond],
            skip_past_data_on_initial_sync=True,
        )

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
            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": token_type,
            }
            notification = Notification()
            notification.notification_category = "event_log"
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = None
            notification.block_timestamp = await self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            await db_session.merge(notification)


class WatchChangeToCanceled(EventWatcher):
    """Watch ChangeToCanceled Event for Share Token

    - Process for registering a notification when a token status is changed to canceled.
    """

    def __init__(self):
        super().__init__(
            filter_name="ChangeToCanceled",
            filter_params={},
            notification_type=NotificationType.CHANGE_TO_CANCELED,
            token_type_list=[TokenType.IbetShare],
            skip_past_data_on_initial_sync=True,
        )

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
            company = company_list.find(token_owner_address)
            metadata = {
                "company_name": company.corporate_name,
                "token_address": entry["address"],
                "token_name": token_name,
                "exchange_address": "",
                "token_type": token_type,
            }
            notification = Notification()
            notification.notification_category = "event_log"
            notification.notification_id = self._gen_notification_id(entry)
            notification.notification_type = self.notification_type
            notification.priority = 0
            notification.address = None
            notification.block_timestamp = await self._gen_block_timestamp(entry)
            notification.args = dict(entry["args"])
            notification.metainfo = metadata
            await db_session.merge(notification)


# AttributeWatcher
class AttributeWatcher:
    def __init__(
        self,
        attribute_key: str,
        notification_type: str,
        token_type_list: list[TokenType] = None,
    ):
        if token_type_list is None:
            token_type_list = list([])
        self.notification_type = notification_type
        self.token_type_list = token_type_list
        self.attribute_key = attribute_key
        self.attribute_key_hash = Web3.keccak(text=attribute_key).hex()[0:8]

    @staticmethod
    def _gen_notification_id(
        timestamp_ms: int, contract_address: str, attribute_key_hash: str, option_type=0
    ):
        contract_address_without_prefix = contract_address.replace("0x", "").lower()
        return f"0x{timestamp_ms:012x}{contract_address_without_prefix}{attribute_key_hash}{option_type:02x}"

    @staticmethod
    async def _get_token_all_list(
        db_session: AsyncSession, token_type_list: list[TokenType]
    ):
        _tokens = []

        stmt = select(IDXTokenListRegister).join(
            Listing,
            and_(Listing.token_address == IDXTokenListRegister.token_address),
        )
        if len(token_type_list) != 0:
            stmt = stmt.where(IDXTokenListRegister.token_template.in_(token_type_list))
        registered_tokens: Sequence[IDXTokenListRegister] = (
            await db_session.scalars(stmt)
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
        token_address: str,
        token_type: str,
        token_name: str,
        token_owner_address: str,
        previous_value: str | int | bool,
        current_value: str | int | bool,
    ):
        pass

    async def loop(self):
        start_time = time.time()
        db_session = BatchAsyncSessionLocal()

        try:
            # Get listed tokens
            _token_list = await self._get_token_all_list(
                db_session, self.token_type_list
            )

            for _token in _token_list:
                try:
                    # Get previous attribute value from DB
                    previous_attribute_key_value = await self.__get_attribute_value(
                        db_session,
                        _token["token"].token_address,
                        self.attribute_key,
                    )
                    is_initial_sync = (
                        True if previous_attribute_key_value is None else False
                    )

                    # Get token detail by token type
                    if _token["token_type"] == TokenType.IbetStraightBond:
                        token_detail = await BondToken.get(
                            async_session=db_session,
                            token_address=_token["token"].token_address,
                        )
                    elif _token["token_type"] == TokenType.IbetShare:
                        token_detail = await ShareToken.get(
                            async_session=db_session,
                            token_address=_token["token"].token_address,
                        )
                    elif _token["token_type"] == TokenType.IbetCoupon:
                        token_detail = await CouponToken.get(
                            async_session=db_session,
                            token_address=_token["token"].token_address,
                        )
                    elif _token["token_type"] == TokenType.IbetMembership:
                        token_detail = await MembershipToken.get(
                            async_session=db_session,
                            token_address=_token["token"].token_address,
                        )
                    else:  # pragma: no cover
                        continue

                    # Get current attribute value from token detail
                    current_attribute_value = token_detail.__dict__.get(
                        self.attribute_key
                    )

                    if is_initial_sync is False:
                        # Get previous attribute value from DB record
                        previous_attribute_value = (
                            previous_attribute_key_value.attribute.get(
                                self.attribute_key, None
                            )
                        )
                        # Register notification only if attribute value has changed
                        if (
                            current_attribute_value is not None
                            and current_attribute_value != previous_attribute_value
                        ):
                            token_name = token_detail.name
                            # Register attribute change notification
                            await self.db_merge(
                                db_session=db_session,
                                token_address=_token["token"].token_address,
                                token_type=_token["token_type"],
                                token_owner_address=_token["token"].owner_address,
                                token_name=token_name,
                                previous_value=previous_attribute_value,
                                current_value=current_attribute_value,
                            )

                    # Save latest attribute value to DB
                    await self.__set_attribute_value(
                        db_session,
                        _token["token"].token_address,
                        self.attribute_key,
                        current_attribute_value,
                    )
                    await db_session.commit()

                except Exception:  # Continue processing even if an exception occurs
                    LOG.exception("Failed to watch attribute")
                    continue

        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        finally:
            await db_session.close()
            elapsed_time = time.time() - start_time
            LOG.info(
                "<{}> finished in {} secs".format(self.__class__.__name__, elapsed_time)
            )

    @staticmethod
    async def __get_attribute_value(
        db_session: AsyncSession, contract_address: str, attribute_key: str
    ):
        """Get latest synchronized attribute value"""
        notification_attribute_value: NotificationAttributeValue | None = (
            await db_session.scalars(
                select(NotificationAttributeValue)
                .where(
                    and_(
                        NotificationAttributeValue.contract_address == contract_address,
                        NotificationAttributeValue.attribute_key == attribute_key,
                    )
                )
                .limit(1)
            )
        ).first()
        return notification_attribute_value

    @staticmethod
    async def __set_attribute_value(
        db_session: AsyncSession,
        contract_address: str,
        attribute_key: str,
        attribute_value: bool | int | str,
    ):
        """Set latest synchronized attribute value"""
        notification_attribute_value: NotificationAttributeValue | None = (
            await db_session.scalars(
                select(NotificationAttributeValue)
                .where(
                    and_(
                        NotificationAttributeValue.contract_address == contract_address,
                        NotificationAttributeValue.attribute_key == attribute_key,
                    )
                )
                .limit(1)
            )
        ).first()
        if notification_attribute_value is None:
            notification_attribute_value = NotificationAttributeValue()
        notification_attribute_value.contract_address = contract_address
        notification_attribute_value.attribute_key = attribute_key
        notification_attribute_value.attribute = {attribute_key: attribute_value}
        await db_session.merge(notification_attribute_value)


class WatchTransferableAttribute(AttributeWatcher):
    """Watch Transferable Attribute

    - Process for registering a notification when a token attribute "transferable" is changed.
    """

    def __init__(self):
        super().__init__(
            attribute_key="transferable",
            notification_type=NotificationType.TRANSFERABLE_CHANGED,
            token_type_list=[TokenType.IbetShare, TokenType.IbetStraightBond],
        )

    async def db_merge(
        self,
        db_session: AsyncSession,
        token_address: str,
        token_type: str,
        token_name: str,
        token_owner_address: str,
        previous_value: str | int | bool,
        current_value: str | int | bool,
    ):
        company_list = await CompanyList.get()
        company = company_list.find(token_owner_address)
        metadata = {
            "company_name": company.corporate_name,
            "token_address": token_address,
            "token_name": token_name,
            "exchange_address": "",
            "token_type": token_type,
        }
        timestamp_ms = int(time.time() * 1000)
        notification = Notification()
        notification.notification_category = "attribute_change"
        notification.notification_id = self._gen_notification_id(
            timestamp_ms=timestamp_ms,
            contract_address=token_address,
            attribute_key_hash=self.attribute_key_hash,
        )
        notification.notification_type = self.notification_type
        notification.priority = 0
        notification.address = None
        notification.block_timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
        notification.args = dict(
            {
                "previous": previous_value,
                "current": current_value,
            }
        )
        notification.metainfo = metadata
        await db_session.merge(notification)


# メイン処理
async def main():
    watchers = [
        WatchTransfer(),
        WatchApplyForTransfer(),
        WatchApproveTransfer(),
        WatchCancelTransfer(),
        WatchForceLock(),
        WatchForceUnlock(),
        WatchChangeToRedeemed(),
        WatchChangeToCanceled(),
        WatchTransferableAttribute(),
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
            LOG.error(e.exceptions)

        elapsed_time = time.time() - start_time
        LOG.info("<LOOP> finished in {} secs".format(elapsed_time))

        await asyncio.sleep(max(NOTIFICATION_PROCESS_INTERVAL - elapsed_time, 0))
        free_malloc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
