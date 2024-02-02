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

from typing import Sequence

from eth_utils import to_checksum_address
from fastapi import APIRouter, Depends, Request
from sqlalchemy import and_, desc, func, select

from app import config, log
from app.contracts import AsyncContract
from app.database import DBAsyncSession
from app.errors import InvalidParameterError, NotSupportedError, ServiceUnavailable
from app.model.db import AgreementStatus, IDXAgreement as Agreement, IDXOrder as Order
from app.model.schema import (
    ListAllLastPriceQuery,
    ListAllLastPriceResponse,
    ListAllOrderBookItemResponse,
    ListAllOrderBookQuery,
    ListAllTickQuery,
    ListAllTicksResponse,
    RetrieveAgreementDetailResponse,
    RetrieveAgreementQuery,
)
from app.model.schema.base import GenericSuccessResponse, SuccessResponse
from app.utils.asyncio_utils import SemaphoreTaskGroup
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()

router = APIRouter(prefix="/DEX/Market", tags=["dex"])


# /DEX/Market/Agreement
@router.get(
    "/Agreement",
    summary="Agreement Details",
    operation_id="GetAgreement",
    response_model=GenericSuccessResponse[RetrieveAgreementDetailResponse],
    responses=get_routers_responses(NotSupportedError, InvalidParameterError),
)
async def retrieve_agreement(
    req: Request, request_query: RetrieveAgreementQuery = Depends()
):
    """
    Returns agreement information of given id.
    """
    if (
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS is None
        and config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS is None
    ):
        raise NotSupportedError(method="GET", url=req.url.path)

    # リクエストから情報を抽出
    order_id = request_query.order_id
    agreement_id = request_query.agreement_id
    exchange_address = to_checksum_address(request_query.exchange_address)

    # 取引コントラクトに接続
    address_list = [
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
    ]
    address_list = [
        to_checksum_address(address) for address in address_list if address is not None
    ]
    if exchange_address not in address_list:
        raise InvalidParameterError(description="Invalid Address")
    exchange_contract = AsyncContract.get_contract("IbetExchange", exchange_address)

    # 注文情報の取得
    (
        maker_address,
        token_address,
        _,
        _,
        is_buy,
        _,
        _,
    ) = await AsyncContract.call_function(
        contract=exchange_contract, function_name="getOrder", args=(order_id,)
    )

    if maker_address == config.ZERO_ADDRESS:
        raise InvalidParameterError("Data not found")

    # 約定情報の取得
    (
        taker_address,
        amount,
        price,
        canceled,
        paid,
        expiry,
    ) = await AsyncContract.call_function(
        contract=exchange_contract,
        function_name="getAgreement",
        args=(
            order_id,
            agreement_id,
        ),
    )

    if taker_address == config.ZERO_ADDRESS:
        raise InvalidParameterError("Data not found")

    if is_buy:
        buyer_address = maker_address
        seller_address = taker_address
    else:
        buyer_address = taker_address
        seller_address = maker_address

    res_data = {
        "token_address": token_address,  # トークンアドレス
        "counterpart": taker_address,  # Takerのアドレス
        "buyer_address": buyer_address,  # 買い手EOA
        "seller_address": seller_address,  # 売り手EOA
        "amount": amount,  # 約定数量
        "price": price,  # 約定単価
        "canceled": canceled,  # 約定取消フラグ
        "paid": paid,  # 支払済フラグ
        "expiry": expiry,  # 有効期限（unixtime）
    }
    return json_response({**SuccessResponse.default(), "data": res_data})


