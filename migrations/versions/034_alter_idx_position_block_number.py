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

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *
from migrations.log import LOG

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    try:
        idx_position_bond_block_number_table = Table("idx_position_bond_block_number", meta, autoload=True)
        _id_column = Column("id", BigInteger, primary_key=True, autoincrement=True)

        # Delete current record
        con = migrate_engine.connect()
        query = idx_position_bond_block_number_table.delete()
        con.execute(query)

        token_address_column = Column("token_address", String(42),  nullable=False)
        token_address_column.create(idx_position_bond_block_number_table)
        PrimaryKeyConstraint(_id_column, table=idx_position_bond_block_number_table).drop()
        PrimaryKeyConstraint(_id_column, token_address_column, table=idx_position_bond_block_number_table).create()
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが存在する場合はWARNINGを出力する
        LOG.warning(err.orig)

    try:
        idx_position_share_block_number_table = Table("idx_position_share_block_number", meta, autoload=True)
        _id_column = Column("id", BigInteger, primary_key=True, autoincrement=True)

        # Delete current record
        con = migrate_engine.connect()
        query = idx_position_share_block_number_table.delete()
        con.execute(query)

        token_address_column = Column("token_address", String(42),  nullable=False)
        token_address_column.create(idx_position_share_block_number_table)
        PrimaryKeyConstraint(_id_column, table=idx_position_share_block_number_table).drop()
        PrimaryKeyConstraint(_id_column, token_address_column, table=idx_position_share_block_number_table).create()
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが存在する場合はWARNINGを出力する
        LOG.warning(err.orig)

    try:
        idx_position_membership_block_number_table = Table("idx_position_membership_block_number", meta, autoload=True)
        _id_column = Column("id", BigInteger, primary_key=True, autoincrement=True)

        # Delete current record
        con = migrate_engine.connect()
        query = idx_position_membership_block_number_table.delete()
        con.execute(query)

        token_address_column = Column("token_address", String(42),  nullable=False)
        token_address_column.create(idx_position_membership_block_number_table)
        PrimaryKeyConstraint(_id_column, table=idx_position_membership_block_number_table).drop()
        PrimaryKeyConstraint(_id_column, token_address_column, table=idx_position_membership_block_number_table).create()
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが存在する場合はWARNINGを出力する
        LOG.warning(err.orig)

    try:
        idx_position_coupon_block_number_table = Table("idx_position_coupon_block_number", meta, autoload=True)
        _id_column = Column("id", BigInteger, primary_key=True, autoincrement=True)

        # Delete current record
        con = migrate_engine.connect()
        query = idx_position_coupon_block_number_table.delete()
        con.execute(query)

        token_address_column = Column("token_address", String(42),  nullable=False)
        token_address_column.create(idx_position_coupon_block_number_table)
        PrimaryKeyConstraint(_id_column, table=idx_position_coupon_block_number_table).drop()
        PrimaryKeyConstraint(_id_column, token_address_column, table=idx_position_coupon_block_number_table).create()
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが存在する場合はWARNINGを出力する
        LOG.warning(err.orig)


def downgrade(migrate_engine):
    meta.bind = migrate_engine

    try:
        idx_position_bond_block_number_table = Table("idx_position_bond_block_number", meta)
        Column("token_address").drop(idx_position_bond_block_number_table)
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが削除されている場合はWARNINGを出力する
        LOG.warning(err.orig)

    try:
        idx_position_share_block_number_table = Table("idx_position_share_block_number", meta)
        Column("token_address").drop(idx_position_share_block_number_table)
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが削除されている場合はWARNINGを出力する
        LOG.warning(err.orig)

    try:
        idx_position_membership_block_number_table = Table("idx_position_membership_block_number", meta)
        Column("token_address").drop(idx_position_membership_block_number_table)
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが削除されている場合はWARNINGを出力する
        LOG.warning(err.orig)

    try:
        idx_position_coupon_block_number_table = Table("idx_position_coupon_block_number", meta)
        Column("token_address").drop(idx_position_coupon_block_number_table)
    except sqlalchemy.exc.ProgrammingError as err:  # NOTE: 既にカラムが削除されている場合はWARNINGを出力する
        LOG.warning(err.orig)
