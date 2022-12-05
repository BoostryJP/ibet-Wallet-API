"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""
import logging
from datetime import datetime

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *


meta = MetaData()

table = Table(
    "tx_data", meta,
    Column("hash", String(66), primary_key=True),
    Column("block_hash", String(66)),
    Column("block_number", BigInteger, index=True),
    Column("transaction_index", Integer),
    Column("from_address", String(42), index=True),
    Column("to_address", String(42), index=True),
    Column("input", String),
    Column("gas", Integer),
    Column("gas_price", BigInteger),
    Column("value", BigInteger),
    Column("nonce", Integer),
    Column("created", DateTime, default=datetime.utcnow),
    Column("modified", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
)


def upgrade(migrate_engine):
    meta.bind = migrate_engine
    try:
        table.create()
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    table.drop()
