"""v25_6_0_feature_1605

Revision ID: f8faa777c5f2
Revises: 95f5a9de7153
Create Date: 2025-03-26 16:22:49.191603

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import update


from app.database import get_db_schema
from app.model.db import IDXLock

# revision identifiers, used by Alembic.
revision = "f8faa777c5f2"
down_revision = "95f5a9de7153"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.add_column(
        "lock",
        sa.Column("is_force_lock", sa.Boolean(), nullable=True),
        schema=get_db_schema(),
    )
    op.get_bind().execute(update(IDXLock).values(is_force_lock=False))
    op.alter_column(
        "lock",
        "is_force_lock",
        existing_type=sa.Boolean(),
        nullable=False,
        schema=get_db_schema(),
    )


def downgrade():
    connection = op.get_bind()

    op.drop_column("lock", "is_force_lock", schema=get_db_schema())
