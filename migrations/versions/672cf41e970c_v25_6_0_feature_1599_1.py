"""v25_6_0_feature_1599_1

Revision ID: 672cf41e970c
Revises: 603fd86dc179
Create Date: 2025-03-24 10:38:27.017973

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "672cf41e970c"
down_revision = "603fd86dc179"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.rename_table("token_list", "token_list_register", schema=get_db_schema())


def downgrade():
    connection = op.get_bind()

    op.rename_table("token_list_register", "token_list", schema=get_db_schema())
