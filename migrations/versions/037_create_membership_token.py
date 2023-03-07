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
    "membership_token",
    meta,
    Column("token_address", String(42), primary_key=True),
    Column("token_template", String(40)),
    Column("owner_address", String(42), index=True),
    Column("company_name", Text),
    Column("rsa_publickey", String(2000)),
    Column("name", String(200)),
    Column("symbol", String(200)),
    Column("total_supply", BigInteger),
    Column("tradable_exchange", String(42), index=True),
    Column("contact_information", String(2000)),
    Column("privacy_policy", String(5000)),
    Column("status", Boolean),
    Column("max_holding_quantity", BigInteger),
    Column("max_sell_amount", BigInteger),
    Column("details", String(2000)),
    Column("return_details", String(2000)),
    Column("expiration_date", String(8)),
    Column("memo", String(2000)),
    Column("transferable", Boolean),
    Column("initial_offering_status", Boolean),
    Column("image_url", JSON),
    Column("short_term_cache_created", DateTime),
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
