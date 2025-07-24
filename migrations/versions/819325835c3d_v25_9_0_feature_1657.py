"""v25_9_0_feature_1657

Revision ID: 819325835c3d
Revises: 9a28ed8d4afd
Create Date: 2025-07-23 18:08:21.277260

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import update, cast, String


from app.database import get_db_schema
from app.model.db import IDXTransfer, IDXLock, IDXUnlock

# revision identifiers, used by Alembic.
revision = "819325835c3d"
down_revision = "9a28ed8d4afd"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    op.get_bind().execute(
        update(IDXTransfer)
        .values(message=None, data={})
        .where(IDXTransfer.message == "inheritance")
    )
    op.get_bind().execute(
        update(IDXLock)
        .values(data={})
        .where(cast(IDXLock.data, String).like(f"%inheritance%"))
    )
    op.get_bind().execute(
        update(IDXUnlock)
        .values(data={})
        .where(cast(IDXUnlock.data, String).like(f"%inheritance%"))
    )


def downgrade():
    connection = op.get_bind()

    pass
