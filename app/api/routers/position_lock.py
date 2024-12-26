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

from datetime import timedelta, timezone
from typing import Annotated, Sequence
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy import String, cast, column, desc, func, literal, null, select

from app import config, log
from app.config import TZ
from app.database import DBAsyncSession
from app.errors import DataNotExistsError, InvalidParameterError, NotSupportedError
from app.model.blockchain import (
    BondToken,
    ShareToken,
    TokenClassTypes as BlockChainTokenModel,
)
from app.model.db import (
    IDXBondToken,
    IDXLock,
    IDXLockedPosition,
    IDXShareToken,
    IDXTokenInstance,
    IDXTokenModel,
    IDXUnlock,
)
from app.model.schema import (
    ListAllLockedPositionQuery,
    ListAllLockedPositionResponse,
    ListAllLockEventQuery,
    ListAllLockEventsResponse,
    LockEventCategory,
    LockEventSortItem,
    RetrieveShareTokenResponse,
    RetrieveStraightBondTokenResponse,
)
from app.model.schema.base import (
    EthereumAddress,
    GenericSuccessResponse,
    SuccessResponse,
    TokenType,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()

UTC = timezone(timedelta(hours=0), "UTC")
local_tz = ZoneInfo(TZ)

router = APIRouter(prefix="/Position", tags=["user_position"])


class ListAllLock:
    token_type: str
    token_model: BlockChainTokenModel
    idx_token_model: IDXTokenModel

    def __init__(
        self,
        token_type: str,
        token_model: BlockChainTokenModel,
        idx_token_model: IDXTokenModel,
    ):
        self.token_type = token_type
        self.token_model = token_model
        self.idx_token_model = idx_token_model

    async def __call__(
        self,
        async_session: DBAsyncSession,
        req: Request,
        account_address: Annotated[
            EthereumAddress, Path(description="account address")
        ],
        request_query: Annotated[ListAllLockedPositionQuery, Query()],
    ):
        if self.token_type == TokenType.IbetShare:
            token_enabled = config.SHARE_TOKEN_ENABLED
        else:  # IbetStraightBond
            token_enabled = config.BOND_TOKEN_ENABLED
        if token_enabled is False:
            raise NotSupportedError(method="GET", url=req.url.path)

        token_address_list = request_query.token_address_list
        lock_address = request_query.lock_address
        limit = request_query.limit
        offset = request_query.offset

        sort_item = request_query.sort_item
        sort_order = request_query.sort_order  # default: asc

        stmt = select(IDXLockedPosition, self.idx_token_model).join(
            self.idx_token_model,
            IDXLockedPosition.token_address == self.idx_token_model.token_address,
        )
        if len(token_address_list) > 0:
            stmt = stmt.where(IDXLockedPosition.token_address.in_(token_address_list))
        stmt = stmt.where(IDXLockedPosition.account_address == account_address).where(
            IDXLockedPosition.value > 0
        )

        total = await async_session.scalar(
            stmt.with_only_columns(func.count())
            .select_from(IDXLockedPosition)
            .order_by(None)
        )

        if lock_address is not None:
            stmt = stmt.where(IDXLockedPosition.lock_address == lock_address)

        count = await async_session.scalar(
            stmt.with_only_columns(func.count())
            .select_from(IDXLockedPosition)
            .order_by(None)
        )

        sort_attr = getattr(IDXLockedPosition, sort_item, None)

        if sort_order == 0:  # ASC
            stmt = stmt.order_by(sort_attr)
        else:  # DESC
            stmt = stmt.order_by(desc(sort_attr))

        # NOTE: Set secondary sort for consistent results
        if sort_item != "token_address":
            stmt = stmt.order_by(IDXLockedPosition.token_address)
        else:
            stmt = stmt.order_by(IDXLockedPosition.created)

        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)

        _locked_list: Sequence[tuple[IDXLockedPosition, IDXTokenInstance]] = (
            await async_session.execute(stmt)
        ).all()
        locked_list = []

        for _locked in _locked_list:
            _locked_data = _locked[0].json()
            if request_query.include_token_details is True:
                _locked_data["token"] = self.token_model.from_model(_locked[1]).__dict__
            locked_list.append(_locked_data)

        data = {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": total,
            },
            "locked_positions": locked_list,
        }

        return data


