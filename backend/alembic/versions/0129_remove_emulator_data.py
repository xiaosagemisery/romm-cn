"""Drop the emulator-era tables and columns

Removes the save, state, screenshot, memory card, firmware, play session,
save-sync and streaming container tables, the sync columns on ``devices``, and
the ``firmware`` rows of the permission tables, whose entity enum no longer
has that member.

Revision ID: 0129_remove_emulator_data
Revises: 0128_hltb_main_story_column
Create Date: 2026-10-24 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]

from utils.database import is_postgresql

# revision identifiers, used by Alembic.
revision = "0129_remove_emulator_data"
down_revision = "0128_hltb_main_story_column"
branch_labels = None
depends_on = None

# Children before the tables they reference.
DROPPED_TABLES = (
    "device_save_sync",
    "play_sessions",
    "sync_sessions",
    "memory_card_versions",
    "memory_cards",
    "streaming_container_adoptions",
    "saves",
    "states",
    "screenshots",
    "firmware",
)
DROPPED_DEVICE_COLUMNS = ("sync_mode", "sync_enabled", "sync_config")
DROPPED_ENUM_TYPES = ("syncmode", "syncsessionstatus")
PERMISSION_TABLES = (
    "permission_group_grants",
    "user_permission_overrides",
    "hidden_entities",
)


def upgrade() -> None:
    bind = op.get_bind()

    for table in PERMISSION_TABLES:
        op.execute(sa.text(f"DELETE FROM {table} WHERE entity = 'firmware'"))

    for table in DROPPED_TABLES:
        op.drop_table(table, if_exists=True)

    device_columns = {c["name"] for c in sa.inspect(bind).get_columns("devices")}
    for column in DROPPED_DEVICE_COLUMNS:
        if column in device_columns:
            op.drop_column("devices", column)

    if is_postgresql(bind):
        for enum_type in DROPPED_ENUM_TYPES:
            op.execute(sa.text(f"DROP TYPE IF EXISTS {enum_type}"))


def downgrade() -> None:
    raise NotImplementedError(
        "The emulator tables were dropped with their data and cannot be restored"
    )
