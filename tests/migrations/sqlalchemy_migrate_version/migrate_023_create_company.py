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
from datetime import datetime

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError

from migrations.log import LOG

# Table定義
meta = MetaData()
table = Table(
    "company",
    meta,
    Column("address", String(42), primary_key=True),
    Column("corporate_name", Text),
    Column("rsa_publickey", String(2000)),
    Column("homepage", Text),
    Column("created", DateTime, default=datetime.utcnow),
    Column("modified", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
)


# Upgrade
def upgrade(migrate_engine):
    meta.bind = migrate_engine
    try:
        table.create()
    except ProgrammingError as err:  # NOTE: 既にTBLが存在する場合はWARNINGを出力する
        LOG.warning(err.orig)


# Downgrade
def downgrade(migrate_engine):
    meta.bind = migrate_engine
    try:
        table.drop()
    except Exception as err:
        LOG.warning(err)
