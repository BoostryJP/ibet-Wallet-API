# -*- coding: utf-8 -*-
import logging

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    listing = Table("listing", meta, autoload=True)
    try:
        col = Column("is_public", Boolean)
        col.create(listing)
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)


def downgrade(migrate_engine):
    meta.bind = migrate_engine

    listing = Table("listing", meta, autoload=True)
    try:
        Column("is_public").drop(listing)
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)
