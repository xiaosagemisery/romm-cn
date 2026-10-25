from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from utils.translator import _TRANSLATION_CACHE, translate_game_metadata, translate_text


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
async def test_translate_game_metadata():
    with patch("utils.translator.translate_text") as mock_translate_text:
        mock_translate_text.side_effect = lambda t, **kwargs: (f"ZH_{t}" if t else t)

        name, summary = await translate_game_metadata("Pokemon", "A great game.")
        assert name == "ZH_Pokemon"
        assert summary == "ZH_A great game."

        none_name, none_summary = await translate_game_metadata(None, None)
        assert none_name is None
        assert none_summary is None
