import pytest

from models.base import compute_file_name_parts
from models.rom import Rom, compute_name_sort_key


@pytest.mark.parametrize(
    ("file_name", "no_tags", "no_ext", "extension"),
    [
        ("Sonic (USA) [!].md", "Sonic", "Sonic (USA) [!]", "md"),
        ("game.tar.gz", "game", "game", "tar.gz"),
        ("README", "README", "README", ""),
        (
            "Final Fantasy VII (Disc 1).bin",
            "Final Fantasy VII",
            "Final Fantasy VII (Disc 1)",
            "bin",
        ),
    ],
)
def test_compute_file_name_parts(file_name, no_tags, no_ext, extension):
    parts = compute_file_name_parts(file_name)

    assert parts.no_tags == no_tags
    assert parts.no_ext == no_ext
    assert parts.extension == extension


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("The Legend of Zelda 2", "legend of zelda 000000000002"),
        ("A Bug's Life", "bug's life"),
        ("Final Fantasy 10", "final fantasy 000000000010"),
        (None, ""),
    ],
)
def test_compute_name_sort_key(name, expected):
    assert compute_name_sort_key(name) == expected


def test_rom_validator_derives_fs_name_parts_on_construction():
    rom = Rom(fs_name="The Legend of Zelda (USA) (Rev 1).z64")

    assert rom.fs_name_no_tags == "The Legend of Zelda"
    assert rom.fs_name_no_ext == "The Legend of Zelda (USA) (Rev 1)"
    assert rom.fs_extension == "z64"
    # The validator only fires on assignment; name was never set, so its
    # derived column keeps the column default rather than being computed.
    assert rom.name_sort_key is None


def test_rom_validator_resyncs_on_mutation():
    rom = Rom(fs_name="old.zip", name="The Old Game")
    assert rom.name_sort_key == "old game"

    rom.fs_name = "Sonic (Europe).md"
    rom.name = "A New Game 2"

    assert rom.fs_name_no_tags == "Sonic"
    assert rom.fs_extension == "md"
    assert rom.name_sort_key == "new game 000000000002"