# /DEX/Market/OrderBook/Membership
@router.get(
    "/OrderBook/Membership",
    summary="Membership Token Order Book",
    operation_id="MembershipOrderBook",
    response_model=GenericSuccessResponse[ListAllOrderBookItemResponse],
    responses=get_routers_responses(NotSupportedError),
)
async def list_all_membership_order_book(
    async_session: DBAsyncSession,
    req: Request,
    request_query: ListAllOrderBookQuery = Depends(),
):
    """
    [Membership]Returns orderbook of given token.
    """
    if (
        config.MEMBERSHIP_TOKEN_ENABLED is False
        or config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS is None
    ):
        raise NotSupportedError(method="GET", url=req.url.path)

    # 入力値を抽出
    token_address = to_checksum_address(request_query.token_address)

    # 注文を抽出
    is_buy = request_query.order_type == "buy"  # 相対注文が買い注文かどうか
    exchange_address = to_checksum_address(
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS
    )

    stmt = (
        select(
            Order.order_id,
            Order.amount,
            Order.price,
            Order.exchange_address,
            Order.account_address,
            func.sum(Agreement.amount),
        )
        .outerjoin(
            Agreement,
            and_(
                Order.unique_order_id == Agreement.unique_order_id,
                Agreement.status != AgreementStatus.CANCELED.value,
            ),  # 約定取消時に注文中状態に戻るため約定数量には取消分を含めない
        )
        .group_by(
            Order.order_id,
            Order.amount,
            Order.price,
            Order.exchange_address,
            Order.account_address,
        )
        .where(Order.exchange_address == exchange_address)
        .where(Order.token_address == token_address)
        .where(Order.agent_address == request_query.exchange_agent_address)
        .where(Order.is_cancelled == False)  # 未キャンセル
    )

    if is_buy:  # 買注文
        stmt = stmt.where(Order.is_buy == False)
    else:  # 売注文
        stmt = stmt.where(Order.is_buy == True)

    # account_address（注文者のアドレス）指定時は注文者以外の注文板を取得する
    # account_address（注文者のアドレス）未指定時は全ての注文板を取得する
    if request_query.account_address is not None:
        account_address = to_checksum_address(request_query.account_address)
        orders = (
            await async_session.execute(
                stmt.where(Order.account_address != account_address)
            )
        ).all()
    else:
        orders = (await async_session.execute(stmt)).all()

    # レスポンス用の注文一覧を構築
    order_list_tmp = []
    for (
        order_id,
        amount,
        price,
        exchange_address,
        account_address,
        agreement_amount,
    ) in orders:
        # 残存注文数量 = 発注数量 - 約定済み数量
        if not (agreement_amount is None):
            amount -= int(agreement_amount)
        # 残注文ありの注文のみを抽出する
        if amount <= 0:
            continue

        order_list_tmp.append(
            {
                "exchange_address": exchange_address,
                "order_id": order_id,
                "price": price,
                "amount": amount,
                "account_address": account_address,
            }
        )

    # 買い注文の場合は価格で昇順に、売り注文の場合は価格で降順にソートする
    if request_query.order_type == "buy":
        order_list = sorted(order_list_tmp, key=lambda x: x["price"])
    else:
        order_list = sorted(order_list_tmp, key=lambda x: -x["price"])

    return json_response({**SuccessResponse.default(), "data": order_list})


# /DEX/Market/LastPrice/Membership
@router.get(
    "/LastPrice/Membership",
    summary="Membership Token Last Price (Bulk Get)",
    operation_id="MembershipLastPrice",
    response_model=GenericSuccessResponse[ListAllLastPriceResponse],
    responses=get_routers_responses(NotSupportedError),
)
async def list_all_membership_last_price(
    req: Request, request_query: ListAllLastPriceQuery = Depends()
):
    """
    [Membership]Returns last price of given token.
    """
    if (
        config.MEMBERSHIP_TOKEN_ENABLED is False
        or config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS is None
    ):
        raise NotSupportedError(method="GET", url=req.url.path)

    exchange_contract = AsyncContract.get_contract(
        "IbetExchange", config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS
    )

    try:
        tasks = await SemaphoreTaskGroup.run(
            *[
                AsyncContract.call_function(
                    contract=exchange_contract,
                    function_name="lastPrice",
                    args=(to_checksum_address(token_address),),
                    default_returns=0,
                )
                for token_address in request_query.address_list
            ],
            max_concurrency=3
        )
        last_prices = [task.result() for task in tasks]
    except ExceptionGroup:
        raise ServiceUnavailable from None

    price_list = [
        {"token_address": token_address, "last_price": last_price}
        for token_address, last_price in zip(request_query.address_list, last_prices)
    ]
    return json_response({**SuccessResponse.default(), "data": price_list})


