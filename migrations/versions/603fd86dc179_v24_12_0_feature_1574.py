"""v24_12_0_feature_1574

Revision ID: 603fd86dc179
Revises: 418af51b07b5
Create Date: 2024-11-01 11:01:24.485369

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "603fd86dc179"
down_revision = "418af51b07b5"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.add_column(
        "transfer",
        sa.Column("message", sa.String(length=50), nullable=True),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_transfer_message"),
        "transfer",
        ["message"],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    connection = op.get_bind()

    op.drop_index(
        op.f("ix_transfer_message"), table_name="transfer", schema=get_db_schema()
    )
    op.drop_column("transfer", "message", schema=get_db_schema())
