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

from app.database import engine

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


@fixture(scope="function", autouse=True)
def migration_test(caplog: LogCaptureFixture):
    m = MetaData()
    m.reflect(engine)
    m.drop_all(engine)
    if engine.name != "mysql":
        with engine.connect() as connect:
            connect.execute(text("DROP SEQUENCE IF EXISTS notification_id_seq"))
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
class TestMigrationsUpgrade:
    @staticmethod
    def sqlalchemy_migrate_definition(scripts: list) -> MetaData:
        for migrate_script in scripts:
            importlib.reload(migrate_script)
            migrate_script.upgrade(engine)
        m = MetaData(bind=engine)
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
        metadata = MetaData()
        migrate_version = Table(
            "migrate_version",
            metadata,
            Column("repository_id", String(250), primary_key=True),
            Column("repository_path", Text),
            Column("version", Integer),
        )
        metadata.create_all(bind=db_engine)

        with db_engine.connect() as connection:
            stmt = insert(migrate_version).values(
                {"repository_id": "apldb", "repository_path": ".", "version": version}
            )
            connection.execute(stmt)
            connection.commit()

    @classmethod
    def reset_alembic_revision(cls, db_engine: Engine):
        metadata = MetaData()
        alembic_version = Table(
            "alembic_version",
            metadata,
            Column("version_num", String(32), primary_key=True),
        )
        metadata.drop_all(bind=db_engine)

    @staticmethod
    def get_migrate_version(db_engine: Engine):
        with db_engine.connect() as connection:
            return connection.execute(
                text("SELECT version FROM migrate_version")
            ).scalar()

    @mark.parametrize("from_legacy_migration", [True, False])
    def test_upgrade_v22_3_to_head(
        self,
        alembic_runner: MigrationContext,
        caplog: LogCaptureFixture,
        from_legacy_migration: bool,
    ):
        # 1. Migrate at v22.3
        meta = self.alembic_definition(REVISION_UP_TO_1_8, alembic_runner)
        if from_legacy_migration:
            self.reset_alembic_revision(engine)
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

        # 3. Migrate up to head
        alembic_runner.migrate_up_to("head")
        if from_legacy_migration:
            assert self.get_migrate_version(engine) == 54

    @mark.parametrize("from_legacy_migration", [True, False])
    def test_upgrade_v22_6_to_head(
        self,
        alembic_runner: MigrationContext,
        caplog: LogCaptureFixture,
        from_legacy_migration: bool,
    ):
        # 1. Migrate at v22.6
        meta = self.alembic_definition(REVISION_UP_TO_22_6, alembic_runner)
        if from_legacy_migration:
            self.reset_alembic_revision(engine)
            self.create_migrate_version(engine, 34)
            alembic_runner.config.alembic_config.set_main_option(
                "sqlalchemy_migrate_version", str("34")
            )
        assert "WARNING" not in caplog.text

        # 2. Insert null contained data
        with engine.connect() as conn:
            pass

        # 3. Migrate up to head
        alembic_runner.migrate_up_to("head")
        if from_legacy_migration:
            assert self.get_migrate_version(engine) == 54

    @mark.parametrize("from_legacy_migration", [True, False])
    def test_upgrade_v22_9_to_v23_6_initial(
        self,
        alembic_runner: MigrationContext,
        caplog: LogCaptureFixture,
        from_legacy_migration: bool,
    ):
        # 1. Migrate at v22.9
        meta = self.alembic_definition(REVISION_UP_TO_22_9, alembic_runner)
        if from_legacy_migration:
            self.reset_alembic_revision(engine)
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
            conn.commit()

        # 3. Migrate up to head
        alembic_runner.migrate_up_to("head")
        if from_legacy_migration:
            assert self.get_migrate_version(engine) == 54

    @mark.parametrize("from_legacy_migration", [True, False])
    def test_upgrade_v22_12_to_v23_6_initial(
        self,
        alembic_runner: MigrationContext,
        caplog: LogCaptureFixture,
        from_legacy_migration: bool,
    ):
        # 1. Migrate at v22.12
        meta = self.alembic_definition(REVISION_UP_TO_22_12, alembic_runner)
        if from_legacy_migration:
            self.reset_alembic_revision(engine)
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
            conn.commit()

        # 3. Migrate up to head
        alembic_runner.migrate_up_to("head")
        if from_legacy_migration:
            assert self.get_migrate_version(engine) == 54

    @mark.parametrize("from_legacy_migration", [True, False])
    def test_upgrade_v23_3_to_v23_6_initial(
        self,
        alembic_runner: MigrationContext,
        caplog: LogCaptureFixture,
        from_legacy_migration: bool,
    ):
        # 1. Migrate at v23.3
        meta = self.alembic_definition(REVISION_UP_TO_23_3, alembic_runner)
        if from_legacy_migration:
            self.reset_alembic_revision(engine)
            self.create_migrate_version(engine, 54)
            alembic_runner.config.alembic_config.set_main_option(
                "sqlalchemy_migrate_version", str("54")
            )
        assert "WARNING" not in caplog.text

        # 2. Insert null contained data

        # 3. Migrate up to head
        alembic_runner.migrate_up_to("head")
        if from_legacy_migration:
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
            conn.commit()

        position = meta.tables.get("position")
        stmt1 = insert(position).values(
            id=1,
            token_address=None,
            account_address=None,
            modified=datetime(2023, 4, 1, 0, 0, 0),
        )  # removed after migration
        stmt2 = insert(position).values(
            id=2,
            token_address=None,
            account_address=None,
            modified=datetime(2023, 4, 2, 0, 0, 0),
        )  # removed after migration
        stmt3 = insert(position).values(
            id=3,
            token_address="token_address1",
            account_address=None,
            modified=datetime(2023, 4, 3, 0, 0, 0),
        )  # removed after migration
        stmt4 = insert(position).values(
            id=4,
            token_address=None,
            account_address="account_address1",
            modified=datetime(2023, 4, 4, 0, 0, 0),
        )  # removed after migration
        stmt5 = insert(position).values(
            id=5,
            token_address="token_address1",
            account_address="account_address1",
            modified=datetime(2023, 4, 5, 0, 0, 0),
        )  # removed after migration
        stmt6 = insert(position).values(
            id=6,
            token_address="token_address1",
            account_address="account_address1",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration
        stmt7 = insert(position).values(
            id=7,
            token_address="token_address1",
            account_address="account_address2",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration
        stmt8 = insert(position).values(
            id=8,
            token_address="token_address2",
            account_address="account_address2",
            modified=datetime(2023, 4, 5, 0, 0, 0),
        )  # removed after migration
        stmt9 = insert(position).values(
            id=9,
            token_address="token_address2",
            account_address="account_address2",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration

        with engine.connect() as conn:
            conn.execute(stmt1)
            conn.execute(stmt2)
            conn.execute(stmt3)
            conn.execute(stmt4)
            conn.execute(stmt5)
            conn.execute(stmt6)
            conn.execute(stmt7)
            conn.execute(stmt8)
            conn.execute(stmt9)
            conn.commit()

        executable_contract = meta.tables.get("executable_contract")
        stmt1 = insert(executable_contract).values(
            id=1,
            contract_address=None,
            modified=datetime(2023, 4, 1, 0, 0, 0),
        )  # removed after migration
        stmt2 = insert(executable_contract).values(
            id=2,
            contract_address=None,
            modified=datetime(2023, 4, 2, 0, 0, 0),
        )  # removed after migration
        stmt3 = insert(executable_contract).values(
            id=3,
            contract_address="token_address1",
            modified=datetime(2023, 4, 3, 0, 0, 0),
        )  # removed after migration
        stmt4 = insert(executable_contract).values(
            id=4,
            contract_address="token_address1",
            modified=datetime(2023, 4, 4, 0, 0, 0),
        )  # remains after migration
        stmt5 = insert(executable_contract).values(
            id=5,
            contract_address="token_address2",
            modified=datetime(2023, 4, 5, 0, 0, 0),
        )  # removed after migration
        stmt6 = insert(executable_contract).values(
            id=6,
            contract_address="token_address2",
            modified=datetime(2023, 4, 6, 0, 0, 0),
        )  # remains after migration

        with engine.connect() as conn:
            conn.execute(stmt1)
            conn.execute(stmt2)
            conn.execute(stmt3)
            conn.execute(stmt4)
            conn.execute(stmt5)
            conn.execute(stmt6)
            conn.commit()

        # 3. Run to head
        alembic_runner.migrate_up_to("head")

        with engine.connect() as conn:
            all_position_row_count = conn.execute(
                text("SELECT COUNT(*) FROM position")
            ).scalar()
            token_address_1_count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM position WHERE token_address = 'token_address1'"
                )
            ).scalar()

            # Ensure that there are 3 records.
            #    (token_address1, account_address1)
            #    (token_address1, account_address2)
            #    (token_address2, account_address2)
            assert all_position_row_count == 3
            assert token_address_1_count == 2

            all_executable_contract_row_count = conn.execute(
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
            assert all_executable_contract_row_count == 2
            assert token_address_1_count == 1
