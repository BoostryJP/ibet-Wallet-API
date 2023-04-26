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
import importlib
import logging
from datetime import datetime
from typing import Final

from pytest import LogCaptureFixture, fixture, mark
from pytest_alembic import MigrationContext
from sqlalchemy import Column, Integer, MetaData, String, Table, Text, insert, text
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateTable

from app.config import ZERO_ADDRESS
from app.database import engine

REVISION_22_3: Final = "a80595c53d52"
REVISION_22_6: Final = "e8d970fdd886"
REVISION_22_9: Final = "55dee53de2ca"
REVISION_22_12: Final = "446f913d1f41"
REVISION_23_3: Final = "1055cb068506"

REVISION_DOWN_TO_23_3 = [REVISION_23_3, REVISION_22_12]
REVISION_DOWN_TO_22_12 = REVISION_DOWN_TO_23_3 + [REVISION_22_9]
REVISION_DOWN_TO_22_9 = REVISION_DOWN_TO_22_12 + [REVISION_22_6]
REVISION_DOWN_TO_22_6 = REVISION_DOWN_TO_22_9 + [REVISION_22_3]


@fixture(scope="function", autouse=True)
def migration_test(caplog: LogCaptureFixture):
    m = MetaData()
    m.reflect(engine)
    m.drop_all(engine)
    if engine.name != "mysql":
        with engine.connect() as connect:
            connect.execute(text("DROP SEQUENCE IF EXISTS notification_id_seq"))
            connect.execute(text("DROP SEQUENCE IF EXISTS position_id_seq"))
            connect.execute(text("DROP SEQUENCE IF EXISTS executable_contract_id_seq"))
            connect.execute(
                text("DROP SEQUENCE IF EXISTS idx_position_bond_block_number_id_seq")
            )
            connect.execute(
                text("DROP SEQUENCE IF EXISTS idx_position_share_block_number_id_seq")
            )
            connect.execute(
                text(
                    "DROP SEQUENCE IF EXISTS idx_position_membership_block_number_id_seq"
                )
            )
            connect.execute(
                text("DROP SEQUENCE IF EXISTS idx_position_coupon_block_number_id_seq")
            )
            connect.commit()

    LOG = logging.getLogger("alembic.runtime.migration")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True

    yield caplog

    LOG.propagate = False
    LOG.setLevel(default_log_level)

    m = MetaData()
    m.reflect(engine)
    m.drop_all(engine)
    if engine.name != "mysql":
        with engine.connect() as connect:
            connect.execute(text("DROP SEQUENCE IF EXISTS notification_id_seq"))
            connect.execute(text("DROP SEQUENCE IF EXISTS position_id_seq"))
            connect.execute(text("DROP SEQUENCE IF EXISTS executable_contract_id_seq"))
            connect.execute(
                text("DROP SEQUENCE IF EXISTS idx_position_bond_block_number_id_seq")
            )
            connect.execute(
                text("DROP SEQUENCE IF EXISTS idx_position_share_block_number_id_seq")
            )
            connect.execute(
                text(
                    "DROP SEQUENCE IF EXISTS idx_position_membership_block_number_id_seq"
                )
            )
            connect.execute(
                text("DROP SEQUENCE IF EXISTS idx_position_coupon_block_number_id_seq")
            )
            connect.commit()


@fixture(scope="function", autouse=True)
def alembic_engine():
    yield engine


@fixture
def alembic_config():
    from alembic.config import Config

    cfg = Config("alembic.ini")
    return cfg


