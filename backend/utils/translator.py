from __future__ import annotations

import asyncio
import json
import re
import unicodedata
from collections.abc import Sequence
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any

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
# The Traditional, Taiwan and Hong Kong labels are left out: their titles can
# differ from the mainland ones. The generic "zh" label may be in either script.
WIKIDATA_ZH_LANGS = (*WIKIDATA_SIMPLIFIED_LANGS, "zh")
# The query service answers in up to ~10 s while a scan runs several workers.
WIKIDATA_TIMEOUT = 30.0
WIKIDATA_ATTEMPTS = 2
BANGUMI_SEARCH_URL = "https://api.bgm.tv/v0/search/subjects"
BANGUMI_GAME_TYPE = 4
# Bangumi is searched by at most this many of a game's names per lookup.
BANGUMI_MAX_KEYWORDS = 3
IGDB_SLUG_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]*")
# Wikidata disambiguation suffix, e.g. "斑鳩 (電視遊戲)".
LABEL_QUALIFIER_PATTERN = re.compile(r"\s*[（(][^()（）]*[)）]\s*$")
_WIKIDATA_CACHE: dict[str, dict[str, str]] = {}
_BANGUMI_CACHE: dict[str, list[dict[str, Any]]] = {}
# Latin-only token that machine translation leaves alone, standing in for the
# game title while the summary is translated.
TITLE_PLACEHOLDER = "ZQX0ZQX"
HAN_CHARACTER_PATTERN = re.compile(r"[\u4e00-\u9fff]")
KANA_PATTERN = re.compile(r"[\u3040-\u30ff]")
# Release labels in Chinese filenames, which only add noise to a title search.
CHINESE_RELEASE_LABEL_PATTERN = re.compile(
    r"(简体中文版|繁体中文版|中文版|汉化版|英文版|日文版|美版|日版|欧版)"
)
# Disc markers ("DiscA", "Disc 2"); a multi-disc game is catalogued as one title.
DISC_MARKER_PATTERN = re.compile(r"\bdisc\s*[a-z0-9]\b", re.IGNORECASE)
# A trailing "1" numbers the first entry of a series, which catalogs list without it.
FIRST_ENTRY_NUMBER_PATTERN = re.compile(r"(?<![\d.])\s*1$")


def normalize_title(title: str) -> str:
    """Casefold a title and drop accents, spaces and punctuation for lookups."""
    decomposed = unicodedata.normalize("NFKD", title).casefold()
    return "".join(char for char in decomposed if char.isalnum())


def exact_title_key(title: str) -> str:
    """Fold width and case and drop spaces and punctuation, keeping a "+" edition mark."""
    folded = unicodedata.normalize("NFKC", title).casefold()
    return "".join(char for char in folded if char.isalnum() or char == "+")


@lru_cache(maxsize=1)
def _t2s() -> OpenCC:
    return OpenCC("t2s")


def to_simplified(text: str) -> str:
    """Convert Traditional Chinese characters to Simplified, leaving Japanese as is."""
    if KANA_PATTERN.search(text):
        return text
    return _t2s().convert(text)


def is_simplified_chinese(text: str) -> bool:
    return bool(HAN_CHARACTER_PATTERN.search(text)) and to_simplified(text) == text


def _clean_chinese_title(title: str) -> str:
    """Drop release labels, disc markers and a first-entry "1" from a Chinese title."""
    title = CHINESE_RELEASE_LABEL_PATTERN.sub(" ", title)
    title = " ".join(DISC_MARKER_PATTERN.sub(" ", title).split())
    return FIRST_ENTRY_NUMBER_PATTERN.sub("", title)


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


