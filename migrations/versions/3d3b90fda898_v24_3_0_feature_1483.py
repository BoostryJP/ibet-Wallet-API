"""v24_3_0_feature_1483

Revision ID: 3d3b90fda898
Revises: f6f13d28bb48
Create Date: 2024-02-21 09:47:53.425654

"""

from alembic import op
from sqlalchemy import delete
from app.model.db import IDXTokenListBlockNumber


# revision identifiers, used by Alembic.
revision = "3d3b90fda898"
down_revision = "f6f13d28bb48"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    # Delete all `token_cache` data
    op.get_bind().execute(delete(IDXTokenListBlockNumber))


def downgrade():
    connection = op.get_bind()

    pass
