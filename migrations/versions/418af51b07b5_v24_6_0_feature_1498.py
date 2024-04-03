"""v24_6_0_feature_1498

Revision ID: 418af51b07b5
Revises: 3d3b90fda898
Create Date: 2024-04-03 20:12:10.136869

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import update

from app.database import get_db_schema
from app.model.db import IDXBondToken, IDXShareToken

# revision identifiers, used by Alembic.
revision = "418af51b07b5"
down_revision = "3d3b90fda898"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.add_column(
        "bond_token",
        sa.Column("require_personal_info_registered", sa.Boolean(), nullable=True),
        schema=get_db_schema(),
    )
    stmt = update(IDXBondToken).values(require_personal_info_registered=True)
    op.get_bind().execute(stmt)

    op.add_column(
        "share_token",
        sa.Column("require_personal_info_registered", sa.Boolean(), nullable=True),
        schema=get_db_schema(),
    )
    stmt = update(IDXShareToken).values(require_personal_info_registered=True)
    op.get_bind().execute(stmt)


def downgrade():
    connection = op.get_bind()

    op.drop_column(
        "share_token",
        "require_personal_info_registered",
        schema=get_db_schema(),
    )
    op.drop_column(
        "bond_token",
        "require_personal_info_registered",
        schema=get_db_schema(),
    )
