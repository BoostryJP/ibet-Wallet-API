"""v25_6_0_feature_1599_2

Revision ID: 95f5a9de7153
Revises: 672cf41e970c
Create Date: 2025-03-25 09:42:52.756402

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "95f5a9de7153"
down_revision = "672cf41e970c"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.create_table(
        "token_list",
        sa.Column("token_address", sa.String(length=42), nullable=False),
        sa.Column("token_template", sa.String(length=50), nullable=False),
        sa.Column("key_manager", sa.JSON(), nullable=False),
        sa.Column("product_type", sa.Integer(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("token_address"),
        schema=get_db_schema(),
    )
    op.drop_index(
        "ix_token_list_owner_address",
        table_name="token_list_register",
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_token_list_register_owner_address"),
        "token_list_register",
        ["owner_address"],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    connection = op.get_bind()

    op.drop_index(
        op.f("ix_token_list_register_owner_address"),
        table_name="token_list_register",
        schema=get_db_schema(),
    )
    op.create_index(
        "ix_token_list_owner_address",
        "token_list_register",
        ["owner_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.drop_table("token_list", schema=get_db_schema())
