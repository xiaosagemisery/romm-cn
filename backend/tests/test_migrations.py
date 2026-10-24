"""Guard the models against drifting away from the migrated schema.

The test database is built from the migrations, so an index declared in one but
not the other goes unnoticed until autogenerate proposes dropping it.
"""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Table, UniqueConstraint

import models
from handler.database import db_collection_handler
from handler.database.base_handler import sync_engine
from models.base import BaseModel
from models.collection import Collection, SmartCollection
from models.rom import compute_full_path_hash
from models.user import User
from utils.database import (
    AUTOGENERATE_EXEMPT_INDEX_NAMES,
    POSTGRESQL_FK_INDEXES,
    full_path_digest_sql,
)

# `compare_metadata` yields flat tuples for schema-level diffs, and a list of
# tuples for column-level ones. Only these two name an index.
INDEX_DIFF_OPS = frozenset({"add_index", "remove_index"})


def _leading_columns(table: Table) -> set[str]:
    """Names of the columns a lookup on this table can start from."""
    groups = [list(table.primary_key.columns)]
    groups += [list(index.columns) for index in table.indexes]
    groups += [
        list(constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    ]
    return {columns[0].name for columns in groups if columns}


def test_no_index_drift_between_models_and_migrations():
    """Every migrated index is declared on its model, and vice versa.

    A failure names the index: declare it in the model's `__table_args__`, or in
    `AUTOGENERATE_EXEMPT_INDEX_NAMES` if it is dialect-specific.
    """
    models.load_all_models()

    with sync_engine.connect() as connection:
        context = MigrationContext.configure(connection)
        drift = [
            f"{diff[0]}: {diff[1].name} on {diff[1].table.name}"
            for diff in compare_metadata(context, BaseModel.metadata)
            if not isinstance(diff, list)
            and diff[0] in INDEX_DIFF_OPS
            and diff[1].name not in AUTOGENERATE_EXEMPT_INDEX_NAMES
        ]

    assert drift == []


def test_postgresql_fk_indexes_cover_every_unindexed_foreign_key():
    """`POSTGRESQL_FK_INDEXES` holds exactly the foreign keys that need it.

    MariaDB and MySQL index a foreign key implicitly unless its column already
    leads an index; PostgreSQL does not.
    """
    models.load_all_models()

    expected = {
        (table.name, f"ix_{table.name}_{column}", column)
        for table in BaseModel.metadata.tables.values()
        for constraint in table.foreign_key_constraints
        for column in [c.name for c in constraint.columns]
        if len(constraint.columns) == 1 and column not in _leading_columns(table)
    }

    assert expected == set(POSTGRESQL_FK_INDEXES)


@pytest.mark.parametrize(
    "fs_path,fs_name",
    [
        ("roms/nes", "Game (USA).zip"),
        ("roms/nes/Hacks & Tra'nslations", "Zelda [T-Eng].nes"),
        ("roms/nes/Ünïcøde", "Pokémon Édition Rouge.gb"),
        ("", ""),
    ],
)
def test_the_migrated_full_path_digest_matches_the_models(fs_path: str, fs_name: str):
    """0126 backfills `full_path_hash` in SQL; the app writes it from Python.

    A mismatch would make every pre-existing rom look new to the unique index.
    """
    with sync_engine.connect() as connection:
        digest = connection.execute(
            sa.text(
                f"SELECT {full_path_digest_sql(connection)} FROM "
                "(SELECT :fs_path AS fs_path, :fs_name AS fs_name) AS one_rom"
            ),
            {"fs_path": fs_path, "fs_name": fs_name},
        ).scalar_one()

    assert digest == compute_full_path_hash(fs_path, fs_name)


def _load_migration(filename: str) -> ModuleType:
    path = Path(__file__).parent.parent / "alembic" / "versions" / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_cross_user_smart_scopes_revision_empties_only_those_caches(
    admin_user: User, editor_user: User
):
    migration = _load_migration("0152_cross_user_smart_scopes.py")
    private, public = (
        db_collection_handler.add_collection(
            Collection(
                name=name, description="", user_id=admin_user.id, is_public=is_public
            )
        )
        for name, is_public in (("Secret", False), ("Shared", True))
    )
    borrowed, own, borrowed_public = (
        db_collection_handler.add_smart_collection(
            SmartCollection(
                name=f"Scoped {index}",
                user_id=owner.id,
                rom_ids=[1, 2],
                path_covers_small=["cover"],
                filter_criteria={"collection_id": scope.id},
            )
        )
        for index, (owner, scope) in enumerate(
            (
                (editor_user, private),
                (admin_user, private),
                (editor_user, public),
            )
        )
    )

    with sync_engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

    cleared = db_collection_handler.get_smart_collection(borrowed.id)
    assert cleared is not None
    assert (cleared.rom_ids, cleared.path_covers_small) == ([], [])
    for kept_id in (own.id, borrowed_public.id):
        kept = db_collection_handler.get_smart_collection(kept_id)
        assert kept is not None
        assert (kept.rom_ids, kept.path_covers_small) == ([1, 2], ["cover"])
