"""optimize locked position lookup

Revision ID: c2a9f6e81d73
Revises: b7e4c2d91f60
Create Date: 2026-09-18 00:00:00.000000
"""

from alembic import op

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "c2a9f6e81d73"
down_revision = "b7e4c2d91f60"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        op.f("ix_locked_position_token_address_account_address_value"),
        "locked_position",
        ["token_address", "account_address", "value"],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_index(
        op.f("ix_locked_position_token_address_account_address_value"),
        table_name="locked_position",
        schema=get_db_schema(),
    )
