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

from migrate import *
from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError

from migrations.log import LOG

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    try:
        # NOTE: カラム追加
        transfer = Table("transfer", meta, autoload=True)
        Column("data", JSON).create(transfer)
        Column(
            "source_event", String(50), nullable=False, server_default="Transfer"
        ).create(transfer)

        # NOTE: 新規レコード登録時のデフォルト値設定の削除
        meta.clear()
        transfer = Table("transfer", meta, autoload=True)
        transfer.c.source_event.alter(String(50), nullable=False, server_default=None)

    except sqlalchemy.exc.ProgrammingError as err:
        LOG.warning(err.orig)


def downgrade(migrate_engine):
    meta.bind = migrate_engine

    try:
        transfer = Table("transfer", meta, autoload=True)
        Column("data").drop(transfer)
        Column("source_event").drop(transfer)

    except sqlalchemy.exc.ProgrammingError as err:
        LOG.warning(err.orig)
