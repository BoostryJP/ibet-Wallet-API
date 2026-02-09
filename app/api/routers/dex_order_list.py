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

from datetime import datetime
from typing import Annotated, Sequence, TypeAlias

from eth_utils.address import to_checksum_address
from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from web3.contract import AsyncContract as Web3AsyncContract

from app import config, log
from app.contracts import AsyncContract
from app.database import DBAsyncSession
from app.errors import InvalidParameterError, NotSupportedError, ServiceUnavailable
from app.model.blockchain import CouponToken, MembershipToken, TokenClassTypes
from app.model.db import AgreementStatus, IDXAgreement as Agreement, IDXOrder as Order
from app.model.schema import (
    ListAllOrderListQuery,
    ListAllOrderListResponse,
    RetrieveCouponTokenResponse,
    RetrieveMembershipTokenResponse,
    TokenAddress,
)
from app.model.schema.base import GenericSuccessResponse, SuccessResponse
from app.model.type import EthereumAddress
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()

router = APIRouter(prefix="/DEX/OrderList", tags=["dex"])

OrderSnapshot: TypeAlias = tuple[str, str, int, int, bool, str, bool]
AgreementSnapshot: TypeAlias = tuple[str, int, int, bool, bool, int]
OrderListItem: TypeAlias = dict[str, object]
OrderListResponseDict: TypeAlias = dict[str, list[OrderListItem]]


def _format_timestamp(value: datetime) -> str:
    return "{}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
        value.year,
        value.month,
        value.day,
        value.hour,
        value.minute,
        value.second,
    )


def _sort_by_sort_id(item: OrderListItem) -> int:
    sort_id = item.get("sort_id")
    if isinstance(sort_id, int):
        return sort_id
    return -1


