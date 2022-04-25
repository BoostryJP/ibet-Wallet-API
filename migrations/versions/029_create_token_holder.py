# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *


meta = MetaData()

table = Table(
    "token_holder", meta,
    Column("holder_list", BigInteger, primary_key=True),
    Column("account_address", String(42), primary_key=True),
    Column("hold_balance", BigInteger),
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