async def wikidata_zh_labels(igdb_slug: str | None) -> dict[str, str]:
    """Look up a game's Chinese labels on Wikidata by its IGDB slug, keyed by language.

    Returns an empty dict when Wikidata has no usable label or cannot be reached.
    """
    if not igdb_slug or not IGDB_SLUG_PATTERN.fullmatch(igdb_slug):
        return {}
    if igdb_slug in _WIKIDATA_CACHE:
        return _WIKIDATA_CACHE[igdb_slug]

    langs = ", ".join(f'"{lang}"' for lang in WIKIDATA_ZH_LANGS)
    query = (
        "SELECT ?lang ?label WHERE { "
        f'?item wdt:P5794 "{igdb_slug}" . ?item rdfs:label ?label . '
        f"BIND(LANG(?label) AS ?lang) FILTER(?lang IN ({langs})) }}"
    )
    for attempt in range(1, WIKIDATA_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(timeout=WIKIDATA_TIMEOUT) as client:
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
            break
        except Exception as exc:
            if attempt == WIKIDATA_ATTEMPTS:
                log.warning(f"Wikidata lookup failed for {igdb_slug!r}: {exc!r}")
                return {}
            await asyncio.sleep(attempt)

    labels: dict[str, str] = {}
    for row in bindings:
        label = LABEL_QUALIFIER_PATTERN.sub("", row["label"]["value"]).strip()
        if label:
            labels[row["lang"]["value"]] = label
    _WIKIDATA_CACHE[igdb_slug] = labels
    return labels


async def _bangumi_search(keyword: str) -> list[dict[str, Any]]:
    if keyword in _BANGUMI_CACHE:
        return _BANGUMI_CACHE[keyword]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                BANGUMI_SEARCH_URL,
                params={"limit": 10},
                json={"keyword": keyword, "filter": {"type": [BANGUMI_GAME_TYPE]}},
                headers={"User-Agent": WIKIDATA_USER_AGENT},
            )
            response.raise_for_status()
            subjects = response.json().get("data") or []
    except Exception as exc:
        log.warning(f"Bangumi lookup failed for {keyword!r}: {exc}")
        return []

    _BANGUMI_CACHE[keyword] = subjects
    return subjects


async def bangumi_zh_title(
    names: Sequence[str], file_title: str | None = None
) -> str | None:
    """Find a game's Chinese title on Bangumi.

    Only a subject whose original title equals one of `names` (ignoring case,
    width, spaces and punctuation) and whose Chinese title has Han characters
    counts. Japanese names are searched first,
    since Bangumi lists Japanese games under their Japanese title. Provider
    names can include a sibling game's title, so when several subjects match,
    the one closest to the Chinese `file_title` wins.
    """
    keys = {key for name in names if name and (key := exact_title_key(name))}
    if not keys:
        return None

    keywords = sorted(
        dict.fromkeys(name.strip() for name in names if name and name.strip()),
        key=lambda name: not KANA_PATTERN.search(name),
    )
    file_zh_title = filename_zh_title(file_title)
    matches: list[str] = []
    for keyword in keywords[:BANGUMI_MAX_KEYWORDS]:
        for subject in await _bangumi_search(keyword):
            name_cn = (subject.get("name_cn") or "").strip()
            if not HAN_CHARACTER_PATTERN.search(name_cn):
                continue
            if exact_title_key(subject.get("name") or "") in keys:
                matches.append(to_simplified(name_cn))
        if matches and not file_zh_title:
            break

    if not matches or not file_zh_title:
        return matches[0] if matches else None
    return max(
        matches,
        key=lambda title: SequenceMatcher(None, title, file_zh_title).ratio(),
    )


def filename_zh_title(file_title: str | None) -> str | None:
    """The Simplified Chinese title a filename spells out, if it has one."""
    if not file_title or KANA_PATTERN.search(file_title):
        return None
    title = _clean_chinese_title(file_title)
    if not HAN_CHARACTER_PATTERN.search(title):
        return None
    return to_simplified(title)


async def resolve_zh_title(
    name: str,
    igdb_slug: str | None = None,
    alternative_names: Sequence[str] = (),
    file_title: str | None = None,
) -> str:
    """Pick a game's Simplified Chinese title without machine translation.

    In order: the listed official title, the Bangumi title, a Simplified
    Wikidata label, a Traditional Wikidata label or Chinese provider name
    converted to Simplified, then the Chinese filename. Falls back to `name`.
    Bangumi comes before Wikidata because it names more games.
    """
    if official := official_name(name):
        return official
    if bangumi := await bangumi_zh_title([name, *alternative_names], file_title):
        return bangumi

    labels = await wikidata_zh_labels(igdb_slug)
    generic = labels.get("zh")
    simplified = next(
        (labels[lang] for lang in WIKIDATA_SIMPLIFIED_LANGS if lang in labels),
        generic if generic and is_simplified_chinese(generic) else None,
    )
    if simplified:
        return simplified
    if generic:
        return to_simplified(generic)
    if HAN_CHARACTER_PATTERN.search(name) and not KANA_PATTERN.search(name):
        return to_simplified(name)
    return filename_zh_title(file_title) or name


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
    alternative_names: Sequence[str] = (),
    file_title: str | None = None,
) -> tuple[str | None, str | None]:
    """Resolve a game's title with `resolve_zh_title` and translate its summary.

    The title is never machine translated.
    """
    if not name and not summary:
        return name, summary

    title = name
    if name and target_lang.lower().startswith("zh"):
        title = await resolve_zh_title(name, igdb_slug, alternative_names, file_title)
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

    title = _clean_chinese_title(search_term)
    if known := _search_titles().get(normalize_title(title)):
        return known

    translated = await translate_text(title, target_lang="en", source_lang="zh-CN")
    return translated or title
