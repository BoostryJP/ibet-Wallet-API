"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed onan "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

import logging

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    agreement = Table("agreement", meta, autoload=True)
    agreement.c.exchange_address.alter(type=String(42), index=True)
    agreement.c.buyer_address.alter(type=String(42), index=True)
    agreement.c.seller_address.alter(type=String(42), index=True)
    agreement.c.counterpart_address.alter(type=String(42))

    col = Column("transaction_hash", String(66))
    try:
        col.create(agreement)
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが存在する場合はWARNINGを出力する
        logging.warning(err)
    except Exception as err:
        logging.warning(err)

    col = Column("agreement_timestamp", DateTime, default=None)
    try:
        col.create(agreement)
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが存在する場合はWARNINGを出力する
        logging.warning(err)
    except Exception as err:
        logging.warning(err)


def downgrade(migrate_engine):
    meta.bind = migrate_engine

    agreement = Table("agreement", meta, autoload=True)
    agreement.c.exchange_address.alter(type=String(256), index=True)
    agreement.c.buyer_address.alter(type=String(256), index=True)
    agreement.c.seller_address.alter(type=String(256), index=True)
    agreement.c.counterpart_address.alter(type=String(256))

    Column("transaction_hash").drop(agreement)
    Column("agreement_timestamp").drop(agreement)
