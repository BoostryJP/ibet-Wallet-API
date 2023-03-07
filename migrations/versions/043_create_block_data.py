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

from migrate import *
from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError

meta = MetaData()

table = Table(
    "block_data",
    meta,
    Column("number", BigInteger, primary_key=True, autoincrement=False),
    Column("parent_hash", String(66), nullable=False),
    Column("sha3_uncles", String(66)),
    Column("miner", String(42)),
    Column("state_root", String(66)),
    Column("transactions_root", String(66)),
    Column("receipts_root", String(66)),
    Column("logs_bloom", String(514)),
    Column("difficulty", BigInteger),
    Column("gas_limit", Integer),
    Column("gas_used", Integer),
    Column("timestamp", Integer, nullable=False, index=True),
    Column("proof_of_authority_data", Text),
    Column("mix_hash", String(66)),
    Column("nonce", String(18)),
    Column("hash", String(66), nullable=False, index=True),
    Column("size", Integer),
    Column("transactions", JSON),
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