class BaseOrderList:
    @staticmethod
    async def _get_order_snapshot(
        exchange_contract: Web3AsyncContract, order_id: int
    ) -> OrderSnapshot:
        return await AsyncContract.call_function(
            contract=exchange_contract,
            function_name="getOrder",
            args=(order_id,),
            default_returns=(
                config.ZERO_ADDRESS,
                config.ZERO_ADDRESS,
                0,
                0,
                False,
                config.ZERO_ADDRESS,
                False,
            ),
        )

    @staticmethod
    async def _get_agreement_snapshot(
        exchange_contract: Web3AsyncContract, order_id: int, agreement_id: int
    ) -> AgreementSnapshot:
        return await AsyncContract.call_function(
            contract=exchange_contract,
            function_name="getAgreement",
            args=(
                order_id,
                agreement_id,
            ),
            default_returns=(config.ZERO_ADDRESS, 0, 0, False, False, 0),
        )

    @staticmethod
    async def _with_token(
        async_session: AsyncSession,
        token_model: TokenClassTypes | None,
        token_address: str,
        payload: OrderListItem,
    ) -> None:
        if token_model is None:
            return
        token = await token_model.get(async_session, to_checksum_address(token_address))
        payload["token"] = token.to_dict()

    @staticmethod
    async def get_order_list(
        async_session: AsyncSession,
        token_model: TokenClassTypes | None,
        exchange_contract_address: str,
        account_address: str,
        include_canceled_items: bool | None,
    ) -> list[OrderListItem]:
        """List all orders from the account (DEX)"""
        exchange_address = to_checksum_address(exchange_contract_address)
        exchange_contract = AsyncContract.get_contract("IbetExchange", exchange_address)

        stmt = (
            select(Order.id, Order.order_id, Order.order_timestamp)
            .where(Order.exchange_address == exchange_address)
            .where(Order.account_address == account_address)
        )

        if include_canceled_items is True:
            order_events: Sequence[tuple[int | None, int | None, datetime | None]] = (
                (await async_session.execute(stmt)).tuples().all()
            )
        else:
            order_events = (
                (await async_session.execute(stmt.where(Order.is_cancelled == False)))
                .tuples()
                .all()
            )

        order_list: list[OrderListItem] = []
        for id_, order_id, order_timestamp in order_events:
            # TODO: Migrate order.id to NOT NULL and update ORM typing
            assert id_ is not None
            # TODO: Migrate order.order_id to NOT NULL and update ORM typing
            assert order_id is not None
            # TODO: Migrate order.order_timestamp to NOT NULL and update ORM typing
            assert order_timestamp is not None

            order_book = await BaseOrderList._get_order_snapshot(
                exchange_contract, order_id
            )
            if order_book[2] == 0:
                continue

            order_payload: OrderListItem = {
                "order": {
                    "order_id": order_id,
                    "counterpart_address": "",
                    "amount": order_book[2],
                    "price": order_book[3],
                    "is_buy": order_book[4],
                    "canceled": order_book[6],
                    "order_timestamp": _format_timestamp(order_timestamp),
                },
                "sort_id": id_,
            }
            await BaseOrderList._with_token(
                async_session=async_session,
                token_model=token_model,
                token_address=order_book[1],
                payload=order_payload,
            )
            order_list.append(order_payload)

        return order_list

    @staticmethod
    async def get_settlement_list(
        async_session: AsyncSession,
        token_model: TokenClassTypes | None,
        exchange_contract_address: str,
        account_address: str,
    ) -> list[OrderListItem]:
        """List all orders in process of settlement (DEX)"""
        exchange_address = to_checksum_address(exchange_contract_address)
        exchange_contract = AsyncContract.get_contract("IbetExchange", exchange_address)

        agreement_events: Sequence[
            tuple[int | None, int | None, int | None, datetime | None, str | None]
        ] = (
            (
                await async_session.execute(
                    select(
                        Agreement.id,
                        Agreement.order_id,
                        Agreement.agreement_id,
                        Agreement.agreement_timestamp,
                        Agreement.buyer_address,
                    )
                    .where(Agreement.exchange_address == exchange_address)
                    .where(
                        or_(
                            Agreement.buyer_address == account_address,
                            Agreement.seller_address == account_address,
                        )
                    )
                    .where(Agreement.status == AgreementStatus.PENDING.value)
                )
            )
            .tuples()
            .all()
        )

        settlement_list: list[OrderListItem] = []
        for (
            id_,
            order_id,
            agreement_id,
            agreement_timestamp,
            buyer_address,
        ) in agreement_events:
            # TODO: Migrate agreement.id to NOT NULL and update ORM typing
            assert id_ is not None
            # TODO: Migrate agreement.order_id to NOT NULL and update ORM typing
            assert order_id is not None
            # TODO: Migrate agreement.agreement_id to NOT NULL and update ORM typing
            assert agreement_id is not None
            # TODO: Migrate agreement.agreement_timestamp to NOT NULL and update ORM typing
            assert agreement_timestamp is not None
            # TODO: Migrate agreement.buyer_address to NOT NULL and update ORM typing
            assert buyer_address is not None

            try:
                order_book = await BaseOrderList._get_order_snapshot(
                    exchange_contract, order_id
                )
                agreement = await BaseOrderList._get_agreement_snapshot(
                    exchange_contract,
                    order_id,
                    agreement_id,
                )
            except Exception:
                raise ServiceUnavailable from None

            settlement_payload: OrderListItem = {
                "agreement": {
                    "exchange_address": exchange_contract_address,
                    "order_id": order_id,
                    "agreement_id": agreement_id,
                    "amount": agreement[1],
                    "price": agreement[2],
                    "is_buy": buyer_address == account_address,
                    "canceled": agreement[3],
                    "agreement_timestamp": _format_timestamp(agreement_timestamp),
                },
                "sort_id": id_,
            }
            await BaseOrderList._with_token(
                async_session=async_session,
                token_model=token_model,
                token_address=order_book[1],
                payload=settlement_payload,
            )
            settlement_list.append(settlement_payload)

        return settlement_list

    @staticmethod
    async def get_complete_list(
        async_session: AsyncSession,
        token_model: TokenClassTypes | None,
        exchange_contract_address: str,
        account_address: str,
        include_canceled_items: bool | None,
    ) -> list[OrderListItem]:
        """List all orders that have been settled (DEX)"""
        exchange_address = to_checksum_address(exchange_contract_address)
        exchange_contract = AsyncContract.get_contract("IbetExchange", exchange_address)

        stmt = (
            select(
                Agreement.id,
                Agreement.order_id,
                Agreement.agreement_id,
                Agreement.agreement_timestamp,
                Agreement.settlement_timestamp,
                Agreement.buyer_address,
            )
            .where(Agreement.exchange_address == exchange_address)
            .where(
                or_(
                    Agreement.buyer_address == account_address,
                    Agreement.seller_address == account_address,
                )
            )
        )

        if include_canceled_items is True:
            agreement_events: Sequence[
                tuple[
                    int | None,
                    int | None,
                    int | None,
                    datetime | None,
                    datetime | None,
                    str | None,
                ]
            ] = (
                (
                    await async_session.execute(
                        stmt.where(
                            or_(
                                Agreement.status == AgreementStatus.DONE.value,
                                Agreement.status == AgreementStatus.CANCELED.value,
                            )
                        )
                    )
                )
                .tuples()
                .all()
            )
        else:
            agreement_events = (
                (
                    await async_session.execute(
                        stmt.where(Agreement.status == AgreementStatus.DONE.value)
                    )
                )
                .tuples()
                .all()
            )

        complete_list: list[OrderListItem] = []
        for (
            id_,
            order_id,
            agreement_id,
            agreement_timestamp,
            settlement_timestamp,
            buyer_address,
        ) in agreement_events:
            # TODO: Migrate agreement.id to NOT NULL and update ORM typing
            assert id_ is not None
            # TODO: Migrate agreement.order_id to NOT NULL and update ORM typing
            assert order_id is not None
            # TODO: Migrate agreement.agreement_id to NOT NULL and update ORM typing
            assert agreement_id is not None
            # TODO: Migrate agreement.agreement_timestamp to NOT NULL and update ORM typing
            assert agreement_timestamp is not None
            # TODO: Migrate agreement.buyer_address to NOT NULL and update ORM typing
            assert buyer_address is not None

            if settlement_timestamp is not None:
                settlement_timestamp_jp = _format_timestamp(settlement_timestamp)
            else:
                settlement_timestamp_jp = ""

            try:
                order_book = await BaseOrderList._get_order_snapshot(
                    exchange_contract, order_id
                )
                agreement = await BaseOrderList._get_agreement_snapshot(
                    exchange_contract,
                    order_id,
                    agreement_id,
                )
            except Exception:
                raise ServiceUnavailable from None

            complete_payload: OrderListItem = {
                "agreement": {
                    "exchange_address": exchange_contract_address,
                    "order_id": order_id,
                    "agreement_id": agreement_id,
                    "amount": agreement[1],
                    "price": agreement[2],
                    "is_buy": buyer_address == account_address,
                    "canceled": agreement[3],
                    "agreement_timestamp": _format_timestamp(agreement_timestamp),
                },
                "settlement_timestamp": settlement_timestamp_jp,
                "sort_id": id_,
            }
            await BaseOrderList._with_token(
                async_session=async_session,
                token_model=token_model,
                token_address=order_book[1],
                payload=complete_payload,
            )
            complete_list.append(complete_payload)

        return complete_list

    @staticmethod
    async def get_order_list_filtered_by_token(
        async_session: AsyncSession,
        token_address: str,
        account_address: str,
        include_canceled_items: bool | None,
    ) -> list[OrderListItem]:
        """List orders from accounts filtered by token address (DEX)"""
        stmt = (
            select(
                Order.id, Order.exchange_address, Order.order_id, Order.order_timestamp
            )
            .where(Order.token_address == token_address)
            .where(Order.account_address == account_address)
        )

        if include_canceled_items is True:
            order_events: Sequence[
                tuple[int | None, str | None, int | None, datetime | None]
            ] = (await async_session.execute(stmt)).tuples().all()
        else:
            order_events = (
                (await async_session.execute(stmt.where(Order.is_cancelled == False)))
                .tuples()
                .all()
            )

        order_list: list[OrderListItem] = []
        for id_, exchange_contract_address, order_id, order_timestamp in order_events:
            # TODO: Migrate order.id to NOT NULL and update ORM typing
            assert id_ is not None
            # TODO: Migrate order.exchange_address to NOT NULL and update ORM typing
            assert exchange_contract_address is not None
            # TODO: Migrate order.order_id to NOT NULL and update ORM typing
            assert order_id is not None
            # TODO: Migrate order.order_timestamp to NOT NULL and update ORM typing
            assert order_timestamp is not None

            exchange_contract = AsyncContract.get_contract(
                contract_name="IbetExchange", address=exchange_contract_address
            )
            order_book = await BaseOrderList._get_order_snapshot(
                exchange_contract, order_id
            )
            if order_book[2] == 0:
                continue

            order_list.append(
                {
                    "token": {"token_address": token_address},
                    "order": {
                        "order_id": order_id,
                        "counterpart_address": "",
                        "amount": order_book[2],
                        "price": order_book[3],
                        "is_buy": order_book[4],
                        "canceled": order_book[6],
                        "order_timestamp": _format_timestamp(order_timestamp),
                    },
                    "sort_id": id_,
                }
            )

        return order_list

    @staticmethod
    async def get_settlement_list_filtered_by_token(
        async_session: AsyncSession,
        token_address: str,
        account_address: str,
    ) -> list[OrderListItem]:
        """List all orders in process of settlement (DEX)"""
        agreement_events: Sequence[
            tuple[
                int | None,
                str | None,
                int | None,
                int | None,
                datetime | None,
                str | None,
            ]
        ] = (
            (
                await async_session.execute(
                    select(
                        Agreement.id,
                        Agreement.exchange_address,
                        Agreement.order_id,
                        Agreement.agreement_id,
                        Agreement.agreement_timestamp,
                        Agreement.buyer_address,
                    )
                    .outerjoin(
                        Order, Agreement.unique_order_id == Order.unique_order_id
                    )
                    .where(Order.token_address == token_address)
                    .where(
                        or_(
                            Agreement.buyer_address == account_address,
                            Agreement.seller_address == account_address,
                        )
                    )
                    .where(Agreement.status == AgreementStatus.PENDING.value)
                )
            )
            .tuples()
            .all()
        )

        settlement_list: list[OrderListItem] = []
        for (
            id_,
            exchange_contract_address,
            order_id,
            agreement_id,
            agreement_timestamp,
            buyer_address,
        ) in agreement_events:
            # TODO: Migrate agreement.id to NOT NULL and update ORM typing
            assert id_ is not None
            # TODO: Migrate agreement.exchange_address to NOT NULL and update ORM typing
            assert exchange_contract_address is not None
            # TODO: Migrate agreement.order_id to NOT NULL and update ORM typing
            assert order_id is not None
            # TODO: Migrate agreement.agreement_id to NOT NULL and update ORM typing
            assert agreement_id is not None
            # TODO: Migrate agreement.agreement_timestamp to NOT NULL and update ORM typing
            assert agreement_timestamp is not None
            # TODO: Migrate agreement.buyer_address to NOT NULL and update ORM typing
            assert buyer_address is not None

            exchange_contract = AsyncContract.get_contract(
                contract_name="IbetExchange", address=exchange_contract_address
            )
            agreement = await BaseOrderList._get_agreement_snapshot(
                exchange_contract,
                order_id,
                agreement_id,
            )
            settlement_list.append(
                {
                    "token": {"token_address": token_address},
                    "agreement": {
                        "exchange_address": exchange_contract_address,
                        "order_id": order_id,
                        "agreement_id": agreement_id,
                        "amount": agreement[1],
                        "price": agreement[2],
                        "is_buy": buyer_address == account_address,
                        "canceled": agreement[3],
                        "agreement_timestamp": _format_timestamp(agreement_timestamp),
                    },
                    "sort_id": id_,
                }
            )

        return settlement_list

    @staticmethod
    async def get_complete_list_filtered_by_token(
        async_session: AsyncSession,
        token_address: str,
        account_address: str,
        include_canceled_items: bool | None,
    ) -> list[OrderListItem]:
        """List all orders that have been settled (DEX)"""
        stmt = (
            select(
                Agreement.id,
                Agreement.exchange_address,
                Agreement.order_id,
                Agreement.agreement_id,
                Agreement.agreement_timestamp,
                Agreement.settlement_timestamp,
                Agreement.buyer_address,
            )
            .outerjoin(Order, Agreement.unique_order_id == Order.unique_order_id)
            .where(
                or_(
                    Agreement.buyer_address == account_address,
                    Agreement.seller_address == account_address,
                )
            )
            .where(Order.token_address == token_address)
        )

        if include_canceled_items is True:
            agreement_events: Sequence[
                tuple[
                    int | None,
                    str | None,
                    int | None,
                    int | None,
                    datetime | None,
                    datetime | None,
                    str | None,
                ]
            ] = (
                (
                    await async_session.execute(
                        stmt.where(
                            or_(
                                Agreement.status == AgreementStatus.DONE.value,
                                Agreement.status == AgreementStatus.CANCELED.value,
                            )
                        )
                    )
                )
                .tuples()
                .all()
            )
        else:
            agreement_events = (
                (
                    await async_session.execute(
                        stmt.where(Agreement.status == AgreementStatus.DONE.value)
                    )
                )
                .tuples()
                .all()
            )

        complete_list: list[OrderListItem] = []
        for (
            id_,
            exchange_contract_address,
            order_id,
            agreement_id,
            agreement_timestamp,
            settlement_timestamp,
            buyer_address,
        ) in agreement_events:
            # TODO: Migrate agreement.id to NOT NULL and update ORM typing
            assert id_ is not None
            # TODO: Migrate agreement.exchange_address to NOT NULL and update ORM typing
            assert exchange_contract_address is not None
            # TODO: Migrate agreement.order_id to NOT NULL and update ORM typing
            assert order_id is not None
            # TODO: Migrate agreement.agreement_id to NOT NULL and update ORM typing
            assert agreement_id is not None
            # TODO: Migrate agreement.agreement_timestamp to NOT NULL and update ORM typing
            assert agreement_timestamp is not None
            # TODO: Migrate agreement.buyer_address to NOT NULL and update ORM typing
            assert buyer_address is not None

            if settlement_timestamp is not None:
                settlement_timestamp_jp = _format_timestamp(settlement_timestamp)
            else:
                settlement_timestamp_jp = ""

            exchange_contract = AsyncContract.get_contract(
                contract_name="IbetExchange", address=exchange_contract_address
            )
            agreement = await BaseOrderList._get_agreement_snapshot(
                exchange_contract,
                order_id,
                agreement_id,
            )
            complete_list.append(
                {
                    "token": {"token_address": token_address},
                    "agreement": {
                        "exchange_address": exchange_contract_address,
                        "order_id": order_id,
                        "agreement_id": agreement_id,
                        "amount": agreement[1],
                        "price": agreement[2],
                        "is_buy": buyer_address == account_address,
                        "canceled": agreement[3],
                        "agreement_timestamp": _format_timestamp(agreement_timestamp),
                    },
                    "settlement_timestamp": settlement_timestamp_jp,
                    "sort_id": id_,
                }
            )

        return complete_list