@mark.alembic
class TestMigrationsDowngrade:
    @staticmethod
    def sqlalchemy_migrate_definition(scripts: list) -> MetaData:
        for migrate_script in scripts:
            importlib.reload(migrate_script)
            migrate_script.downgrade(engine)
        m = MetaData()
        m.reflect(engine)
        return m

    @staticmethod
    def alembic_definition(
        revs: list[str], alembic_runner: MigrationContext
    ) -> MetaData:
        for rev in revs:
            alembic_runner.migrate_down_to(rev)
        m = MetaData()
        m.reflect(engine)
        return m

    @staticmethod
    def create_sorted_table(original_table: Table) -> Table:
        sorted_columns = sorted(original_table.columns, key=lambda c: c.name)
        sorted_table = Table(original_table.name, MetaData())
        for column in sorted_columns:
            column_copy = column._copy()
            sorted_table.append_column(column_copy)
        return sorted_table

    @classmethod
    def create_migrate_version(cls, db_engine: Engine, version: int):
        metadata = MetaData(bind=db_engine)
        migrate_version = Table(
            "migrate_version",
            metadata,
            Column("repository_id", String(250), primary_key=True),
            Column("repository_path", Text),
            Column("version", Integer),
        )
        metadata.create_all()

        with db_engine.connect() as connection:
            stmt = insert(migrate_version).values(
                {"repository_id": "apldb", "repository_path": ".", "version": version}
            )
            connection.execute(stmt)

    @staticmethod
    def get_migrate_version(db_engine: Engine):
        with db_engine.connect() as connection:
            return connection.execute(
                text("SELECT version FROM migrate_version")
            ).scalar()

    def test_downgrade_from_v23_6(
        self, alembic_runner: MigrationContext, caplog: LogCaptureFixture
    ):
        # 1-1. Migrate to v23.3
        alembic_runner.migrate_up_to(REVISION_23_3)
        metadata_bf = MetaData()
        metadata_bf.reflect(bind=engine)
        tables_bf = metadata_bf.tables
        table_name_list = set(metadata_bf.tables.keys())

        # 1-2. Migrate to v23.6
        alembic_runner.migrate_up_to("37cfcb200317")
        meta = MetaData()
        meta.reflect(bind=engine)

        # 2. Insert test record
        # NOTE: node data
        node = meta.tables.get("node")
        stmt1 = insert(node).values(id=2, is_synced=True)
        with engine.connect() as conn:
            conn.execute(stmt1)
            conn.commit()

        # NOTE: position data
        position = meta.tables.get("position")
        stmt1 = insert(position).values(
            token_address="token_address1",
            account_address="account_address1",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration
        stmt2 = insert(position).values(
            token_address="token_address1",
            account_address="account_address2",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration
        stmt3 = insert(position).values(
            token_address="token_address2",
            account_address="account_address2",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration
        with engine.connect() as conn:
            conn.execute(stmt1)
            conn.execute(stmt2)
            conn.execute(stmt3)
            conn.commit()

        # NOTE: executable_contract data
        executable_contract = meta.tables.get("executable_contract")
        stmt1 = insert(executable_contract).values(
            contract_address="token_address1",
            modified=datetime(2023, 4, 4, 0, 0, 0),
        )  # remains after migration
        stmt2 = insert(executable_contract).values(
            contract_address="token_address2",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration

        with engine.connect() as conn:
            conn.execute(stmt1)
            conn.execute(stmt2)
            conn.commit()

        # NOTE: idx_position_bond_block_number data
        idx_position_bond_block_number = meta.tables.get(
            "idx_position_bond_block_number"
        )
        stmt1 = insert(idx_position_bond_block_number).values(
            token_address="token_address1",
            exchange_address="exchange_address1",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration
        stmt2 = insert(idx_position_bond_block_number).values(
            token_address="token_address1",
            exchange_address="exchange_address2",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration
        stmt3 = insert(idx_position_bond_block_number).values(
            token_address="token_address2",
            exchange_address="exchange_address2",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration

        with engine.connect() as conn:
            conn.execute(stmt1)
            conn.execute(stmt2)
            conn.execute(stmt3)
            conn.commit()

        # NOTE: idx_position_share_block_number data
        idx_position_share_block_number = meta.tables.get(
            "idx_position_share_block_number"
        )
        stmt1 = insert(idx_position_share_block_number).values(
            token_address="token_address1",
            exchange_address="exchange_address1",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration
        stmt2 = insert(idx_position_share_block_number).values(
            token_address="token_address1",
            exchange_address="exchange_address2",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration
        stmt3 = insert(idx_position_share_block_number).values(
            token_address="token_address2",
            exchange_address="exchange_address2",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration

        with engine.connect() as conn:
            conn.execute(stmt1)
            conn.execute(stmt2)
            conn.execute(stmt3)
            conn.commit()

        # NOTE: idx_position_coupon_block_number data
        idx_position_coupon_block_number = meta.tables.get(
            "idx_position_coupon_block_number"
        )
        stmt1 = insert(idx_position_coupon_block_number).values(
            token_address="token_address1",
            exchange_address="exchange_address1",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration
        stmt2 = insert(idx_position_coupon_block_number).values(
            token_address="token_address1",
            exchange_address="exchange_address2",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration
        stmt3 = insert(idx_position_coupon_block_number).values(
            token_address="token_address2",
            exchange_address="exchange_address2",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration

        with engine.connect() as conn:
            conn.execute(stmt1)
            conn.execute(stmt2)
            conn.execute(stmt3)
            conn.commit()

        # NOTE: idx_position_membership_block_number data
        idx_position_membership_block_number = meta.tables.get(
            "idx_position_membership_block_number"
        )
        stmt1 = insert(idx_position_membership_block_number).values(
            token_address="token_address1",
            exchange_address="exchange_address1",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration
        stmt2 = insert(idx_position_membership_block_number).values(
            token_address="token_address1",
            exchange_address="exchange_address2",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration
        stmt3 = insert(idx_position_membership_block_number).values(
            token_address="token_address2",
            exchange_address="exchange_address2",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration

        with engine.connect() as conn:
            conn.execute(stmt1)
            conn.execute(stmt2)
            conn.execute(stmt3)
            conn.commit()

        idx_lock = meta.tables.get("lock")
        idx_unlock = meta.tables.get("unlock")
        stmt1 = insert(idx_lock).values(
            transaction_hash="." * 66,
            msg_sender=ZERO_ADDRESS,
            block_number=1,
            token_address="." * 42,
            lock_address="." * 42,
            account_address="." * 42,
            value=1,
            data={},
            block_timestamp=datetime(2023, 4, 25, 18, 50, 0),
        )
        stmt2 = insert(idx_lock).values(
            transaction_hash="." * 66,
            msg_sender=ZERO_ADDRESS,
            block_number=1,
            token_address="." * 42,
            lock_address="." * 42,
            account_address="." * 42,
            value=1,
            data={},
            block_timestamp=datetime(2023, 4, 25, 18, 50, 0),
        )
        stmt3 = insert(idx_unlock).values(
            transaction_hash="." * 66,
            msg_sender=ZERO_ADDRESS,
            block_number=1,
            token_address="." * 42,
            lock_address="." * 42,
            account_address="." * 42,
            recipient_address="." * 42,
            value=1,
            data={},
            block_timestamp=datetime(2023, 4, 25, 18, 50, 0),
        )
        stmt4 = insert(idx_unlock).values(
            transaction_hash="." * 66,
            msg_sender=ZERO_ADDRESS,
            block_number=1,
            token_address="." * 42,
            lock_address="." * 42,
            account_address="." * 42,
            recipient_address="." * 42,
            value=1,
            data={},
            block_timestamp=datetime(2023, 4, 25, 18, 50, 0),
        )
        with engine.connect() as conn:
            conn.execute(stmt1)
            conn.execute(stmt2)
            conn.execute(stmt3)
            conn.execute(stmt4)
            conn.commit()

        # 3. Downgrade
        alembic_runner.migrate_down_to(REVISION_23_3)
        metadata_af = MetaData()
        metadata_af.reflect(bind=engine)
        tables_af = metadata_af.tables

        with engine.connect() as conn:
            # NOTE: position
            all_row_count = conn.execute(text("SELECT COUNT(*) FROM position")).scalar()
            token_address_1_count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM position WHERE token_address = 'token_address1'"
                )
            ).scalar()

            # Ensure that there are 3 records.
            #    (token_address1, account_address1)
            #    (token_address1, account_address2)
            #    (token_address2, account_address2)
            assert all_row_count == 3
            assert token_address_1_count == 2

            # NOTE: executable_contract
            all_row_count = conn.execute(
                text("SELECT COUNT(*) FROM executable_contract")
            ).scalar()
            token_address_1_count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM executable_contract WHERE contract_address = 'token_address1'"
                )
            ).scalar()

            # Ensure that there are 2 records.
            #    (token_address1)
            #    (token_address2)
            assert all_row_count == 2
            assert token_address_1_count == 1

            # NOTE: idx_position_bond_block_number
            all_row_count = conn.execute(
                text("SELECT COUNT(*) FROM idx_position_bond_block_number")
            ).scalar()
            token_address_1_count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM idx_position_bond_block_number WHERE token_address = 'token_address1'"
                )
            ).scalar()

            # Ensure that there are 3 records.
            #    (token_address1, exchange_address1)
            #    (token_address1, exchange_address2)
            #    (token_address2, exchange_address2)
            assert all_row_count == 3
            assert token_address_1_count == 2

            # NOTE: idx_position_share_block_number
            all_row_count = conn.execute(
                text("SELECT COUNT(*) FROM idx_position_share_block_number")
            ).scalar()
            token_address_1_count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM idx_position_share_block_number WHERE token_address = 'token_address1'"
                )
            ).scalar()

            # Ensure that there are 3 records.
            #    (token_address1, exchange_address1)
            #    (token_address1, exchange_address2)
            #    (token_address2, exchange_address2)
            assert all_row_count == 3
            assert token_address_1_count == 2

            # NOTE: idx_position_coupon_block_number
            all_row_count = conn.execute(
                text("SELECT COUNT(*) FROM idx_position_coupon_block_number")
            ).scalar()
            token_address_1_count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM idx_position_coupon_block_number WHERE token_address = 'token_address1'"
                )
            ).scalar()

            # Ensure that there are 3 records.
            #    (token_address1, exchange_address1)
            #    (token_address1, exchange_address2)
            #    (token_address2, exchange_address2)
            assert all_row_count == 3
            assert token_address_1_count == 2

            # NOTE: idx_position_membership_block_number
            all_row_count = conn.execute(
                text("SELECT COUNT(*) FROM idx_position_membership_block_number")
            ).scalar()
            token_address_1_count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM idx_position_membership_block_number WHERE token_address = 'token_address1'"
                )
            ).scalar()

            # Ensure that there are 3 records.
            #    (token_address1, exchange_address1)
            #    (token_address1, exchange_address2)
            #    (token_address2, exchange_address2)
            assert all_row_count == 3
            assert token_address_1_count == 2

            # NOTE: idx_lock
            if engine.name == "mysql":
                all_row_count = conn.execute(
                    text(f"""SELECT COUNT(*) FROM `lock`;""")
                ).scalar()
            else:
                all_row_count = conn.execute(
                    text(f"""SELECT COUNT(*) FROM "lock";""")
                ).scalar()
            assert all_row_count == 2

            # NOTE: idx_unlock
            if engine.name == "mysql":
                all_row_count = conn.execute(
                    text(f"""SELECT COUNT(*) FROM `unlock`;""")
                ).scalar()
            else:
                all_row_count = conn.execute(
                    text(f"""SELECT COUNT(*) FROM "unlock";""")
                ).scalar()
            assert all_row_count == 2

        for assert_table_name in table_name_list:
            table_bf = self.create_sorted_table(tables_bf[assert_table_name])
            table_af = self.create_sorted_table(tables_af[assert_table_name])
            assert (
                CreateTable(table_af).compile(engine).string
                == CreateTable(table_bf).compile(engine).string
            )
