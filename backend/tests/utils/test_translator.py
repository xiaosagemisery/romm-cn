from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from utils.translator import (
    _TRANSLATION_CACHE,
    TITLE_PLACEHOLDER,
    normalize_title,
    official_name,
    translate_game_metadata,
    translate_search_term,
    translate_text,
)


@pytest.fixture(autouse=True)
def clear_cache():
    _TRANSLATION_CACHE.clear()
    yield
    _TRANSLATION_CACHE.clear()


@pytest.mark.asyncio
async def test_translate_text_empty_or_none():
    assert await translate_text(None) is None
    assert await translate_text("") == ""
    assert await translate_text("   ") == "   "


@pytest.mark.asyncio
async def test_translate_text_success():
    fake_response_data = [
        [["塞尔达传说：时之笛", "The Legend of Zelda: Ocarina of Time", None, None]],
        None,
        "en",
    ]

    mock_resp = MagicMock()
    mock_resp.json = lambda: fake_response_data

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        result = await translate_text("The Legend of Zelda: Ocarina of Time")
        assert result == "塞尔达传说：时之笛"

    # Test cache hit (httpx should not be called again)
    with patch("httpx.AsyncClient") as mock_client_cls2:
        cached_result = await translate_text("The Legend of Zelda: Ocarina of Time")
        assert cached_result == "塞尔达传说：时之笛"
        mock_client_cls2.assert_not_called()


@pytest.mark.asyncio
async def test_translate_text_fallback_on_error():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection timed out")
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await translate_text("Super Mario World")
        assert result == "Super Mario World"


@pytest.mark.asyncio
async def test_translate_game_metadata_keeps_the_title_and_translates_the_summary():
    with patch("utils.translator.translate_text") as mock_translate_text:
        mock_translate_text.side_effect = lambda t, **kwargs: (f"ZH_{t}" if t else t)

        name, summary = await translate_game_metadata("Pokemon", "A great game.")
        assert name == "Pokemon"
        assert summary == "ZH_A great game."

        none_name, none_summary = await translate_game_metadata(None, None)
        assert none_name is None
        assert none_summary is None


@pytest.mark.asyncio
async def test_translate_game_metadata_uses_the_official_name_in_the_summary():
    seen: list[str] = []

    async def fake_translate(text: str | None, **_kwargs):
        seen.append(text or "")
        return f"《{TITLE_PLACEHOLDER}》是一款格斗游戏。"

    with patch("utils.translator.translate_text", fake_translate):
        name, summary = await translate_game_metadata(
            "Super Smash Bros.", "Super Smash Bros. is a fighting game."
        )

    assert name == "任天堂明星大乱斗"
    assert summary == "《任天堂明星大乱斗》是一款格斗游戏。"
    assert seen == [f"{TITLE_PLACEHOLDER} is a fighting game."]


@pytest.mark.asyncio
async def test_translate_game_metadata_falls_back_when_the_placeholder_is_lost():
    async def fake_translate(text: str | None, **_kwargs):
        return "一款游戏。"

    with patch("utils.translator.translate_text", fake_translate):
        name, summary = await translate_game_metadata(
            "Shining Soul", "Shining Soul is an action RPG."
        )

    assert name == "Shining Soul"
    assert summary == "一款游戏。"


@pytest.mark.asyncio
async def test_translate_game_metadata_summary_only_is_plain_translation():
    with patch("utils.translator.translate_text") as mock_translate_text:
        mock_translate_text.side_effect = lambda t, **kwargs: f"ZH_{t}"

        name, summary = await translate_game_metadata(None, "A great game.")

    assert name is None
    assert summary == "ZH_A great game."


def test_official_name_matches_ignoring_case_accents_and_punctuation():
    assert normalize_title("Pokémon: Emerald!") == "pokemonemerald"
    assert official_name("SUPER SMASH BROS") == "任天堂明星大乱斗"
    assert official_name("Super Smash Bros.") == "任天堂明星大乱斗"
    assert official_name("Unknown Game") is None


def test_official_name_applies_to_chinese_targets_only():
    assert official_name("Super Smash Bros.", target_lang="zh-TW") is not None
    assert official_name("Super Smash Bros.", target_lang="ja") is None


@pytest.mark.asyncio
async def test_translate_search_term_leaves_non_chinese_terms_alone():
    with patch("utils.translator.translate_text", new=AsyncMock()) as translate:
        assert await translate_search_term("Super Mario 64") == "Super Mario 64"
        assert await translate_search_term("ドラゴンクエスト") == "ドラゴンクエスト"

    translate.assert_not_awaited()


@pytest.mark.asyncio
async def test_translate_search_term_drops_release_labels_before_translating():
    with patch(
        "utils.translator.translate_text", new=AsyncMock(return_value="Wario World")
    ) as translate:
        assert await translate_search_term("瓦力欧世界 英文版") == "Wario World"

    translate.assert_awaited_once_with(
        "瓦力欧世界", target_lang="en", source_lang="zh-CN"
    )


@pytest.mark.asyncio
async def test_translate_search_term_keeps_the_title_when_translation_fails():
    with patch(
        "utils.translator.translate_text",
        new=AsyncMock(side_effect=lambda text, **_: text),
    ):
        assert await translate_search_term("斑鸠 汉化版") == "斑鸠"