class ListAllLockEvent:
    token_type: str
    token_model: BlockChainTokenModel
    idx_token_model: IDXTokenModel

    def __init__(
        self,
        token_type: str,
        token_model: BlockChainTokenModel,
        idx_token_model: IDXTokenModel,
    ):
        self.token_type = token_type
        self.token_model = token_model
        self.idx_token_model = idx_token_model

    async def __call__(
        self,
        async_session: DBAsyncSession,
        req: Request,
        account_address: Annotated[
            EthereumAddress, Path(description="account address")
        ],
        request_query: Annotated[ListAllLockEventQuery, Query()],
    ):
        if self.token_type == TokenType.IbetShare:
            token_enabled = config.SHARE_TOKEN_ENABLED
        else:  # IbetStraightBond
            token_enabled = config.BOND_TOKEN_ENABLED
        if token_enabled is False:
            raise NotSupportedError(method="GET", url=req.url.path)

        token_address_list = request_query.token_address_list
        category = request_query.category

        stmt_lock = select(
            literal(value=LockEventCategory.Lock.value, type_=String).label(
                "history_category"
            ),
            IDXLock.transaction_hash.label("transaction_hash"),
            IDXLock.msg_sender.label("msg_sender"),
            IDXLock.token_address.label("token_address_alias"),
            IDXLock.lock_address.label("lock_address"),
            IDXLock.account_address.label("account_address"),
            null().label("recipient_address"),
            IDXLock.value.label("value"),
            IDXLock.data.label("data"),
            IDXLock.block_timestamp.label("block_timestamp"),
        )
        stmt_unlock = select(
            literal(value=LockEventCategory.Unlock.value, type_=String).label(
                "history_category"
            ),
            IDXUnlock.transaction_hash.label("transaction_hash"),
            IDXUnlock.msg_sender.label("msg_sender"),
            IDXUnlock.token_address.label("token_address_alias"),
            IDXUnlock.lock_address.label("lock_address"),
            IDXUnlock.account_address.label("account_address"),
            IDXUnlock.recipient_address.label("recipient_address"),
            IDXUnlock.value.label("value"),
            IDXUnlock.data.label("data"),
            IDXUnlock.block_timestamp.label("block_timestamp"),
        )

        if len(token_address_list) > 0:
            stmt_lock = stmt_lock.where(
                IDXLock.token_address.label("token_address").in_(token_address_list)
            )
            stmt_unlock = stmt_unlock.where(
                IDXUnlock.token_address.label("token_address").in_(token_address_list)
            )

        total = await async_session.scalar(
            stmt_lock.with_only_columns(func.count())
            .select_from(IDXLock)
            .order_by(None)
        ) + await async_session.scalar(
            stmt_unlock.with_only_columns(func.count())
            .select_from(IDXUnlock)
            .order_by(None)
        )

        match category:
            case LockEventCategory.Lock:
                stmt = stmt_lock.subquery()
            case LockEventCategory.Unlock:
                stmt = stmt_unlock.subquery()
            case _:
                stmt = stmt_lock.union_all(stmt_unlock).subquery()

        stmt = (
            select(stmt)
            .join(
                self.idx_token_model,
                column("token_address_alias") == self.idx_token_model.token_address,
            )
            .add_columns(self.idx_token_model)
        )
        stmt = stmt.where(column("account_address") == account_address)

        if request_query.msg_sender is not None:
            stmt = stmt.where(column("msg_sender") == request_query.msg_sender)
        if request_query.lock_address is not None:
            stmt = stmt.where(column("lock_address") == request_query.lock_address)
        if request_query.recipient_address is not None:
            stmt = stmt.where(
                column("recipient_address") == request_query.recipient_address
            )
        if request_query.data is not None:
            stmt = stmt.where(
                cast(column("data"), String).like("%" + request_query.data + "%")
            )
        count = await async_session.scalar(
            stmt.with_only_columns(func.count()).order_by(None)
        )

        # Sort
        sort_attr = column(request_query.sort_item)
        if request_query.sort_order == 0:  # ASC
            stmt = stmt.order_by(sort_attr.is_(None), sort_attr)
        else:  # DESC
            stmt = stmt.order_by(sort_attr.is_(None), desc(sort_attr))
        if request_query.sort_item != LockEventSortItem.block_timestamp:
            # NOTE: Set secondary sort for consistent results
            stmt = stmt.order_by(desc(column(LockEventSortItem.block_timestamp)))

        # Pagination
        if request_query.offset is not None:
            stmt = stmt.offset(request_query.offset)
        if request_query.limit is not None:
            stmt = stmt.limit(request_query.limit)
        lock_events = (await async_session.execute(stmt)).all()

        resp_data = []
        for lock_event in lock_events:
            event_data = {
                "category": lock_event[0],
                "transaction_hash": lock_event[1],
                "msg_sender": lock_event[2],
                "token_address": lock_event[3],
                "lock_address": lock_event[4],
                "account_address": lock_event[5],
                "recipient_address": lock_event[6],
                "value": lock_event[7],
                "data": lock_event[8],
                "block_timestamp": lock_event[9]
                .replace(tzinfo=UTC)
                .astimezone(local_tz),
            }
            if request_query.include_token_details is True:
                event_data["token"] = self.token_model.from_model(
                    lock_event[10]
                ).__dict__
            resp_data.append(event_data)

        data = {
            "result_set": {
                "count": count,
                "offset": request_query.offset,
                "limit": request_query.limit,
                "total": total,
            },
            "events": resp_data,
        }
        return data


