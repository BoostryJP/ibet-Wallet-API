"""034_v22.6

Revision ID: e8d970fdd886
Revises: a80595c53d52
Create Date: 2023-03-30 17:39:41.701943

"""
from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema
from migrations import skip_based_on_legacy_engine_version
from migrations.log import LOG

# revision identifiers, used by Alembic.
revision = "e8d970fdd886"
down_revision = "a80595c53d52"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if skip_based_on_legacy_engine_version(op, __name__):
        LOG.info("skipped")
        return

    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "idx_position_bond_block_number",
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("exchange_address", sa.String(length=42), nullable=False),
        sa.Column("latest_block_number", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", "token_address", "exchange_address"),
        schema=get_db_schema(),
    )
    op.create_table(
        "idx_position_coupon_block_number",
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("exchange_address", sa.String(length=42), nullable=False),
        sa.Column("latest_block_number", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", "token_address", "exchange_address"),
        schema=get_db_schema(),
    )
    op.create_table(
        "idx_position_membership_block_number",
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("exchange_address", sa.String(length=42), nullable=False),
        sa.Column("latest_block_number", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", "token_address", "exchange_address"),
        schema=get_db_schema(),
    )
    op.create_table(
        "idx_position_share_block_number",
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("exchange_address", sa.String(length=42), nullable=False),
        sa.Column("latest_block_number", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", "token_address", "exchange_address"),
        schema=get_db_schema(),
    )
    op.create_table(
        "idx_transfer_approval_block_number",
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("exchange_address", sa.String(length=42), nullable=False),
        sa.Column("latest_block_number", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", "token_address", "exchange_address"),
        schema=get_db_schema(),
    )
    op.create_table(
        "token_holder",
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.Column("holder_list", sa.BigInteger(), nullable=False),
        sa.Column("account_address", sa.String(length=42), nullable=False),
        sa.Column("hold_balance", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("holder_list", "account_address"),
        schema=get_db_schema(),
    )
    op.create_table(
        "token_holders_list",
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("token_address", sa.String(length=42), nullable=True),
        sa.Column("block_number", sa.BigInteger(), nullable=True),
        sa.Column("list_id", sa.String(length=36), nullable=True),
        sa.Column("batch_status", sa.String(length=256), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=get_db_schema(),
    )
    op.add_column(
        "transfer_approval",
        sa.Column("escrow_finished", sa.Boolean(), nullable=True),
        schema=get_db_schema(),
    )
    # NOTE: Update sqlalchemy-migrate version
    tables = sa.inspect(connection).get_table_names()
    if "migrate_version" in tables:
        op.get_bind().execute(sa.text(f"UPDATE migrate_version SET version = 34;"))
    # ### end Alembic commands ###


def downgrade():
    connection = op.get_bind()
    if skip_based_on_legacy_engine_version(op, __name__, is_downgrade=True):
        LOG.info("skipped")
        return
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("transfer_approval", "escrow_finished", schema=get_db_schema())
    op.drop_table("token_holders_list", schema=get_db_schema())
    op.drop_table("token_holder", schema=get_db_schema())
    op.drop_table("idx_transfer_approval_block_number", schema=get_db_schema())
    op.drop_table("idx_position_share_block_number", schema=get_db_schema())
    op.drop_table("idx_position_membership_block_number", schema=get_db_schema())
    op.drop_table("idx_position_coupon_block_number", schema=get_db_schema())
    op.drop_table("idx_position_bond_block_number", schema=get_db_schema())
    # NOTE: Update sqlalchemy-migrate version
    tables = sa.inspect(connection).get_table_names()
    if "migrate_version" in tables:
        op.get_bind().execute(sa.text(f"UPDATE migrate_version SET version = 26;"))
    # ### end Alembic commands ###
