"""v23_6_feature_1377

Revision ID: 40ee030e9302
Revises: ca8ff8c0c01d
Create Date: 2023-04-07 11:07:01.686463

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


from app.database import get_db_schema, engine
from app.model.db import IDXPosition, ExecutableContract, IDXPositionBondBlockNumber

# revision identifiers, used by Alembic.
revision = "40ee030e9302"
down_revision = "ca8ff8c0c01d"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    ############################
    # Migration for position
    ############################
    op.get_bind().execute(sa.text(f"DELETE FROM position WHERE token_address IS null;"))
    op.get_bind().execute(
        sa.text(f"DELETE FROM position WHERE account_address IS null;")
    )
    op.get_bind().execute(sa.text(f"DELETE FROM position WHERE modified IS null;"))
    op.get_bind().execute(
        sa.text(
            f"""DELETE FROM position WHERE (modified) NOT IN (
                    SELECT latest_position.max_modified AS modified FROM (
                        SELECT  max(modified) AS max_modified FROM position GROUP BY token_address, account_address
                    ) AS latest_position
                );"""
        )
    )
    op.alter_column(
        "position",
        "token_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "position",
        "account_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=False,
        schema=get_db_schema(),
    )
    op.drop_index(
        "ix_position_token_address",
        table_name="position",
        schema=get_db_schema(),
    )
    op.drop_column("position", "id", schema=get_db_schema())
    op.create_primary_key(
        "position_pkey", "position", ["token_address", "account_address"]
    )

    ############################
    # Migration for executable_contract
    ############################
    op.get_bind().execute(
        sa.text(f"DELETE FROM executable_contract WHERE contract_address IS null;")
    )
    op.get_bind().execute(
        sa.text(f"DELETE FROM executable_contract WHERE contract_address IS null;")
    )
    op.get_bind().execute(
        sa.text(f"DELETE FROM executable_contract WHERE modified IS null;")
    )
    op.get_bind().execute(
        sa.text(
            f"""DELETE FROM executable_contract WHERE (modified) NOT IN (
                    SELECT latest_executable_contract.max_modified AS modified FROM (
                        SELECT  max(modified) AS max_modified FROM executable_contract GROUP BY contract_address
                    ) AS latest_executable_contract
                );"""
        )
    )
    op.alter_column(
        "executable_contract",
        "contract_address",
        existing_type=sa.VARCHAR(length=256),
        nullable=False,
        schema=get_db_schema(),
    )
    op.drop_index(
        "ix_executable_contract_contract_address",
        table_name="executable_contract",
        schema=get_db_schema(),
    )
    op.drop_column("executable_contract", "id", schema=get_db_schema())
    op.create_primary_key(
        "executable_contract_pkey",
        "executable_contract",
        ["contract_address"],
        schema=get_db_schema(),
    )

    ############################
    # Migration for idx_position_bond_block_number
    ############################
    op.get_bind().execute(
        sa.text(f"DELETE FROM idx_position_bond_block_number WHERE modified IS null;")
    )
    op.get_bind().execute(
        sa.text(
            f"""DELETE FROM idx_position_bond_block_number WHERE (modified) NOT IN (
                    SELECT latest_idx_position_bond_block_number.max_modified AS modified FROM (
                        SELECT  max(modified) AS max_modified FROM idx_position_bond_block_number GROUP BY token_address, exchange_address
                    ) AS latest_idx_position_bond_block_number
                );"""
        )
    )
    op.drop_column("idx_position_bond_block_number", "id", schema=get_db_schema())
    if engine.name == "mysql":
        op.drop_constraint(
            "idx_position_bond_block_number_pkey",
            "idx_position_bond_block_number",
            type_="primary",
            schema=get_db_schema(),
        )
    op.create_primary_key(
        "idx_position_bond_block_number_pkey",
        "idx_position_bond_block_number",
        ["token_address", "exchange_address"],
        schema=get_db_schema(),
    )

    ############################
    # Migration for idx_position_share_block_number
    ############################
    op.get_bind().execute(
        sa.text(f"DELETE FROM idx_position_share_block_number WHERE modified IS null;")
    )
    op.get_bind().execute(
        sa.text(
            f"""DELETE FROM idx_position_share_block_number WHERE (modified) NOT IN (
                    SELECT latest_idx_position_share_block_number.max_modified AS modified FROM (
                        SELECT  max(modified) AS max_modified FROM idx_position_share_block_number GROUP BY token_address, exchange_address
                    ) AS latest_idx_position_share_block_number
                );"""
        )
    )
    op.drop_column("idx_position_share_block_number", "id", schema=get_db_schema())
    if engine.name == "mysql":
        op.drop_constraint(
            "idx_position_share_block_number_pkey",
            "idx_position_share_block_number",
            type_="primary",
            schema=get_db_schema(),
        )
    op.create_primary_key(
        "idx_position_share_block_number_pkey",
        "idx_position_share_block_number",
        ["token_address", "exchange_address"],
        schema=get_db_schema(),
    )

    ############################
    # Migration for idx_position_coupon_block_number
    ############################
    op.get_bind().execute(
        sa.text(f"DELETE FROM idx_position_coupon_block_number WHERE modified IS null;")
    )
    op.get_bind().execute(
        sa.text(
            f"""DELETE FROM idx_position_coupon_block_number WHERE (modified) NOT IN (
                    SELECT latest_idx_position_coupon_block_number.max_modified AS modified FROM (
                        SELECT  max(modified) AS max_modified FROM idx_position_coupon_block_number GROUP BY token_address, exchange_address
                    ) AS latest_idx_position_coupon_block_number
                );"""
        )
    )
    op.drop_column("idx_position_coupon_block_number", "id", schema=get_db_schema())
    if engine.name == "mysql":
        op.drop_constraint(
            "idx_position_coupon_block_number_pkey",
            "idx_position_coupon_block_number",
            type_="primary",
            schema=get_db_schema(),
        )
    op.create_primary_key(
        "idx_position_coupon_block_number_pkey",
        "idx_position_coupon_block_number",
        ["token_address", "exchange_address"],
        schema=get_db_schema(),
    )

    ############################
    # Migration for idx_position_membership_block_number
    ############################
    op.get_bind().execute(
        sa.text(
            f"DELETE FROM idx_position_membership_block_number WHERE modified IS null;"
        )
    )
    op.get_bind().execute(
        sa.text(
            f"""DELETE FROM idx_position_membership_block_number WHERE (modified) NOT IN (
                    SELECT latest_idx_position_membership_block_number.max_modified AS modified FROM (
                        SELECT  max(modified) AS max_modified FROM idx_position_membership_block_number GROUP BY token_address, exchange_address
                    ) AS latest_idx_position_membership_block_number
                );"""
        )
    )
    op.drop_column("idx_position_membership_block_number", "id", schema=get_db_schema())
    if engine.name == "mysql":
        op.drop_constraint(
            "idx_position_membership_block_number_pkey",
            "idx_position_membership_block_number",
            type_="primary",
            schema=get_db_schema(),
        )
    op.create_primary_key(
        "idx_position_membership_block_number_pkey",
        "idx_position_membership_block_number",
        ["token_address", "exchange_address"],
        schema=get_db_schema(),
    )


def downgrade():
    connection = op.get_bind()

    ############################
    # Migration for position
    ############################
    if op.get_context().dialect.name != "mysql":
        op.get_bind().execute(
            sa.text("CREATE SEQUENCE IF NOT EXISTS position_id_seq START 1")
        )
        op.add_column(
            "position",
            sa.Column(
                "id",
                sa.BigInteger(),
                autoincrement=True,
                nullable=False,
                server_default=sa.text("nextval('position_id_seq'::regclass)"),
            ),
            schema=get_db_schema(),
        )
    else:
        op.add_column(
            "position",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            schema=get_db_schema(),
        )
        # NOTE: Set default auto_increment value manually for MySQL
        position_table = IDXPosition
        select_stmt = sa.select(
            position_table.token_address, position_table.account_address
        )
        position_list = op.get_bind().execute(select_stmt)
        if position_list is not None:
            for i, position in enumerate(position_list):
                token_address = position[0]
                account_address = position[1]
                op.get_bind().execute(
                    sa.text(
                        f"UPDATE position SET id = {i + 1} WHERE token_address = '{token_address}' AND account_address = '{account_address}';"
                    )
                )

    op.drop_constraint("position_pkey", "position", type_="primary")
    op.create_primary_key("position_pkey", "position", ["id"])
    if op.get_context().dialect.name == "mysql":
        op.get_bind().execute(
            sa.text(f"ALTER TABLE position MODIFY id BIGINT NOT NULL AUTO_INCREMENT;")
        )
    op.create_index(
        "ix_position_token_address",
        "position",
        ["token_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "position",
        "account_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "position",
        "token_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=True,
        schema=get_db_schema(),
    )

    ############################
    # Migration for executable_contract
    ############################
    if op.get_context().dialect.name != "mysql":
        op.get_bind().execute(
            sa.text("CREATE SEQUENCE IF NOT EXISTS executable_contract_id_seq START 1")
        )
        op.add_column(
            "executable_contract",
            sa.Column(
                "id",
                sa.BigInteger(),
                autoincrement=True,
                nullable=False,
                server_default=sa.text(
                    "nextval('executable_contract_id_seq'::regclass)"
                ),
            ),
            schema=get_db_schema(),
        )
    else:
        op.add_column(
            "executable_contract",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            schema=get_db_schema(),
        )
        # NOTE: Set default auto_increment value manually for MySQL
        executable_contract_table = ExecutableContract
        select_stmt = sa.select(executable_contract_table.contract_address)
        executable_contract_list = op.get_bind().execute(select_stmt)
        if executable_contract_list is not None:
            for i, executable_contract in enumerate(executable_contract_list):
                contract_address = executable_contract[0]
                op.get_bind().execute(
                    sa.text(
                        f"UPDATE executable_contract SET id = {i + 1} WHERE contract_address = '{contract_address}';"
                    )
                )
    op.drop_constraint(
        "executable_contract_pkey",
        "executable_contract",
        type_="primary",
        schema=get_db_schema(),
    )
    op.create_primary_key("executable_contract_pkey", "executable_contract", ["id"])
    if op.get_context().dialect.name == "mysql":
        op.get_bind().execute(
            sa.text(
                f"ALTER TABLE executable_contract MODIFY id BIGINT NOT NULL AUTO_INCREMENT;"
            )
        )
    op.create_index(
        "ix_executable_contract_contract_address",
        "executable_contract",
        ["contract_address"],
        schema=get_db_schema(),
    )
    op.alter_column(
        "executable_contract",
        "contract_address",
        existing_type=sa.VARCHAR(length=256),
        nullable=True,
        schema=get_db_schema(),
    )

    ############################
    # Migration for idx_position_bond_block_number
    ############################
    if op.get_context().dialect.name != "mysql":
        op.get_bind().execute(
            sa.text(
                "CREATE SEQUENCE IF NOT EXISTS idx_position_bond_block_number_id_seq START 1"
            )
        )
        op.add_column(
            "idx_position_bond_block_number",
            sa.Column(
                "id",
                sa.BigInteger(),
                autoincrement=True,
                nullable=False,
                server_default=sa.text(
                    "nextval('idx_position_bond_block_number_id_seq'::regclass)"
                ),
            ),
            schema=get_db_schema(),
        )
    else:
        op.add_column(
            "idx_position_bond_block_number",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            schema=get_db_schema(),
        )
        # NOTE: Set default auto_increment value manually for MySQL
        idx_position_bond_block_number_table = IDXPositionBondBlockNumber
        select_stmt = sa.select(
            idx_position_bond_block_number_table.token_address,
            idx_position_bond_block_number_table.exchange_address,
        )
        idx_position_bond_block_number_table_list = op.get_bind().execute(select_stmt)
        if idx_position_bond_block_number_table_list is not None:
            for i, idx_position_bond_block_number_table in enumerate(
                idx_position_bond_block_number_table_list
            ):
                token_address = idx_position_bond_block_number_table[0]
                exchange_address = idx_position_bond_block_number_table[1]
                op.get_bind().execute(
                    sa.text(
                        f"UPDATE idx_position_bond_block_number SET id = {i + 1} WHERE token_address = '{token_address}' AND exchange_address = '{exchange_address}';"
                    )
                )
    op.drop_constraint(
        "idx_position_bond_block_number_pkey",
        "idx_position_bond_block_number",
        type_="primary",
        schema=get_db_schema(),
    )
    op.create_primary_key(
        "idx_position_bond_block_number_pkey",
        "idx_position_bond_block_number",
        ["id", "token_address", "exchange_address"],
        schema=get_db_schema(),
    )
    if op.get_context().dialect.name == "mysql":
        op.get_bind().execute(
            sa.text(
                f"ALTER TABLE idx_position_bond_block_number MODIFY id BIGINT NOT NULL AUTO_INCREMENT;"
            )
        )

    ############################
    # Migration for idx_position_share_block_number
    ############################
    if op.get_context().dialect.name != "mysql":
        op.get_bind().execute(
            sa.text(
                "CREATE SEQUENCE IF NOT EXISTS idx_position_share_block_number_id_seq START 1"
            )
        )
        op.add_column(
            "idx_position_share_block_number",
            sa.Column(
                "id",
                sa.BigInteger(),
                autoincrement=True,
                nullable=False,
                server_default=sa.text(
                    "nextval('idx_position_share_block_number_id_seq'::regclass)"
                ),
            ),
            schema=get_db_schema(),
        )
    else:
        op.add_column(
            "idx_position_share_block_number",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            schema=get_db_schema(),
        )
        # NOTE: Set default auto_increment value manually for MySQL
        idx_position_share_block_number_table = IDXPositionBondBlockNumber
        select_stmt = sa.select(
            idx_position_share_block_number_table.token_address,
            idx_position_share_block_number_table.exchange_address,
        )
        idx_position_share_block_number_table_list = op.get_bind().execute(select_stmt)
        if idx_position_share_block_number_table_list is not None:
            for i, idx_position_share_block_number_table in enumerate(
                idx_position_share_block_number_table_list
            ):
                token_address = idx_position_share_block_number_table[0]
                exchange_address = idx_position_share_block_number_table[1]
                op.get_bind().execute(
                    sa.text(
                        f"UPDATE idx_position_share_block_number SET id = {i + 1} WHERE token_address = '{token_address}' AND exchange_address = '{exchange_address}';"
                    )
                )
    op.drop_constraint(
        "idx_position_share_block_number_pkey",
        "idx_position_share_block_number",
        type_="primary",
        schema=get_db_schema(),
    )
    op.create_primary_key(
        "idx_position_share_block_number_pkey",
        "idx_position_share_block_number",
        ["id", "token_address", "exchange_address"],
        schema=get_db_schema(),
    )
    if op.get_context().dialect.name == "mysql":
        op.get_bind().execute(
            sa.text(
                f"ALTER TABLE idx_position_share_block_number MODIFY id BIGINT NOT NULL AUTO_INCREMENT;"
            )
        )

    ############################
    # Migration for idx_position_coupon_block_number
    ############################
    if op.get_context().dialect.name != "mysql":
        op.get_bind().execute(
            sa.text(
                "CREATE SEQUENCE IF NOT EXISTS idx_position_coupon_block_number_id_seq START 1"
            )
        )
        op.add_column(
            "idx_position_coupon_block_number",
            sa.Column(
                "id",
                sa.BigInteger(),
                autoincrement=True,
                nullable=False,
                server_default=sa.text(
                    "nextval('idx_position_coupon_block_number_id_seq'::regclass)"
                ),
            ),
            schema=get_db_schema(),
        )
    else:
        op.add_column(
            "idx_position_coupon_block_number",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            schema=get_db_schema(),
        )
        # NOTE: Set default auto_increment value manually for MySQL
        idx_position_coupon_block_number_table = IDXPositionBondBlockNumber
        select_stmt = sa.select(
            idx_position_coupon_block_number_table.token_address,
            idx_position_coupon_block_number_table.exchange_address,
        )
        idx_position_coupon_block_number_table_list = op.get_bind().execute(select_stmt)
        if idx_position_coupon_block_number_table_list is not None:
            for i, idx_position_coupon_block_number_table in enumerate(
                idx_position_coupon_block_number_table_list
            ):
                token_address = idx_position_coupon_block_number_table[0]
                exchange_address = idx_position_coupon_block_number_table[1]
                op.get_bind().execute(
                    sa.text(
                        f"UPDATE idx_position_coupon_block_number SET id = {i + 1} WHERE token_address = '{token_address}' AND exchange_address = '{exchange_address}';"
                    )
                )
    op.drop_constraint(
        "idx_position_coupon_block_number_pkey",
        "idx_position_coupon_block_number",
        type_="primary",
        schema=get_db_schema(),
    )
    op.create_primary_key(
        "idx_position_coupon_block_number_pkey",
        "idx_position_coupon_block_number",
        ["id", "token_address", "exchange_address"],
        schema=get_db_schema(),
    )
    if op.get_context().dialect.name == "mysql":
        op.get_bind().execute(
            sa.text(
                f"ALTER TABLE idx_position_coupon_block_number MODIFY id BIGINT NOT NULL AUTO_INCREMENT;"
            )
        )

    ############################
    # Migration for idx_position_membership_block_number
    ############################
    if op.get_context().dialect.name != "mysql":
        op.get_bind().execute(
            sa.text(
                "CREATE SEQUENCE IF NOT EXISTS idx_position_membership_block_number_id_seq START 1"
            )
        )
        op.add_column(
            "idx_position_membership_block_number",
            sa.Column(
                "id",
                sa.BigInteger(),
                autoincrement=True,
                nullable=False,
                server_default=sa.text(
                    "nextval('idx_position_membership_block_number_id_seq'::regclass)"
                ),
            ),
            schema=get_db_schema(),
        )
    else:
        op.add_column(
            "idx_position_membership_block_number",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            schema=get_db_schema(),
        )
        # NOTE: Set default auto_increment value manually for MySQL
        idx_position_membership_block_number_table = IDXPositionBondBlockNumber
        select_stmt = sa.select(
            idx_position_membership_block_number_table.token_address,
            idx_position_membership_block_number_table.exchange_address,
        )
        idx_position_membership_block_number_table_list = op.get_bind().execute(
            select_stmt
        )
        if idx_position_membership_block_number_table_list is not None:
            for i, idx_position_membership_block_number_table in enumerate(
                idx_position_membership_block_number_table_list
            ):
                token_address = idx_position_membership_block_number_table[0]
                exchange_address = idx_position_membership_block_number_table[1]
                op.get_bind().execute(
                    sa.text(
                        f"UPDATE idx_position_membership_block_number SET id = {i + 1} WHERE token_address = '{token_address}' AND exchange_address = '{exchange_address}';"
                    )
                )
    op.drop_constraint(
        "idx_position_membership_block_number_pkey",
        "idx_position_membership_block_number",
        type_="primary",
        schema=get_db_schema(),
    )
    op.create_primary_key(
        "idx_position_membership_block_number_pkey",
        "idx_position_membership_block_number",
        ["id", "token_address", "exchange_address"],
        schema=get_db_schema(),
    )
    if op.get_context().dialect.name == "mysql":
        op.get_bind().execute(
            sa.text(
                f"ALTER TABLE idx_position_membership_block_number MODIFY id BIGINT NOT NULL AUTO_INCREMENT;"
            )
        )
