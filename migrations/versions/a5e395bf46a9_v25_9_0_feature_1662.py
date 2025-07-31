"""v25_9_0_feature_1662

Revision ID: a5e395bf46a9
Revises: 819325835c3d
Create Date: 2025-07-31 12:02:12.029337

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema
from app.model.db import Notification

# revision identifiers, used by Alembic.
revision = "a5e395bf46a9"
down_revision = "819325835c3d"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.create_table(
        "notification_attribute_value",
        sa.Column("contract_address", sa.String(length=42), nullable=False),
        sa.Column("attribute_key", sa.String(length=256), nullable=False),
        sa.Column("attribute", sa.JSON(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("contract_address", "attribute_key"),
        schema=get_db_schema(),
    )
    op.add_column(
        "notification",
        sa.Column("notification_category", sa.String(length=20), nullable=True),
        schema=get_db_schema(),
    )
    op.get_bind().execute(
        sa.update(Notification).values(notification_category="event_log")
    )
    op.alter_column(
        "notification",
        "notification_category",
        existing_type=sa.String(length=20),
        nullable=False,
        schema=get_db_schema(),
    )
    op.drop_constraint("notification_pkey", "notification", type_="primary")
    op.create_primary_key(
        "notification_pkey",
        "notification",
        ["notification_category", "notification_id"],
        schema=get_db_schema(),
    )


def downgrade():
    connection = op.get_bind()

    op.drop_column("notification", "notification_category", schema=get_db_schema())
    op.drop_table("notification_attribute_value", schema=get_db_schema())
