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

from typing import Annotated

from eth_utils import to_checksum_address
from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import config, log
from app.contracts import AsyncContract
from app.database import DBAsyncSession
from app.errors import InvalidParameterError, NotSupportedError, ServiceUnavailable
from app.model.blockchain import CouponToken, MembershipToken
from app.model.db import AgreementStatus, IDXAgreement as Agreement, IDXOrder as Order
from app.model.schema import (
    ListAllOrderListQuery,
    ListAllOrderListResponse,
    RetrieveCouponTokenResponse,
    RetrieveMembershipTokenResponse,
    TokenAddress,
)
from app.model.schema.base import (
    GenericSuccessResponse,
    SuccessResponse,
)
from app.model.type import EthereumAddress
from app.utils.asyncio_utils import SemaphoreTaskGroup
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()

router = APIRouter(prefix="/DEX/OrderList", tags=["dex"])


class BaseOrderList(object):
    @staticmethod
    async def get_order_list(
        async_session: AsyncSession,
        token_model,
        exchange_contract_address,
        account_address,
        include_canceled_items,
    ):
        """List all orders from the account (DEX)"""
        # Get exchange contract
        exchange_address = to_checksum_address(exchange_contract_address)
        exchange_contract = AsyncContract.get_contract("IbetExchange", exchange_address)

        # Filter order events that are generated from account_address
        stmt = (
            select(Order.id, Order.order_id, Order.order_timestamp)
            .where(Order.exchange_address == exchange_address)
            .where(Order.account_address == account_address)
        )

        if include_canceled_items is not None and include_canceled_items is True:
            _order_events = (await async_session.execute(stmt)).all()
        else:  # default
            _order_events = (
                await async_session.execute(stmt.where(Order.is_cancelled == False))
            ).all()

        order_list = []
        for id, order_id, order_timestamp in _order_events:
            order_book = await AsyncContract.call_function(
                contract=exchange_contract,
                function_name="getOrder",
                args=(order_id,),
            )
            # If there are no remaining orders, skip this process
            if order_book[2] != 0:
                _order = {
                    "order": {
                        "order_id": order_id,
                        "counterpart_address": "",
                        "amount": order_book[2],
                        "price": order_book[3],
                        "is_buy": order_book[4],
                        "canceled": order_book[6],
                        "order_timestamp": "{}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
                            order_timestamp.year,
                            order_timestamp.month,
                            order_timestamp.day,
                            order_timestamp.hour,
                            order_timestamp.minute,
                            order_timestamp.second,
                        ),
                    },
                    "sort_id": id,
                }
                if token_model is not None:
                    token_detail = await token_model.get(
                        async_session=async_session,
                        token_address=to_checksum_address(order_book[1]),
                    )
                    _order["token"] = token_detail.__dict__

                order_list.append(_order)

        return order_list

    @staticmethod
    async def get_settlement_list(
        async_session: AsyncSession,
        token_model,
        exchange_contract_address,
        account_address,
    ):
        """List all orders in process of settlement (DEX)"""
        # Get exchange contract
        exchange_address = to_checksum_address(exchange_contract_address)
        exchange_contract = AsyncContract.get_contract("IbetExchange", exchange_address)

        # Filter agreement events (settlement not completed) generated from account_address
        _agreement_events = (
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
        ).all()

        settlement_list = []
        for (
            id,
            order_id,
            agreement_id,
            agreement_timestamp,
            buyer_address,
        ) in _agreement_events:
            try:
                tasks = await SemaphoreTaskGroup.run(
                    AsyncContract.call_function(
                        contract=exchange_contract,
                        function_name="getOrder",
                        args=(order_id,),
                    ),
                    AsyncContract.call_function(
                        contract=exchange_contract,
                        function_name="getAgreement",
                        args=(
                            order_id,
                            agreement_id,
                        ),
                    ),
                    max_concurrency=3,
                )
                order_book, agreement = [task.result() for task in tasks]
            except ExceptionGroup:
                raise ServiceUnavailable from None
            _settlement = {
                "agreement": {
                    "exchange_address": exchange_contract_address,
                    "order_id": order_id,
                    "agreement_id": agreement_id,
                    "amount": agreement[1],
                    "price": agreement[2],
                    "is_buy": buyer_address == account_address,
                    "canceled": agreement[3],
                    "agreement_timestamp": "{}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
                        agreement_timestamp.year,
                        agreement_timestamp.month,
                        agreement_timestamp.day,
                        agreement_timestamp.hour,
                        agreement_timestamp.minute,
                        agreement_timestamp.second,
                    ),
                },
                "sort_id": id,
            }
            if token_model is not None:
                token_detail = await token_model.get(
                    async_session=async_session,
                    token_address=to_checksum_address(order_book[1]),
                )
                _settlement["token"] = token_detail.__dict__

            settlement_list.append(_settlement)

        return settlement_list

    @staticmethod
    async def get_complete_list(
        async_session: AsyncSession,
        token_model,
        exchange_contract_address,
        account_address,
        include_canceled_items,
    ):
        """List all orders that have been settled (DEX)"""
        # Get exchange contract
        exchange_address = to_checksum_address(exchange_contract_address)
        exchange_contract = AsyncContract.get_contract("IbetExchange", exchange_address)

        # Filter agreement events (settlement completed) generated from account_address
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

        if include_canceled_items is not None and include_canceled_items is True:
            _agreement_events = (
                await async_session.execute(
                    stmt.where(
                        or_(
                            Agreement.status == AgreementStatus.DONE.value,
                            Agreement.status == AgreementStatus.CANCELED.value,
                        )
                    )
                )
            ).all()
        else:  # default
            _agreement_events = (
                await async_session.execute(
                    stmt.where(Agreement.status == AgreementStatus.DONE.value)
                )
            ).all()

        complete_list = []
        for (
            id,
            order_id,
            agreement_id,
            agreement_timestamp,
            settlement_timestamp,
            buyer_address,
        ) in _agreement_events:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = (
                    "{}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
                        settlement_timestamp.year,
                        settlement_timestamp.month,
                        settlement_timestamp.day,
                        settlement_timestamp.hour,
                        settlement_timestamp.minute,
                        settlement_timestamp.second,
                    )
                )
            else:
                settlement_timestamp_jp = ""
            try:
                tasks = await SemaphoreTaskGroup.run(
                    AsyncContract.call_function(
                        contract=exchange_contract,
                        function_name="getOrder",
                        args=(order_id,),
                    ),
                    AsyncContract.call_function(
                        contract=exchange_contract,
                        function_name="getAgreement",
                        args=(
                            order_id,
                            agreement_id,
                        ),
                    ),
                    max_concurrency=3,
                )
                order_book, agreement = [task.result() for task in tasks]
            except ExceptionGroup:
                raise ServiceUnavailable from None
            _complete = {
                "agreement": {
                    "exchange_address": exchange_contract_address,
                    "order_id": order_id,
                    "agreement_id": agreement_id,
                    "amount": agreement[1],
                    "price": agreement[2],
                    "is_buy": buyer_address == account_address,
                    "canceled": agreement[3],
                    "agreement_timestamp": "{}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
                        agreement_timestamp.year,
                        agreement_timestamp.month,
                        agreement_timestamp.day,
                        agreement_timestamp.hour,
                        agreement_timestamp.minute,
                        agreement_timestamp.second,
                    ),
                },
                "settlement_timestamp": settlement_timestamp_jp,
                "sort_id": id,
            }
            if token_model is not None:
                token_detail = await token_model.get(
                    async_session=async_session,
                    token_address=to_checksum_address(order_book[1]),
                )
                _complete["token"] = token_detail.__dict__

            complete_list.append(_complete)

        return complete_list

    @staticmethod
    async def get_order_list_filtered_by_token(
        async_session: AsyncSession,
        token_address,
        account_address,
        include_canceled_items,
    ):
        """List orders from accounts filtered by token address (DEX)"""

        # Filter order events that are generated from account_address
        stmt = (
            select(
                Order.id, Order.exchange_address, Order.order_id, Order.order_timestamp
            )
            .where(Order.token_address == token_address)
            .where(Order.account_address == account_address)
        )

        if include_canceled_items is not None and include_canceled_items is True:
            _order_events = (await async_session.execute(stmt)).all()
        else:  # default
            _order_events = (
                await async_session.execute(stmt.where(Order.is_cancelled == False))
            ).all()

        order_list = []
        for id, exchange_contract_address, order_id, order_timestamp in _order_events:
            exchange_contract = AsyncContract.get_contract(
                contract_name="IbetExchange", address=exchange_contract_address
            )
            order_book = await AsyncContract.call_function(
                contract=exchange_contract,
                function_name="getOrder",
                args=(order_id,),
            )
            # If there are no remaining orders, skip this process
            if order_book[2] != 0:
                _order = {
                    "token": {"token_address": token_address},
                    "order": {
                        "order_id": order_id,
                        "counterpart_address": "",
                        "amount": order_book[2],
                        "price": order_book[3],
                        "is_buy": order_book[4],
                        "canceled": order_book[6],
                        "order_timestamp": "{}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
                            order_timestamp.year,
                            order_timestamp.month,
                            order_timestamp.day,
                            order_timestamp.hour,
                            order_timestamp.minute,
                            order_timestamp.second,
                        ),
                    },
                    "sort_id": id,
                }
                order_list.append(_order)

        return order_list

    @staticmethod
    async def get_settlement_list_filtered_by_token(
        async_session: AsyncSession, token_address, account_address
    ):
        """List all orders in process of settlement (DEX)"""

        # Filter agreement events (settlement not completed) generated from account_address
        _agreement_events = (
            await async_session.execute(
                select(
                    Agreement.id,
                    Agreement.exchange_address,
                    Agreement.order_id,
                    Agreement.agreement_id,
                    Agreement.agreement_timestamp,
                    Agreement.buyer_address,
                )
                .outerjoin(Order, Agreement.unique_order_id == Order.unique_order_id)
                .where(Order.token_address == token_address)
                .where(
                    or_(
                        Agreement.buyer_address == account_address,
                        Agreement.seller_address == account_address,
                    )
                )
                .where(Agreement.status == AgreementStatus.PENDING.value)
            )
        ).all()

        settlement_list = []
        for (
            id,
            exchange_contract_address,
            order_id,
            agreement_id,
            agreement_timestamp,
            buyer_address,
        ) in _agreement_events:
            exchange_contract = AsyncContract.get_contract(
                contract_name="IbetExchange", address=exchange_contract_address
            )
            agreement = await AsyncContract.call_function(
                contract=exchange_contract,
                function_name="getAgreement",
                args=(
                    order_id,
                    agreement_id,
                ),
            )
            _settlement = {
                "token": {"token_address": token_address},
                "agreement": {
                    "exchange_address": exchange_contract_address,
                    "order_id": order_id,
                    "agreement_id": agreement_id,
                    "amount": agreement[1],
                    "price": agreement[2],
                    "is_buy": buyer_address == account_address,
                    "canceled": agreement[3],
                    "agreement_timestamp": "{}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
                        agreement_timestamp.year,
                        agreement_timestamp.month,
                        agreement_timestamp.day,
                        agreement_timestamp.hour,
                        agreement_timestamp.minute,
                        agreement_timestamp.second,
                    ),
                },
                "sort_id": id,
            }
            settlement_list.append(_settlement)

        return settlement_list

    @staticmethod
    async def get_complete_list_filtered_by_token(
        async_session: AsyncSession,
        token_address,
        account_address,
        include_canceled_items,
    ):
        """List all orders that have been settled (DEX)"""

        # Filter agreement events (settlement completed) generated from account_address
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

        if include_canceled_items is not None and include_canceled_items is True:
            _agreement_events = (
                await async_session.execute(
                    stmt.where(
                        or_(
                            Agreement.status == AgreementStatus.DONE.value,
                            Agreement.status == AgreementStatus.CANCELED.value,
                        )
                    )
                )
            ).all()
        else:  # default
            _agreement_events = (
                await async_session.execute(
                    stmt.where(Agreement.status == AgreementStatus.DONE.value)
                )
            ).all()

        complete_list = []
        for (
            id,
            exchange_contract_address,
            order_id,
            agreement_id,
            agreement_timestamp,
            settlement_timestamp,
            buyer_address,
        ) in _agreement_events:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = (
                    "{}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
                        settlement_timestamp.year,
                        settlement_timestamp.month,
                        settlement_timestamp.day,
                        settlement_timestamp.hour,
                        settlement_timestamp.minute,
                        settlement_timestamp.second,
                    )
                )
            else:
                settlement_timestamp_jp = ""
            exchange_contract = AsyncContract.get_contract(
                contract_name="IbetExchange", address=exchange_contract_address
            )
            agreement = await AsyncContract.call_function(
                contract=exchange_contract,
                function_name="getAgreement",
                args=(
                    order_id,
                    agreement_id,
                ),
            )
            _complete = {
                "token": {"token_address": token_address},
                "agreement": {
                    "exchange_address": exchange_contract_address,
                    "order_id": order_id,
                    "agreement_id": agreement_id,
                    "amount": agreement[1],
                    "price": agreement[2],
                    "is_buy": buyer_address == account_address,
                    "canceled": agreement[3],
                    "agreement_timestamp": "{}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
                        agreement_timestamp.year,
                        agreement_timestamp.month,
                        agreement_timestamp.day,
                        agreement_timestamp.hour,
                        agreement_timestamp.minute,
                        agreement_timestamp.second,
                    ),
                },
                "settlement_timestamp": settlement_timestamp_jp,
                "sort_id": id,
            }
            complete_list.append(_complete)

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
    ):
        if (
            config.MEMBERSHIP_TOKEN_ENABLED is False
            or config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS is None
        ):
            raise NotSupportedError(method="GET", url=req.url.path)

        order_list = []
        settlement_list = []
        complete_list = []

        for account_address in request_query.account_address_list:
            try:
                # order_list
                order_list.extend(
                    await self.get_order_list(
                        async_session=async_session,
                        token_model=MembershipToken,
                        exchange_contract_address=config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                        include_canceled_items=request_query.include_canceled_items,
                    )
                )
                order_list = sorted(order_list, key=lambda x: x["sort_id"])

                # settlement_list
                settlement_list.extend(
                    await self.get_settlement_list(
                        async_session=async_session,
                        token_model=MembershipToken,
                        exchange_contract_address=config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                    )
                )
                settlement_list = sorted(settlement_list, key=lambda x: x["sort_id"])

                # complete_list
                complete_list.extend(
                    await self.get_complete_list(
                        async_session=async_session,
                        token_model=MembershipToken,
                        exchange_contract_address=config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                        include_canceled_items=request_query.include_canceled_items,
                    )
                )
                complete_list = sorted(complete_list, key=lambda x: x["sort_id"])
            except Exception as err:
                LOG.exception(err)

        response_json = {
            "order_list": order_list,
            "settlement_list": settlement_list,
            "complete_list": complete_list,
        }

        return response_json


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
    order_list_res: ListAllOrderListResponse[RetrieveMembershipTokenResponse] = Depends(
        MembershipOrderList()
    ),
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
    ):
        if (
            config.COUPON_TOKEN_ENABLED is False
            or config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS is None
        ):
            raise NotSupportedError(method="GET", url=req.url.path)

        order_list = []
        settlement_list = []
        complete_list = []

        for account_address in request_query.account_address_list:
            try:
                # order_list
                order_list.extend(
                    await self.get_order_list(
                        async_session=async_session,
                        token_model=CouponToken,
                        exchange_contract_address=config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                        include_canceled_items=request_query.include_canceled_items,
                    )
                )
                order_list = sorted(order_list, key=lambda x: x["sort_id"])

                # settlement_list
                settlement_list.extend(
                    await self.get_settlement_list(
                        async_session=async_session,
                        token_model=CouponToken,
                        exchange_contract_address=config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                    )
                )
                settlement_list = sorted(settlement_list, key=lambda x: x["sort_id"])

                # complete_list
                complete_list.extend(
                    await self.get_complete_list(
                        async_session=async_session,
                        token_model=CouponToken,
                        exchange_contract_address=config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                        include_canceled_items=request_query.include_canceled_items,
                    )
                )
                complete_list = sorted(complete_list, key=lambda x: x["sort_id"])
            except Exception as err:
                LOG.exception(err)

        response_json = {
            "order_list": order_list,
            "settlement_list": settlement_list,
            "complete_list": complete_list,
        }

        return response_json


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
    order_list_res: ListAllOrderListResponse[RetrieveCouponTokenResponse] = Depends(
        CouponOrderList()
    ),
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
    ):
        order_list = []
        settlement_list = []
        complete_list = []
        for account_address in request_query.account_address_list:
            try:
                # order_list
                order_list.extend(
                    await self.get_order_list_filtered_by_token(
                        async_session=async_session,
                        token_address=token_address,
                        account_address=account_address,
                        include_canceled_items=request_query.include_canceled_items,
                    )
                )
                order_list = sorted(order_list, key=lambda x: x["sort_id"])

                # settlement_list
                settlement_list.extend(
                    await self.get_settlement_list_filtered_by_token(
                        async_session=async_session,
                        token_address=token_address,
                        account_address=account_address,
                    )
                )
                settlement_list = sorted(settlement_list, key=lambda x: x["sort_id"])

                # complete_list
                complete_list.extend(
                    await self.get_complete_list_filtered_by_token(
                        async_session=async_session,
                        token_address=token_address,
                        account_address=account_address,
                        include_canceled_items=request_query.include_canceled_items,
                    )
                )
                complete_list = sorted(complete_list, key=lambda x: x["sort_id"])
            except Exception as err:
                LOG.exception(err)

        response_json = {
            "order_list": order_list,
            "settlement_list": settlement_list,
            "complete_list": complete_list,
        }

        return response_json


@router.get(
    "/{token_address}",
    summary="Order History filtered by token (Bulk Get)",
    operation_id="IbetExchange",
    response_model=GenericSuccessResponse[ListAllOrderListResponse[TokenAddress]],
    responses=get_routers_responses(NotSupportedError, InvalidParameterError),
)
async def list_all_order_history_by_token_address(
    order_list_res: ListAllOrderListResponse[TokenAddress] = Depends(OrderList()),
):
    """
    Returns order history.
    """
    return json_response({**SuccessResponse.default(), "data": order_list_res})
