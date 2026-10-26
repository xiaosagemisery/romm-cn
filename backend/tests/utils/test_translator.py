from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from utils.translator import (
    _BANGUMI_CACHE,
    _TRANSLATION_CACHE,
    _WIKIDATA_CACHE,
    TITLE_PLACEHOLDER,
    bangumi_zh_title,
    exact_title_key,
    filename_zh_title,
    normalize_title,
    official_name,
    resolve_zh_title,
    to_simplified,
    translate_game_metadata,
    translate_search_term,
    translate_text,
    wikidata_zh_labels,
)


@pytest.fixture(autouse=True)
def clear_cache():
    _TRANSLATION_CACHE.clear()
    _WIKIDATA_CACHE.clear()
    _BANGUMI_CACHE.clear()
    yield
    _TRANSLATION_CACHE.clear()
    _WIKIDATA_CACHE.clear()
    _BANGUMI_CACHE.clear()


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
            "Obscure Quest", "Obscure Quest is an action RPG."
        )

    assert name == "Obscure Quest"
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


@pytest.mark.parametrize(
    ("search_term", "title"),
    [
        ("生化危机4 英文版 DiscA", "生化危机4"),
        ("生化危机 代号维罗妮卡 汉化版 Disc B", "生化危机 代号维罗妮卡"),
        ("生化危机1 汉化版 DiscA", "生化危机"),
        ("银河战士 Prime 1 汉化版", "银河战士 Prime"),
        ("路易吉鬼屋1", "路易吉鬼屋"),
    ],
)
@pytest.mark.asyncio
async def test_translate_search_term_drops_disc_markers_and_a_first_entry_number(
    search_term: str, title: str
):
    with patch(
        "utils.translator.translate_text",
        new=AsyncMock(side_effect=lambda text, **_: text),
    ) as translate:
        assert await translate_search_term(search_term) == title

    translate.assert_awaited_once_with(title, target_lang="en", source_lang="zh-CN")


@pytest.mark.parametrize(
    "search_term", ["勇者斗恶龙11", "马里奥与路易吉RPG1 DX", "圆形竞技场 1.2.1"]
)
@pytest.mark.asyncio
async def test_translate_search_term_keeps_numbers_that_are_part_of_the_title(
    search_term: str,
):
    with patch(
        "utils.translator.translate_text",
        new=AsyncMock(side_effect=lambda text, **_: text),
    ):
        assert await translate_search_term(search_term) == search_term


@pytest.mark.asyncio
async def test_translate_search_term_keeps_the_title_when_translation_fails():
    with patch(
        "utils.translator.translate_text",
        new=AsyncMock(side_effect=lambda text, **_: text),
    ):
        assert await translate_search_term("忍者龙剑传 汉化版") == "忍者龙剑传"


@pytest.mark.asyncio
async def test_translate_search_term_prefers_a_known_english_title():
    with patch("utils.translator.translate_text", new=AsyncMock()) as translate:
        assert await translate_search_term("斑鸠 汉化版") == "Ikaruga"
        assert await translate_search_term("星之卡比  三重彩") == "Kirby: Triple Deluxe"

    translate.assert_not_awaited()


def _wikidata_response(rows: dict[str, str]) -> MagicMock:
    response = MagicMock()
    response.json = lambda: {
        "results": {
            "bindings": [
                {"lang": {"value": lang}, "label": {"value": label}}
                for lang, label in rows.items()
            ]
        }
    }
    return response


def _patch_wikidata(response: MagicMock | Exception):
    client = AsyncMock()
    if isinstance(response, Exception):
        client.get.side_effect = response
    else:
        client.get.return_value = response
    patcher = patch("httpx.AsyncClient")
    mock_cls = patcher.start()
    mock_cls.return_value.__aenter__.return_value = client
    return patcher, client


@pytest.mark.asyncio
async def test_wikidata_zh_labels_drop_the_qualifier_and_are_cached():
    patcher, client = _patch_wikidata(
        _wikidata_response({"zh": "斑鳩 (電視遊戲)", "zh-cn": "斑鸠 (电子游戏)"})
    )
    try:
        expected = {"zh": "斑鳩", "zh-cn": "斑鸠"}
        assert await wikidata_zh_labels("ikaruga") == expected
        assert await wikidata_zh_labels("ikaruga") == expected
    finally:
        patcher.stop()

    client.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_wikidata_zh_labels_are_empty_without_a_label_and_failures_are_not_cached():
    patcher, _client = _patch_wikidata(_wikidata_response({}))
    try:
        assert await wikidata_zh_labels("obscure-game") == {}
    finally:
        patcher.stop()

    patcher, client = _patch_wikidata(Exception("rate limited"))
    try:
        with patch("utils.translator.asyncio.sleep", new=AsyncMock()):
            assert await wikidata_zh_labels("flaky-game") == {}
    finally:
        patcher.stop()
    assert "flaky-game" not in _WIKIDATA_CACHE
    assert client.get.await_count == 2


