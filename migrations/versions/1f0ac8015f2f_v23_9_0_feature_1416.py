"""v23.9.0_feature_1416

Revision ID: 1f0ac8015f2f
Revises: ae65533fdc41
Create Date: 2023-08-02 20:08:28.198371

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "1f0ac8015f2f"
down_revision = "ae65533fdc41"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    if op.get_bind().dialect.name == "mysql":
        op.alter_column(
            "mail",
            "file_content",
            existing_type=sa.BLOB(),
            type_=sa.LargeBinary().with_variant(mysql.LONGBLOB(), "mysql"),
            existing_nullable=True,
            schema=get_db_schema(),
        )


def downgrade():
    connection = op.get_bind()

    if op.get_bind().dialect.name == "mysql":
        op.alter_column(
            "mail",
            "file_content",
            existing_type=sa.LargeBinary().with_variant(mysql.LONGBLOB(), "mysql"),
            type_=sa.BLOB(),
            existing_nullable=True,
            schema=get_db_schema(),
        )
