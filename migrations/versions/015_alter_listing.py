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

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *
from migrations.log import LOG

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine
    try:
        listing = Table("listing", meta, autoload=True)
        Column("payment_method_credit_card").drop(listing)
        Column("payment_method_bank").drop(listing)
    except sqlalchemy.exc.ProgrammingError as err:
        LOG.warning(err.orig)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    try:
        listing = Table("listing", meta, autoload=True)
        Column("payment_method_credit_card", Boolean).create(listing)
        Column("payment_method_bank", Boolean).create(listing)
    except sqlalchemy.exc.ProgrammingError as err:
        LOG.warning(err.orig)
