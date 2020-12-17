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

import sys

import pymysql
from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *
from migrations.log import LOG

from app import config

URI = config.DATABASE_URL
engine = create_engine(URI, echo=False)

meta = MetaData()

if engine.name != "mysql":
    notification_id_seq = Sequence(
        "notification_id_seq",
        metadata=meta,
        start=1,
        increment=1,
        minvalue=1,
        maxvalue=sys.maxsize,
        cache=1
    )


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    try:
        notification_table = Table("notification", meta)
        if engine.name != "mysql":
            try:
                notification_id_seq.create(bind=migrate_engine)
            except sqlalchemy.exc.ProgrammingError as err:
                LOG.warning(err.orig)

            col = Column(
                "id",
                BigInteger,
                server_default=notification_id_seq.next_value(),
                autoincrement=True
            )
        else:
            col = Column(
                "id",
                BigInteger,
                autoincrement=True
            )
        col.create(notification_table)
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが存在する場合はWARNINGを出力する
        LOG.warning(err.orig)
    except pymysql.err.OperationalError as err:  # NOTE: 既にカラムが存在する場合はWARNINGを出力する（MySQLの場合）
        LOG.warning(err)


def downgrade(migrate_engine):
    meta.bind = migrate_engine

    try:
        notification_table = Table("notification", meta)
        Column("id").drop(notification_table)
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが削除されている場合はWARNINGを出力する
        LOG.warning(err.orig)

    if engine.name != "mysql":
        try:
            notification_id_seq.drop(bind=migrate_engine)
        except sqlalchemy.exc.ProgrammingError as err:
            LOG.warning(err.orig)
