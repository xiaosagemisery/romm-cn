from config import FRONTEND_RESOURCES_PATH
from models.rom import Rom


def continue_playing_screenshot(rom: Rom) -> str | None:
    """The "where you left off" image for a rom, in priority order: the title
    screen, then the first gameplay screenshot. None lets the frontend fall back
    to cover art. Shared by the continue-playing rail and the live-activity
    board."""
    title_screen = (rom.ss_metadata or {}).get("title_screen_path") or (
        rom.gamelist_metadata or {}
    ).get("title_screen_path")
    if title_screen:
        return f"{FRONTEND_RESOURCES_PATH}/{title_screen}"

    if rom.merged_screenshots:
        return rom.merged_screenshots[0]

    return None
