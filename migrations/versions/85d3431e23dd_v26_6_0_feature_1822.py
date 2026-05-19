"""v26_6_0_feature_1822

Revision ID: 85d3431e23dd
Revises: 93f1494c3975
Create Date: 2026-05-19 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "85d3431e23dd"
down_revision = "93f1494c3975"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "token_list",
        sa.Column("contract_version", sa.String(length=20), nullable=True),
        schema=get_db_schema(),
    )

    token_list = sa.Table(
        "token_list",
        sa.MetaData(),
        sa.Column("contract_version", sa.String(length=20)),
        schema=get_db_schema(),
    )

    op.get_bind().execute(
        token_list.update()
        .where(token_list.c.contract_version.is_(None))
        .values(contract_version="25_09")
    )

    op.alter_column(
        "token_list",
        "contract_version",
        existing_type=sa.String(length=20),
        nullable=False,
        schema=get_db_schema(),
    )


def downgrade():
    op.drop_column("token_list", "contract_version", schema=get_db_schema())
