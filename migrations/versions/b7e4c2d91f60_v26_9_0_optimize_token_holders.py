"""optimize token holders query

Revision ID: b7e4c2d91f60
Revises: 0c1e4f2d9a7b
Create Date: 2026-09-18 00:00:00.000000
"""

from alembic import op

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "b7e4c2d91f60"
down_revision = "0c1e4f2d9a7b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        op.f("ix_position_token_address_created"),
        "position",
        ["token_address", "created"],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_index(
        op.f("ix_position_token_address_created"),
        table_name="position",
        schema=get_db_schema(),
    )
