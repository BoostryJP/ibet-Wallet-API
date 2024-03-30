"""v23_12_0_feature_1447

Revision ID: 4164b4e8dfe6
Revises: 550546d384e7
Create Date: 2023-11-21 11:17:58.139399

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "4164b4e8dfe6"
down_revision = "550546d384e7"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.create_table(
        "account_tag",
        sa.Column("account_address", sa.String(length=42), nullable=False),
        sa.Column("account_tag", sa.String(length=50), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("account_address"),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_account_tag_account_tag"),
        "account_tag",
        ["account_tag"],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    connection = op.get_bind()

    op.drop_index(
        op.f("ix_account_tag_account_tag"),
        table_name="account_tag",
        schema=get_db_schema(),
    )
    op.drop_table("account_tag", schema=get_db_schema())
