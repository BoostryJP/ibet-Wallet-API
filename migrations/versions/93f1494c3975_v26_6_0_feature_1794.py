"""v26_6_0_feature_1794

Revision ID: 93f1494c3975
Revises: c3e1f4a7b91d
Create Date: 2026-04-07 16:55:27.314211
"""

import sqlalchemy as sa
from alembic import op

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "93f1494c3975"
down_revision = "c3e1f4a7b91d"
branch_labels = None
depends_on = None


def _get_notification_table() -> sa.Table:
    return sa.Table(
        "notification",
        sa.MetaData(),
        sa.Column("notification_type", sa.String(length=256)),
        sa.Column("priority", sa.Integer()),
        sa.Column("is_read", sa.Boolean()),
        sa.Column("is_flagged", sa.Boolean()),
        sa.Column("is_deleted", sa.Boolean()),
        sa.Column("block_timestamp", sa.DateTime()),
        sa.Column("metainfo", sa.JSON()),
        schema=get_db_schema(),
    )


def upgrade():
    ############################
    # Migration for notification not null columns
    ############################
    notification = _get_notification_table()
    connection = op.get_bind()
    notification_invalid_condition = sa.or_(
        notification.c.notification_type.is_(None),
        notification.c.block_timestamp.is_(None),
        notification.c.metainfo.is_(None),
        notification.c.metainfo == sa.JSON.NULL,
    )

    connection.execute(
        notification.update()
        .where(notification.c.priority.is_(None))
        .values(priority=0)
    )
    connection.execute(
        notification.update()
        .where(notification.c.is_read.is_(None))
        .values(is_read=False)
    )
    connection.execute(
        notification.update()
        .where(notification.c.is_flagged.is_(None))
        .values(is_flagged=False)
    )
    connection.execute(
        notification.update()
        .where(notification.c.is_deleted.is_(None))
        .values(is_deleted=False)
    )
    connection.execute(notification.delete().where(notification_invalid_condition))

    op.alter_column(
        "notification",
        "notification_type",
        existing_type=sa.String(length=256),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "notification",
        "priority",
        existing_type=sa.Integer(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "notification",
        "is_read",
        existing_type=sa.Boolean(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "notification",
        "is_flagged",
        existing_type=sa.Boolean(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "notification",
        "is_deleted",
        existing_type=sa.Boolean(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "notification",
        "block_timestamp",
        existing_type=sa.DateTime(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "notification",
        "metainfo",
        existing_type=sa.JSON(),
        nullable=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.alter_column(
        "notification",
        "metainfo",
        existing_type=sa.JSON(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "notification",
        "block_timestamp",
        existing_type=sa.DateTime(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "notification",
        "is_deleted",
        existing_type=sa.Boolean(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "notification",
        "is_flagged",
        existing_type=sa.Boolean(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "notification",
        "is_read",
        existing_type=sa.Boolean(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "notification",
        "priority",
        existing_type=sa.Integer(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "notification",
        "notification_type",
        existing_type=sa.String(length=256),
        nullable=True,
        schema=get_db_schema(),
    )
