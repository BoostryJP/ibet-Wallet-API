# -*- coding: utf-8 -*-
import logging

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *


# Table定義
meta = MetaData()
table = Table(
    "consume_coupon", meta,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("transaction_hash", String(66), index=True),
    Column("token_address", String(42), index=True),
    Column("account_address", String(42), index=True),
    Column("amount", BigInteger),
    Column("block_timestamp", DateTime, default=None),
    Column("created", DateTime, default=func.now()),
    Column("modified", DateTime, default=func.now(), onupdate=func.now())
)


# Upgrade
def upgrade(migrate_engine):
    meta.bind = migrate_engine
    try:
        table.create()
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にTBLが存在する場合はWARNINGを出力する
        logging.warning(err)


# Downgrade
def downgrade(migrate_engine):
    meta.bind = migrate_engine
    table.drop()
