"""v23_12_0_feature_1454

Revision ID: f6f13d28bb48
Revises: a70bd06d34a7
Create Date: 2023-12-05 22:35:03.035560

"""
from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema, engine

# revision identifiers, used by Alembic.
revision = "f6f13d28bb48"
down_revision = "a70bd06d34a7"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    if engine.name == "mysql":
        op.create_index(
            "ix_company_covering",
            "company",
            [
                "created",
                "address",
                # Index length is specified because of some limits on index length for MySQL
                sa.text("corporate_name(100)"),
                sa.text("rsa_publickey(255)"),
                sa.text("homepage(255)"),
                "modified",
            ],
            unique=False,
            schema=get_db_schema(),
        )
    else:
        op.create_index(
            "ix_company_covering",
            "company",
            [
                "created",
                "address",
                "corporate_name",
                "rsa_publickey",
                "homepage",
                "modified",
            ],
            unique=False,
            schema=get_db_schema(),
        )


def downgrade():
    connection = op.get_bind()

    op.drop_index("ix_company_covering", table_name="company", schema=get_db_schema())
