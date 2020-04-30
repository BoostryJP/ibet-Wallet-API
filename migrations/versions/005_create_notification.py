# -*- coding: utf-8 -*-
import logging

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *


# Table定義
meta = MetaData()
table = Table(
    "notification", meta,
    Column("notification_id", String(256), primary_key=True),
    Column("notification_type", String(256)),
    Column("priority", Integer),
    Column("address", String(256)),
    Column("is_read", Boolean, default=False),
    Column("is_flagged", Boolean, default=False),
    Column("is_deleted", Boolean, default=False),
    Column("deleted_at", DateTime, default=None),
    Column("block_timestamp", DateTime),
    Column("args", JSON),
    Column("metainfo", JSON),
    Column("created", DateTime, default=func.now()),
    Column("modified", DateTime, default=func.now(), onupdate=func.now())
)

notification_index_1 = Index(
    "notification_index_1",
    table.c.address,
    table.c.notification_id
)

notification_index_2 = Index(
    "notification_index_2",
    table.c.address,
    table.c.priority,
    table.c.notification_id
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