# /DEX/Market/Tick/Membership
@router.get(
    "/Tick/Membership",
    summary="Membership Token Tick (Bulk Get)",
    operation_id="MembershipTick",
    response_model=GenericSuccessResponse[ListAllTicksResponse],
    responses=get_routers_responses(NotSupportedError),
)
async def list_all_membership_tick(
    async_session: DBAsyncSession,
    req: Request,
    request_query: ListAllTickQuery = Depends(),
):
    """
    [Membership]Returns ticks of given token.
    """
    if (
        config.MEMBERSHIP_TOKEN_ENABLED is False
        or config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS is None
    ):
        raise NotSupportedError(method="GET", url=req.url.path)

    tick_list = []
    # TokenごとにTickを取得
    for token_address in request_query.address_list:
        token = to_checksum_address(token_address)
        try:
            entries: Sequence[tuple[Agreement, Order]] = (
                (
                    await async_session.execute(
                        select(Agreement, Order)
                        .join(Order, Agreement.unique_order_id == Order.unique_order_id)
                        .where(
                            and_(
                                Order.token_address == token,
                                Agreement.status == AgreementStatus.DONE.value,
                            )
                        )
                        .order_by(desc(Agreement.settlement_timestamp))
                    )
                )
                .tuples()
                .all()
            )
            _tick = [
                {
                    "block_timestamp": "{}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
                        entry[0].settlement_timestamp.year,
                        entry[0].settlement_timestamp.month,
                        entry[0].settlement_timestamp.day,
                        entry[0].settlement_timestamp.hour,
                        entry[0].settlement_timestamp.minute,
                        entry[0].settlement_timestamp.second,
                    ),
                    "buy_address": entry[0].buyer_address,
                    "sell_address": entry[0].seller_address,
                    "order_id": entry[0].order_id,
                    "agreement_id": entry[0].agreement_id,
                    "price": entry[1].price,
                    "amount": entry[0].amount,
                }
                for entry in entries
            ]
            tick_list.append({"token_address": token_address, "tick": _tick})
        except Exception as e:
            LOG.error(e)
            tick_list = []

    return json_response({**SuccessResponse.default(), "data": tick_list})


# /DEX/Market/OrderBook/Coupon
@router.get(
    "/OrderBook/Coupon",
    summary="Coupon Token Order Book",
    operation_id="CouponOrderBook",
    response_model=GenericSuccessResponse[ListAllOrderBookItemResponse],
    responses=get_routers_responses(NotSupportedError),
)
async def list_all_coupon_order_book(
    async_session: DBAsyncSession,
    req: Request,
    request_query: ListAllOrderBookQuery = Depends(),
):
    """
    [Coupon]Returns orderbook of given token.
    """
    if (
        config.COUPON_TOKEN_ENABLED is False
        or config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS is None
    ):
        raise NotSupportedError(method="GET", url=req.url.path)

    # 入力値を抽出
    token_address = to_checksum_address(request_query.token_address)

    # 注文を抽出
    is_buy = request_query.order_type == "buy"  # 相対注文が買い注文かどうか
    exchange_address = to_checksum_address(config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS)

    stmt = (
        select(
            Order.order_id,
            Order.amount,
            Order.price,
            Order.exchange_address,
            Order.account_address,
            func.sum(Agreement.amount),
        )
        .outerjoin(
            Agreement,
            and_(
                Order.unique_order_id == Agreement.unique_order_id,
                Agreement.status != AgreementStatus.CANCELED.value,
            ),  # 約定取消時に注文中状態に戻るため約定数量には取消分を含めない
        )
        .group_by(
            Order.order_id,
            Order.amount,
            Order.price,
            Order.exchange_address,
            Order.account_address,
        )
        .where(Order.exchange_address == exchange_address)
        .where(Order.token_address == token_address)
        .where(Order.agent_address == request_query.exchange_agent_address)
        .where(Order.is_cancelled == False)  # 未キャンセル
    )

    if is_buy:  # 買注文
        stmt = stmt.where(Order.is_buy == False)
    else:  # 売注文
        stmt = stmt.where(Order.is_buy == True)

    # account_address（注文者のアドレス）指定時は注文者以外の注文板を取得する
    # account_address（注文者のアドレス）未指定時は全ての注文板を取得する
    if request_query.account_address is not None:
        account_address = to_checksum_address(request_query.account_address)
        orders = (
            await async_session.execute(
                stmt.where(Order.account_address != account_address)
            )
        ).all()
    else:
        orders = (await async_session.execute(stmt)).all()

    # レスポンス用の注文一覧を構築
    order_list_tmp = []
    for (
        order_id,
        amount,
        price,
        exchange_address,
        account_address,
        agreement_amount,
    ) in orders:
        # 残存注文数量 = 発注数量 - 約定済み数量
        if not (agreement_amount is None):
            amount -= int(agreement_amount)
        # 残注文ありの注文のみを抽出する
        if amount <= 0:
            continue

        order_list_tmp.append(
            {
                "exchange_address": exchange_address,
                "order_id": order_id,
                "price": price,
                "amount": amount,
                "account_address": account_address,
            }
        )

    # 買い注文の場合は価格で昇順に、売り注文の場合は価格で降順にソートする
    if request_query.order_type == "buy":
        order_list = sorted(order_list_tmp, key=lambda x: x["price"])
    else:
        order_list = sorted(order_list_tmp, key=lambda x: -x["price"])

    return json_response({**SuccessResponse.default(), "data": order_list})


