# -*- coding: utf-8 -*-
import logging

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    order = Table("order", meta, autoload=True)

    col = Column("counterpart_address", String(42))
    try:
        col.create(order)
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)


def downgrade(migrate_engine):
    meta.bind = migrate_engine

    order = Table("order", meta, autoload=True)

    try:
        Column("counterpart_address").drop(order)
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)