# ------------------------------
# 注文一覧・約定一覧（会員権）
# ------------------------------
class MembershipOrderList(BaseOrderList):
    async def __call__(
        self,
        async_session: DBAsyncSession,
        req: Request,
        request_query: Annotated[ListAllOrderListQuery, Query()],
    ) -> OrderListResponseDict:
        if (
            config.MEMBERSHIP_TOKEN_ENABLED is False
            or config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS is None
        ):
            raise NotSupportedError(method="GET", url=req.url.path)

        order_list: list[OrderListItem] = []
        settlement_list: list[OrderListItem] = []
        complete_list: list[OrderListItem] = []

        for account_address in request_query.account_address_list:
            try:
                order_list.extend(
                    await self.get_order_list(
                        async_session=async_session,
                        token_model=MembershipToken,
                        exchange_contract_address=config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                        include_canceled_items=request_query.include_canceled_items,
                    )
                )
                order_list = sorted(order_list, key=_sort_by_sort_id)

                settlement_list.extend(
                    await self.get_settlement_list(
                        async_session=async_session,
                        token_model=MembershipToken,
                        exchange_contract_address=config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                    )
                )
                settlement_list = sorted(settlement_list, key=_sort_by_sort_id)

                complete_list.extend(
                    await self.get_complete_list(
                        async_session=async_session,
                        token_model=MembershipToken,
                        exchange_contract_address=config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                        include_canceled_items=request_query.include_canceled_items,
                    )
                )
                complete_list = sorted(complete_list, key=_sort_by_sort_id)
            except Exception as err:
                LOG.exception(err)

        return {
            "order_list": order_list,
            "settlement_list": settlement_list,
            "complete_list": complete_list,
        }


