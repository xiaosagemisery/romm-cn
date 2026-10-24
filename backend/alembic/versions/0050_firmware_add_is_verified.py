"""Add is_verified column to firmware table

Revision ID: 0050_firmware_add_is_verified
Revises: 0049_add_fs_size_bytes
Create Date: 2025-08-22 04:42:22.367888

"""

import sqlalchemy as sa
from alembic import op

from utils.database import is_postgresql

# revision identifiers, used by Alembic.
revision = "0050_firmware_add_is_verified"
down_revision = "0049_add_fs_size_bytes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("firmware", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_verified", sa.Boolean(), nullable=True), if_not_exists=True
        )

    # The verification backfill needed the firmware model, which no longer
    # exists; the table is dropped by 0129, so every row starts unverified.
    if is_postgresql(op.get_bind()):
        op.execute(sa.text("UPDATE firmware SET is_verified = FALSE"))
    else:
        op.execute(sa.text("UPDATE firmware SET is_verified = 0"))

    with op.batch_alter_table("firmware", schema=None) as batch_op:
        batch_op.alter_column("is_verified", existing_type=sa.Boolean(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("firmware", schema=None) as batch_op:
        batch_op.drop_column("is_verified", if_exists=True)
