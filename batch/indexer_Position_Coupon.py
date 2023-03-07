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
from itertools import groupby
from typing import List, Optional

from eth_utils import to_checksum_address
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from web3.exceptions import ABIEventFunctionNotFound

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

import log

from app.config import DATABASE_URL, TOKEN_LIST_CONTRACT_ADDRESS, ZERO_ADDRESS
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.db import IDXPosition, IDXPositionCouponBlockNumber, Listing
from app.utils.web3_utils import Web3Wrapper

process_name = "INDEXER-POSITION-COUPON"
LOG = log.get_logger(process_name=process_name)

web3 = Web3Wrapper()
db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    """Processor for indexing Coupon balances"""

    class TargetTokenList:
        class TargetToken:
            """
            Attributes:
                token_contract: contract object
                exchange_address: address of associated exchange
                start_block_number(int): block number that the processor first reads
                cursor(int): pointer where next process should be start
            """

            def __init__(
                self, token_contract, exchange_address: str, block_number: int
            ):
                self.token_contract = token_contract
                self.exchange_address = exchange_address
                self.start_block_number = block_number
                self.cursor = block_number

        target_token_list: List[TargetToken]

        def __init__(self):
            self.target_token_list = []

        def append(self, token_contract, exchange_address: str, block_number: int):
            is_duplicate = False
            for i, t in enumerate(self.target_token_list):
                if t.token_contract.address == token_contract.address:
                    is_duplicate = True
                    if self.target_token_list[i].start_block_number > block_number:
                        self.target_token_list[i].start_block_number = block_number
                        self.target_token_list[i].cursor = block_number
            if not is_duplicate:
                target_token = self.TargetToken(
                    token_contract, exchange_address, block_number
                )
                self.target_token_list.append(target_token)

        def get_cursor(self, token_address: str) -> int:
            for t in self.target_token_list:
                if t.token_contract.address == token_address:
                    return t.cursor
            return 0

        def __iter__(self):
            return iter(self.target_token_list)

        def __len__(self):
            return len(self.target_token_list)

    class TargetExchangeList:
        class TargetExchange:
            """
            Attributes:
                exchange_address: contract address of exchange or escrow
                start_block_number(int): block number that the processor first reads
                cursor(int): pointer where next process should be start
            """

            def __init__(self, exchange_address: str, block_number: int):
                self.exchange_address = exchange_address
                self.start_block_number = block_number
                self.cursor = block_number

        target_exchange_list: List[TargetExchange]

        def __init__(self):
            self.target_exchange_list = []

        def append(self, exchange_address: str, block_number: int):
            is_duplicate = False
            for i, e in enumerate(self.target_exchange_list):
                if e.exchange_address == exchange_address:
                    is_duplicate = True
                    if self.target_exchange_list[i].start_block_number > block_number:
                        self.target_exchange_list[i].start_block_number = block_number
                        self.target_exchange_list[i].cursor = block_number
            if not is_duplicate:
                target_exchange = self.TargetExchange(exchange_address, block_number)
                self.target_exchange_list.append(target_exchange)

        def __iter__(self):
            return iter(self.target_exchange_list)

    token_list: TargetTokenList
    exchange_list: TargetExchangeList

    def __init__(self):
        self.token_list = self.TargetTokenList()
        self.exchange_list = self.TargetExchangeList()

    @staticmethod
    def __get_db_session():
        return Session(autocommit=False, autoflush=True, bind=db_engine)

    def initial_sync(self):
        local_session = self.__get_db_session()
        try:
            self.__get_contract_list(local_session)
            # Synchronize 1,000,000 blocks each
            # if some blocks have already synced, sync starting from next block
            latest_block = web3.eth.block_number
            _from_block = self.__get_oldest_cursor(self.token_list, latest_block)
            _to_block = 999999 + _from_block
            if latest_block > _to_block:
                while _to_block < latest_block:
                    self.__sync_all(
                        db_session=local_session,
                        block_to=_to_block,
                    )
                    _to_block += 1000000
                self.__sync_all(db_session=local_session, block_to=latest_block)
            else:
                self.__sync_all(db_session=local_session, block_to=latest_block)
            self.__set_idx_position_block_number(
                local_session, self.token_list, latest_block
            )
            local_session.commit()
        except Exception as e:
            local_session.rollback()
            raise e
        finally:
            local_session.close()
            self.token_list = self.TargetTokenList()
            self.exchange_list = self.TargetExchangeList()
        LOG.info("Initial sync has been completed")

    def sync_new_logs(self):
        local_session = self.__get_db_session()
        try:
            self.__get_contract_list(local_session)
            # Synchronize 1,000,000 blocks each
            # if some blocks have already synced, sync starting from next block
            latest_block = web3.eth.block_number
            _from_block = self.__get_oldest_cursor(self.token_list, latest_block)
            _to_block = 999999 + _from_block
            if latest_block > _to_block:
                while _to_block < latest_block:
                    self.__sync_all(
                        db_session=local_session,
                        block_to=_to_block,
                    )
                    _to_block += 1000000
                self.__sync_all(db_session=local_session, block_to=latest_block)
            else:
                self.__sync_all(db_session=local_session, block_to=latest_block)
            self.__set_idx_position_block_number(
                local_session, self.token_list, latest_block
            )
            local_session.commit()
        except Exception as e:
            local_session.rollback()
            raise e
        finally:
            local_session.close()
            self.token_list = self.TargetTokenList()
            self.exchange_list = self.TargetExchangeList()
        LOG.info("Sync job has been completed")

    def __get_contract_list(self, db_session: Session):
        self.token_list = self.TargetTokenList()
        self.exchange_list = self.TargetExchangeList()

        list_contract = Contract.get_contract(
            contract_name="TokenList", address=TOKEN_LIST_CONTRACT_ADDRESS
        )
        listed_tokens = db_session.query(Listing).all()

        _exchange_list_tmp = []
        for listed_token in listed_tokens:
            token_info = Contract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(listed_token.token_address,),
                default_returns=(ZERO_ADDRESS, "", ZERO_ADDRESS),
            )
            if token_info[1] == "IbetCoupon":
                token_contract = Contract.get_contract(
                    contract_name="IbetCoupon", address=listed_token.token_address
                )
                tradable_exchange_address = Contract.call_function(
                    contract=token_contract,
                    function_name="tradableExchange",
                    args=(),
                    default_returns=ZERO_ADDRESS,
                )
                synced_block_number = self.__get_idx_position_block_number(
                    db_session=db_session,
                    token_address=listed_token.token_address,
                    exchange_address=tradable_exchange_address,
                )
                block_from = synced_block_number + 1
                self.token_list.append(
                    token_contract, tradable_exchange_address, block_from
                )
                if tradable_exchange_address != ZERO_ADDRESS:
                    self.exchange_list.append(tradable_exchange_address, block_from)

    def __sync_all(self, db_session: Session, block_to: int):
        LOG.info("Syncing to={}".format(block_to))

        self.__sync_transfer(db_session, block_to)
        self.__sync_exchange(db_session, block_to)
        self.__sync_escrow(db_session, block_to)

        self.__update_cursor(block_to + 1)

    def __update_cursor(self, block_number):
        """Memorize the block number where next processing should start from

        :param block_number: block number to be set
        :return: None
        """
        for target in self.token_list:
            if block_number > target.start_block_number:
                target.cursor = block_number
        for exchange in self.exchange_list:
            if block_number > exchange.start_block_number:
                exchange.cursor = block_number

    def __sync_transfer(self, db_session: Session, block_to: int):
        """Sync Transfer Events

        :param db_session: ORM session
        :param block_to: To block
        :return: None
        """
        for target in self.token_list:
            token = target.token_contract
            block_from = target.cursor
            if block_from > block_to:
                continue
            try:
                events = token.events.Transfer.getLogs(
                    fromBlock=block_from, toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                accounts_filtered = self.remove_duplicate_event_by_token_account_desc(
                    events=events, account_keys=["from", "to"]
                )
                for _account in accounts_filtered:
                    if web3.eth.get_code(_account).hex() == "0x":
                        (
                            _balance,
                            _exchange_balance,
                            _exchange_commitment,
                        ) = self.__get_account_balance_all(token, _account)
                        self.__sink_on_position(
                            db_session=db_session,
                            token_address=to_checksum_address(token.address),
                            account_address=_account,
                            balance=_balance,
                            exchange_balance=_exchange_balance,
                            exchange_commitment=_exchange_commitment,
                        )
            except Exception as e:
                raise e

    def __sync_consume(self, db_session: Session, block_to: int):
        """Sync Consume Events

        :param db_session: ORM session
        :param block_to: To block
        :return: None
        """
        for target in self.token_list:
            token = target.token_contract
            block_from = target.cursor
            if block_from > block_to:
                continue
            try:
                events = token.events.Consume.getLogs(
                    fromBlock=block_from, toBlock=block_to
                )
            except ABIEventFunctionNotFound:
                events = []
            try:
                accounts_filtered = self.remove_duplicate_event_by_token_account_desc(
                    events=events, account_keys=["consumer"]
                )
                for consumer_address in accounts_filtered:
                    balance = self.__get_account_balance_token(token, consumer_address)
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=consumer_address,
                        balance=balance,
                    )
            except Exception as e:
                raise e

    def __sync_exchange(self, db_session: Session, block_to: int):
        """Sync Events from IbetExchange

        :param db_session: ORM session
        :param block_to: To block
        :return: None
        """
        for exchange in self.exchange_list:
            block_from = exchange.cursor
            if block_from > block_to:
                continue
            exchange_address = exchange.exchange_address
            try:
                exchange = Contract.get_contract(
                    contract_name="IbetExchange", address=exchange_address
                )

                account_list_tmp = []

                # NewOrder event
                try:
                    _event_list = exchange.events.NewOrder.getLogs(
                        fromBlock=block_from, toBlock=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("tokenAddress", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "accountAddress", ZERO_ADDRESS
                            ),
                        }
                    )

                # CancelOrder event
                try:
                    _event_list = exchange.events.CancelOrder.getLogs(
                        fromBlock=block_from, toBlock=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("tokenAddress", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "accountAddress", ZERO_ADDRESS
                            ),
                        }
                    )

                # ForceCancelOrder event
                try:
                    _event_list = exchange.events.ForceCancelOrder.getLogs(
                        fromBlock=block_from, toBlock=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("tokenAddress", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "accountAddress", ZERO_ADDRESS
                            ),
                        }
                    )

                # Agree event
                try:
                    _event_list = exchange.events.Agree.getLogs(
                        fromBlock=block_from, toBlock=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("tokenAddress", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "sellAddress", ZERO_ADDRESS
                            ),  # only seller has changed
                        }
                    )

                # SettlementOK event
                try:
                    _event_list = exchange.events.SettlementOK.getLogs(
                        fromBlock=block_from, toBlock=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("tokenAddress", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "buyAddress", ZERO_ADDRESS
                            ),
                        }
                    )
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "sellAddress", ZERO_ADDRESS
                            ),
                        }
                    )

                # SettlementNG event
                try:
                    _event_list = exchange.events.SettlementNG.getLogs(
                        fromBlock=block_from, toBlock=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("tokenAddress", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "sellAddress", ZERO_ADDRESS
                            ),  # only seller has changed
                        }
                    )

                # Make temporary list unique
                account_list_tmp.sort(
                    key=lambda x: (x["token_address"], x["account_address"])
                )
                account_list_unfiltered = []
                for k, g in groupby(
                    account_list_tmp,
                    lambda x: (x["token_address"], x["account_address"]),
                ):
                    account_list_unfiltered.append(
                        {"token_address": k[0], "account_address": k[1]}
                    )

                # Filter account_list by listed token
                token_address_list = [t.token_contract.address for t in self.token_list]
                account_list = []
                for _account in account_list_unfiltered:
                    if _account["token_address"] in token_address_list:
                        account_list.append(_account)

                # Update position
                for _account in account_list:
                    token_address = _account["token_address"]
                    account_address = _account["account_address"]
                    (
                        exchange_balance,
                        exchange_commitment,
                    ) = self.__get_account_balance_exchange(
                        exchange_address=exchange_address,
                        token_address=token_address,
                        account_address=account_address,
                    )
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=token_address,
                        account_address=account_address,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment,
                    )
            except Exception as e:
                raise e

    def __sync_escrow(self, db_session: Session, block_to: int):
        """Sync Events from IbetEscrow

        :param db_session: ORM session
        :param block_to: To block
        :return: None
        """
        for exchange in self.exchange_list:
            block_from = exchange.cursor
            if block_from > block_to:
                continue
            exchange_address = exchange.exchange_address
            try:
                escrow = Contract.get_contract("IbetEscrow", exchange_address)

                account_list_tmp = []

                # EscrowCreated event
                try:
                    _event_list = escrow.events.EscrowCreated.getLogs(
                        fromBlock=block_from, toBlock=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("token", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get(
                                "sender", ZERO_ADDRESS
                            ),  # only sender has changed
                        }
                    )

                # EscrowCanceled event
                try:
                    _event_list = escrow.events.EscrowCanceled.getLogs(
                        fromBlock=block_from, toBlock=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("token", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get(
                                "sender", ZERO_ADDRESS
                            ),  # only sender has changed
                        }
                    )

                # EscrowFinished event
                try:
                    _event_list = escrow.events.EscrowFinished.getLogs(
                        fromBlock=block_from, toBlock=block_to
                    )
                except ABIEventFunctionNotFound:
                    _event_list = []
                for _event in _event_list:
                    event_block_number = _event.get("blockNumber", block_from)
                    token_cursor = self.token_list.get_cursor(
                        _event["args"].get("token", ZERO_ADDRESS)
                    )
                    if event_block_number < token_cursor:
                        continue
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get(
                                "sender", ZERO_ADDRESS
                            ),
                        }
                    )
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get(
                                "recipient", ZERO_ADDRESS
                            ),
                        }
                    )

                # Make temporary list unique
                account_list_tmp.sort(
                    key=lambda x: (x["token_address"], x["account_address"])
                )
                account_list_unfiltered = []
                for k, g in groupby(
                    account_list_tmp,
                    lambda x: (x["token_address"], x["account_address"]),
                ):
                    account_list_unfiltered.append(
                        {"token_address": k[0], "account_address": k[1]}
                    )

                # Filter account_list by listed token
                token_address_list = [t.token_contract.address for t in self.token_list]
                account_list = []
                for _account in account_list_unfiltered:
                    if _account["token_address"] in token_address_list:
                        account_list.append(_account)

                # Update position
                for _account in account_list:
                    token_address = _account["token_address"]
                    account_address = _account["account_address"]
                    (
                        exchange_balance,
                        exchange_commitment,
                    ) = self.__get_account_balance_exchange(
                        exchange_address=exchange_address,
                        token_address=token_address,
                        account_address=account_address,
                    )
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=token_address,
                        account_address=account_address,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment,
                    )
            except Exception as e:
                raise e

    @staticmethod
    def __get_oldest_cursor(target_token_list: TargetTokenList, block_to: int) -> int:
        """Get the oldest block number for given target token list"""
        oldest_block_number = block_to
        if len(target_token_list) == 0:
            return 0
        for target_token in target_token_list:
            if target_token.cursor < oldest_block_number:
                oldest_block_number = target_token.cursor
        return oldest_block_number

    @staticmethod
    def __get_idx_position_block_number(
        db_session: Session, token_address: str, exchange_address: str
    ):
        """Get position index for Bond"""
        _idx_position_block_number = (
            db_session.query(IDXPositionCouponBlockNumber)
            .filter(IDXPositionCouponBlockNumber.token_address == token_address)
            .filter(IDXPositionCouponBlockNumber.exchange_address == exchange_address)
            .first()
        )
        if _idx_position_block_number is None:
            return -1
        else:
            return _idx_position_block_number.latest_block_number

    @staticmethod
    def __set_idx_position_block_number(
        db_session: Session, target_token_list: TargetTokenList, block_number: int
    ):
        """Set position index for Bond"""
        for target_token in target_token_list:
            _idx_position_block_number = (
                db_session.query(IDXPositionCouponBlockNumber)
                .filter(
                    IDXPositionCouponBlockNumber.token_address
                    == target_token.token_contract.address
                )
                .filter(
                    IDXPositionCouponBlockNumber.exchange_address
                    == target_token.exchange_address
                )
                .populate_existing()
                .first()
            )
            if _idx_position_block_number is None:
                _idx_position_block_number = IDXPositionCouponBlockNumber()
            _idx_position_block_number.latest_block_number = block_number
            _idx_position_block_number.token_address = (
                target_token.token_contract.address
            )
            _idx_position_block_number.exchange_address = target_token.exchange_address
            db_session.merge(_idx_position_block_number)

    @staticmethod
    def __get_account_balance_all(token_contract, account_address: str):
        """Get balance"""
        balance = Contract.call_function(
            contract=token_contract,
            function_name="balanceOf",
            args=(account_address,),
            default_returns=0,
        )
        exchange_balance = 0
        exchange_commitment = 0
        tradable_exchange_address = Contract.call_function(
            contract=token_contract,
            function_name="tradableExchange",
            args=(),
            default_returns=ZERO_ADDRESS,
        )
        if tradable_exchange_address != ZERO_ADDRESS:
            exchange_contract = Contract.get_contract(
                "IbetExchangeInterface", tradable_exchange_address
            )
            exchange_balance = Contract.call_function(
                contract=exchange_contract,
                function_name="balanceOf",
                args=(
                    account_address,
                    token_contract.address,
                ),
                default_returns=0,
            )
            exchange_commitment = Contract.call_function(
                contract=exchange_contract,
                function_name="commitmentOf",
                args=(
                    account_address,
                    token_contract.address,
                ),
                default_returns=0,
            )
        return balance, exchange_balance, exchange_commitment

    @staticmethod
    def __get_account_balance_token(token_contract, account_address: str):
        """Get balance on token"""
        balance = Contract.call_function(
            contract=token_contract,
            function_name="balanceOf",
            args=(account_address,),
            default_returns=0,
        )
        return balance

    @staticmethod
    def __get_account_balance_exchange(
        exchange_address: str, token_address: str, account_address: str
    ):
        """Get balance on exchange"""
        exchange_contract = Contract.get_contract(
            contract_name="IbetExchangeInterface", address=exchange_address
        )
        exchange_balance = Contract.call_function(
            contract=exchange_contract,
            function_name="balanceOf",
            args=(
                account_address,
                token_address,
            ),
            default_returns=0,
        )
        exchange_commitment = Contract.call_function(
            contract=exchange_contract,
            function_name="commitmentOf",
            args=(
                account_address,
                token_address,
            ),
            default_returns=0,
        )
        return exchange_balance, exchange_commitment

    @staticmethod
    def __sink_on_position(
        db_session: Session,
        token_address: str,
        account_address: str,
        balance: Optional[int] = None,
        exchange_balance: Optional[int] = None,
        exchange_commitment: Optional[int] = None,
    ):
        """Update Position data in DB

        :param db_session: ORM session
        :param token_address: token address
        :param account_address: account address
        :param balance: updated balance
        :param exchange_balance: balance on exchange
        :param exchange_commitment: commitment volume on exchange
        :return: None
        """
        position = (
            db_session.query(IDXPosition)
            .filter(IDXPosition.token_address == token_address)
            .filter(IDXPosition.account_address == account_address)
            .first()
        )
        if position is not None:
            if balance is not None:
                position.balance = balance
            if exchange_balance is not None:
                position.exchange_balance = exchange_balance
            if exchange_commitment is not None:
                position.exchange_commitment = exchange_commitment
            db_session.merge(position)
        elif any(
            value is not None and value > 0
            for value in [balance, exchange_balance, exchange_commitment]
        ):
            LOG.debug(
                f"Position created (Coupon): token_address={token_address}, account_address={account_address}"
            )
            position = IDXPosition()
            position.token_address = token_address
            position.account_address = account_address
            position.balance = balance or 0
            position.exchange_balance = exchange_balance or 0
            position.exchange_commitment = exchange_commitment or 0
            db_session.add(position)

    @staticmethod
    def remove_duplicate_event_by_token_account_desc(
        events: List, account_keys: List[str]
    ) -> List[str]:
        """Remove duplicate account from event list.
        Events that have same account key will be removed.

        :param events: event list
        :param account_keys: keys in which event contains account address
        :return: account_list: account_list list filtered
        """
        event_account_list = []

        # reversed events loop for removing duplicates from the front
        for event in reversed(events):
            args = event["args"]
            for arg_key in account_keys:
                account_address = args.get(arg_key, ZERO_ADDRESS)
                if account_address != ZERO_ADDRESS:
                    event_account_list.append(account_address)
        seen = set()
        remove_duplicate_list = []
        for record in event_account_list:
            if record not in seen:
                remove_duplicate_list.append(record)
                seen.add(record)

        # return events in original order
        return list(reversed(remove_duplicate_list))


def main():
    LOG.info("Service started successfully")
    processor = Processor()

    initial_synced_completed = False
    while not initial_synced_completed:
        try:
            processor.initial_sync()
            initial_synced_completed = True
        except Exception:
            LOG.exception("Initial sync failed")

        time.sleep(10)

    while True:
        try:
            processor.sync_new_logs()
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception("An exception occurred during event synchronization")

        time.sleep(10)


if __name__ == "__main__":
    main()