@router.get(
    "/Membership",
    summary="Membership Order History (Bulk Get)",
    operation_id="MembershipOrderList",
    response_model=GenericSuccessResponse[
        ListAllOrderListResponse[RetrieveMembershipTokenResponse]
    ],
    responses=get_routers_responses(NotSupportedError),
)
async def list_all_membership_order_history(
    order_list_res: OrderListResponseDict = Depends(MembershipOrderList()),
):
    """
    [Membership]Returns order history of given token.
    """
    return json_response({**SuccessResponse.default(), "data": order_list_res})


# ------------------------------
# 注文一覧・約定一覧（クーポン）
# ------------------------------
class CouponOrderList(BaseOrderList):
    async def __call__(
        self,
        async_session: DBAsyncSession,
        req: Request,
        request_query: Annotated[ListAllOrderListQuery, Query()],
    ) -> OrderListResponseDict:
        if (
            config.COUPON_TOKEN_ENABLED is False
            or config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS is None
        ):
            raise NotSupportedError(method="GET", url=req.url.path)

        order_list: list[OrderListItem] = []
        settlement_list: list[OrderListItem] = []
        complete_list: list[OrderListItem] = []

        for account_address in request_query.account_address_list:
            try:
                order_list.extend(
                    await self.get_order_list(
                        async_session=async_session,
                        token_model=CouponToken,
                        exchange_contract_address=config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                        include_canceled_items=request_query.include_canceled_items,
                    )
                )
                order_list = sorted(order_list, key=_sort_by_sort_id)

                settlement_list.extend(
                    await self.get_settlement_list(
                        async_session=async_session,
                        token_model=CouponToken,
                        exchange_contract_address=config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                    )
                )
                settlement_list = sorted(settlement_list, key=_sort_by_sort_id)

                complete_list.extend(
                    await self.get_complete_list(
                        async_session=async_session,
                        token_model=CouponToken,
                        exchange_contract_address=config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                        include_canceled_items=request_query.include_canceled_items,
                    )
                )
                complete_list = sorted(complete_list, key=_sort_by_sort_id)
            except Exception as err:
                LOG.exception(err)

        return {
            "order_list": order_list,
            "settlement_list": settlement_list,
            "complete_list": complete_list,
        }


