"""English titles for Chinese-named ROMs, looked up by the product code in their headers."""

from __future__ import annotations

import asyncio
import io
import string
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Final

from defusedxml import ElementTree as ET

from handler.redis_handler import async_cache
from logger.logger import log
from utils.context import ctx_httpx_client
from utils.platform_slugs import UniversalPlatformSlug as UPS
from utils.translator import HAN_CHARACTER_PATTERN, translate_search_term

if TYPE_CHECKING:
    from models.rom import Rom

# GameTDB asks for permission before its files are used on a website, so the
# databases are fetched at runtime into the instance's own cache, never shipped.
GAMETDB_URLS: Final = {
    UPS.NGC: "https://www.gametdb.com/wiitdb.zip",
    UPS.N3DS: "https://www.gametdb.com/3dstdb.zip",
}
GAMETDB_TITLES_KEY: Final = "romm-cn:gametdb:{platform}"
GAMETDB_FRESH_KEY: Final = "romm-cn:gametdb:{platform}:fresh"
GAMETDB_RETRY_KEY: Final = "romm-cn:gametdb:{platform}:retry"
GAMETDB_REFRESH_SECONDS: Final = 7 * 24 * 3600
GAMETDB_RETRY_SECONDS: Final = 3600
# Entries of these types are hacks and homebrew that reuse a retail product code.
GAMETDB_SKIPPED_TYPES: Final = frozenset({"CUSTOM", "Homebrew"})
_gametdb_locks: dict[str, asyncio.Lock] = {}

N3DS_EXTENSIONS: Final = frozenset({"3ds", "cci"})
N64_EXTENSIONS: Final = frozenset({"z64", "n64", "v64"})
N64_BIG_ENDIAN_MAGIC: Final = bytes.fromhex("80371240")
N64_LITTLE_ENDIAN_MAGIC: Final = bytes.fromhex("40123780")
N64_BYTE_SWAPPED_MAGIC: Final = bytes.fromhex("37804012")
N64_PRINTABLE: Final = frozenset(string.ascii_letters + string.digits + " '&!.-:")

# iQue Player releases of N64 games, whose headers carry a Chinese name. A product
# code ending in "C" marks the iQue region.
IQUE_TITLES: Final = {
    "BALC": "Super Smash Bros.",
    "BCXC": "Custom Robo",
    "BFXC": "Star Fox 64",
    "BFZC": "F-Zero X",
    "BGUC": "Sin and Punishment",
    "BMQC": "Paper Mario",
    "BMXC": "Excitebike 64",
    "BN6C": "Dr. Mario 64",
    "BSMC": "Super Mario 64",
    "BWRC": "Wave Race 64",
    "NZLC": "The Legend of Zelda: Ocarina of Time",
}


async def product_code_search_term(rom: Rom, search_term: str) -> str:
    """A Chinese filename's search term: the product code's English title, else a translation."""
    if not HAN_CHARACTER_PATTERN.search(search_term):
        return search_term
    try:
        title = await product_code_title(rom)
    except (OSError, ValueError) as exc:
        log.debug(f"Could not read the product code of {rom.fs_name}: {exc}")
        title = None
    return title or await translate_search_term(search_term)


async def product_code_title(rom: Rom) -> str | None:
    """The English title the ROM's product code stands for, if one is known."""
    platform = rom.platform.slug if rom.platform else None
    if platform == UPS.NGC:
        code = gamecube_product_code(rom.title_id)
        return await gametdb_title(UPS.NGC, code) if code else None
    if platform == UPS.N3DS and (rom.fs_extension or "").lower() in N3DS_EXTENSIONS:
        path = _rom_file_path(rom)
        code = await asyncio.to_thread(n3ds_product_code, path) if path else None
        return await gametdb_title(UPS.N3DS, code) if code else None
    if platform == UPS.N64 and (rom.fs_extension or "").lower() in N64_EXTENSIONS:
        path = _rom_file_path(rom)
        return await asyncio.to_thread(n64_header_title, path) if path else None
    return None


def gamecube_product_code(title_id: str | None) -> str | None:
    """The four-letter product code a GameCube title id (its hex form) spells."""
    try:
        code = bytes.fromhex(title_id or "").decode("ascii")
    except (ValueError, UnicodeDecodeError):
        return None
    return code if len(code) == 4 and code.isalnum() else None


