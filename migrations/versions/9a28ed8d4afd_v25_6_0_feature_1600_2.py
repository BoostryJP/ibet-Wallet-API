"""v25_6_0_feature_1600_2

Revision ID: 9a28ed8d4afd
Revises: f8faa777c5f2
Create Date: 2025-04-03 15:53:32.528086

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "9a28ed8d4afd"
down_revision = "f8faa777c5f2"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.add_column(
        "public_account_list",
        sa.Column("key_manager_name", sa.String(length=200), nullable=False),
        schema=get_db_schema(),
    )


def downgrade():
    connection = op.get_bind()

    op.drop_column("public_account_list", "key_manager_name", schema=get_db_schema())
