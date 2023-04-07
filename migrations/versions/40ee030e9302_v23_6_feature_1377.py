"""v23_6_feature_1377

Revision ID: 40ee030e9302
Revises: ca8ff8c0c01d
Create Date: 2023-04-07 11:07:01.686463

"""
from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "40ee030e9302"
down_revision = "ca8ff8c0c01d"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.get_bind().execute(sa.text(f"DELETE FROM position WHERE token_address IS null;"))
    op.get_bind().execute(
        sa.text(f"DELETE FROM position WHERE account_address IS null;")
    )
    op.get_bind().execute(sa.text(f"DELETE FROM position WHERE modified IS null;"))
    op.get_bind().execute(
        sa.text(
            f"DELETE FROM POSITION WHERE (modified) NOT IN (SELECT latest_position.max_modified AS modified FROM (SELECT  max(modified) AS max_modified FROM position GROUP BY token_address, account_address) AS latest_position);"
        )
    )

    op.alter_column(
        "position",
        "token_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "position",
        "account_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=False,
        schema=get_db_schema(),
    )
    op.drop_index(
        "ix_position_token_address",
        table_name="position",
        schema=get_db_schema(),
    )
    op.drop_column("position", "id", schema=get_db_schema())
    # op.drop_constraint("position_pkey", "position", type_="primary")
    op.create_primary_key(
        "position_pkey", "position", ["token_address", "account_address"]
    )


def downgrade():
    connection = op.get_bind()

    op.add_column(
        "position",
        sa.Column("id", sa.BIGINT(), autoincrement=True, nullable=False),
        schema=get_db_schema(),
    )
    op.drop_constraint("position_pkey", "position", type_="primary")
    op.create_primary_key("position_pkey", "position", ["id"])
    op.create_index(
        "ix_position_token_address",
        "position",
        ["token_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "position",
        "account_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "position",
        "token_address",
        existing_type=sa.VARCHAR(length=42),
        nullable=True,
        schema=get_db_schema(),
    )
