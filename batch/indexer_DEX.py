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
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.exceptions import ABIEventFunctionNotFound

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

import log

from app.config import (
    IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS,
    IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
    TZ,
)
from app.contracts import AsyncContract
from app.database import BatchAsyncSessionLocal
from app.errors import ServiceUnavailable
from app.model.db import (
    AgreementStatus,
    IDXAgreement as Agreement,
    IDXOrder as Order,
    Listing,
)
from app.utils.web3_utils import AsyncWeb3Wrapper

local_tz = ZoneInfo(TZ)

process_name = "INDEXER-DEX"
LOG = log.get_logger(process_name=process_name)

async_web3 = AsyncWeb3Wrapper()


class Processor:
    """Processor for indexing IbetExchange events"""

    latest_block = 0

    def __init__(self):
        self.exchange_list = []
        # MEMBERSHIP Exchange
        if IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS is not None:
            membership_exchange_contract = AsyncContract.get_contract(
                "IbetExchange", IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS
            )
            self.exchange_list.append(membership_exchange_contract)
        # COUPON Exchange
        if IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS is not None:
            coupon_exchange_contract = AsyncContract.get_contract(
                "IbetExchange", IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS
            )
            self.exchange_list.append(coupon_exchange_contract)

    @staticmethod
    def __get_db_session():
        return BatchAsyncSessionLocal()

    async def initial_sync(self):
        local_session = self.__get_db_session()
        latest_block_at_start = self.latest_block
        self.latest_block = await async_web3.eth.block_number
        try:
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

    async def __sync_all(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        LOG.info("Syncing from={}, to={}".format(block_from, block_to))
        await self.__sync_new_order(db_session, block_from, block_to)
        await self.__sync_cancel_order(db_session, block_from, block_to)
        await self.__sync_force_cancel_order(db_session, block_from, block_to)
        await self.__sync_agree(db_session, block_from, block_to)
        await self.__sync_settlement_ok(db_session, block_from, block_to)
        await self.__sync_settlement_ng(db_session, block_from, block_to)

    async def __sync_new_order(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        for exchange_contract in self.exchange_list:
            try:
                events = await exchange_contract.events.NewOrder.get_logs(
                    fromBlock=block_from, toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                for event in events:
                    args = event["args"]
                    if args["price"] > sys.maxsize or args["amount"] > sys.maxsize:
                        pass
                    else:
                        available_token = (
                            await db_session.scalars(
                                select(Listing)
                                .where(Listing.token_address == args["tokenAddress"])
                                .limit(1)
                            )
                        ).first()
                        transaction_hash = event["transactionHash"].hex()
                        order_timestamp = datetime.utcfromtimestamp(
                            (await async_web3.eth.get_block(event["blockNumber"]))[
                                "timestamp"
                            ]
                        )
                        if available_token is not None:
                            account_address = args["accountAddress"]
                            counterpart_address = ""
                            is_buy = args["isBuy"]

                            await self.__sink_on_new_order(
                                db_session=db_session,
                                transaction_hash=transaction_hash,
                                token_address=args["tokenAddress"],
                                exchange_address=exchange_contract.address,
                                order_id=args["orderId"],
                                account_address=account_address,
                                counterpart_address=counterpart_address,
                                is_buy=is_buy,
                                price=args["price"],
                                amount=args["amount"],
                                agent_address=args["agentAddress"],
                                order_timestamp=order_timestamp,
                            )
            except Exception as e:
                raise e

    async def __sync_cancel_order(self, db_session: AsyncSession, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                events = await exchange_contract.events.CancelOrder.get_logs(
                    fromBlock=block_from, toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                for event in events:
                    await self.__sink_on_cancel_order(
                        db_session=db_session,
                        exchange_address=exchange_contract.address,
                        order_id=event["args"]["orderId"],
                    )
            except Exception as e:
                raise e

    async def __sync_force_cancel_order(
        self, db_session: AsyncSession, block_from, block_to
    ):
        for exchange_contract in self.exchange_list:
            try:
                events = await exchange_contract.events.ForceCancelOrder.get_logs(
                    fromBlock=block_from, toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                for event in events:
                    await self.__sink_on_force_cancel_order(
                        db_session=db_session,
                        exchange_address=exchange_contract.address,
                        order_id=event["args"]["orderId"],
                    )
            except Exception as e:
                raise e

    async def __sync_agree(self, db_session: AsyncSession, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                events = await exchange_contract.events.Agree.get_logs(
                    fromBlock=block_from, toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                for event in events:
                    args = event["args"]
                    if args["amount"] > sys.maxsize:
                        pass
                    else:
                        order_id = args["orderId"]
                        orderbook = await AsyncContract.call_function(
                            contract=exchange_contract,
                            function_name="getOrder",
                            args=(order_id,),
                        )
                        is_buy = orderbook[4]
                        if is_buy:
                            counterpart_address = args["sellAddress"]
                        else:
                            counterpart_address = args["buyAddress"]
                        transaction_hash = event["transactionHash"].hex()
                        agreement_timestamp = datetime.utcfromtimestamp(
                            (await async_web3.eth.get_block(event["blockNumber"]))[
                                "timestamp"
                            ]
                        )
                        await self.__sink_on_agree(
                            db_session=db_session,
                            transaction_hash=transaction_hash,
                            exchange_address=exchange_contract.address,
                            order_id=args["orderId"],
                            agreement_id=args["agreementId"],
                            buyer_address=args["buyAddress"],
                            seller_address=args["sellAddress"],
                            counterpart_address=counterpart_address,
                            amount=args["amount"],
                            agreement_timestamp=agreement_timestamp,
                        )
            except Exception as e:
                raise e

    async def __sync_settlement_ok(
        self, db_session: AsyncSession, block_from, block_to
    ):
        for exchange_contract in self.exchange_list:
            try:
                events = await exchange_contract.events.SettlementOK.get_logs(
                    fromBlock=block_from, toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                for event in events:
                    args = event["args"]
                    settlement_timestamp = datetime.utcfromtimestamp(
                        (await async_web3.eth.get_block(event["blockNumber"]))[
                            "timestamp"
                        ]
                    )
                    await self.__sink_on_settlement_ok(
                        db_session=db_session,
                        exchange_address=exchange_contract.address,
                        order_id=args["orderId"],
                        agreement_id=args["agreementId"],
                        settlement_timestamp=settlement_timestamp,
                    )
            except Exception as e:
                raise e

    async def __sync_settlement_ng(
        self, db_session: AsyncSession, block_from, block_to
    ):
        for exchange_contract in self.exchange_list:
            try:
                events = await exchange_contract.events.SettlementNG.get_logs(
                    fromBlock=block_from, toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                for event in events:
                    args = event["args"]
                    await self.__sink_on_settlement_ng(
                        db_session=db_session,
                        exchange_address=exchange_contract.address,
                        order_id=args["orderId"],
                        agreement_id=args["agreementId"],
                    )
            except Exception as e:
                raise e

    async def __sink_on_new_order(
        self,
        db_session: AsyncSession,
        transaction_hash: str,
        token_address: str,
        exchange_address: str,
        order_id: int,
        account_address: str,
        counterpart_address: str,
        is_buy: bool,
        price: int,
        amount: int,
        agent_address: str,
        order_timestamp: datetime,
    ):
        order = await self.__get_order(
            db_session=db_session, exchange_address=exchange_address, order_id=order_id
        )
        if order is None:
            LOG.debug(
                f"NewOrder: exchange_address={exchange_address}, order_id={order_id}"
            )
            order = Order()
            order.transaction_hash = transaction_hash
            order.token_address = token_address
            order.exchange_address = exchange_address
            order.order_id = order_id
            order.unique_order_id = exchange_address + "_" + str(order_id)
            order.account_address = account_address
            order.counterpart_address = counterpart_address
            order.is_buy = is_buy
            order.price = price
            order.amount = amount
            order.agent_address = agent_address
            order.is_cancelled = False
            order.order_timestamp = order_timestamp
            await db_session.merge(order)

    async def __sink_on_cancel_order(
        self, db_session: AsyncSession, exchange_address: str, order_id: int
    ):
        order = await self.__get_order(
            db_session=db_session, exchange_address=exchange_address, order_id=order_id
        )
        if order is not None:
            LOG.debug(
                f"CancelOrder: exchange_address={exchange_address}, order_id={order_id}"
            )
            order.is_cancelled = True

    async def __sink_on_force_cancel_order(
        self, db_session: AsyncSession, exchange_address: str, order_id: int
    ):
        order = await self.__get_order(
            db_session=db_session, exchange_address=exchange_address, order_id=order_id
        )
        if order is not None:
            LOG.debug(
                f"ForceCancelOrder: exchange_address={exchange_address}, order_id={order_id}"
            )
            order.is_cancelled = True

    async def __sink_on_agree(
        self,
        db_session: AsyncSession,
        transaction_hash: str,
        exchange_address: str,
        order_id: int,
        agreement_id: int,
        buyer_address: str,
        seller_address: str,
        counterpart_address: str,
        amount: int,
        agreement_timestamp: datetime,
    ):
        agreement = await self.__get_agreement(
            db_session=db_session,
            exchange_address=exchange_address,
            order_id=order_id,
            agreement_id=agreement_id,
        )
        if agreement is None:
            LOG.debug(
                f"Agree: exchange_address={exchange_address}, orderId={order_id}, agreementId={agreement_id}"
            )
            agreement = Agreement()
            agreement.transaction_hash = transaction_hash
            agreement.exchange_address = exchange_address
            agreement.order_id = order_id
            agreement.agreement_id = agreement_id
            agreement.unique_order_id = exchange_address + "_" + str(order_id)
            agreement.buyer_address = buyer_address
            agreement.seller_address = seller_address
            agreement.counterpart_address = counterpart_address
            agreement.amount = amount
            agreement.status = AgreementStatus.PENDING.value
            agreement.agreement_timestamp = agreement_timestamp
            await db_session.merge(agreement)

    async def __sink_on_settlement_ok(
        self,
        db_session: AsyncSession,
        exchange_address: str,
        order_id: int,
        agreement_id: int,
        settlement_timestamp: datetime,
    ):
        agreement = await self.__get_agreement(
            db_session=db_session,
            exchange_address=exchange_address,
            order_id=order_id,
            agreement_id=agreement_id,
        )
        if agreement is not None:
            LOG.debug(
                f"SettlementOK: exchange_address={exchange_address}, orderId={order_id}, agreementId={agreement_id}"
            )
            agreement.status = AgreementStatus.DONE.value
            agreement.settlement_timestamp = settlement_timestamp

    async def __sink_on_settlement_ng(
        self,
        db_session: AsyncSession,
        exchange_address: str,
        order_id: int,
        agreement_id: int,
    ):
        agreement = await self.__get_agreement(
            db_session=db_session,
            exchange_address=exchange_address,
            order_id=order_id,
            agreement_id=agreement_id,
        )
        if agreement is not None:
            LOG.debug(
                f"SettlementNG: exchange_address={exchange_address}, orderId={order_id}, agreementId={agreement_id}"
            )
            agreement.status = AgreementStatus.CANCELED.value

    @staticmethod
    async def __get_order(
        db_session: AsyncSession, exchange_address: str, order_id: int
    ):
        return (
            await db_session.scalars(
                select(Order)
                .where(Order.exchange_address == exchange_address)
                .where(Order.order_id == order_id)
                .limit(1)
            )
        ).first()

    @staticmethod
    async def __get_agreement(
        db_session: AsyncSession,
        exchange_address: str,
        order_id: int,
        agreement_id: int,
    ):
        return (
            await db_session.scalars(
                select(Agreement)
                .where(Agreement.exchange_address == exchange_address)
                .where(Agreement.order_id == order_id)
                .where(Agreement.agreement_id == agreement_id)
                .limit(1)
            )
        ).first()


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

        await asyncio.sleep(1)

    while True:
        try:
            await processor.sync_new_logs()
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception("An exception occurred during event synchronization")

        await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