@router.get(
    "/Coupon",
    summary="Coupon Order History (Bulk Get)",
    operation_id="CouponOrderList",
    response_model=GenericSuccessResponse[
        ListAllOrderListResponse[RetrieveCouponTokenResponse]
    ],
    responses=get_routers_responses(NotSupportedError),
)
async def list_all_coupon_order_history(
    order_list_res: OrderListResponseDict = Depends(CouponOrderList()),
):
    """
    [Coupon]Returns order history of given token.
    """
    return json_response({**SuccessResponse.default(), "data": order_list_res})


# ------------------------------
# 注文一覧・約定一覧
# ------------------------------
class OrderList(BaseOrderList):
    async def __call__(
        self,
        async_session: DBAsyncSession,
        req: Request,
        token_address: Annotated[EthereumAddress, Path(description="Token address")],
        request_query: Annotated[ListAllOrderListQuery, Query()],
    ) -> OrderListResponseDict:
        order_list: list[OrderListItem] = []
        settlement_list: list[OrderListItem] = []
        complete_list: list[OrderListItem] = []

        for account_address in request_query.account_address_list:
            try:
                order_list.extend(
                    await self.get_order_list_filtered_by_token(
                        async_session=async_session,
                        token_address=token_address,
                        account_address=account_address,
                        include_canceled_items=request_query.include_canceled_items,
                    )
                )
                order_list = sorted(order_list, key=_sort_by_sort_id)

                settlement_list.extend(
                    await self.get_settlement_list_filtered_by_token(
                        async_session=async_session,
                        token_address=token_address,
                        account_address=account_address,
                    )
                )
                settlement_list = sorted(settlement_list, key=_sort_by_sort_id)

                complete_list.extend(
                    await self.get_complete_list_filtered_by_token(
                        async_session=async_session,
                        token_address=token_address,
                        account_address=account_address,
                        include_canceled_items=request_query.include_canceled_items,
                    )
                )
                complete_list = sorted(complete_list, key=_sort_by_sort_id)
            except Exception as err:
                LOG.exception(err)

        return {
            "order_list": order_list,
            "settlement_list": settlement_list,
            "complete_list": complete_list,
        }


@router.get(
    "/{token_address}",
    summary="Order History filtered by token (Bulk Get)",
    operation_id="IbetExchange",
    response_model=GenericSuccessResponse[ListAllOrderListResponse[TokenAddress]],
    responses=get_routers_responses(NotSupportedError, InvalidParameterError),
)
async def list_all_order_history_by_token_address(
    order_list_res: OrderListResponseDict = Depends(OrderList()),
):
    """
    Returns order history.
    """
    return json_response({**SuccessResponse.default(), "data": order_list_res})
