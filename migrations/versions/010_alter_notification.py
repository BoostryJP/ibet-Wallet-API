# -*- coding: utf-8 -*-
import logging
import sys

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *

meta = MetaData()

notification_id_seq = Sequence(
    "notification_id_seq",
    metadata=meta,
    start=1,
    increment=1,
    minvalue=1,
    maxvalue=sys.maxsize,
    cache=1
)


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    try:
        notification_id_seq.create(bind=migrate_engine)
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)

    notification_table = Table("notification", meta)
    col = Column(
        "id",
        BigInteger,
        server_default=notification_id_seq.next_value(),
        autoincrement=True
    )
    try:
        col.create(notification_table)
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが存在する場合はWARNINGを出力する
        logging.warning(err)


def downgrade(migrate_engine):
    meta.bind = migrate_engine

    notification_table = Table("notification", meta)
    try:
        Column("id").drop(notification_table)
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが削除されている場合はWARNINGを出力する
        logging.warning(err)

    try:
        notification_id_seq.drop(bind=migrate_engine)
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)
