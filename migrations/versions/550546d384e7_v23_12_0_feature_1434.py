"""v23_12_0_feature_1434

Revision ID: 550546d384e7
Revises: 1f0ac8015f2f
Create Date: 2023-10-30 15:18:01.628901

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import update


from app.database import get_db_schema
from app.model.db import IDXBondToken

# revision identifiers, used by Alembic.
revision = "550546d384e7"
down_revision = "1f0ac8015f2f"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.add_column(
        "bond_token",
        sa.Column("face_value_currency", sa.String(length=3), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "bond_token",
        sa.Column("interest_payment_currency", sa.String(length=3), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "bond_token",
        sa.Column("redemption_value_currency", sa.String(length=3), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "bond_token",
        sa.Column("base_fx_rate", sa.Numeric(precision=16, scale=6), nullable=True),
        schema=get_db_schema(),
    )

    stmt = update(IDXBondToken).values(
        face_value_currency="JPY",
        interest_payment_currency="",
        redemption_value_currency="",
        base_fx_rate=0.0,
    )
    op.get_bind().execute(stmt)

    op.alter_column(
        "bond_token",
        "face_value_currency",
        existing_type=sa.String(length=3),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "bond_token",
        "interest_payment_currency",
        existing_type=sa.String(length=3),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "bond_token",
        "redemption_value_currency",
        existing_type=sa.String(length=3),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "bond_token",
        "base_fx_rate",
        existing_type=sa.Numeric(precision=16, scale=6),
        nullable=False,
        schema=get_db_schema(),
    )


def downgrade():
    connection = op.get_bind()

    op.drop_column("bond_token", "base_fx_rate", schema=get_db_schema())
    op.drop_column("bond_token", "redemption_value_currency", schema=get_db_schema())
    op.drop_column("bond_token", "interest_payment_currency", schema=get_db_schema())
    op.drop_column("bond_token", "face_value_currency", schema=get_db_schema())
