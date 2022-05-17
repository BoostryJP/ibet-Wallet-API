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
import os
import sys
import time
from datetime import (
    datetime,
    timezone,
    timedelta
)

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from web3.exceptions import ABIEventFunctionNotFound

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app.config import (
    DATABASE_URL,
    IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
    IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
    IBET_CP_EXCHANGE_CONTRACT_ADDRESS,
    IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS
)
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.db import (
    IDXAgreement as Agreement,
    AgreementStatus,
    IDXOrder as Order,
    Listing
)
from app.utils.web3_utils import Web3Wrapper
import log

JST = timezone(timedelta(hours=+9), "JST")

process_name = "INDEXER-DEX"
LOG = log.get_logger(process_name=process_name)

web3 = Web3Wrapper()
db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    """Processor for indexing IbetExchange events"""
    latest_block = 0

    def __init__(self):
        self.exchange_list = []
        # 債券取引コントラクト登録
        if IBET_SB_EXCHANGE_CONTRACT_ADDRESS is not None:
            bond_exchange_contract = Contract.get_contract(
                "IbetExchange",
                IBET_SB_EXCHANGE_CONTRACT_ADDRESS
            )
            self.exchange_list.append(bond_exchange_contract)
        # 会員権取引コントラクト登録
        if IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS is not None:
            membership_exchange_contract = Contract.get_contract(
                "IbetExchange",
                IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS
            )
            self.exchange_list.append(membership_exchange_contract)
        # クーポン取引コントラクト登録
        if IBET_CP_EXCHANGE_CONTRACT_ADDRESS is not None:
            coupon_exchange_contract = Contract.get_contract(
                "IbetExchange",
                IBET_CP_EXCHANGE_CONTRACT_ADDRESS
            )
            self.exchange_list.append(coupon_exchange_contract)
        # 株式取引コントラクト登録
        if IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS is not None:
            self.share_exchange_contract = Contract.get_contract(
                "IbetExchange",
                IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS
            )
            self.exchange_list.append(self.share_exchange_contract)
        else:
            self.share_exchange_contract = ""

    @staticmethod
    def __get_db_session():
        return Session(autocommit=False, autoflush=True, bind=db_engine)

    def initial_sync(self):
        local_session = self.__get_db_session()
        latest_block_at_start = self.latest_block
        self.latest_block = web3.eth.blockNumber
        try:
            # Synchronize 1,000,000 blocks at a time
            _to_block = 999999
            _from_block = 0
            if self.latest_block > 999999:
                while _to_block < self.latest_block:
                    self.__sync_all(
                        db_session=local_session,
                        block_from=_from_block,
                        block_to=_to_block
                    )
                    _to_block += 1000000
                    _from_block += 1000000
                self.__sync_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=self.latest_block
                )
            else:
                self.__sync_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=self.latest_block
                )
            local_session.commit()
        except Exception as e:
            LOG.exception("An exception occurred during event synchronization")
            local_session.rollback()
            self.latest_block = latest_block_at_start
            raise e
        finally:
            local_session.close()

        LOG.info(f"<{process_name}> Initial sync has been completed")

    def sync_new_logs(self):
        local_session = self.__get_db_session()
        latest_block_at_start = self.latest_block
        try:
            blockTo = web3.eth.blockNumber
            if blockTo == self.latest_block:
                return

            self.__sync_all(
                db_session=local_session,
                block_from=self.latest_block + 1,
                block_to=blockTo
            )
            self.latest_block = blockTo
            local_session.commit()
        except Exception as e:
            LOG.exception("An exception occurred during event synchronization")
            local_session.rollback()
            self.latest_block = latest_block_at_start
            raise e
        finally:
            local_session.close()

    def __sync_all(self, db_session, block_from, block_to):
        LOG.info("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_new_order(db_session, block_from, block_to)
        self.__sync_cancel_order(db_session, block_from, block_to)
        self.__sync_agree(db_session, block_from, block_to)
        self.__sync_settlement_ok(db_session, block_from, block_to)
        self.__sync_settlement_ng(db_session, block_from, block_to)

    def __sync_new_order(self, db_session, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                events = exchange_contract.events.NewOrder.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                for event in events:
                    args = event["args"]
                    if args["price"] > sys.maxsize or args["amount"] > sys.maxsize:
                        pass
                    else:
                        available_token = db_session.query(Listing). \
                            filter(Listing.token_address == args["tokenAddress"]). \
                            first()
                        transaction_hash = event["transactionHash"].hex()
                        order_timestamp = datetime.fromtimestamp(
                            web3.eth.getBlock(event["blockNumber"])["timestamp"],
                            JST
                        )
                        if available_token is not None:
                            account_address = args["accountAddress"]
                            counterpart_address = ""
                            is_buy = args["isBuy"]

                            self.__sink_on_new_order(
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
                                order_timestamp=order_timestamp
                            )
            except Exception as e:
                raise e

    def __sync_cancel_order(self, db_session, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                events = exchange_contract.events.CancelOrder.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                for event in events:
                    self.__sink_on_cancel_order(
                        db_session=db_session,
                        exchange_address=exchange_contract.address,
                        order_id=event["args"]["orderId"]
                    )
            except Exception as e:
                raise e

    def __sync_agree(self, db_session, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                events = exchange_contract.events.Agree.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
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
                        orderbook = exchange_contract.functions.getOrder(order_id).call()
                        is_buy = orderbook[4]
                        if is_buy:
                            counterpart_address = args["sellAddress"]
                        else:
                            counterpart_address = args["buyAddress"]
                        transaction_hash = event["transactionHash"].hex()
                        agreement_timestamp = datetime.fromtimestamp(
                            web3.eth.getBlock(event["blockNumber"])["timestamp"],
                            JST
                        )
                        self.__sink_on_agree(
                            db_session=db_session,
                            transaction_hash=transaction_hash,
                            exchange_address=exchange_contract.address,
                            order_id=args["orderId"],
                            agreement_id=args["agreementId"],
                            buyer_address=args["buyAddress"],
                            seller_address=args["sellAddress"],
                            counterpart_address=counterpart_address,
                            amount=args["amount"],
                            agreement_timestamp=agreement_timestamp
                        )
            except Exception as e:
                raise e

    def __sync_settlement_ok(self, db_session, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                events = exchange_contract.events.SettlementOK.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                for event in events:
                    args = event["args"]
                    settlement_timestamp = datetime.fromtimestamp(
                        web3.eth.getBlock(event["blockNumber"])["timestamp"],
                        JST
                    )
                    self.__sink_on_settlement_ok(
                        db_session=db_session,
                        exchange_address=exchange_contract.address,
                        order_id=args["orderId"],
                        agreement_id=args["agreementId"],
                        settlement_timestamp=settlement_timestamp
                    )
            except Exception as e:
                raise e

    def __sync_settlement_ng(self, db_session, block_from, block_to):
        for exchange_contract in self.exchange_list:
            try:
                events = exchange_contract.events.SettlementNG.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                for event in events:
                    args = event["args"]
                    self.__sink_on_settlement_ng(
                        db_session=db_session,
                        exchange_address=exchange_contract.address,
                        order_id=args["orderId"],
                        agreement_id=args["agreementId"]
                    )
            except Exception as e:
                raise e

    def __sink_on_new_order(self,
                            db_session: Session,
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
                            order_timestamp: datetime):
        order = self.__get_order(
            db_session=db_session,
            exchange_address=exchange_address,
            order_id=order_id
        )
        if order is None:
            LOG.debug(f"NewOrder: exchange_address={exchange_address}, order_id={order_id}")
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
            db_session.merge(order)

    def __sink_on_cancel_order(self,
                               db_session: Session,
                               exchange_address: str,
                               order_id: int):
        order = self.__get_order(
            db_session=db_session,
            exchange_address=exchange_address,
            order_id=order_id
        )
        if order is not None:
            LOG.debug(f"CancelOrder: exchange_address={exchange_address}, order_id={order_id}")
            order.is_cancelled = True

    def __sink_on_agree(self,
                        db_session: Session,
                        transaction_hash: str,
                        exchange_address: str,
                        order_id: int,
                        agreement_id: int,
                        buyer_address: str,
                        seller_address: str,
                        counterpart_address: str,
                        amount: int, agreement_timestamp: datetime):
        agreement = self.__get_agreement(
            db_session=db_session,
            exchange_address=exchange_address,
            order_id=order_id,
            agreement_id=agreement_id
        )
        if agreement is None:
            LOG.debug(f"Agree: exchange_address={exchange_address}, orderId={order_id}, agreementId={agreement_id}")
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
            db_session.merge(agreement)

    def __sink_on_settlement_ok(self,
                                db_session: Session,
                                exchange_address: str,
                                order_id: int,
                                agreement_id: int,
                                settlement_timestamp: datetime):
        agreement = self.__get_agreement(
            db_session=db_session,
            exchange_address=exchange_address,
            order_id=order_id,
            agreement_id=agreement_id
        )
        if agreement is not None:
            LOG.debug(
                f"SettlementOK: exchange_address={exchange_address}, orderId={order_id}, agreementId={agreement_id}")
            agreement.status = AgreementStatus.DONE.value
            agreement.settlement_timestamp = settlement_timestamp

    def __sink_on_settlement_ng(self,
                                db_session: Session,
                                exchange_address: str,
                                order_id: int,
                                agreement_id: int):
        agreement = self.__get_agreement(
            db_session=db_session,
            exchange_address=exchange_address,
            order_id=order_id,
            agreement_id=agreement_id
        )
        if agreement is not None:
            LOG.debug(
                f"SettlementNG: exchange_address={exchange_address}, orderId={order_id}, agreementId={agreement_id}")
            agreement.status = AgreementStatus.CANCELED.value

    @staticmethod
    def __get_order(db_session: Session,
                    exchange_address: str,
                    order_id: int):
        return db_session.query(Order). \
            filter(Order.exchange_address == exchange_address). \
            filter(Order.order_id == order_id). \
            first()

    @staticmethod
    def __get_agreement(db_session: Session,
                        exchange_address: str,
                        order_id: int,
                        agreement_id: int):
        return db_session.query(Agreement). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.order_id == order_id). \
            filter(Agreement.agreement_id == agreement_id). \
            first()


def main():
    LOG.info("Service started successfully")
    processor = Processor()
    processor.initial_sync()
    while True:
        try:
            processor.sync_new_logs()
            LOG.debug("Processed")
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception(ex)

        time.sleep(1)


if __name__ == "__main__":
    main()