# /DEX/Market/LastPrice/Coupon
@router.get(
    "/LastPrice/Coupon",
    summary="Coupon Token Last Price (Bulk Get)",
    operation_id="CouponLastPrice",
    response_model=GenericSuccessResponse[ListAllLastPriceResponse],
    responses=get_routers_responses(NotSupportedError),
)
async def list_all_coupon_last_price(
    req: Request, request_query: ListAllLastPriceQuery = Depends()
):
    """
    [Coupon]Returns last price of given token.
    """
    if (
        config.COUPON_TOKEN_ENABLED is False
        or config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS is None
    ):
        raise NotSupportedError(method="GET", url=req.url.path)

    exchange_contract = AsyncContract.get_contract(
        "IbetExchange", config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS
    )

    try:
        tasks = await SemaphoreTaskGroup.run(
            *[
                AsyncContract.call_function(
                    contract=exchange_contract,
                    function_name="lastPrice",
                    args=(to_checksum_address(token_address),),
                    default_returns=0,
                )
                for token_address in request_query.address_list
            ],
            max_concurrency=3
        )
        last_prices = [task.result() for task in tasks]
    except ExceptionGroup:
        raise ServiceUnavailable from None
    price_list = [
        {
            "token_address": token_address,
            "last_price": last_price,
        }
        for token_address, last_price in zip(request_query.address_list, last_prices)
    ]
    return json_response({**SuccessResponse.default(), "data": price_list})


# /DEX/Market/Tick/Coupon
@router.get(
    "/Tick/Coupon",
    summary="Coupon Token Tick (Bulk Get)",
    operation_id="CouponTick",
    response_model=GenericSuccessResponse[ListAllTicksResponse],
    responses=get_routers_responses(NotSupportedError),
)
async def list_all_coupon_tick(
    async_session: DBAsyncSession,
    req: Request,
    request_query: ListAllTickQuery = Depends(),
):
    """
    [Coupon]Returns ticks of given token.
    """
    if (
        config.COUPON_TOKEN_ENABLED is False
        or config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS is None
    ):
        raise NotSupportedError(method="GET", url=req.url.path)

    tick_list = []
    # TokenごとにTickを取得
    for token_address in request_query.address_list:
        token = to_checksum_address(token_address)
        try:
            entries: Sequence[tuple[Agreement, Order]] = (
                (
                    await async_session.execute(
                        select(Agreement, Order)
                        .join(Order, Agreement.unique_order_id == Order.unique_order_id)
                        .where(
                            and_(
                                Order.token_address == token,
                                Agreement.status == AgreementStatus.DONE.value,
                            )
                        )
                        .order_by(desc(Agreement.settlement_timestamp))
                    )
                )
                .tuples()
                .all()
            )
            _tick = [
                {
                    "block_timestamp": "{}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
                        entry[0].settlement_timestamp.year,
                        entry[0].settlement_timestamp.month,
                        entry[0].settlement_timestamp.day,
                        entry[0].settlement_timestamp.hour,
                        entry[0].settlement_timestamp.minute,
                        entry[0].settlement_timestamp.second,
                    ),
                    "buy_address": entry[0].buyer_address,
                    "sell_address": entry[0].seller_address,
                    "order_id": entry[0].order_id,
                    "agreement_id": entry[0].agreement_id,
                    "price": entry[1].price,
                    "amount": entry[0].amount,
                }
                for entry in entries
            ]
            tick_list.append({"token_address": token_address, "tick": _tick})
        except Exception as e:
            LOG.error(e)
            tick_list = []

    return json_response({**SuccessResponse.default(), "data": tick_list})
