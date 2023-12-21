"""v23_12_0_feature_1451

Revision ID: a70bd06d34a7
Revises: 4164b4e8dfe6
Create Date: 2023-12-03 12:42:26.008879

"""
from alembic import op
import sqlalchemy as sa


from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = "a70bd06d34a7"
down_revision = "4164b4e8dfe6"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.create_index(
        op.f("ix_company_created"),
        "company",
        ["created"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_listing_created"),
        "listing",
        ["created"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_lock_block_timestamp"),
        "lock",
        ["block_timestamp"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_lock_value"),
        "lock",
        ["value"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_locked_position_value"),
        "locked_position",
        ["value"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_notification_created"),
        "notification",
        ["created"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_position_balance"),
        "position",
        ["balance"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_transfer_from_address"),
        "transfer",
        ["from_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_transfer_to_address"),
        "transfer",
        ["to_address"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_transfer_value"),
        "transfer",
        ["value"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_unlock_block_timestamp"),
        "unlock",
        ["block_timestamp"],
        unique=False,
        schema=get_db_schema(),
    )
    op.create_index(
        op.f("ix_unlock_value"),
        "unlock",
        ["value"],
        unique=False,
        schema=get_db_schema(),
    )


def downgrade():
    connection = op.get_bind()

    op.drop_index(op.f("ix_unlock_value"), table_name="unlock", schema=get_db_schema())
    op.drop_index(
        op.f("ix_unlock_block_timestamp"),
        table_name="unlock",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_transfer_value"),
        table_name="transfer",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_transfer_to_address"),
        table_name="transfer",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_transfer_from_address"),
        table_name="transfer",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_position_balance"),
        table_name="position",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_notification_created"),
        table_name="notification",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_locked_position_value"),
        table_name="locked_position",
        schema=get_db_schema(),
    )
    op.drop_index(op.f("ix_lock_value"), table_name="lock", schema=get_db_schema())
    op.drop_index(
        op.f("ix_lock_block_timestamp"),
        table_name="lock",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_listing_created"),
        table_name="listing",
        schema=get_db_schema(),
    )
    op.drop_index(
        op.f("ix_company_created"),
        table_name="company",
        schema=get_db_schema(),
    )
