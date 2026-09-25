"""v26_9_0_feature_1858_2

Revision ID: 0c1e4f2d9a7b
Revises: c7b40745b8d9
Create Date: 2026-08-24 00:00:00.000000
"""

from alembic import op

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "0c1e4f2d9a7b"
down_revision = "c7b40745b8d9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        op.f("ix_transfer_source_event_id"),
        "transfer",
        ["source_event", "id"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_transfer_token_address_source_event_id"),
        "transfer",
        ["token_address", "source_event", "id"],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_index(
        op.f("ix_transfer_token_address_source_event_id"),
        table_name="transfer",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_transfer_source_event_id"),
        table_name="transfer",
        schema=get_db_schema(),
    )
