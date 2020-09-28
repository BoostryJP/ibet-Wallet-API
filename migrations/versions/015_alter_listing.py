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
        Column("payment_method_credit_card").drop(listing)
        Column("payment_method_bank").drop(listing)
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)
    except Exception as err:
        logging.warning(err)


def downgrade(migrate_engine):
    meta.bind = migrate_engine

    listing = Table("listing", meta, autoload=True)

    col = Column("payment_method_credit_card", Boolean)
    try:
        col.create(listing)
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)
    except Exception as err:
        logging.warning(err)

    col = Column("payment_method_bank", Boolean)
    try:
        col.create(listing)
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)
    except Exception as err:
        logging.warning(err)
