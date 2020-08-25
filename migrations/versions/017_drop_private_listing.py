# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    private_listing = Table("private_listing", meta, autoload=True)
    try:
        private_listing.drop()
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)


def downgrade(migrate_engine):
    meta.bind = migrate_engine

    private_listing = Table(
        "private_listing", meta,
        Column("id", BigInteger, primary_key=True, autoincrement=True),
        Column("token_address", String(256), index=True),
        Column("max_holding_quantity", BigInteger),
        Column("max_sell_amount", BigInteger),
        Column("created", DateTime, default=datetime.utcnow),
        Column("modified", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
    try:
        private_listing.create()
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にTBLが存在する場合はWARNINGを出力する
        logging.warning(err)
