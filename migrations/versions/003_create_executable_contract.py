# -*- coding: utf-8 -*-
import logging

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *


# Table定義
meta = MetaData()
table = Table(
    "executable_contract", meta,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("contract_address", String(256), index=True),
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
