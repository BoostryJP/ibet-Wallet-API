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
import log
from app.utils.web3_utils import Web3Wrapper
from app.contracts import Contract
from app.model.db import (
    Listing,
    IDXPosition
)
from app.config import (
    DATABASE_URL,
    TOKEN_LIST_CONTRACT_ADDRESS,
    ZERO_ADDRESS,
)
from typing import Optional
import os
import sys
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session
)
from eth_utils import to_checksum_address

from web3.exceptions import (
    BadFunctionCallOutput
)

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)


process_name = "INDEXER-POSITION-BOND"
LOG = log.get_logger(process_name=process_name)

web3 = Web3Wrapper()

engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)


class Sinks:
    def __init__(self):
        self.sinks = []

    def register(self, _sink):
        self.sinks.append(_sink)

    def on_position(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_position(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_position(self, token_address: str, account_address: str,
                    balance: Optional[int] = None, pending_transfer: Optional[int] = None,
                    exchange_balance: Optional[int] = None, exchange_commitment: Optional[int] = None):
        """Update Position data in DB

        :param token_address: token address
        :param account_address: account address
        :param balance: updated balance
        :param pending_transfer: updated pending_transfer
        :param exchange_balance: balance on exchange
        :param exchange_commitment: commitment volume on exchange
        :return: None
        """
        position = self.db.query(IDXPosition). \
            filter(IDXPosition.token_address == token_address). \
            filter(IDXPosition.account_address == account_address). \
            first()
        if position is None:
            LOG.debug(
                f"Position created (Bond): token_address={token_address}, account_address={account_address}")
            position = IDXPosition()
            position.token_address = token_address
            position.account_address = account_address
            position.balance = balance or 0
            position.pending_transfer = pending_transfer or 0
            position.exchange_balance = exchange_balance or 0
            position.exchange_commitment = exchange_commitment or 0
        else:
            if balance is not None:
                position.balance = balance
            if pending_transfer is not None:
                position.pending_transfer = pending_transfer
            if exchange_balance is not None:
                position.exchange_balance = exchange_balance
            if exchange_commitment is not None:
                position.exchange_commitment = exchange_commitment

        self.db.merge(position)

    def flush(self):
        self.db.commit()


class Processor:
    def __init__(self, sink, db):
        self.sink = sink
        self.latest_block = web3.eth.blockNumber
        self.db = db
        self.token_list = []

    def get_contract_list(self):
        self.token_list = []
        self.token_address_list = []
        self.exchange_list = []
        list_contract = Contract.get_contract("TokenList", TOKEN_LIST_CONTRACT_ADDRESS)
        listed_tokens = self.db.query(Listing).all()

        _exchange_list_tmp = []
        for listed_token in listed_tokens:
            token_info = Contract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(listed_token.token_address,),
                default_returns=(ZERO_ADDRESS, "", ZERO_ADDRESS)
            )
            if token_info[1] == "IbetStraightBond":
                token_contract = Contract.get_contract(
                    "IbetStraightBond", listed_token.token_address)
                self.token_list.append(token_contract)
                self.token_address_list.append(token_contract.address)
                tradable_exchange_address = token_contract.functions.tradableExchange().call()
                if tradable_exchange_address != ZERO_ADDRESS:
                    _exchange_list_tmp.append(tradable_exchange_address)

        # Remove duplicate exchanges from a list
        for _exchange_address in list(set(_exchange_list_tmp)):
            exchange_contract = Contract.get_contract(
                # exchange_contract is only used for event logs, so anything is OK
                contract_name="IbetExchangeInterface",
                address=_exchange_address
            )
            self.exchange_list.append(exchange_contract)

    def initial_sync(self):
        self.get_contract_list()
        # 1,000,000ブロックずつ同期処理を行う
        _to_block = 999999
        _from_block = 0
        if self.latest_block > 999999:
            while _to_block < self.latest_block:
                self.__init_sync_all(_from_block, _to_block)
                _to_block += 1000000
                _from_block += 1000000
            self.__init_sync_all(_from_block, self.latest_block)
        else:
            self.__init_sync_all(_from_block, self.latest_block)
        self.sink.flush()
        LOG.info(f"<{process_name}> Initial sync has been completed")

    def sync_new_logs(self):
        self.get_contract_list()
        blockTo = web3.eth.blockNumber
        if blockTo == self.latest_block:
            return
        self.__sync_all(self.latest_block + 1, blockTo)
        self.latest_block = blockTo

    def __init_sync_all(self, block_from: int, block_to: int):
        LOG.info("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_transfer(block_from, block_to)
        self.__sync_lock(block_from, block_to)
        self.__sync_unlock(block_from, block_to)
        self.__sync_issue(block_from, block_to)
        self.__sync_redeem(block_from, block_to)
        self.__sync_apply_for_transfer(block_from, block_to)
        self.__sync_cancel_transfer(block_from, block_to)
        self.__sync_approve_transfer(block_from, block_to)
        self.__sync_holder_changed(block_from, block_to)
        self.__sync_set_commitment(block_from, block_to)

    def __sync_all(self, block_from: int, block_to: int):
        LOG.info("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_transfer(block_from, block_to)
        self.__sync_lock(block_from, block_to)
        self.__sync_unlock(block_from, block_to)
        self.__sync_issue(block_from, block_to)
        self.__sync_redeem(block_from, block_to)
        self.__sync_apply_for_transfer(block_from, block_to)
        self.__sync_cancel_transfer(block_from, block_to)
        self.__sync_approve_transfer(block_from, block_to)
        self.__sync_holder_changed(block_from, block_to)
        self.__sync_set_commitment(block_from, block_to)
        self.sink.flush()

    def __sync_transfer(self, block_from: int, block_to: int):
        """Transferイベントの同期

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

                exchange_contract_address = token.functions.tradableExchange().call()

                for event in events:
                    args = event["args"]
                    # from address
                    from_account = args.get("from", ZERO_ADDRESS)
                    if from_account != exchange_contract_address:
                        from_account_balance, from_account_pending_transfer, from_account_exchange_balance, from_account_exchange_commitment = self.__get_account_balance(
                            token, from_account)
                        self.sink.on_position(
                            token_address=to_checksum_address(token.address),
                            account_address=from_account,
                            balance=from_account_balance,
                            pending_transfer=from_account_pending_transfer,
                            exchange_balance=from_account_exchange_balance,
                            exchange_commitment=from_account_exchange_commitment
                        )
                    # to address
                    to_account = args.get("to", ZERO_ADDRESS)
                    if to_account != exchange_contract_address:
                        to_account_balance, to_account_pending_transfer, to_account_exchange_balance, to_account_exchange_commitment = self.__get_account_balance(
                            token, to_account)
                        self.sink.on_position(
                            token_address=to_checksum_address(token.address),
                            account_address=to_account,
                            balance=to_account_balance,
                            pending_transfer=to_account_pending_transfer,
                            exchange_balance=to_account_exchange_balance,
                            exchange_commitment=to_account_exchange_commitment
                        )
            except Exception as e:
                LOG.exception(e)

    def __sync_lock(self, block_from: int, block_to: int):
        """Lockイベントの同期

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
                for event in events:
                    args = event["args"]
                    account = args.get("accountAddress", ZERO_ADDRESS)
                    balance, pending_transfer, exchange_balance, exchange_commitment = self.__get_account_balance(
                        token, account)
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_unlock(self, block_from: int, block_to: int):
        """Sync Unlock Events

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
                for event in events:
                    args = event["args"]
                    account = args.get("recipientAddress", ZERO_ADDRESS)
                    balance, pending_transfer, exchange_balance, exchange_commitment = self.__get_account_balance(
                        token, account)
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_issue(self, block_from: int, block_to: int):
        """Sync Issue Events

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
                for event in events:
                    args = event["args"]
                    account = args.get("targetAddress", ZERO_ADDRESS)
                    balance, pending_transfer, exchange_balance, exchange_commitment = self.__get_account_balance(
                        token, account)
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_redeem(self, block_from: int, block_to: int):
        """Sync Redeem Events

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
                for event in events:
                    args = event["args"]
                    account = args.get("targetAddress", ZERO_ADDRESS)
                    balance, pending_transfer, exchange_balance, exchange_commitment = self.__get_account_balance(
                        token, account)
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_apply_for_transfer(self, block_from: int, block_to: int):
        """Sync ApplyForTransfer Events

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
                for event in events:
                    args = event["args"]
                    account = args.get("from", ZERO_ADDRESS)
                    balance, pending_transfer, exchange_balance, exchange_commitment = self.__get_account_balance(
                        token, account)
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_cancel_transfer(self, block_from: int, block_to: int):
        """Sync CancelTransfer Events

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
                for event in events:
                    args = event["args"]
                    account = args.get("from", ZERO_ADDRESS)
                    balance, pending_transfer, exchange_balance, exchange_commitment = self.__get_account_balance(
                        token, account)
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_approve_transfer(self, block_from: int, block_to: int):
        """Sync ApproveTransfer Events

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
                for event in events:
                    args = event["args"]
                    # from address
                    from_account = args.get("from", ZERO_ADDRESS)
                    from_account_balance, from_account_pending_transfer, from_account_exchange_balance, from_account_exchange_commitment = self.__get_account_balance(
                        token, from_account)
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=from_account,
                        balance=from_account_balance,
                        pending_transfer=from_account_pending_transfer,
                        exchange_balance=from_account_exchange_balance,
                        exchange_commitment=from_account_exchange_commitment
                    )
                    # to address
                    to_account = args.get("to", ZERO_ADDRESS)
                    to_account_balance, to_account_pending_transfer, to_account_exchange_balance, to_account_exchange_commitment = self.__get_account_balance(
                        token, to_account)
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=to_account,
                        balance=to_account_balance,
                        pending_transfer=to_account_pending_transfer,
                        exchange_balance=to_account_exchange_balance,
                        exchange_commitment=to_account_exchange_commitment
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_holder_changed(self, block_from: int, block_to: int):
        """[DEX]Sync HolderChanged Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for exchange in self.exchange_list:
            try:
                events = exchange.events.HolderChanged.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                target_events = []
                for event in events:
                    if event["args"].get("token") in self.token_address_list:
                        target_events.append(event)
                for event in target_events:
                    args = event["args"]
                    from_exchange_balance = 0
                    from_exchange_commitment = 0
                    try:
                        from_exchange_balance = Contract.call_function(
                            contract=exchange,
                            function_name="balanceOf",
                            args=(args.get("from", ZERO_ADDRESS), args.get("token", ZERO_ADDRESS),),
                            default_returns=0
                        )   
                        from_exchange_commitment = Contract.call_function(
                            contract=exchange,
                            function_name="commitmentOf",
                            args=(args.get("from", ZERO_ADDRESS), args.get("token", ZERO_ADDRESS),),
                            default_returns=0
                        )  
                    except BadFunctionCallOutput:
                        pass
                    self.sink.on_position(
                        token_address=args.get("token", ZERO_ADDRESS),
                        account_address=args.get("from", ZERO_ADDRESS),
                        exchange_balance=from_exchange_balance,
                        exchange_commitment=from_exchange_commitment
                    )
                    to_exchange_balance = 0
                    to_exchange_commitment = 0
                    try:
                        to_exchange_balance = Contract.call_function(
                            contract=exchange,
                            function_name="balanceOf",
                            args=(args.get("to", ZERO_ADDRESS), args.get("token", ZERO_ADDRESS),),
                            default_returns=0
                        )   
                        to_exchange_commitment = Contract.call_function(
                            contract=exchange,
                            function_name="commitmentOf",
                            args=(args.get("to", ZERO_ADDRESS), args.get("token", ZERO_ADDRESS),),
                            default_returns=0
                        )  
                    except BadFunctionCallOutput:
                        pass
                    self.sink.on_position(
                        token_address=args.get("token", ZERO_ADDRESS),
                        account_address=args.get("to", ZERO_ADDRESS),
                        exchange_balance=to_exchange_balance,
                        exchange_commitment=to_exchange_commitment
                    )

            except Exception as e:
                LOG.exception(e)

    def __sync_set_commitment(self, block_from: int, block_to: int):
        """[DEX]Sync Events Involved setCommitment

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for exchange in self.exchange_list:
            try:
                # sync for IbetExchange without HolderChanged
                order_events = []
                order_events.append(exchange.events.NewOrder.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                ))
                order_events.append(exchange.events.CancelOrder.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                ))
                order_events.append(exchange.events.ForceCancelOrder.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                ))
                target_events = []
                for event in order_events:
                    if event["args"].get("tokenAddress") in self.token_address_list:
                        target_events.append(event)
                for event in target_events:
                    args = event["args"]
                    exchange_balance = 0
                    exchange_commitment = 0
                    try:
                        exchange_balance = Contract.call_function(
                            contract=exchange,
                            function_name="balanceOf",
                            args=(args.get("accountAddress", ZERO_ADDRESS), args.get("tokenAddress", ZERO_ADDRESS),),
                            default_returns=0
                        )   
                        exchange_commitment = Contract.call_function(
                            contract=exchange,
                            function_name="commitmentOf",
                            args=(args.get("accountAddress", ZERO_ADDRESS), args.get("tokenAddress", ZERO_ADDRESS),),
                            default_returns=0
                        )                    
                    except BadFunctionCallOutput:
                        pass
                    self.sink.on_position(
                        token_address=args.get("tokenAddress", ZERO_ADDRESS),
                        account_address=args.get("accountAddress", ZERO_ADDRESS),
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment
                    )
                settlement_events = []
                settlement_events.append(exchange.events.Agree.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                ))
                settlement_events.append(exchange.events.SettlementNG.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                ))
                target_events = []
                for event in settlement_events:
                    if event["args"].get("tokenAddress") in self.token_address_list:
                        target_events.append(event)
                for event in target_events:
                    args = event["args"]
                    exchange_balance = Contract.call_function(
                        contract=exchange,
                        function_name="balanceOf",
                        args=(args.get("sellAddress", ZERO_ADDRESS), args.get("tokenAddress", ZERO_ADDRESS),),
                        default_returns=0
                    )   
                    exchange_commitment = Contract.call_function(
                        contract=exchange,
                        function_name="commitmentOf",
                        args=(args.get("sellAddress", ZERO_ADDRESS), args.get("tokenAddress", ZERO_ADDRESS),),
                        default_returns=0
                    )
                    self.sink.on_position(
                        token_address=args.get("tokenAddress", ZERO_ADDRESS),
                        account_address=args.get("sellAddress", ZERO_ADDRESS),
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment
                    )
                escrow_events = []
                # sync for IbetSecurityTokenEscrow without HolderChanged
                escrow_events.append(exchange.events.EscrowCreated.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                ))
                escrow_events.append(exchange.events.EscrowCanceled.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                ))
                target_events = []
                for event in escrow_events:
                    if event["args"].get("token") in self.token_address_list:
                        target_events.append(event)
                for event in target_events:
                    args = event["args"]
                    exchange_balance = Contract.call_function(
                        contract=exchange,
                        function_name="balanceOf",
                        args=(args.get("sender", ZERO_ADDRESS), args.get("token", ZERO_ADDRESS),),
                        default_returns=0
                    )   
                    exchange_commitment = Contract.call_function(
                        contract=exchange,
                        function_name="commitmentOf",
                        args=(args.get("sender", ZERO_ADDRESS), args.get("token", ZERO_ADDRESS),),
                        default_returns=0
                    )
                    self.sink.on_position(
                        token_address=args.get("token", ZERO_ADDRESS),
                        account_address=args.get("sender", ZERO_ADDRESS),
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment
                    )

            except Exception as e:
                LOG.exception(e)

    @staticmethod
    def __get_account_balance(token_contract, account_address: str):
        """Get balance of account"""

        balance =  Contract.call_function(
                        contract=token_contract,
                        function_name="balanceOf",
                        args=(account_address,),
                        default_returns=0
                    )
        pending_transfer =  Contract.call_function(
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


_sink = Sinks()
_sink.register(DBSink(db_session))
processor = Processor(_sink, db_session)


def main():
    LOG.info("Service started successfully")

    processor.initial_sync()
    while True:
        processor.sync_new_logs()
        time.sleep(10)


if __name__ == "__main__":
    main()
