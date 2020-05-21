# -*- coding: utf-8 -*-
import logging

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    private_listing = Table("private_listing", meta, autoload=True)

    try:
        Column("payment_method_credit_card").drop(private_listing)
        Column("payment_method_bank").drop(private_listing)
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)


def downgrade(migrate_engine):
    meta.bind = migrate_engine

    private_listing = Table("private_listing", meta, autoload=True)

    col = Column("payment_method_credit_card", Boolean)
    try:
        col.create(private_listing)
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)

    col = Column("payment_method_bank", Boolean)
    try:
        col.create(private_listing)
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)
