# -*- coding: utf-8 -*-
import logging

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    order = Table("order", meta, autoload=True)
    order.c.token_address.alter(type=String(42), index=True)
    order.c.exchange_address.alter(type=String(42), index=True)
    order.c.account_address.alter(type=String(42))
    order.c.agent_address.alter(type=String(42))

    col = Column("transaction_hash", String(66))
    try:
        col.create(order)
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが存在する場合はWARNINGを出力する
        logging.warning(err)
    except Exception as err:
        logging.warning(err)

    col = Column("order_timestamp", DateTime, default=None)
    try:
        col.create(order)
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが存在する場合はWARNINGを出力する
        logging.warning(err)
    except Exception as err:
        logging.warning(err)


def downgrade(migrate_engine):
    meta.bind = migrate_engine

    order = Table("order", meta, autoload=True)
    order.c.token_address.alter(type=String(256), index=True)
    order.c.exchange_address.alter(type=String(256), index=True)
    order.c.account_address.alter(type=String(256))
    order.c.agent_address.alter(type=String(256))

    Column("transaction_hash").drop(order)
    Column("order_timestamp").drop(order)
