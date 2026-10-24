from datetime import datetime
from typing import Any

from handler.auth.base_handler import auth_handler
from handler.database import (
    db_client_token_handler,
    db_platform_handler,
    db_rom_handler,
)
from models.client_token import ClientToken
from models.platform import Platform
from models.rom import Rom
from models.user import User


def make_platform(slug: str, /, **overrides: Any) -> Platform:
    """Persist a platform whose folder and display name derive from `slug`."""
    fields: dict[str, Any] = {
        "slug": slug,
        "fs_slug": slug,
        "name": slug.replace("-", " ").title(),
    }
    return db_platform_handler.add_platform(Platform(**(fields | overrides)))


def make_rom(
    platform: Platform,
    name: str,
    /,
    *,
    fs_stem: str | None = None,
    fs_extension: str = "zip",
    **overrides: Any,
) -> Rom:
    """Persist a ROM whose slug and filename fields derive from `name`.

    Args:
        fs_stem: The filename without its extension, defaulting to `name`.
        fs_extension: The file extension, or empty for a folder ROM.
    """
    stem = name if fs_stem is None else fs_stem
    fields: dict[str, Any] = {
        "platform_id": platform.id,
        "name": name,
        "slug": name.lower().replace(" ", "-"),
        "fs_name": f"{stem}.{fs_extension}" if fs_extension else stem,
        "fs_name_no_tags": stem,
        "fs_name_no_ext": stem,
        "fs_extension": fs_extension,
        "fs_path": f"{platform.slug}/roms",
    }
    return db_rom_handler.add_rom(Rom(**(fields | overrides)))


def make_esrb_rated_rom(platform: Platform, name: str, esrb: str, /) -> Rom:
    """Persist a ROM whose only age rating is IGDB's ESRB `esrb`."""
    return make_rom(
        platform,
        name,
        igdb_metadata={
            "age_ratings": [
                {"category": "ESRB", "rating": esrb, "rating_cover_url": ""}
            ]
        },
    )


def make_device_token(
    user: User,
    device_id: str | None,
    /,
    *,
    scopes: str = "devices.read devices.write roms.read",
    expires_at: datetime | None = None,
    **overrides: Any,
) -> tuple[ClientToken, str]:
    """Persist a client token bound to `device_id`, or unbound when it is None.

    Returns:
        The stored token and the raw `rmm_` credential a client sends.
    """
    raw_token = auth_handler.generate_client_token()
    fields: dict[str, Any] = {
        "user_id": user.id,
        "name": "Handheld",
        "hashed_token": auth_handler.hash_client_token(raw_token),
        "scopes": scopes,
        "expires_at": expires_at,
        "device_id": device_id,
    }
    token = db_client_token_handler.add_token(ClientToken(**(fields | overrides)))
    return token, raw_token
