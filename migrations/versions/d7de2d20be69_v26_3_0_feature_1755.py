"""v26_3_0_feature_1755

Revision ID: d7de2d20be69
Revises: 1cd2ee459858
Create Date: 2026-02-10 02:53:36.815929

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "d7de2d20be69"
down_revision = "1cd2ee459858"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.drop_index(
        op.f("ix_agreement_buyer_address"),
        table_name="agreement",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_agreement_seller_address"),
        table_name="agreement",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_agreement_unique_order_id"),
        table_name="agreement",
        schema=get_db_schema(),
    )
    op.drop_table("agreement", schema=get_db_schema())
    op.drop_index(
        op.f("ix_order_exchange_address"), table_name="order", schema=get_db_schema()
    )
    op.drop_index(op.f("ix_order_order_id"), table_name="order", schema=get_db_schema())
    op.drop_index(
        op.f("ix_order_token_address"), table_name="order", schema=get_db_schema()
    )
    op.drop_index(
        op.f("ix_order_unique_order_id"), table_name="order", schema=get_db_schema()
    )
    op.drop_table("order", schema=get_db_schema())


def downgrade():
    connection = op.get_bind()

    op.create_table(
        "order",
        sa.Column(
            "created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "modified", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column("id", sa.BIGINT(), autoincrement=True, nullable=False),
        sa.Column(
            "transaction_hash",
            sa.VARCHAR(length=66),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "token_address", sa.VARCHAR(length=42), autoincrement=False, nullable=True
        ),
        sa.Column(
            "exchange_address",
            sa.VARCHAR(length=42),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("order_id", sa.BIGINT(), autoincrement=False, nullable=True),
        sa.Column(
            "unique_order_id",
            sa.VARCHAR(length=256),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "account_address", sa.VARCHAR(length=42), autoincrement=False, nullable=True
        ),
        sa.Column(
            "counterpart_address",
            sa.VARCHAR(length=42),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("is_buy", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column("price", sa.BIGINT(), autoincrement=False, nullable=True),
        sa.Column("amount", sa.BIGINT(), autoincrement=False, nullable=True),
        sa.Column(
            "agent_address", sa.VARCHAR(length=42), autoincrement=False, nullable=True
        ),
        sa.Column("is_cancelled", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column(
            "order_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("order_pkey")),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_order_unique_order_id"),
        "order",
        ["unique_order_id"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_order_token_address"),
        "order",
        ["token_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_order_order_id"),
        "order",
        ["order_id"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_order_exchange_address"),
        "order",
        ["exchange_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_table(
        "agreement",
        sa.Column(
            "created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "modified", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column("id", sa.BIGINT(), autoincrement=True, nullable=False),
        sa.Column(
            "transaction_hash",
            sa.VARCHAR(length=66),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "exchange_address",
            sa.VARCHAR(length=42),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("order_id", sa.BIGINT(), autoincrement=False, nullable=False),
        sa.Column("agreement_id", sa.BIGINT(), autoincrement=False, nullable=False),
        sa.Column(
            "unique_order_id",
            sa.VARCHAR(length=256),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "buyer_address", sa.VARCHAR(length=42), autoincrement=False, nullable=True
        ),
        sa.Column(
            "seller_address", sa.VARCHAR(length=42), autoincrement=False, nullable=True
        ),
        sa.Column(
            "counterpart_address",
            sa.VARCHAR(length=42),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("amount", sa.BIGINT(), autoincrement=False, nullable=True),
        sa.Column("status", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column(
            "agreement_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "settlement_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.PrimaryKeyConstraint(
            "id",
            "exchange_address",
            "order_id",
            "agreement_id",
            name=op.f("agreement_pkey"),
        ),
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_agreement_unique_order_id"),
        "agreement",
        ["unique_order_id"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_agreement_seller_address"),
        "agreement",
        ["seller_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_agreement_buyer_address"),
        "agreement",
        ["buyer_address"],
        unique=False,
        schema=get_db_schema(),
    )
