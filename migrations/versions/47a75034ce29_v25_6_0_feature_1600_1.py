"""v25_6_0_feature_1600

Revision ID: 47a75034ce29
Revises: 95f5a9de7153
Create Date: 2025-03-26 17:50:23.807632

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "47a75034ce29"
down_revision = "95f5a9de7153"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.create_table(
        "public_account_list",
        sa.Column("key_manager", sa.String(length=20), nullable=False),
        sa.Column("account_type", sa.Integer(), nullable=False),
        sa.Column("account_address", sa.String(length=42), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("key_manager", "account_type"),
        schema=get_db_schema(),
    )


def downgrade():
    connection = op.get_bind()

    op.drop_table("public_account_list", schema=get_db_schema())
