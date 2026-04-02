"""v26_6_0_feature_1792

Revision ID: 4df7e2c1b8a3
Revises: d7de2d20be69
Create Date: 2026-04-02 20:04:29.343543

"""

from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


from app.database import engine, get_db_schema

# revision identifiers, used by Alembic.
revision = "4df7e2c1b8a3"
down_revision = "d7de2d20be69"
branch_labels = None
depends_on = None


AUDIT_TABLE_NAMES = [
    "account_tag",
    "bond_token",
    "chat_webhook",
    "company",
    "consume_coupon",
    "coupon_token",
    "executable_contract",
    "idx_position_bond_block_number",
    "idx_position_coupon_block_number",
    "idx_position_membership_block_number",
    "idx_position_share_block_number",
    "idx_token_list_block_number",
    "idx_transfer_approval_block_number",
    "idx_transfer_block_number",
    "listing",
    "lock",
    "locked_position",
    "mail",
    "membership_token",
    "node",
    "notification",
    "notification_attribute_value",
    "notification_block_number",
    "position",
    "public_account_list",
    "share_token",
    "token_holder",
    "token_holders_list",
    "token_list",
    "token_list_register",
    "transfer",
    "transfer_approval",
    "unlock",
]


def _get_audit_datetime_type():
    if engine.name == "mysql":
        return mysql.DATETIME(fsp=6)
    else:
        return sa.DateTime()


def _get_audit_table(table_name: str):
    datetime_type = _get_audit_datetime_type()
    return sa.Table(
        table_name,
        sa.MetaData(),
        sa.Column("created", datetime_type),
        sa.Column("modified", datetime_type),
        schema=get_db_schema(),
    )


def _backfill_audit_columns(table_name: str, current_dt: datetime):
    table = _get_audit_table(table_name)

    op.get_bind().execute(
        table.update().where(table.c.created.is_(None)).values(created=current_dt)
    )
    op.get_bind().execute(
        table.update().where(table.c.modified.is_(None)).values(modified=current_dt)
    )


def _alter_audit_columns(table_name: str, nullable: bool):
    datetime_type = _get_audit_datetime_type()
    op.alter_column(
        table_name,
        "created",
        existing_type=datetime_type,
        nullable=nullable,
        schema=get_db_schema(),
    )
    op.alter_column(
        table_name,
        "modified",
        existing_type=datetime_type,
        nullable=nullable,
        schema=get_db_schema(),
    )


def upgrade():
    current_dt = datetime.now(UTC).replace(tzinfo=None)
    datetime_type = _get_audit_datetime_type()

    ############################
    # Migration for listing
    ############################
    listing = sa.Table(
        "listing",
        sa.MetaData(),
        sa.Column("token_address", sa.String(length=256)),
        sa.Column("is_public", sa.Boolean()),
        sa.Column("owner_address", sa.String(length=256)),
        sa.Column("created", datetime_type),
        sa.Column("modified", datetime_type),
        schema=get_db_schema(),
    )
    executable_contract = sa.Table(
        "executable_contract",
        sa.MetaData(),
        sa.Column("contract_address", sa.String(length=256)),
        schema=get_db_schema(),
    )
    listing_invalid_condition = sa.or_(
        listing.c.token_address.is_(None),
        listing.c.owner_address.is_(None),
    )

    op.get_bind().execute(
        listing.update().where(listing.c.is_public.is_(None)).values(is_public=True)
    )
    op.get_bind().execute(listing.delete().where(listing_invalid_condition))
    op.get_bind().execute(
        executable_contract.delete().where(
            sa.not_(
                sa.exists(
                    sa.select(1)
                    .select_from(listing)
                    .where(
                        listing.c.token_address
                        == executable_contract.c.contract_address
                    )
                )
            )
        )
    )

    ############################
    # Migration for created/modified columns
    ############################
    for table_name in AUDIT_TABLE_NAMES:
        _backfill_audit_columns(table_name, current_dt)

    ############################
    # Migration for listing not null columns
    ############################
    op.alter_column(
        "listing",
        "token_address",
        existing_type=sa.String(length=256),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "listing",
        "is_public",
        existing_type=sa.Boolean(),
        nullable=False,
        schema=get_db_schema(),
    )
    op.alter_column(
        "listing",
        "owner_address",
        existing_type=sa.String(length=256),
        nullable=False,
        schema=get_db_schema(),
    )

    for table_name in AUDIT_TABLE_NAMES:
        _alter_audit_columns(table_name, nullable=False)


def downgrade():
    op.alter_column(
        "listing",
        "token_address",
        existing_type=sa.String(length=256),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "listing",
        "is_public",
        existing_type=sa.Boolean(),
        nullable=True,
        schema=get_db_schema(),
    )
    op.alter_column(
        "listing",
        "owner_address",
        existing_type=sa.String(length=256),
        nullable=True,
        schema=get_db_schema(),
    )

    for table_name in AUDIT_TABLE_NAMES:
        _alter_audit_columns(table_name, nullable=True)