@pytest.mark.asyncio
async def test_wikidata_zh_labels_retry_once_after_a_failure():
    patcher, client = _patch_wikidata(_wikidata_response({"zh-cn": "斑鸠"}))
    client.get.side_effect = [Exception("timed out"), client.get.return_value]
    try:
        with patch("utils.translator.asyncio.sleep", new=AsyncMock()) as sleep:
            assert await wikidata_zh_labels("ikaruga") == {"zh-cn": "斑鸠"}
    finally:
        patcher.stop()
    sleep.assert_awaited_once()


@pytest.mark.asyncio
async def test_wikidata_zh_labels_reject_a_slug_that_is_not_an_igdb_slug():
    with patch("httpx.AsyncClient") as mock_cls:
        assert await wikidata_zh_labels(None) == {}
        assert await wikidata_zh_labels('x" . } #') == {}
    mock_cls.assert_not_called()


def test_to_simplified_converts_traditional_and_leaves_japanese_alone():
    assert to_simplified("逆轉裁判5") == "逆转裁判5"
    assert to_simplified("勇者斗恶龙XI") == "勇者斗恶龙XI"
    assert to_simplified("ゼルダの伝説 夢をみる島") == "ゼルダの伝説 夢をみる島"


def test_exact_title_key_keeps_an_edition_plus():
    assert exact_title_key("どうぶつの森＋") == exact_title_key("どうぶつの森 +")
    assert exact_title_key("どうぶつの森+") != exact_title_key("どうぶつの森")
    assert exact_title_key("Cave Story 3D") == exact_title_key("cave story 3d")


@pytest.mark.parametrize(
    ("file_title", "title"),
    [
        ("红侠乔伊2 英文版", "红侠乔伊2"),
        ("大盗伍佑卫门1", "大盗伍佑卫门"),
        ("勇者鬥惡龍7", "勇者斗恶龙7"),
        ("Shining Soul", None),
        ("Wave Race Blue Storm 英文版", None),
        ("シャイニング・ソウル", None),
        (None, None),
    ],
)
def test_filename_zh_title(file_title: str | None, title: str | None):
    assert filename_zh_title(file_title) == title


def _bangumi_subjects(*subjects: tuple[str, str]) -> list[dict[str, str]]:
    return [{"name": name, "name_cn": name_cn} for name, name_cn in subjects]


@pytest.mark.asyncio
async def test_bangumi_zh_title_needs_an_exact_original_title():
    search = AsyncMock(
        return_value=_bangumi_subjects(
            ("どうぶつの森", "动物之森"), ("どうぶつの森+", "动物森友会+")
        )
    )
    with patch("utils.translator._bangumi_search", search):
        assert await bangumi_zh_title(["Animal Crossing", "どうぶつの森＋"]) == (
            "动物森友会+"
        )
        assert await bangumi_zh_title(["Doubutsu no Mori e+"]) is None


@pytest.mark.asyncio
async def test_bangumi_zh_title_skips_a_chinese_title_without_han_characters():
    search = AsyncMock(return_value=_bangumi_subjects(("F-ZERO X", "F-ZERO X")))
    with patch("utils.translator._bangumi_search", search):
        assert await bangumi_zh_title(["F-Zero X"]) is None


@pytest.mark.asyncio
async def test_bangumi_zh_title_searches_japanese_names_first_and_skips_empty_titles():
    search = AsyncMock(
        side_effect=[
            _bangumi_subjects(("ゼルダ無双 ハイラルオールスターズ", "")),
            _bangumi_subjects(("Hyrule Warriors: Legends", "塞尔达无双 海拉尔全明星")),
        ]
    )
    with patch("utils.translator._bangumi_search", search):
        title = await bangumi_zh_title(
            ["Hyrule Warriors: Legends", "ゼルダ無双 ハイラルオールスターズ"]
        )

    assert title == "塞尔达无双 海拉尔全明星"
    assert [call.args[0] for call in search.await_args_list] == [
        "ゼルダ無双 ハイラルオールスターズ",
        "Hyrule Warriors: Legends",
    ]


@pytest.mark.asyncio
async def test_bangumi_zh_title_picks_the_match_closest_to_the_filename():
    search = AsyncMock(
        side_effect=[
            _bangumi_subjects(
                ("逆転裁判456 王泥喜セレクション", "逆转裁判456 王泥喜精选集")
            ),
            _bangumi_subjects(
                ("逆転裁判123 成歩堂セレクション", "逆转裁判123 成步堂精选集")
            ),
            [],
        ]
    )
    names = [
        "Phoenix Wright: Ace Attorney Trilogy",
        "逆転裁判456 王泥喜セレクション",
        "逆転裁判123 成歩堂セレクション",
    ]
    with patch("utils.translator._bangumi_search", search):
        assert await bangumi_zh_title(names, "逆转裁判123 成步堂精选集") == (
            "逆转裁判123 成步堂精选集"
        )

    search.reset_mock(side_effect=True)
    search.side_effect = [
        _bangumi_subjects(
            ("逆転裁判456 王泥喜セレクション", "逆转裁判456 王泥喜精选集")
        )
    ]
    with patch("utils.translator._bangumi_search", search):
        assert await bangumi_zh_title(names) == "逆转裁判456 王泥喜精选集"
    search.assert_awaited_once()


