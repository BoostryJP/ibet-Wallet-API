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
from typing import Final
from app.database import engine
from pytest_alembic import MigrationContext
from pytest import LogCaptureFixture, fixture, mark
from sqlalchemy_migrate_version import (
    migrate_001_create_agreement,
    migrate_002_create_consume_coupon,
    migrate_003_create_executable_contract,
    migrate_004_create_listing,
    migrate_005_create_notification,
    migrate_006_create_order,
    migrate_007_create_position,
    migrate_008_create_private_listing,
    migrate_009_alter_listing_and_private_listing,
    migrate_010_alter_notification,
    migrate_011_create_transfer,
    migrate_012_alter_order,
    migrate_013_alter_agreement,
    migrate_014_alter_order,
    migrate_015_alter_listing,
    migrate_016_alter_private_listing,
    migrate_017_drop_private_listing,
    migrate_018_alter_listing,
    migrate_019_create_node,
    migrate_020_alter_position,
    migrate_021_create_transfer_approval,
    migrate_022_alter_node,
    migrate_023_create_company,
    migrate_024_alter_transfer_approval,
    migrate_025_alter_position,
    migrate_026_alter_transfer_approval,
    migrate_027_alter_transfer_approval,
    migrate_028_create_token_holders_list,
    migrate_029_create_token_holder,
    migrate_030_create_idx_position_bond_block_number,
    migrate_031_create_idx_position_share_block_number,
    migrate_032_create_idx_position_membership_block_number,
    migrate_033_create_idx_position_coupon_block_number,
    migrate_034_create_idx_transfer_approval_block_number,
    migrate_035_create_bond_token,
    migrate_036_create_share_token,
    migrate_037_create_membership_token,
    migrate_038_create_coupon_token,
    migrate_039_create_token_list,
    migrate_040_create_idx_token_list_block_number,
    migrate_041_create_idx_transfer_block_number,
    migrate_042_create_notification_block_number,
    migrate_043_create_block_data,
    migrate_044_create_idx_block_data_block_number,
    migrate_045_create_tx_data,
    migrate_046_alter_bond_token,
    migrate_047_alter_share_token,
    migrate_048_create_locked_position,
    migrate_049_create_lock,
    migrate_050_create_unlock,
    migrate_051_alter_transfer,
    migrate_052_create_mail,
    migrate_053_alter_token_holder,
    migrate_054_create_chat_webhook,
)
from sqlalchemy import (
    MetaData,
    Table,
    Column,
    String,
    Integer,
    Text,
    insert,
)
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateTable


REVISION_22_3: Final = "a80595c53d52"
REVISION_22_6: Final = "e8d970fdd886"
REVISION_22_9: Final = "55dee53de2ca"
REVISION_22_12: Final = "446f913d1f41"
REVISION_23_3: Final = "1055cb068506"

REVISION_UP_TO_1_8 = [REVISION_22_3]
REVISION_UP_TO_22_6 = REVISION_UP_TO_1_8 + [REVISION_22_6]
REVISION_UP_TO_22_9 = REVISION_UP_TO_22_6 + [REVISION_22_9]
REVISION_UP_TO_22_12 = REVISION_UP_TO_22_9 + [REVISION_22_12]
REVISION_UP_TO_23_3 = REVISION_UP_TO_22_12 + [REVISION_23_3]

MIGRATIONS_22_3: Final = [
    migrate_001_create_agreement,
    migrate_002_create_consume_coupon,
    migrate_003_create_executable_contract,
    migrate_004_create_listing,
    migrate_005_create_notification,
    migrate_006_create_order,
    migrate_007_create_position,
    migrate_008_create_private_listing,
    migrate_009_alter_listing_and_private_listing,
    migrate_010_alter_notification,
    migrate_011_create_transfer,
    migrate_012_alter_order,
    migrate_013_alter_agreement,
    migrate_014_alter_order,
    migrate_015_alter_listing,
    migrate_016_alter_private_listing,
    migrate_017_drop_private_listing,
    migrate_018_alter_listing,
    migrate_019_create_node,
    migrate_020_alter_position,
    migrate_021_create_transfer_approval,
    migrate_022_alter_node,
    migrate_023_create_company,
    migrate_024_alter_transfer_approval,
    migrate_025_alter_position,
    migrate_026_alter_transfer_approval,
]
MIGRATIONS_22_6: Final = [
    migrate_027_alter_transfer_approval,
    migrate_028_create_token_holders_list,
    migrate_029_create_token_holder,
    migrate_030_create_idx_position_bond_block_number,
    migrate_031_create_idx_position_share_block_number,
    migrate_032_create_idx_position_membership_block_number,
    migrate_033_create_idx_position_coupon_block_number,
]
MIGRATIONS_22_9: Final = [
    migrate_034_create_idx_transfer_approval_block_number,
    migrate_035_create_bond_token,
    migrate_036_create_share_token,
    migrate_037_create_membership_token,
    migrate_038_create_coupon_token,
    migrate_039_create_token_list,
    migrate_040_create_idx_token_list_block_number,
]
MIGRATIONS_22_12: Final = [
    migrate_041_create_idx_transfer_block_number,
    migrate_042_create_notification_block_number,
    migrate_043_create_block_data,
    migrate_044_create_idx_block_data_block_number,
    migrate_045_create_tx_data,
    migrate_046_alter_bond_token,
    migrate_047_alter_share_token,
]
MIGRATIONS_23_3: Final = [
    migrate_048_create_locked_position,
    migrate_049_create_lock,
    migrate_050_create_unlock,
    migrate_051_alter_transfer,
    migrate_052_create_mail,
    migrate_053_alter_token_holder,
    migrate_054_create_chat_webhook,
]

