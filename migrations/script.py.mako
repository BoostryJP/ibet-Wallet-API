"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

from app.database import get_db_schema

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    connection = op.get_bind()

    ${upgrades if upgrades else "pass"}


def downgrade():
    connection = op.get_bind()

    ${downgrades if downgrades else "pass"}
