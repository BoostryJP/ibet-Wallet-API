"""v25_12_0_feature_1692

Revision ID: 835dd5b51e23
Revises: a5e395bf46a9
Create Date: 2025-11-12 19:27:29.889267

"""

from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "835dd5b51e23"
down_revision = "a5e395bf46a9"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.add_column(
        "company",
        sa.Column("trustee_corporate_name", sa.String(length=30), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "company",
        sa.Column("trustee_corporate_number", sa.String(length=20), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "company",
        sa.Column("trustee_corporate_address", sa.String(length=60), nullable=True),
        schema=get_db_schema(),
    )
    op.add_column(
        "token_list",
        sa.Column("issuer_address", sa.String(length=42), nullable=True),
        schema=get_db_schema(),
    )
    op.create_check_constraint(
        "ck_company_trustee_fields_complete",
        "company",
        "((trustee_corporate_name IS NULL AND trustee_corporate_number IS NULL AND trustee_corporate_address IS NULL) "
        "OR (trustee_corporate_name IS NOT NULL AND trustee_corporate_number IS NOT NULL AND trustee_corporate_address IS NOT NULL))",
        schema=get_db_schema(),
    )


def downgrade():
    connection = op.get_bind()

    op.drop_constraint(
        "ck_company_trustee_fields_complete",
        "company",
        type_="check",
        schema=get_db_schema(),
    )
    op.drop_column("token_list", "issuer_address", schema=get_db_schema())
    op.drop_column("company", "trustee_corporate_address", schema=get_db_schema())
    op.drop_column("company", "trustee_corporate_number", schema=get_db_schema())
    op.drop_column("company", "trustee_corporate_name", schema=get_db_schema())