MIGRATIONS_UP_TO_22_3 = MIGRATIONS_22_3
MIGRATIONS_UP_TO_22_6 = MIGRATIONS_UP_TO_22_3 + MIGRATIONS_22_6
MIGRATIONS_UP_TO_22_9 = MIGRATIONS_UP_TO_22_6 + MIGRATIONS_22_9
MIGRATIONS_UP_TO_22_12 = MIGRATIONS_UP_TO_22_9 + MIGRATIONS_22_12
MIGRATIONS_UP_TO_23_3 = MIGRATIONS_UP_TO_22_12 + MIGRATIONS_23_3


@fixture(scope="function", autouse=True)
def migration_test(caplog: LogCaptureFixture):
    m = MetaData()
    m.reflect(engine)
    m.drop_all(engine)
    if engine.name != "mysql":
        engine.execute("DROP SEQUENCE IF EXISTS notification_id_seq")

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
        engine.execute("DROP SEQUENCE IF EXISTS notification_id_seq")


@fixture(scope="function", autouse=True)
def alembic_engine():
    yield engine


@fixture
def alembic_config():
    from alembic.config import Config

    cfg = Config("alembic.ini")
    return cfg


@mark.alembic
class TestMigrationsUpgrade:
    @staticmethod
    def sqlalchemy_migrate_definition(scripts: list) -> MetaData:
        for migrate_script in scripts:
            importlib.reload(migrate_script)
            migrate_script.upgrade(engine)
        m = MetaData()
        m.reflect(engine)
        return m

    @staticmethod
    def alembic_definition(
        revs: list[str], alembic_runner: MigrationContext
    ) -> MetaData:
        for rev in revs:
            alembic_runner.migrate_up_to(rev)
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
            return connection.execute("SELECT version FROM migrate_version").scalar()

    @mark.parametrize(
        "alembic_revs, migrate_scripts",
        [
            (REVISION_UP_TO_1_8, MIGRATIONS_UP_TO_22_3),
            (REVISION_UP_TO_22_6, MIGRATIONS_UP_TO_22_6),
            (REVISION_UP_TO_22_9, MIGRATIONS_UP_TO_22_9),
            (REVISION_UP_TO_22_12, MIGRATIONS_UP_TO_22_12),
            (REVISION_UP_TO_23_3, MIGRATIONS_UP_TO_23_3),
        ],
    )
    def test_verify_alembic_output(
        self,
        alembic_revs: list[str],
        migrate_scripts: list,
        alembic_runner: MigrationContext,
        caplog: LogCaptureFixture,
    ):
        metadata_alembic = self.alembic_definition(alembic_revs, alembic_runner)
        tables_alembic = metadata_alembic.tables
        table_name_list_alembic = set(metadata_alembic.tables.keys())
        metadata_alembic.drop_all(engine)
        if engine.name != "mysql":
            engine.execute("DROP SEQUENCE IF EXISTS notification_id_seq")

        metadata_migrate = self.sqlalchemy_migrate_definition(migrate_scripts)
        tables_migrate = metadata_migrate.tables
        table_name_list_migrate = set(metadata_migrate.tables.keys())

        common_table_names = table_name_list_alembic.intersection(
            table_name_list_migrate
        )

        for assert_table_name in common_table_names:
            table_alembic = self.create_sorted_table(tables_alembic[assert_table_name])
            table_migrate = self.create_sorted_table(tables_migrate[assert_table_name])
            assert (
                CreateTable(table_alembic).compile(engine).string
                == CreateTable(table_migrate).compile(engine).string
            )

        metadata_migrate.drop_all(engine)

    def test_upgrade_v22_3_to_v23_6_initial(
        self, alembic_runner: MigrationContext, caplog: LogCaptureFixture
    ):
        # 1. Migrate at v1.8
        meta = self.sqlalchemy_migrate_definition(MIGRATIONS_UP_TO_22_3)
        self.create_migrate_version(engine, 26)
        alembic_runner.config.alembic_config.set_main_option(
            "sqlalchemy_migrate_version", str("26")
        )
        assert "WARNING" not in caplog.text

        # 2. Insert null contained data
        #   027_alter_transfer_approval.py
        transfer_approval = meta.tables.get("transfer_approval")
        stmt1 = insert(transfer_approval).values(id=1)
        with engine.connect() as conn:
            conn.execute(stmt1)

        # 3. Migrate up to initial state of 23.6
        for rev in [
            REVISION_22_3,
            REVISION_22_6,
            REVISION_22_9,
            REVISION_22_12,
            REVISION_23_3,
        ]:
            alembic_runner.migrate_up_to(rev)
        assert self.get_migrate_version(engine) == 54

    def test_upgrade_v22_6_to_v23_6_initial(
        self, alembic_runner: MigrationContext, caplog: LogCaptureFixture
    ):
        # 1. Migrate at v22.6
        meta = self.sqlalchemy_migrate_definition(MIGRATIONS_UP_TO_22_6)
        self.create_migrate_version(engine, 34)
        alembic_runner.config.alembic_config.set_main_option(
            "sqlalchemy_migrate_version", str("34")
        )
        assert "WARNING" not in caplog.text

        # 2. Insert null contained data
        with engine.connect() as conn:
            pass

        # 3. Migrate up to initial state of 23.6
        for rev in [
            REVISION_22_3,
            REVISION_22_6,
            REVISION_22_9,
            REVISION_22_12,
            REVISION_23_3,
        ]:
            alembic_runner.migrate_up_to(rev)
        assert self.get_migrate_version(engine) == 54

    def test_upgrade_v22_9_to_v23_6_initial(
        self, alembic_runner: MigrationContext, caplog: LogCaptureFixture
    ):
        # 1. Migrate at v22.9
        meta = self.sqlalchemy_migrate_definition(MIGRATIONS_UP_TO_22_9)
        self.create_migrate_version(engine, 47)
        alembic_runner.config.alembic_config.set_main_option(
            "sqlalchemy_migrate_version", str("47")
        )
        assert "WARNING" not in caplog.text

        # 2. Insert null contained data
        #   046_alter_bond_token.py
        bond_token = meta.tables.get("bond_token")
        stmt1 = insert(bond_token).values(token_address="." * 42, memo="." * 2000)
        #   047_alter_share_token.py
        share_token = meta.tables.get("share_token")
        stmt2 = insert(share_token).values(token_address="." * 42, memo="." * 2000)
        with engine.connect() as conn:
            conn.execute(stmt1)
            conn.execute(stmt2)

        # 3. Migrate up to initial state of 23.6
        for rev in [
            REVISION_22_3,
            REVISION_22_6,
            REVISION_22_9,
            REVISION_22_12,
            REVISION_23_3,
        ]:
            alembic_runner.migrate_up_to(rev)
        assert self.get_migrate_version(engine) == 54

    def test_upgrade_v22_12_to_v23_6_initial(
        self, alembic_runner: MigrationContext, caplog: LogCaptureFixture
    ):
        # 1. Migrate at v22.12
        meta = self.sqlalchemy_migrate_definition(MIGRATIONS_UP_TO_22_12)
        self.create_migrate_version(engine, 47)
        alembic_runner.config.alembic_config.set_main_option(
            "sqlalchemy_migrate_version", str("47")
        )
        assert "WARNING" not in caplog.text

        # 2. Insert null contained data
        #   052_alter_transfer.py
        transfer = meta.tables.get("transfer")
        stmt1 = insert(transfer).values(id=1)
        #   053_alter_token_holder.py
        token_holder = meta.tables.get("token_holder")
        stmt2 = insert(token_holder).values(holder_list=1, account_address="." * 42)

        with engine.connect() as conn:
            conn.execute(stmt1)
            conn.execute(stmt2)

        # 3. Migrate up to initial state of 23.6
        for rev in [
            REVISION_22_3,
            REVISION_22_6,
            REVISION_22_9,
            REVISION_22_12,
            REVISION_23_3,
        ]:
            alembic_runner.migrate_up_to(rev)
        assert self.get_migrate_version(engine) == 54

    def test_upgrade_v23_3_to_v23_6_initial(
        self, alembic_runner: MigrationContext, caplog: LogCaptureFixture
    ):
        # 1. Migrate at v23.3
        self.sqlalchemy_migrate_definition(MIGRATIONS_UP_TO_23_3)
        self.create_migrate_version(engine, 54)
        alembic_runner.config.alembic_config.set_main_option(
            "sqlalchemy_migrate_version", str("54")
        )
        assert "WARNING" not in caplog.text

        # 2. Insert null contained data

        # 3. Migrate up to initial state of 23.6
        for rev in [
            REVISION_22_3,
            REVISION_22_6,
            REVISION_22_9,
            REVISION_22_12,
            REVISION_23_3,
        ]:
            alembic_runner.migrate_up_to(rev)
        assert self.get_migrate_version(engine) == 54

    def test_upgrade_v23_6_to(
        self, alembic_runner: MigrationContext, caplog: LogCaptureFixture
    ):
        # 1. Migrate to v23.6 initial
        alembic_runner.migrate_up_to(REVISION_23_3)
        meta = MetaData()
        meta.reflect(bind=engine)

        # 2. Insert test record
        node = meta.tables.get("node")
        stmt1 = insert(node).values(id=1, is_synced=None)
        stmt2 = insert(node).values(id=2, is_synced=True)
        with engine.connect() as conn:
            conn.execute(stmt1)
            conn.execute(stmt2)

        # 3. Run to head
        alembic_runner.migrate_up_to("head")
