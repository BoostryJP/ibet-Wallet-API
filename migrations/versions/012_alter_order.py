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

    order = Table("order", meta, autoload=True)
    order.c.token_address.alter(type=String(42), index=True)
    order.c.exchange_address.alter(type=String(42), index=True)
    order.c.account_address.alter(type=String(42))
    order.c.agent_address.alter(type=String(42))

    col = Column("transaction_hash", String(66))
    try:
        col.create(order)
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが存在する場合はWARNINGを出力する
        logging.warning(err)
    except Exception as err:
        logging.warning(err)

    col = Column("order_timestamp", DateTime, default=None)
    try:
        col.create(order)
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが存在する場合はWARNINGを出力する
        logging.warning(err)
    except Exception as err:
        logging.warning(err)


def downgrade(migrate_engine):
    meta.bind = migrate_engine

    order = Table("order", meta, autoload=True)
    order.c.token_address.alter(type=String(256), index=True)
    order.c.exchange_address.alter(type=String(256), index=True)
    order.c.account_address.alter(type=String(256))
    order.c.agent_address.alter(type=String(256))

    Column("transaction_hash").drop(order)
    Column("order_timestamp").drop(order)
