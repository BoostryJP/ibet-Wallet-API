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

from datetime import datetime

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *
from migrations.log import LOG


# Table定義
meta = MetaData()
table = Table(
    "notification", meta,
    Column("notification_id", String(256), primary_key=True),
    Column("notification_type", String(256)),
    Column("priority", Integer),
    Column("address", String(256)),
    Column("is_read", Boolean, default=False),
    Column("is_flagged", Boolean, default=False),
    Column("is_deleted", Boolean, default=False),
    Column("deleted_at", DateTime, default=None),
    Column("block_timestamp", DateTime),
    Column("args", JSON),
    Column("metainfo", JSON),
    Column("created", DateTime, default=datetime.utcnow),
    Column("modified", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
)

notification_index_1 = Index(
    "notification_index_1",
    table.c.address,
    table.c.notification_id
)

notification_index_2 = Index(
    "notification_index_2",
    table.c.address,
    table.c.priority,
    table.c.notification_id
)


# Upgrade
def upgrade(migrate_engine):
    meta.bind = migrate_engine
    try:
        table.create()
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にTBLが存在する場合はWARNINGを出力する
        LOG.warning(err.orig)


# Downgrade
def downgrade(migrate_engine):
    meta.bind = migrate_engine
    table.drop()
