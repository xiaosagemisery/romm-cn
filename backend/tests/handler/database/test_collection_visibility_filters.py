"""The ROM filters answer for the collections the caller can see, and no others."""

from handler.database import db_collection_handler, db_rom_handler
from models.collection import Collection, SmartCollection
from models.rom import Rom
from models.user import User


def _collection(owner: User, rom: Rom, *, is_public: bool = False) -> Collection:
    collection = db_collection_handler.add_collection(
        Collection(
            name=f"Collection {owner.id} {is_public}",
            description="",
            user_id=owner.id,
            is_public=is_public,
        )
    )
    db_collection_handler.add_roms_to_collection(collection.id, [rom.id])
    return collection


def _smart_collection(
    owner: User, criteria: dict, *, is_public: bool = False
) -> SmartCollection:
    return db_collection_handler.add_smart_collection(
        SmartCollection(
            name=f"Smart {owner.id} {is_public}",
            description="",
            user_id=owner.id,
            is_public=is_public,
            filter_criteria=criteria,
        )
    )


def _ids(**filters) -> set[int]:
    return {rom.id for rom in db_rom_handler.get_roms_scalar(**filters)}


def test_collection_filter_hides_another_users_private_collection(
    rom: Rom, admin_user: User, editor_user: User
):
    private = _collection(admin_user, rom)

    assert _ids(collection_id=private.id, user_id=admin_user.id) == {rom.id}
    assert _ids(collection_id=private.id, user_id=editor_user.id) == set()


def test_collection_filter_serves_a_shared_collection_to_everyone(
    rom: Rom, admin_user: User, editor_user: User
):
    shared = _collection(admin_user, rom, is_public=True)

    assert _ids(collection_id=shared.id, user_id=editor_user.id) == {rom.id}


def test_smart_collection_filter_hides_another_users_private_smart_collection(
    rom: Rom, admin_user: User, editor_user: User
):
    private = _smart_collection(admin_user, {"platform_ids": [rom.platform_id]})

    assert _ids(smart_collection_id=private.id, user_id=admin_user.id) == {rom.id}
    assert _ids(smart_collection_id=private.id, user_id=editor_user.id) == set()


def test_smart_collection_scoped_to_another_users_private_collection_matches_nothing(
    rom: Rom, admin_user: User, editor_user: User
):
    private = _collection(admin_user, rom)
    borrowed = _smart_collection(
        editor_user, {"collection_id": private.id}, is_public=True
    )

    assert _ids(smart_collection_id=borrowed.id, user_id=editor_user.id) == set()
    assert _ids(smart_collection_id=borrowed.id, user_id=admin_user.id) == set()
    refreshed = db_collection_handler.refresh_smart_collection(borrowed.id)
    assert refreshed is not None
    assert refreshed.rom_ids == []


def test_smart_collection_scoped_to_its_owners_collection_serves_its_viewers(
    rom: Rom, admin_user: User, editor_user: User
):
    private = _collection(admin_user, rom)
    shared = _smart_collection(
        admin_user, {"collection_id": private.id}, is_public=True
    )

    assert _ids(smart_collection_id=shared.id, user_id=editor_user.id) == {rom.id}


def test_unsharing_a_collection_empties_the_smart_collections_scoped_to_it(
    rom: Rom, admin_user: User, editor_user: User
):
    shared = _collection(admin_user, rom, is_public=True)
    borrowed = _smart_collection(editor_user, {"collection_id": shared.id})
    refreshed = db_collection_handler.refresh_smart_collection(borrowed.id)
    assert refreshed is not None
    assert refreshed.rom_ids == [rom.id]

    db_collection_handler.update_collection(
        shared.id,
        {"name": shared.name, "description": "", "is_public": False},
        [rom.id],
    )
    db_collection_handler.refresh_smart_collections_scoped_to(shared.id)

    after = db_collection_handler.get_smart_collection(borrowed.id)
    assert after is not None
    assert after.rom_ids == []
