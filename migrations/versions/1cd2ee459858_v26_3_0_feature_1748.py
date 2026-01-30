"""v26_3_0_feature_1748

Revision ID: 1cd2ee459858
Revises: 835dd5b51e23
Create Date: 2026-01-30 16:10:08.786675

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "1cd2ee459858"
down_revision = "835dd5b51e23"
branch_labels = None
depends_on = None


def _schema_name() -> str:
    return get_db_schema() or "public"


def upgrade():
    schema = _schema_name()

    op.execute(f'DROP INDEX IF EXISTS {schema}."ix_tx_data_block_number"')
    op.execute(f'DROP INDEX IF EXISTS {schema}."ix_tx_data_from_address"')
    op.execute(f'DROP INDEX IF EXISTS {schema}."ix_tx_data_to_address"')
    op.execute(f"DROP TABLE IF EXISTS {schema}.tx_data")

    op.execute(f'DROP INDEX IF EXISTS {schema}."ix_block_data_hash"')
    op.execute(f'DROP INDEX IF EXISTS {schema}."ix_block_data_timestamp"')
    op.execute(f"DROP TABLE IF EXISTS {schema}.block_data")

    op.execute(f"DROP TABLE IF EXISTS {schema}.idx_block_data_block_number")


def downgrade():
    connection = op.get_bind()

    op.create_table(
        "idx_block_data_block_number",
        sa.Column(
            "created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "modified", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "chain_id", sa.VARCHAR(length=10), autoincrement=False, nullable=False
        ),
        sa.Column(
            "latest_block_number", sa.BIGINT(), autoincrement=False, nullable=True
        ),
        sa.PrimaryKeyConstraint(
            "chain_id", name=op.f("idx_block_data_block_number_pkey")
        ),
        schema=get_db_schema(),
    )
    op.create_table(
        "block_data",
        sa.Column(
            "created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "modified", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column("number", sa.BIGINT(), autoincrement=False, nullable=False),
        sa.Column(
            "parent_hash", sa.VARCHAR(length=66), autoincrement=False, nullable=False
        ),
        sa.Column(
            "sha3_uncles", sa.VARCHAR(length=66), autoincrement=False, nullable=True
        ),
        sa.Column("miner", sa.VARCHAR(length=42), autoincrement=False, nullable=True),
        sa.Column(
            "state_root", sa.VARCHAR(length=66), autoincrement=False, nullable=True
        ),
        sa.Column(
            "transactions_root",
            sa.VARCHAR(length=66),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "receipts_root", sa.VARCHAR(length=66), autoincrement=False, nullable=True
        ),
        sa.Column(
            "logs_bloom", sa.VARCHAR(length=514), autoincrement=False, nullable=True
        ),
        sa.Column("difficulty", sa.BIGINT(), autoincrement=False, nullable=True),
        sa.Column("gas_limit", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("gas_used", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("timestamp", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "proof_of_authority_data", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "mix_hash", sa.VARCHAR(length=66), autoincrement=False, nullable=True
        ),
        sa.Column("nonce", sa.VARCHAR(length=18), autoincrement=False, nullable=True),
        sa.Column("hash", sa.VARCHAR(length=66), autoincrement=False, nullable=False),
        sa.Column("size", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column(
            "transactions",
            postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("number", name=op.f("block_data_pkey")),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_block_data_timestamp"),
        "block_data",
        ["timestamp"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_block_data_hash"),
        "block_data",
        ["hash"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_table(
        "tx_data",
        sa.Column(
            "created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "modified", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column("hash", sa.VARCHAR(length=66), autoincrement=False, nullable=False),
        sa.Column(
            "block_hash", sa.VARCHAR(length=66), autoincrement=False, nullable=True
        ),
        sa.Column("block_number", sa.BIGINT(), autoincrement=False, nullable=True),
        sa.Column(
            "transaction_index", sa.INTEGER(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "from_address", sa.VARCHAR(length=42), autoincrement=False, nullable=True
        ),
        sa.Column(
            "to_address", sa.VARCHAR(length=42), autoincrement=False, nullable=True
        ),
        sa.Column("input", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("gas", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("gas_price", sa.BIGINT(), autoincrement=False, nullable=True),
        sa.Column("value", sa.BIGINT(), autoincrement=False, nullable=True),
        sa.Column("nonce", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("hash", name=op.f("tx_data_pkey")),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_tx_data_to_address"),
        "tx_data",
        ["to_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_tx_data_from_address"),
        "tx_data",
        ["from_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_tx_data_block_number"),
        "tx_data",
        ["block_number"],
        unique=False,
        schema=get_db_schema(),
    )
