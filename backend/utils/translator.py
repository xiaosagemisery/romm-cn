from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import httpx
from opencc import OpenCC

from logger.logger import log

_TRANSLATION_CACHE: dict[tuple[str, str], str] = {}
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
OFFICIAL_NAMES_PATH = Path(__file__).with_name("official_names_zh.json")
SEARCH_TITLES_PATH = Path(__file__).with_name("search_titles_en.json")
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
WIKIDATA_USER_AGENT = "romm-cn/0.1 (https://github.com/xiaosagemisery/romm-cn)"
WIKIDATA_SIMPLIFIED_LANGS = ("zh-cn", "zh-hans", "zh-sg", "zh-my")
# Wikidata label languages, Simplified Chinese first; the rest get converted.
WIKIDATA_ZH_LANGS = (
    *WIKIDATA_SIMPLIFIED_LANGS,
    "zh",
    "zh-hant",
    "zh-tw",
    "zh-hk",
    "zh-mo",
)
IGDB_SLUG_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]*")
# Wikidata disambiguation suffix, e.g. "斑鳩 (電視遊戲)".
LABEL_QUALIFIER_PATTERN = re.compile(r"\s*[（(][^()（）]*[)）]\s*$")
_WIKIDATA_CACHE: dict[str, str | None] = {}
# Latin-only token that machine translation leaves alone, standing in for the
# game title while the summary is translated.
TITLE_PLACEHOLDER = "ZQX0ZQX"
HAN_CHARACTER_PATTERN = re.compile(r"[\u4e00-\u9fff]")
# Release labels in Chinese filenames, which only add noise to a title search.
CHINESE_RELEASE_LABEL_PATTERN = re.compile(
    r"(简体中文版|繁体中文版|中文版|汉化版|英文版|日文版|美版|日版|欧版)"
)


def normalize_title(title: str) -> str:
    """Casefold a title and drop accents, spaces and punctuation for lookups."""
    decomposed = unicodedata.normalize("NFKD", title).casefold()
    return "".join(char for char in decomposed if char.isalnum())


def _load_title_map(path: Path) -> dict[str, str]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.warning(f"Could not load {path.name}: {exc}")
        return {}
    return {normalize_title(title): value for title, value in raw.items() if value}


@lru_cache(maxsize=1)
def _official_names() -> dict[str, str]:
    return _load_title_map(OFFICIAL_NAMES_PATH)


@lru_cache(maxsize=1)
def _traditional_to_simplified() -> OpenCC:
    return OpenCC("t2s")


@lru_cache(maxsize=1)
def _search_titles() -> dict[str, str]:
    return _load_title_map(SEARCH_TITLES_PATH)


def official_name(name: str, target_lang: str = "zh-CN") -> str | None:
    """Return the verified official Chinese title for a game name, if known."""
    if not target_lang.lower().startswith("zh"):
        return None
    return _official_names().get(normalize_title(name))


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


async def wikidata_zh_title(igdb_slug: str | None) -> str | None:
    """Look up a game's Chinese title on Wikidata by its IGDB slug.

    Returns None when Wikidata has no Chinese label or cannot be reached.
    """
    if not igdb_slug or not IGDB_SLUG_PATTERN.fullmatch(igdb_slug):
        return None
    if igdb_slug in _WIKIDATA_CACHE:
        return _WIKIDATA_CACHE[igdb_slug]

    langs = ", ".join(f'"{lang}"' for lang in WIKIDATA_ZH_LANGS)
    query = (
        "SELECT ?lang ?label WHERE { "
        f'?item wdt:P5794 "{igdb_slug}" . ?item rdfs:label ?label . '
        f"BIND(LANG(?label) AS ?lang) FILTER(?lang IN ({langs})) }}"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                WIKIDATA_SPARQL_URL,
                params={"query": query},
                headers={
                    "Accept": "application/sparql-results+json",
                    "User-Agent": WIKIDATA_USER_AGENT,
                },
            )
            response.raise_for_status()
            bindings = response.json()["results"]["bindings"]
    except Exception as exc:
        log.warning(f"Wikidata lookup failed for {igdb_slug!r}: {exc}")
        return None

    labels = {row["lang"]["value"]: row["label"]["value"] for row in bindings}
    lang = next((lang for lang in WIKIDATA_ZH_LANGS if lang in labels), None)
    title = None
    if lang:
        title = LABEL_QUALIFIER_PATTERN.sub("", labels[lang]).strip()
        if lang not in WIKIDATA_SIMPLIFIED_LANGS:
            title = _traditional_to_simplified().convert(title)
    _WIKIDATA_CACHE[igdb_slug] = title or None
    return title or None


async def _translate_summary(
    summary: str, name: str | None, title: str | None, target_lang: str
) -> str:
    """Translate a summary, keeping the game's title as `title`.

    Machine translation renders a title differently from the title shown in the
    UI, so the name is swapped for a placeholder first and the final title put
    back afterwards.
    """
    if name and title and name in summary:
        translated = await translate_text(
            summary.replace(name, TITLE_PLACEHOLDER), target_lang=target_lang
        )
        if translated and TITLE_PLACEHOLDER in translated:
            return translated.replace(TITLE_PLACEHOLDER, title)

    return await translate_text(summary, target_lang=target_lang) or summary


async def translate_game_metadata(
    name: str | None,
    summary: str | None,
    target_lang: str = "zh-CN",
    igdb_slug: str | None = None,
) -> tuple[str | None, str | None]:
    """Resolve a game's title and translate its summary.

    The title is never machine translated: it becomes the listed official
    title, else the game's Chinese title on Wikidata (found by `igdb_slug`),
    and stays as given when neither exists.
    """
    if not name and not summary:
        return name, summary

    title = name
    if name and target_lang.lower().startswith("zh"):
        title = (
            official_name(name, target_lang)
            or await wikidata_zh_title(igdb_slug)
            or name
        )
    translated_summary = summary
    if summary:
        translated_summary = await _translate_summary(summary, name, title, target_lang)

    return title, translated_summary


async def translate_search_term(search_term: str) -> str:
    """Turn a filename-derived search term with Chinese characters into English.

    A title listed in `search_titles_en.json` maps to its known English title;
    any other is machine translated.
    """
    if not HAN_CHARACTER_PATTERN.search(search_term):
        return search_term

    title = " ".join(CHINESE_RELEASE_LABEL_PATTERN.sub(" ", search_term).split())
    if known := _search_titles().get(normalize_title(title)):
        return known

    translated = await translate_text(title, target_lang="en", source_lang="zh-CN")
    return translated or title
