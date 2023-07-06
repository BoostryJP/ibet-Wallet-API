"""v23_9_feature_1399

Revision ID: 89675a75634b
Revises: 37cfcb200317
Create Date: 2023-07-07 07:59:54.869008

"""
from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "89675a75634b"
down_revision = "37cfcb200317"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.add_column(
        "mail",
        sa.Column("file_content", sa.Text(), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "mail",
        sa.Column("file_name", sa.String(length=144), nullable=True),
        schema=get_db_schema(),
    )


def downgrade():
    connection = op.get_bind()

    op.drop_column("mail", "file_name", schema=get_db_schema())
    op.drop_column("mail", "file_content", schema=get_db_schema())
