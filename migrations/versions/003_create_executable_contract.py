# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *


# Table定義
meta = MetaData()
table = Table(
    "executable_contract", meta,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("contract_address", String(256), index=True),
    Column("created", DateTime, default=datetime.utcnow),
    Column("modified", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
