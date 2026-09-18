"""v26_9_0_feature_1813

Revision ID: e7d2a61b9f4c
Revises: b7e4c2d91f60
Create Date: 2026-09-18 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "e7d2a61b9f4c"
down_revision = "b7e4c2d91f60"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "mail",
        sa.Column("status", sa.String(length=20), nullable=True),
        schema=get_db_schema(),
    )
    mail = sa.Table(
        "mail",
        sa.MetaData(),
        sa.Column("status", sa.String(length=20)),
        schema=get_db_schema(),
    )
    op.get_bind().execute(
        mail.update().where(mail.c.status.is_(None)).values(status="pending")
    )

    op.alter_column(
        "mail",
        "status",
        existing_type=sa.String(length=20),
        nullable=False,
        server_default="pending",
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_mail_status"),
        "mail",
        ["status"],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_index(op.f("ix_mail_status"), table_name="mail", schema=get_db_schema())
    op.drop_column("mail", "status", schema=get_db_schema())