def n3ds_product_code(path: Path) -> str | None:
    """The four-letter product code ("CTR-P-ABCE") in a 3DS cartridge image."""
    with path.open("rb") as rom_file:
        ncsd = rom_file.read(0x200)
        if ncsd[0x100:0x104] != b"NCSD":
            return None
        # The first partition holds the game; its offset is in 0x200-byte media units.
        rom_file.seek(int.from_bytes(ncsd[0x120:0x124], "little") * 0x200)
        ncch = rom_file.read(0x200)
    if ncch[0x100:0x104] != b"NCCH":
        return None
    product = ncch[0x150:0x160].split(b"\0")[0].decode("ascii", "replace")
    code = product.rsplit("-", 1)[-1]
    return code if product.startswith("CTR-") and len(code) == 4 else None


def n64_header_title(path: Path) -> str | None:
    """An N64 ROM's title: from the iQue table, else its plain-ASCII header name."""
    with path.open("rb") as rom_file:
        header = rom_file.read(0x40)
    magic = header[:4]
    if magic == N64_LITTLE_ENDIAN_MAGIC:
        header = b"".join(header[i : i + 4][::-1] for i in range(0, 0x40, 4))
    elif magic == N64_BYTE_SWAPPED_MAGIC:
        header = b"".join(header[i : i + 2][::-1] for i in range(0, 0x40, 2))
    elif magic != N64_BIG_ENDIAN_MAGIC:
        return None

    code = header[0x3B:0x3F].decode("ascii", "replace")
    if code.endswith("C"):
        return IQUE_TITLES.get(code)
    name = header[0x20:0x34].decode("ascii", "replace").strip(" \0")
    return name if len(name) >= 3 and set(name) <= N64_PRINTABLE else None


async def gametdb_title(platform: str, code: str) -> str | None:
    """The English GameTDB title for a product code, refreshing the cached database weekly."""
    lock = _gametdb_locks.setdefault(platform, asyncio.Lock())
    async with lock:
        if not await async_cache.exists(
            GAMETDB_FRESH_KEY.format(platform=platform),
            GAMETDB_RETRY_KEY.format(platform=platform),
        ):
            await _refresh_gametdb(platform)
    title = await async_cache.hget(GAMETDB_TITLES_KEY.format(platform=platform), code)
    return title or None


async def _refresh_gametdb(platform: str) -> None:
    url = GAMETDB_URLS[platform]
    try:
        response = await ctx_httpx_client.get().get(url, timeout=120)
        response.raise_for_status()
        titles = parse_gametdb(response.content, platform)
    except Exception as exc:
        log.warning(f"GameTDB download failed for {platform}: {exc}")
        await async_cache.set(
            GAMETDB_RETRY_KEY.format(platform=platform), "1", ex=GAMETDB_RETRY_SECONDS
        )
        return

    key = GAMETDB_TITLES_KEY.format(platform=platform)
    async with async_cache.pipeline() as pipe:
        await pipe.delete(key)
        await pipe.hset(key, mapping=titles)
        await pipe.set(
            GAMETDB_FRESH_KEY.format(platform=platform), "1", ex=GAMETDB_REFRESH_SECONDS
        )
        await pipe.execute()
    log.info(f"Loaded {len(titles)} GameTDB titles for {platform}")


def parse_gametdb(archive: bytes, platform: str) -> dict[str, str]:
    """Product code to English title for one platform, from a GameTDB zip."""
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        xml = zipped.read(zipped.namelist()[0])

    titles: dict[str, str] = {}
    for _, game in ET.iterparse(io.BytesIO(xml)):
        if game.tag != "game":
            continue
        game_type = game.findtext("type") or ""
        game_id = game.findtext("id") or ""
        title = next(
            (
                locale.findtext("title")
                for locale in game.findall("locale")
                if locale.get("lang") == "EN"
            ),
            None,
        )
        game.clear()
        if not title or game_type in GAMETDB_SKIPPED_TYPES:
            continue
        # A GameCube id adds a two-character maker code to the product code.
        if platform == UPS.NGC:
            if game_type != "GameCube":
                continue
            game_id = game_id[:4]
        titles.setdefault(game_id, title.strip())
    return titles


def _rom_file_path(rom: Rom) -> Path | None:
    from handler.filesystem import fs_rom_handler

    path = fs_rom_handler.validate_path(rom.full_path)
    return path if path.is_file() else None
