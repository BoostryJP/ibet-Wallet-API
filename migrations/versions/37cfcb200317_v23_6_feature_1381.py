"""v23.6_feature_1381

Revision ID: 37cfcb200317
Revises: 40ee030e9302
Create Date: 2023-04-25 18:24:29.759654

"""

from alembic import op
import sqlalchemy as sa
from app.config import ZERO_ADDRESS
from app.database import get_db_schema, engine

# revision identifiers, used by Alembic.
revision = "37cfcb200317"
down_revision = "40ee030e9302"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.add_column(
        "lock",
        sa.Column("msg_sender", sa.String(length=42), nullable=True),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_lock_msg_sender"),
        "lock",
        ["msg_sender"],
        unique=False,
        schema=get_db_schema(),
    )
    op.add_column(
        "unlock",
        sa.Column("msg_sender", sa.String(length=42), nullable=True),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_unlock_msg_sender"),
        "unlock",
        ["msg_sender"],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    connection = op.get_bind()

    op.drop_index(
        op.f("ix_unlock_msg_sender"),
        table_name="unlock",
        schema=get_db_schema(),
    )
    op.drop_column("unlock", "msg_sender", schema=get_db_schema())
    op.drop_index(op.f("ix_lock_msg_sender"), table_name="lock", schema=get_db_schema())
    op.drop_column("lock", "msg_sender", schema=get_db_schema())
