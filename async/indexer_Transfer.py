# -*- coding: utf-8 -*-
import os
import sys
import time
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(path)

from app import log
from app import config
from app.model import Listing, PrivateListing, Position, Transfer
from app.contracts import Contract

LOG = log.get_logger()
log_fmt = 'PROCESSOR-POSITION [%(asctime)s] [%(process)d] [%(levelname)s] %(message)s'
logging.basicConfig(format=log_fmt)

# 設定の取得
WEB3_HTTP_PROVIDER = config.WEB3_HTTP_PROVIDER
URI = config.DATABASE_URL

# 初期化
web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)
engine = create_engine(URI, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)


class Sinks:
    def __init__(self):
        self.sinks = []

    def register(self, sink):
        self.sinks.append(sink)

    def on_transfer(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_transfer(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class ConsoleSink:
    @staticmethod
    def on_transfer(transaction_hash, token_address,
                    from_account_address, from_account_balance, to_account_address, to_account_balance, value):
        LOG.info(
            "Transfer: transaction_hash={}, token_address={}, from_account_address={}, to_account_address={}".format(
                transaction_hash, token_address, from_account_address, to_account_address
            )
        )

    def flush(self):
        return


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_transfer(self, transaction_hash, token_address,
                    from_account_address, from_account_balance, to_account_address, to_account_balance, value):
        # From-Account の残高情報を更新
        from_position = self.__get_position_record(token_address, from_account_address)
        if from_position is None:
            from_position = Position()
            from_position.token_address = token_address
            from_position.account_address = from_account_address
            from_position.balance = from_account_balance
        else:
            from_position.balance = from_account_balance
        self.db.merge(from_position)

        # To-Account の残高情報を更新
        to_position = self.__get_position_record(token_address, to_account_address)
        if to_position is None:
            to_position = Position()
            to_position.token_address = token_address
            to_position.account_address = to_account_address
            to_position.balance = to_account_balance
        else:
            to_position.balance = to_account_balance
        self.db.merge(to_position)

        # Transfer イベント情報の更新
        transfer = self.__get_transfer_record(transaction_hash)
        if transfer is None:
            transfer = Transfer()
            transfer.transaction_hash = transaction_hash
            transfer.token_address = token_address
            transfer.from_address = from_account_address
            transfer.to_address = to_account_address
            transfer.value = value
            self.db.merge(transfer)

    def flush(self):
        self.db.commit()

    def __get_position_record(self, token_address, account_address):
        return self.db.query(Position). \
            filter(Position.token_address == token_address). \
            filter(Position.account_address == account_address). \
            first()

    def __get_transfer_record(self, transaction_hash):
        return self.db.query(Transfer). \
            filter(Transfer.transaction_hash == transaction_hash). \
            first()


class Processor:
    def __init__(self, web3, sink, db):
        self.web3 = web3
        self.sink = sink
        self.latest_block = web3.eth.blockNumber
        self.db = db
        self.token_list = []

    def get_token_list(self):
        self.token_list = []
        ListContract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)
        listed_tokens = self.db.query(Listing).all()
        listed_tokens = listed_tokens + self.db.query(PrivateListing).all()
        for listed_token in listed_tokens:
            token_info = ListContract.functions.getTokenByAddress(listed_token.token_address).call()
            if token_info[1] == "IbetCoupon":
                token_contract = Contract.get_contract('IbetCoupon', listed_token.token_address)
                self.token_list.append(token_contract)
            elif token_info[1] == "IbetMembership":
                token_contract = Contract.get_contract('IbetMembership', listed_token.token_address)
                self.token_list.append(token_contract)
            elif token_info[1] == "IbetStraightBond":
                token_contract = Contract.get_contract('IbetStraightBond', listed_token.token_address)
                self.token_list.append(token_contract)

    def initial_sync(self):
        self.get_token_list()
        self.__sync_all(0, self.latest_block)

    def sync_new_logs(self):
        self.get_token_list()
        blockTo = web3.eth.blockNumber
        if blockTo == self.latest_block:
            return
        self.__sync_all(self.latest_block + 1, blockTo)
        self.latest_block = blockTo

    def __sync_all(self, block_from, block_to):
        LOG.debug("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_transfer(block_from, block_to)
        self.sink.flush()

    def __sync_transfer(self, block_from, block_to):
        for token in self.token_list:
            try:
                event_filter = token.eventFilter(
                    'Transfer', {
                        'fromBlock': block_from,
                        'toBlock': block_to,
                    }
                )
                for event in event_filter.get_all_entries():
                    args = event['args']
                    from_account_balance = token.functions.balanceOf(args["from"]).call()
                    to_account_balance = token.functions.balanceOf(args["to"]).call()
                    if args['value'] > sys.maxsize:
                        pass
                    else:
                        self.sink.on_transfer(
                            transaction_hash=event["transactionHash"].hex(),
                            token_address=to_checksum_address(token.address),
                            from_account_address=args["from"],
                            from_account_balance=from_account_balance,
                            to_account_address=args["to"],
                            to_account_balance=to_account_balance,
                            value=args["value"]
                        )
                self.web3.eth.uninstallFilter(event_filter.filter_id)
            except Exception as e:
                LOG.exception(e)
                pass


sink = Sinks()
sink.register(ConsoleSink())
sink.register(DBSink(db_session))
processor = Processor(web3, sink, db_session)

processor.initial_sync()
while True:
    processor.sync_new_logs()
    time.sleep(10)