@pytest.mark.asyncio
async def test_bangumi_search_caches_results_but_not_failures():
    response = MagicMock()
    response.json = lambda: {"data": [{"name": "斑鳩", "name_cn": "斑鸠"}]}
    client = AsyncMock()
    client.post.return_value = response
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value = client
        assert await bangumi_zh_title(["斑鳩"]) == "斑鸠"
        assert await bangumi_zh_title(["斑鳩"]) == "斑鸠"
    client.post.assert_awaited_once()

    client.post.side_effect = Exception("rate limited")
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value = client
        assert await bangumi_zh_title(["Ikaruga"]) is None
    assert "Ikaruga" not in _BANGUMI_CACHE


def _patch_sources(
    labels: dict[str, str] | None = None, bangumi: str | None = None
) -> tuple[Any, Any]:
    return (
        patch(
            "utils.translator.wikidata_zh_labels",
            AsyncMock(return_value=labels or {}),
        ),
        patch("utils.translator.bangumi_zh_title", AsyncMock(return_value=bangumi)),
    )


@pytest.mark.parametrize(
    ("labels", "bangumi", "name", "file_title", "title"),
    [
        # Bangumi wins over every Wikidata label.
        ({"zh-hans": "压缩空间"}, "压碎3D", "Crush3D", None, "压碎3D"),
        ({"zh": "薩爾達傳說"}, "塞尔达传说", "Zelda", None, "塞尔达传说"),
        # Then a Simplified Wikidata label, or a generic one already in Simplified.
        ({"zh-hans": "斑鸠", "zh": "斑鳩"}, None, "Ikaruga", None, "斑鸠"),
        ({"zh": "星之卡比 三重豪华版"}, None, "Kirby", None, "星之卡比 三重豪华版"),
        # A Traditional label is converted.
        ({"zh": "逆轉裁判5"}, None, "Ace Attorney", None, "逆转裁判5"),
        # A Chinese provider name is converted; a Latin one takes the filename.
        ({}, None, "瑪利歐派對", "马里奥聚会", "玛利欧派对"),
        (
            {},
            None,
            "Wave Race: Blue Storm",
            "Wave Race Blue Storm 英文版",
            "Wave Race: Blue Storm",
        ),
        ({}, None, "Wetrix", "围水方块", "围水方块"),
        ({}, None, "Wetrix", "Wetrix (USA)", "Wetrix"),
    ],
)
@pytest.mark.asyncio
async def test_resolve_zh_title_order(
    labels: dict[str, str],
    bangumi: str | None,
    name: str,
    file_title: str | None,
    title: str,
):
    wikidata_patch, bangumi_patch = _patch_sources(labels, bangumi)
    with wikidata_patch, bangumi_patch:
        assert await resolve_zh_title(name, "a-slug", file_title=file_title) == title


@pytest.mark.asyncio
async def test_resolve_zh_title_asks_bangumi_with_the_igdb_names():
    wikidata_patch, bangumi_patch = _patch_sources(bangumi="塞尔达无双 海拉尔全明星")
    with wikidata_patch, bangumi_patch as bangumi:
        await resolve_zh_title(
            "Hyrule Warriors: Legends",
            "hyrule-warriors-legends",
            ["ゼルダ無双 ハイラルオールスターズ"],
        )

    bangumi.assert_awaited_once_with(
        ["Hyrule Warriors: Legends", "ゼルダ無双 ハイラルオールスターズ"], None
    )


@pytest.mark.asyncio
async def test_translate_game_metadata_uses_the_resolved_title_in_the_summary():
    async def fake_translate(text: str | None, **_kwargs):
        return f"《{TITLE_PLACEHOLDER}》是一款赛车游戏。"

    wikidata_patch, bangumi_patch = _patch_sources({"zh-cn": "马力欧卡丁车7"})
    with (
        patch("utils.translator.translate_text", fake_translate),
        wikidata_patch as wikidata,
        bangumi_patch,
    ):
        name, summary = await translate_game_metadata(
            "Mario Kart 7",
            "Mario Kart 7 is a racing game.",
            igdb_slug="mario-kart-7",
        )

    wikidata.assert_awaited_once_with("mario-kart-7")
    assert name == "马力欧卡丁车7"
    assert summary == "《马力欧卡丁车7》是一款赛车游戏。"


@pytest.mark.asyncio
async def test_listed_official_name_wins_over_wikidata():
    wikidata_patch, bangumi_patch = _patch_sources()
    with wikidata_patch as wikidata, bangumi_patch as bangumi:
        name, _summary = await translate_game_metadata(
            "Shining Soul", None, igdb_slug="shining-soul"
        )

    assert name == "光明之魂"
    wikidata.assert_not_awaited()
    bangumi.assert_not_awaited()
