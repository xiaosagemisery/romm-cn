import io
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from tests._zipfile_shim import reload_zipfile

from handler.redis_handler import async_cache
from models.platform import Platform
from models.rom import Rom
from utils import product_codes
from utils.platform_slugs import UniversalPlatformSlug as UPS
from utils.product_codes import (
    GAMETDB_TITLES_KEY,
    GameTDBTitle,
    gamecube_product_code,
    gametdb_title,
    igdb_title_by_alternative_name,
    n3ds_product_code,
    n64_header_title,
    parse_gametdb,
    product_code_search_term,
)


def _n64_header(name: bytes, code: bytes) -> bytes:
    header = bytearray(0x40)
    header[:4] = bytes.fromhex("80371240")
    header[0x20 : 0x20 + len(name)] = name
    header[0x3B:0x3F] = code
    return bytes(header)


def _gametdb_zip(name: str, games: str) -> bytes:
    xml = f'<?xml version="1.0" encoding="UTF-8"?><datafile>{games}</datafile>'
    buffer = io.BytesIO()
    reload_zipfile()
    with zipfile.ZipFile(buffer, "w") as zipped:
        zipped.writestr(name, xml.encode("utf-8"))
    return buffer.getvalue()


def _game(game_id: str, game_type: str, title: str) -> str:
    return (
        f"<game><id>{game_id}</id><type>{game_type}</type>"
        f'<locale lang="JA"><title>JA {title}</title></locale>'
        f'<locale lang="EN"><title>{title}</title></locale></game>'
    )


@pytest.mark.parametrize(
    ("title_id", "code"),
    [
        ("474D5345", "GMSE"),
        ("47334645", "G3FE"),
        ("00040000001B5000", None),
        (None, None),
    ],
)
def test_gamecube_product_code_reads_the_hex_title_id(title_id, code):
    assert gamecube_product_code(title_id) == code


@pytest.mark.parametrize(
    ("product", "code"),
    [(b"CTR-P-BZLE", "BZLE"), (b"KTR-P-CFMJ", "CFMJ"), (b"homuhomu", None)],
)
def test_n3ds_product_code_follows_the_first_partition(
    tmp_path: Path, product: bytes, code: str | None
):
    image = bytearray(0x4400)
    image[0x100:0x104] = b"NCSD"
    image[0x120:0x124] = (0x20).to_bytes(4, "little")
    image[0x4100:0x4104] = b"NCCH"
    image[0x4150 : 0x4150 + len(product)] = product
    path = tmp_path / "game.cci"
    path.write_bytes(bytes(image))

    assert n3ds_product_code(path) == code


def test_n3ds_product_code_ignores_other_files(tmp_path: Path):
    path = tmp_path / "game.cci"
    path.write_bytes(bytes(0x4400))

    assert n3ds_product_code(path) is None


@pytest.mark.parametrize(
    ("header", "title"),
    [
        (_n64_header(b"DONKEY KONG 64", b"NDOE"), "DONKEY KONG 64"),
        (_n64_header("神游马力欧".encode("gbk"), b"BSMC"), "Super Mario 64"),
        (_n64_header("未知".encode("gbk"), b"NXXJ"), None),
        (bytes(0x40), None),
    ],
)
def test_n64_header_title(tmp_path: Path, header: bytes, title: str | None):
    path = tmp_path / "game.z64"
    path.write_bytes(header)

    assert n64_header_title(path) == title


def test_n64_header_title_reads_byte_swapped_images(tmp_path: Path):
    header = _n64_header(b"DONKEY KONG 64", b"NDOE")
    path = tmp_path / "game.v64"
    path.write_bytes(b"".join(header[i : i + 2][::-1] for i in range(0, 0x40, 2)))

    assert n64_header_title(path) == "DONKEY KONG 64"


def test_parse_gametdb_keeps_retail_gamecube_titles_by_product_code():
    archive = _gametdb_zip(
        "wiitdb.xml",
        _game("GMSE02", "CUSTOM", "Super Mario Sunshine Multiplayer")
        + _game("GMSE01", "GameCube", "Super Mario Sunshine")
        + _game("RMGE01", "", "Super Mario Galaxy"),
    )

    assert parse_gametdb(archive, UPS.NGC) == {"GMSE": "Super Mario Sunshine"}


def test_parse_gametdb_skips_3ds_homebrew():
    archive = _gametdb_zip(
        "3dstdb.xml",
        _game("BZLE", "3DS", "The Legend of Zelda: A Link Between Worlds")
        + _game("HBRW", "Homebrew", "Some Homebrew"),
    )

    assert parse_gametdb(archive, UPS.N3DS) == {
        "BZLE": "The Legend of Zelda: A Link Between Worlds"
    }


async def test_gametdb_title_refreshes_a_stale_database(mocker):
    mocker.patch.object(async_cache, "exists", new_callable=AsyncMock, return_value=0)
    hmget = mocker.patch.object(
        async_cache,
        "hmget",
        new_callable=AsyncMock,
        return_value=["Super Mario Sunshine", None],
    )
    refresh = mocker.patch.object(product_codes, "_refresh_gametdb", new=AsyncMock())

    assert await gametdb_title(UPS.NGC, "GMSE") == GameTDBTitle(
        "Super Mario Sunshine", western=True
    )
    refresh.assert_awaited_once_with(UPS.NGC)
    hmget.assert_awaited_once_with(
        GAMETDB_TITLES_KEY.format(platform=UPS.NGC), ["GMSE", "GMSP"]
    )


