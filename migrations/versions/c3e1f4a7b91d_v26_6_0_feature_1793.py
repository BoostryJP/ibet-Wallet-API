"""v26_6_0_feature_1793

Revision ID: c3e1f4a7b91d
Revises: 4df7e2c1b8a3
Create Date: 2026-04-03 16:18:20.428731

"""

from alembic import op
import sqlalchemy as sa

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "c3e1f4a7b91d"
down_revision = "4df7e2c1b8a3"
branch_labels = None
depends_on = None


def upgrade():
    consume_coupon = sa.Table(
        "consume_coupon",
        sa.MetaData(),
        sa.Column("amount", sa.BigInteger()),
        sa.Column("block_timestamp", sa.DateTime()),
        schema=get_db_schema(),
    )

    op.get_bind().execute(
        consume_coupon.delete().where(
            sa.or_(
                consume_coupon.c.amount.is_(None),
                consume_coupon.c.block_timestamp.is_(None),
            )
        )
    )

    op.alter_column(
        "consume_coupon",
        "amount",
        existing_type=sa.BigInteger(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "consume_coupon",
        "block_timestamp",
        existing_type=sa.DateTime(),
        nullable=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.alter_column(
        "consume_coupon",
        "amount",
        existing_type=sa.BigInteger(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "consume_coupon",
        "block_timestamp",
        existing_type=sa.DateTime(),
        nullable=True,
        schema=get_db_schema(),
    )
