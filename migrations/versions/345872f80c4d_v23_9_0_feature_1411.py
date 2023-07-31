"""v23_9_0_feature_1411

Revision ID: 345872f80c4d
Revises: cd25c53c036c
Create Date: 2023-07-31 11:09:11.716850

"""
from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "345872f80c4d"
down_revision = "cd25c53c036c"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.create_index(
        op.f("ix_notification_address"),
        "notification",
        ["address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_notification_notification_type"),
        "notification",
        ["notification_type"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_notification_priority"),
        "notification",
        ["priority"],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    connection = op.get_bind()

    op.drop_index(
        op.f("ix_notification_priority"),
        table_name="notification",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_notification_notification_type"),
        table_name="notification",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_notification_address"),
        table_name="notification",
        schema=get_db_schema(),
    )
