# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *


meta = MetaData()

table = Table(
    "token_holders_list", meta,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("token_address", String(42)),
    Column("block_number", BigInteger),
    Column("list_id", String(36), index=False),
    Column("batch_status", String(256)),
    Column("created", DateTime, default=datetime.utcnow),
    Column("modified", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
)


def upgrade(migrate_engine):
    meta.bind = migrate_engine
    try:
        table.create()
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    table.drop()
