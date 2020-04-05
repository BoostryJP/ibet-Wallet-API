# -*- coding: utf-8 -*-
import logging

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *


# Table定義
meta = MetaData()
table = Table(
    "order", meta,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("token_address", String(256), index=True),
    Column("exchange_address", String(256), index=True),
    Column("order_id", BigInteger, index=True),
    Column("unique_order_id", String(256), index=True),
    Column("account_address", String(256)),
    Column("is_buy", Boolean),
    Column("price", BigInteger),
    Column("amount", BigInteger),
    Column("agent_address", String(256)),
    Column("is_cancelled", Boolean),
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