# /Position/{account_address}/Share/Lock
@router.get(
    "/{account_address}/Share/Lock",
    summary="Share Token Locked Position",
    operation_id="GetShareTokenLockedPosition",
    response_model=GenericSuccessResponse[
        ListAllLockedPositionResponse[RetrieveShareTokenResponse]
    ],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError),
)
async def list_all_share_locked_position(
    data: dict = Depends(ListAllLock(TokenType.IbetShare, ShareToken, IDXShareToken)),
):
    """
    [Share]Returns a list of locked positions.
    """
    return json_response({**SuccessResponse.default(), "data": data})


# /Position/{account_address}/Share/Lock/Event
@router.get(
    "/{account_address}/Share/Lock/Event",
    summary="Share Token Lock Events",
    operation_id="GetShareTokenLockEvent",
    response_model=GenericSuccessResponse[
        ListAllLockEventsResponse[RetrieveShareTokenResponse]
    ],
    responses=get_routers_responses(),
)
async def list_all_share_lock_events(
    data: dict = Depends(
        ListAllLockEvent(TokenType.IbetShare, ShareToken, IDXShareToken)
    ),
):
    """
    [Share]Returns a list of lock events.
    """
    return json_response({**SuccessResponse.default(), "data": data})


# /Position/{account_address}/StraightBond/Lock
@router.get(
    "/{account_address}/StraightBond/Lock",
    summary="StraightBond Token Locked Position",
    operation_id="GetStraightBondTokenLockedPosition",
    response_model=GenericSuccessResponse[
        ListAllLockedPositionResponse[RetrieveStraightBondTokenResponse]
    ],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError),
)
async def list_all_straight_bond_locked_position(
    data: dict = Depends(
        ListAllLock(TokenType.IbetStraightBond, BondToken, IDXBondToken)
    ),
):
    """
    [StraightBond]Returns a list of locked positions.
    """
    return json_response({**SuccessResponse.default(), "data": data})


# /Position/{account_address}/StraightBond/Lock/Event
@router.get(
    "/{account_address}/StraightBond/Lock/Event",
    summary="StraightBond Token Lock Events",
    operation_id="GetStraightBondTokenLockEvent",
    response_model=GenericSuccessResponse[
        ListAllLockEventsResponse[RetrieveStraightBondTokenResponse]
    ],
    responses=get_routers_responses(),
)
async def list_all_straight_bond_lock_events(
    data: dict = Depends(
        ListAllLockEvent(TokenType.IbetStraightBond, BondToken, IDXBondToken)
    ),
):
    """
    [StraightBond]Returns a list of lock events.
    """
    return json_response({**SuccessResponse.default(), "data": data})
