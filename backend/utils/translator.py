from __future__ import annotations

import re

import httpx

from logger.logger import log

_TRANSLATION_CACHE: dict[tuple[str, str], str] = {}
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
HAN_CHARACTER_PATTERN = re.compile(r"[\u4e00-\u9fff]")
# Release labels in Chinese filenames, which only add noise to a title search.
CHINESE_RELEASE_LABEL_PATTERN = re.compile(
    r"(简体中文版|繁体中文版|中文版|汉化版|英文版|日文版|美版|日版|欧版)"
)


async def translate_text(
    text: str | None,
    target_lang: str = "zh-CN",
    source_lang: str = "auto",
    timeout: float = 10.0,
) -> str | None:
    """Translate text to target language using public Google Translate API with fallback."""
    if not text or not text.strip():
        return text

    cache_key = (text.strip(), target_lang)
    if cache_key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[cache_key]

    params = {
        "client": "dict-chrome-ex",
        "sl": source_lang,
        "tl": target_lang,
        "dt": "t",
        "q": text,
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                GOOGLE_TRANSLATE_URL, params=params, headers=headers
            )
            response.raise_for_status()
            data = response.json()
            if (
                data
                and isinstance(data, list)
                and len(data) > 0
                and isinstance(data[0], list)
            ):
                translated_segments = [
                    seg[0]
                    for seg in data[0]
                    if isinstance(seg, list) and len(seg) > 0 and seg[0]
                ]
                translated = "".join(translated_segments)
                if translated:
                    _TRANSLATION_CACHE[cache_key] = translated
                    return translated
    except Exception as exc:
        log.warning(f"Translation failed for {text[:30]!r}: {exc}")

    return text


async def translate_game_metadata(
    name: str | None,
    summary: str | None,
    target_lang: str = "zh-CN",
) -> tuple[str | None, str | None]:
    """Translate both game name and summary into target language."""
    if not name and not summary:
        return name, summary

    translated_name = name
    translated_summary = summary

    if name:
        translated_name = await translate_text(name, target_lang=target_lang)
    if summary:
        translated_summary = await translate_text(summary, target_lang=target_lang)

    return translated_name, translated_summary


async def translate_search_term(search_term: str) -> str:
    """Translate a filename-derived search term with Chinese characters to English."""
    if not HAN_CHARACTER_PATTERN.search(search_term):
        return search_term

    title = " ".join(CHINESE_RELEASE_LABEL_PATTERN.sub(" ", search_term).split())
    translated = await translate_text(title, target_lang="en", source_lang="zh-CN")
    return translated or title