async def test_gametdb_title_reuses_a_fresh_database(mocker):
    mocker.patch.object(async_cache, "exists", new_callable=AsyncMock, return_value=1)
    mocker.patch.object(
        async_cache, "hmget", new_callable=AsyncMock, return_value=[None, None, None]
    )
    refresh = mocker.patch.object(product_codes, "_refresh_gametdb", new=AsyncMock())

    assert await gametdb_title(UPS.N3DS, "ZZZJ") is None
    refresh.assert_not_awaited()


async def test_gametdb_title_prefers_a_western_sibling_of_a_japanese_code(mocker):
    mocker.patch.object(async_cache, "exists", new_callable=AsyncMock, return_value=1)
    hmget = mocker.patch.object(
        async_cache,
        "hmget",
        new_callable=AsyncMock,
        return_value=[
            "The Legend of Zelda: Tri Force Heroes",
            None,
            "Zelda no Densetsu: Triforce 3-Juushi",
        ],
    )

    assert await gametdb_title(UPS.N3DS, "EA3J") == GameTDBTitle(
        "The Legend of Zelda: Tri Force Heroes", western=True
    )
    hmget.assert_awaited_once_with(
        GAMETDB_TITLES_KEY.format(platform=UPS.N3DS), ["EA3E", "EA3P", "EA3J"]
    )


async def test_gametdb_title_falls_back_to_the_japanese_entry(mocker):
    mocker.patch.object(async_cache, "exists", new_callable=AsyncMock, return_value=1)
    mocker.patch.object(
        async_cache,
        "hmget",
        new_callable=AsyncMock,
        return_value=[None, None, "Dai Gyakuten Saiban 2"],
    )

    assert await gametdb_title(UPS.N3DS, "AJ2J") == GameTDBTitle(
        "Dai Gyakuten Saiban 2", western=False
    )


async def test_a_japanese_gametdb_title_resolves_through_igdb_alternative_names(
    mocker,
):
    mocker.patch.object(
        product_codes,
        "gametdb_title",
        new=AsyncMock(return_value=GameTDBTitle("Dai Gyakuten Saiban 2", False)),
    )
    mocker.patch.object(
        product_codes,
        "igdb_title_by_alternative_name",
        new=AsyncMock(return_value="The Great Ace Attorney 2: Resolve"),
    )

    assert (
        await product_codes._catalog_title(UPS.N3DS, "AJ2J")
        == "The Great Ace Attorney 2: Resolve"
    )


async def test_a_western_gametdb_title_skips_igdb(mocker):
    mocker.patch.object(
        product_codes,
        "gametdb_title",
        new=AsyncMock(return_value=GameTDBTitle("Kirby: Planet Robobot", True)),
    )
    lookup = mocker.patch.object(
        product_codes, "igdb_title_by_alternative_name", new=AsyncMock()
    )

    assert await product_codes._catalog_title(UPS.N3DS, "AT3A") == (
        "Kirby: Planet Robobot"
    )
    lookup.assert_not_awaited()


@pytest.mark.parametrize(
    ("results", "name"),
    [
        (
            [{"game": {"name": "Pokemon Rumble Blast", "platforms": [37]}}] * 2,
            "Pokemon Rumble Blast",
        ),
        (
            [
                {"game": {"name": "Fire Emblem Warriors", "platforms": [137, 130]}},
                {"game": {"name": "Fire Emblem Warriors (Wii U)", "platforms": [41]}},
            ],
            "Fire Emblem Warriors",
        ),
        (
            [
                {"game": {"name": "A", "platforms": [37]}},
                {"game": {"name": "B", "platforms": [37]}},
            ],
            None,
        ),
        ([], None),
    ],
)
async def test_igdb_title_by_alternative_name_needs_one_game_on_the_platform(
    mocker, results, name
):
    from handler.metadata import meta_igdb_handler

    mocker.patch.object(meta_igdb_handler, "is_enabled", return_value=True)
    lookup = mocker.patch.object(
        meta_igdb_handler.igdb_service,
        "list_alternative_names",
        new=AsyncMock(return_value=results),
    )

    assert await igdb_title_by_alternative_name(UPS.N3DS, 'Super "Scramble"') == name
    assert lookup.await_args.kwargs["where"] == 'name ~ "Super \\"Scramble\\""'


async def test_a_chinese_filename_searches_by_its_product_code_title(mocker):
    translate = mocker.patch.object(
        product_codes, "translate_search_term", new=AsyncMock()
    )
    mocker.patch.object(
        product_codes,
        "_catalog_title",
        new=AsyncMock(return_value="Super Mario Sunshine"),
    )
    rom = Rom(fs_name="阳光马里奥 英文版.gcm", title_id="474D5345")
    rom.platform = Platform(slug=UPS.NGC, fs_slug="ngc", name="GameCube")

    assert (
        await product_code_search_term(rom, "阳光马里奥 英文版")
        == "Super Mario Sunshine"
    )
    translate.assert_not_awaited()


async def test_a_chinese_filename_without_a_known_code_is_translated(mocker):
    mocker.patch.object(
        product_codes,
        "translate_search_term",
        new=AsyncMock(return_value="Sunny Mario"),
    )
    rom = Rom(fs_name="阳光马里奥.iso")

    assert await product_code_search_term(rom, "阳光马里奥") == "Sunny Mario"


async def test_an_english_filename_keeps_its_search_term(mocker):
    lookup = mocker.patch.object(product_codes, "product_code_title", new=AsyncMock())
    rom = Rom(fs_name="Super Mario Sunshine.iso", title_id="474D5345")

    assert await product_code_search_term(rom, "Super Mario Sunshine") == (
        "Super Mario Sunshine"
    )
    lookup.assert_not_awaited()
