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
from typing import Optional, List
import os
import sys
import time
from itertools import groupby

from eth_utils import to_checksum_address
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.model.db.idx_position import IDXPositionShareBlockNumber

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app.config import (
    DATABASE_URL,
    TOKEN_LIST_CONTRACT_ADDRESS,
    ZERO_ADDRESS
)
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.db import (
    Listing,
    IDXPosition
)
from app.utils.web3_utils import Web3Wrapper
import log

process_name = "INDEXER-POSITION-SHARE"
LOG = log.get_logger(process_name=process_name)

web3 = Web3Wrapper()
db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    """Processor for indexing Share balances"""

    def __init__(self):
        self.token_list = []

    @staticmethod
    def __get_db_session():
        return Session(autocommit=False, autoflush=True, bind=db_engine)

    def initial_sync(self):
        local_session = self.__get_db_session()
        try:
            self.__get_contract_list(local_session)
            # Synchronize 1,000,000 blocks each
            # if some blocks have already synced, sync starting from next block
            idx_position_block_number = self.__get_idx_position_block_number(db_session=local_session)
            latest_block = web3.eth.blockNumber
            if idx_position_block_number >= latest_block:
                LOG.debug(
                    f"Initial Sync is skipped since current block number({web3.eth.blockNumber}) is equal to or less "
                    f"than last synced block number({idx_position_block_number}) this processor did."
                )
                pass
            else:
                _from_block = idx_position_block_number + 1
                _to_block = 999999 + _from_block
                if latest_block > _to_block:
                    while _to_block < latest_block:
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
                        block_to=latest_block
                    )
                else:
                    self.__sync_all(
                        db_session=local_session,
                        block_from=_from_block,
                        block_to=latest_block
                    )
                self.__set_idx_position_block_number(local_session, latest_block)
                local_session.commit()
        finally:
            local_session.close()
        LOG.info(f"<{process_name}> Initial sync has been completed")

    def sync_new_logs(self):
        local_session = self.__get_db_session()
        try:
            self.__get_contract_list(local_session)
            latest_block = web3.eth.blockNumber
            # if some blocks have already synced, sync starting from next block
            idx_position_block_number = self.__get_idx_position_block_number(db_session=local_session)
            if idx_position_block_number >= latest_block:
                LOG.debug(
                    f"Initial Sync is skipped since current block number({latest_block}) is equal to or less "
                    f"than last synced block number({idx_position_block_number}) this processor did."
                )
                pass
            else:
                _from_block = idx_position_block_number + 1
                self.__sync_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=latest_block
                )
                self.__set_idx_position_block_number(local_session, latest_block)
                local_session.commit()
        finally:
            local_session.close()

    def __get_contract_list(self, db_session: Session):
        self.token_list = []
        self.token_address_list = []
        self.exchange_address_list = []
        list_contract = Contract.get_contract(
            contract_name="TokenList",
            address=TOKEN_LIST_CONTRACT_ADDRESS
        )
        listed_tokens = db_session.query(Listing).all()

        _exchange_list_tmp = []
        for listed_token in listed_tokens:
            token_info = Contract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(listed_token.token_address,),
                default_returns=(ZERO_ADDRESS, "", ZERO_ADDRESS)
            )
            if token_info[1] == "IbetShare":
                token_contract = Contract.get_contract(
                    contract_name="IbetShare",
                    address=listed_token.token_address
                )
                self.token_list.append(token_contract)
                self.token_address_list.append(token_contract.address)
                tradable_exchange_address = Contract.call_function(
                    contract=token_contract,
                    function_name="tradableExchange",
                    args=(),
                    default_returns=ZERO_ADDRESS
                )
                if tradable_exchange_address != ZERO_ADDRESS:
                    _exchange_list_tmp.append(tradable_exchange_address)

        # Remove duplicate exchanges from a list
        self.exchange_address_list = list(set(_exchange_list_tmp))

    def __sync_all(self, db_session: Session, block_from: int, block_to: int):
        LOG.info("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_transfer(db_session, block_from, block_to)
        self.__sync_lock(db_session, block_from, block_to)
        self.__sync_unlock(db_session, block_from, block_to)
        self.__sync_issue(db_session, block_from, block_to)
        self.__sync_redeem(db_session, block_from, block_to)
        self.__sync_apply_for_transfer(db_session, block_from, block_to)
        self.__sync_cancel_transfer(db_session, block_from, block_to)
        self.__sync_approve_transfer(db_session, block_from, block_to)
        self.__sync_exchange(db_session, block_from, block_to)
        self.__sync_escrow(db_session, block_from, block_to)

    def __sync_transfer(self, db_session: Session, block_from: int, block_to: int):
        """Sync Transfer Events

        :param db_session: ORM session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.Transfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                events_filtered = self.remove_duplicate_event_by_token_account_desc(events, ["from", "to"])
                for event in events_filtered:
                    args = event["args"]
                    for _account in [args.get("from", ZERO_ADDRESS), args.get("to", ZERO_ADDRESS)]:
                        if web3.eth.getCode(_account).hex() == "0x":
                            _balance, _pending_transfer, _exchange_balance, _exchange_commitment = \
                                self.__get_account_balance_all(token, _account)
                            self.__sink_on_position(
                                db_session=db_session,
                                token_address=to_checksum_address(token.address),
                                account_address=_account,
                                balance=_balance,
                                pending_transfer=_pending_transfer,
                                exchange_balance=_exchange_balance,
                                exchange_commitment=_exchange_commitment
                            )
            except Exception as e:
                LOG.exception(e)

    def __sync_lock(self, db_session: Session, block_from: int, block_to: int):
        """Sync Lock Events

        :param db_session: ORM session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.Lock.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                events_filtered = self.remove_duplicate_event_by_token_account_desc(events, ["accountAddress"])
                for event in events_filtered:
                    args = event["args"]
                    account = args.get("accountAddress", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_unlock(self, db_session: Session, block_from: int, block_to: int):
        """Sync Unlock Events

        :param db_session: ORM session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.Unlock.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                events_filtered = self.remove_duplicate_event_by_token_account_desc(events, ["recipientAddress"])
                for event in events_filtered:
                    args = event["args"]
                    account = args.get("recipientAddress", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_issue(self, db_session: Session, block_from: int, block_to: int):
        """Sync Issue Events

        :param db_session: ORM session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.Issue.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                events_filtered = self.remove_duplicate_event_by_token_account_desc(events, ["targetAddress"])
                for event in events_filtered:
                    args = event["args"]
                    account = args.get("targetAddress", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_redeem(self, db_session: Session, block_from: int, block_to: int):
        """Sync Redeem Events

        :param db_session: ORM session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.Redeem.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                events_filtered = self.remove_duplicate_event_by_token_account_desc(events, ["targetAddress"])
                for event in events_filtered:
                    args = event["args"]
                    account = args.get("targetAddress", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_apply_for_transfer(self, db_session: Session, block_from: int, block_to: int):
        """Sync ApplyForTransfer Events

        :param db_session: ORM session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.ApplyForTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                events_filtered = self.remove_duplicate_event_by_token_account_desc(events, ["from"])
                for event in events_filtered:
                    args = event["args"]
                    account = args.get("from", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_cancel_transfer(self, db_session: Session, block_from: int, block_to: int):
        """Sync CancelTransfer Events

        :param db_session: ORM session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.CancelTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                events_filtered = self.remove_duplicate_event_by_token_account_desc(events, ["from"])
                for event in events_filtered:
                    args = event["args"]
                    account = args.get("from", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_approve_transfer(self, db_session: Session, block_from: int, block_to: int):
        """Sync ApproveTransfer Events

        :param db_session: ORM session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.ApproveTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                events_filtered = self.remove_duplicate_event_by_token_account_desc(events, ["from", "to"])
                for event in events_filtered:
                    args = event["args"]
                    for _account in [args.get("from", ZERO_ADDRESS), args.get("to", ZERO_ADDRESS)]:
                        _balance, _pending_transfer = self.__get_account_balance_token(token, _account)
                        self.__sink_on_position(
                            db_session=db_session,
                            token_address=to_checksum_address(token.address),
                            account_address=_account,
                            balance=_balance,
                            pending_transfer=_pending_transfer
                        )
            except Exception as e:
                LOG.exception(e)

    def __sync_exchange(self, db_session: Session, block_from: int, block_to: int):
        """Sync Events from IbetExchange

        :param db_session: ORM session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for exchange_address in self.exchange_address_list:
            try:
                exchange = Contract.get_contract(
                    contract_name="IbetExchange",
                    address=exchange_address
                )

                account_list_tmp = []

                # NewOrder event
                _event_list = exchange.events.NewOrder.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("accountAddress", ZERO_ADDRESS)
                    })

                # CancelOrder event
                _event_list = exchange.events.CancelOrder.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("accountAddress", ZERO_ADDRESS)
                    })

                # ForceCancelOrder event
                _event_list = exchange.events.ForceCancelOrder.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("accountAddress", ZERO_ADDRESS)
                    })

                # Agree event
                _event_list = exchange.events.Agree.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("sellAddress", ZERO_ADDRESS)  # only seller has changed
                    })

                # SettlementOK event
                _event_list = exchange.events.SettlementOK.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("buyAddress", ZERO_ADDRESS)
                    })
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("sellAddress", ZERO_ADDRESS)
                    })

                # SettlementNG event
                _event_list = exchange.events.SettlementNG.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("sellAddress", ZERO_ADDRESS)  # only seller has changed
                    })

                # Make temporary list unique
                account_list_tmp.sort(key=lambda x: (x["token_address"], x["account_address"]))
                account_list = []
                for k, g in groupby(account_list_tmp, lambda x: (x["token_address"], x["account_address"])):
                    account_list.append({"token_address": k[0], "account_address": k[1]})

                # Update position
                for _account in account_list:
                    token_address = _account["token_address"]
                    account_address = _account["account_address"]
                    exchange_balance, exchange_commitment = self.__get_account_balance_exchange(
                        exchange_address=exchange_address,
                        token_address=token_address,
                        account_address=account_address
                    )
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=token_address,
                        account_address=account_address,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_escrow(self, db_session: Session, block_from: int, block_to: int):
        """Sync Events from IbetSecurityTokenEscrow

        :param db_session: ORM session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for exchange_address in self.exchange_address_list:
            try:
                escrow = Contract.get_contract("IbetSecurityTokenEscrow", exchange_address)

                account_list_tmp = []

                # EscrowCreated event
                _event_list = escrow.events.EscrowCreated.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("token", ZERO_ADDRESS),
                        "account_address": _event["args"].get("sender", ZERO_ADDRESS)  # only sender has changed
                    })

                # EscrowCanceled event
                _event_list = escrow.events.EscrowCanceled.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("token", ZERO_ADDRESS),
                        "account_address": _event["args"].get("sender", ZERO_ADDRESS)  # only sender has changed
                    })

                # HolderChanged event
                _event_list = escrow.events.HolderChanged.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("token", ZERO_ADDRESS),
                        "account_address": _event["args"].get("from", ZERO_ADDRESS)
                    })
                    account_list_tmp.append({
                        "token_address": _event["args"].get("token", ZERO_ADDRESS),
                        "account_address": _event["args"].get("to", ZERO_ADDRESS)
                    })

                # Make temporary list unique
                account_list_tmp.sort(key=lambda x: (x["token_address"], x["account_address"]))
                account_list = []
                for k, g in groupby(account_list_tmp, lambda x: (x["token_address"], x["account_address"])):
                    account_list.append({"token_address": k[0], "account_address": k[1]})

                # Update position
                for _account in account_list:
                    token_address = _account["token_address"]
                    account_address = _account["account_address"]
                    exchange_balance, exchange_commitment = self.__get_account_balance_exchange(
                        exchange_address=exchange_address,
                        token_address=token_address,
                        account_address=account_address
                    )
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=token_address,
                        account_address=account_address,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment
                    )
            except Exception as e:
                LOG.exception(e)

    @staticmethod
    def __get_idx_position_block_number(db_session: Session):
        """Get position index for Coupon """
        _idx_position_block_number = db_session.query(IDXPositionShareBlockNumber).first()
        if _idx_position_block_number is None:
            return -1
        else:
            return _idx_position_block_number.latest_block_number

    @staticmethod
    def __set_idx_position_block_number(db_session: Session, block_number: int):
        """Set position index for Coupon """
        _idx_position_block_number = db_session.query(IDXPositionShareBlockNumber). \
            first()
        if _idx_position_block_number is None:
            _idx_position_block_number = IDXPositionShareBlockNumber()
        _idx_position_block_number.latest_block_number = block_number
        db_session.merge(_idx_position_block_number)

    @staticmethod
    def __get_account_balance_all(token_contract, account_address: str):
        """Get balance"""
        balance = Contract.call_function(
            contract=token_contract,
            function_name="balanceOf",
            args=(account_address,),
            default_returns=0
        )
        pending_transfer = Contract.call_function(
            contract=token_contract,
            function_name="pendingTransfer",
            args=(account_address,),
            default_returns=0
        )
        exchange_balance = 0
        exchange_commitment = 0
        tradable_exchange_address = Contract.call_function(
            contract=token_contract,
            function_name="tradableExchange",
            args=(),
            default_returns=ZERO_ADDRESS
        )
        if tradable_exchange_address != ZERO_ADDRESS:
            exchange_contract = Contract.get_contract(
                "IbetExchangeInterface", tradable_exchange_address)
            exchange_balance = Contract.call_function(
                contract=exchange_contract,
                function_name="balanceOf",
                args=(account_address, token_contract.address,),
                default_returns=0
            )
            exchange_commitment = Contract.call_function(
                contract=exchange_contract,
                function_name="commitmentOf",
                args=(account_address, token_contract.address,),
                default_returns=0
            )
        return balance, pending_transfer, exchange_balance, exchange_commitment

    @staticmethod
    def __get_account_balance_token(token_contract, account_address: str):
        """Get balance on token"""
        balance = Contract.call_function(
            contract=token_contract,
            function_name="balanceOf",
            args=(account_address,),
            default_returns=0
        )
        pending_transfer = Contract.call_function(
            contract=token_contract,
            function_name="pendingTransfer",
            args=(account_address,),
            default_returns=0
        )
        return balance, pending_transfer

    @staticmethod
    def __get_account_balance_exchange(exchange_address: str,
                                       token_address: str,
                                       account_address: str):
        """Get balance on exchange"""
        exchange_contract = Contract.get_contract(
            contract_name="IbetExchangeInterface",
            address=exchange_address
        )
        exchange_balance = Contract.call_function(
            contract=exchange_contract,
            function_name="balanceOf",
            args=(account_address, token_address,),
            default_returns=0
        )
        exchange_commitment = Contract.call_function(
            contract=exchange_contract,
            function_name="commitmentOf",
            args=(account_address, token_address,),
            default_returns=0
        )
        return exchange_balance, exchange_commitment

    @staticmethod
    def __sink_on_position(db_session: Session,
                           token_address: str,
                           account_address: str,
                           balance: Optional[int] = None,
                           pending_transfer: Optional[int] = None,
                           exchange_balance: Optional[int] = None,
                           exchange_commitment: Optional[int] = None):
        """Update Position data in DB

        :param db_session: ORM session
        :param token_address: token address
        :param account_address: account address
        :param balance: updated balance
        :param pending_transfer: updated pending_transfer
        :param exchange_balance: balance on exchange
        :param exchange_commitment: commitment volume on exchange
        :return: None
        """
        position = db_session.query(IDXPosition). \
            filter(IDXPosition.token_address == token_address). \
            filter(IDXPosition.account_address == account_address). \
            first()
        if position is not None:
            if balance is not None:
                position.balance = balance
            if pending_transfer is not None:
                position.pending_transfer = pending_transfer
            if exchange_balance is not None:
                position.exchange_balance = exchange_balance
            if exchange_commitment is not None:
                position.exchange_commitment = exchange_commitment
            db_session.merge(position)
        elif any(value is not None and value > 0 for value in
                 [balance, pending_transfer, exchange_balance, exchange_commitment]):
            LOG.debug(
                f"Position created (Share): token_address={token_address}, account_address={account_address}"
            )
            position = IDXPosition()
            position.token_address = token_address
            position.account_address = account_address
            position.balance = balance or 0
            position.pending_transfer = pending_transfer or 0
            position.exchange_balance = exchange_balance or 0
            position.exchange_commitment = exchange_commitment or 0
            db_session.add(position)

    @staticmethod
    def remove_duplicate_event_by_token_account_desc(events: [], account_keys: List[str]):
        """Remove duplicate event from event list.
        Events that have same account key will be removed.

        :param events: event list
        :param account_keys: keys in which event contains account address
        :return: events: event list filtered
        """
        event_token_account_list = []

        # reversed events loop for removing duplicates from the front
        for event in reversed(events):
            args = event["args"]
            for arg_key in account_keys:
                account_address = args.get(arg_key, ZERO_ADDRESS)
                if account_address != ZERO_ADDRESS:
                    event_token_account_list.append([event, account_address])
        seen = set()
        remove_duplicate_list = []
        for record in event_token_account_list:
            record_tuple = tuple(record)
            if record_tuple[1] not in seen:
                remove_duplicate_list.append(record[0])
                seen.add(record_tuple[1])

        # return events in original order
        return reversed(remove_duplicate_list)


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

        time.sleep(10)


if __name__ == "__main__":
    main()
