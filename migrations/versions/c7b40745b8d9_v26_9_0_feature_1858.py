"""v26_9_0_feature_1858

Revision ID: c7b40745b8d9
Revises: 85d3431e23dd
Create Date: 2026-08-21 00:00:00.000000
"""

from alembic import op

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "c7b40745b8d9"
down_revision = "85d3431e23dd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        op.f("ix_transfer_token_address_id"),
        "transfer",
        ["token_address", "id"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_transfer_transaction_hash_id"),
        "transfer",
        ["transaction_hash", "id"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_transfer_from_address_id"),
        "transfer",
        ["from_address", "id"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_transfer_to_address_id"),
        "transfer",
        ["to_address", "id"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_transfer_token_address_transaction_hash_id"),
        "transfer",
        ["token_address", "transaction_hash", "id"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_transfer_token_address_from_address_id"),
        "transfer",
        ["token_address", "from_address", "id"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_transfer_token_address_to_address_id"),
        "transfer",
        ["token_address", "to_address", "id"],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_index(
        op.f("ix_transfer_token_address_to_address_id"),
        table_name="transfer",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_transfer_token_address_from_address_id"),
        table_name="transfer",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_transfer_token_address_transaction_hash_id"),
        table_name="transfer",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_transfer_to_address_id"),
        table_name="transfer",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_transfer_from_address_id"),
        table_name="transfer",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_transfer_transaction_hash_id"),
        table_name="transfer",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_transfer_token_address_id"),
        table_name="transfer",
        schema=get_db_schema(),
    )
