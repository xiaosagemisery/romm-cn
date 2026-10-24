import logging
import os
from contextlib import contextmanager
from pathlib import Path

import pytest

from config.config_manager import (
    DEFAULT_EXCLUDED_PLATFORM_DIRS,
    ConfigManager,
    ConvertoConfig,
    parse_platform_templates,
    parse_structure_template,
)
from exceptions.config_exceptions import ConfigNotWritableException


@contextmanager
def capture_romm_logs(caplog, level=logging.WARNING):
    """Capture the `romm` logger, whose records never reach caplog on their own.

    It sets `propagate = False`, so caplog's handler has to be attached to it
    directly rather than to the root logger.
    """
    romm_logger = logging.getLogger("romm")
    romm_logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(level, logger="romm"):
            yield caplog
    finally:
        romm_logger.removeHandler(caplog.handler)


def test_scan_priority_sources_match_metadata_source_enum():
    """VALID_SCAN_PRIORITY_SOURCES duplicates MetadataSource to avoid a circular
    import; guard against the two drifting apart."""
    from config.config_manager import VALID_SCAN_PRIORITY_SOURCES
    from handler.scan_handler import MetadataSource

    assert VALID_SCAN_PRIORITY_SOURCES == {source.value for source in MetadataSource}


@pytest.mark.parametrize(
    ("template", "platform_dir", "levels"),
    [
        ("{platform}/{game}", (), ()),
        ("roms/{platform}/{game}", ("roms",), ()),
        ("roms/{platform}/{category}/{game}", ("roms",), (None,)),
        ("roms/{platform}/Hacks/{game}", ("roms",), ("Hacks",)),
        (
            "games/all/{platform}/{region}/{system}/{game}",
            ("games", "all"),
            (None, None),
        ),
    ],
)
def test_parse_structure_template_valid(template, platform_dir, levels):
    structure = parse_structure_template(template)
    assert structure.platform_dir == platform_dir
    assert tuple(level.literal for level in structure.levels) == levels


def test_parse_structure_template_accepts_the_platform_folder_by_name():
    """A per-platform override may name the folder outright instead of using the
    macro, which is how the key already reads."""
    structure = parse_structure_template("roms/ps3/{category}/{game}", fs_slug="ps3")
    assert structure.platform_dir == ("roms",)
    assert structure.platform_path("ps3") == "roms/ps3"


@pytest.mark.parametrize(
    "template",
    [
        "",
        "justliteral",
        "roms/{platform}",  # no terminal
        "roms/{platform}/{category}",  # no terminal
        "roms/{game}",  # no platform folder
        "{game}/roms/{platform}",  # terminal not last
        "roms/{platform}/{game}/extra",  # terminal not last
        "roms/{platform}/{platform}/{game}",  # platform folder twice
        "{category}/{platform}/{game}",  # wildcard above the platform folder
        "{library}/roms/{platform}/{game}",  # macro RomM resolves itself
        "roms/{platform}/{}/{game}",  # empty macro
        "roms/{platform}/{gameFile}",  # the terminal is spelled {game}
        "roms/{platform}/./{game}",  # no listing ever yields '.'
        "roms/{platform}/../{game}",
        "../roms/{platform}/{game}",
    ],
)
def test_parse_structure_template_invalid(template):
    with pytest.raises(ValueError):
        parse_structure_template(template)


def test_structure_templates_are_keyed_case_insensitively(monkeypatch, tmp_path):
    """`system.platforms` lowercases its folder names, so `filesystem.structure`
    has to as well or the same key works in one block and not the other."""
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        "filesystem:\n  structure:\n"
        "    'Atari - 2600': 'roms/{platform}/Hacks/{game}'\n"
    )
    config = ConfigManager(str(config_file)).get_config()

    for key in ("Atari - 2600", "atari - 2600"):
        structure = config.platform_structure(key)
        assert len(structure) == 1
        assert structure[0].levels[0].literal == "Hacks"


def test_parse_platform_templates_string_and_list():
    # A bare string yields a single structure.
    single = parse_platform_templates("roms/{platform}/{game}")
    assert len(single) == 1 and single[0].levels == ()

    # A list yields one structure per template, preserving order.
    multi = parse_platform_templates(
        ["roms/{platform}/{game}", "roms/{platform}/{category}/{game}"]
    )
    assert len(multi) == 2
    assert multi[0].levels == ()
    assert len(multi[1].levels) == 1 and multi[1].levels[0].literal is None


def test_parse_platform_templates_propagates_invalid():
    with pytest.raises(ValueError):
        parse_platform_templates(["roms/{platform}/{game}", "nope"])


def test_missing_config_file_is_created(tmp_path):
    config_file = tmp_path / "config" / "config.yml"

    loader = ConfigManager(str(config_file))

    assert config_file.parent.exists()
    assert config_file.exists()
    assert config_file.read_text() == ""
    assert loader.config.CONFIG_FILE_MOUNTED
    assert loader.config.CONFIG_FILE_WRITABLE


def test_forward_compat_unknown_values_are_tolerated():
    """A newer release may ship sample configs that reference media types
    this version doesn't yet recognize. The loader should drop unknowns and
    fall back to defaults rather than exiting."""
    loader = ConfigManager(
        os.path.join(
            Path(__file__).resolve().parent,
            "fixtures",
            "config/forward_compat_config.yml",
        )
    )

    # Unknown entries in scan.media are filtered out; known ones survive.
    assert loader.config.SCAN_MEDIA == ["box2d", "screenshot"]
    # Unknown thumbnail/image values fall back to their defaults.
    assert loader.config.GAMELIST_MEDIA_THUMBNAIL == "box2d"
    assert loader.config.GAMELIST_MEDIA_IMAGE == "screenshot"
    # Unknown region_mode values fall back to the default.
    assert loader.config.SCAN_REGION_MODE == "prefer_rom_tags"


def test_non_string_region_mode_falls_back_to_default(tmp_path):
    """A list/mapping region_mode is unhashable and must not crash the
    membership check against the valid-modes set."""
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        "scan:\n  priority:\n    region_mode:\n      - prefer_config\n"
    )
    loader = ConfigManager(str(config_file))

    assert loader.config.SCAN_REGION_MODE == "prefer_rom_tags"


def test_valid_config_has_no_parse_error():
    """A syntactically valid config should not report a parse error."""
    loader = ConfigManager(
        os.path.join(Path(__file__).resolve().parent, "fixtures", "config/config.yml")
    )

    assert loader.config.CONFIG_FILE_PARSE_ERROR is None


def test_mixed_gamelist_syntax_surfaces_parse_error(tmp_path):
    """Regression for #3708: mixing the old (`scan.export`) and new
    (`scan.gamelist.export`) syntax produces invalid YAML. The whole config is
    discarded and defaults are used, so the parse error must be surfaced rather
    than silently swallowed."""
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        "scan:\n"
        "  gamelist:\n"
        "    export: true\n"
        "  - gamelist_xml: true\n"
        "  media:\n"
        "    - box2d\n"
        "    - video\n"
        "    - manual\n"
    )

    loader = ConfigManager(str(config_file))

    assert loader.config.CONFIG_FILE_PARSE_ERROR is not None
    # The user's scan.media list is lost, falling back to defaults.
    assert loader.config.SCAN_MEDIA == ["box2d", "screenshot", "manual"]


def test_parse_error_is_cleared_when_config_is_missing(tmp_path):
    """A stale parse error from a malformed config must not persist once the
    file is gone. The loader is a singleton, so a later reload that skips YAML
    parsing (e.g. the file was deleted) has to clear the flag."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("scan:\n  - broken: true\n  media: [box2d]\n")

    loader = ConfigManager(str(config_file))
    assert loader.config.CONFIG_FILE_PARSE_ERROR is not None

    # get_config's FileNotFoundError branch must clear the stale error.
    config_file.unlink()
    loader.get_config()
    assert loader.config.CONFIG_FILE_PARSE_ERROR is None


def test_parse_error_is_cleared_when_config_is_recreated(tmp_path):
    """Reloading via a missing file goes through _create_missing_config_file,
    which must also clear a stale parse error from a prior malformed load."""
    broken_file = tmp_path / "config.yml"
    broken_file.write_text("scan:\n  - broken: true\n  media: [box2d]\n")

    ConfigManager(str(broken_file))

    # Reusing the singleton with a missing path exercises the __init__
    # FileNotFoundError -> _create_missing_config_file recreate path.
    broken_file.unlink()
    loader = ConfigManager(str(broken_file))

    assert loader.config.CONFIG_FILE_PARSE_ERROR is None


def test_config_updates_serialize_gamelist_media_as_plain_strings(tmp_path):
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        "scan:\n"
        "  gamelist:\n"
        "    media:\n"
        "      thumbnail: box2d\n"
        "      image: screenshot\n"
    )
    loader = ConfigManager(str(config_file))
    loader.add_platform_binding("atarist", "atari-st")

    config_text = config_file.read_text()
    assert "!!python/object" not in config_text
    assert "thumbnail: box2d" in config_text
    assert "image: screenshot" in config_text

    reloaded = ConfigManager(str(config_file))
    assert reloaded.config.PLATFORMS_BINDING == {"atarist": "atari-st"}


def test_update_scan_settings_round_trip(tmp_path):
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        "scan:\n  priority:\n    region_mode: prefer_config\n  media:\n    - box2d\n"
    )
    loader = ConfigManager(str(config_file))

    loader.update_scan_settings(
        metadata_priority=["ss", "igdb"],
        artwork_priority=["igdb", "ss"],
        artwork_overrides={"cover": ["ss"], "screenshot": None, "manual": None},
        region_priority=["jp", "us"],
        language_priority=["ja", "en"],
        media=["box2d", "screenshot", "manual"],
        gamelist_export=True,
        gamelist_thumbnail="box3d",
        gamelist_image="title_screen",
        pegasus_export=True,
    )

    config_text = config_file.read_text()
    assert "!!python/object" not in config_text

    reloaded = ConfigManager(str(config_file))
    assert reloaded.config.SCAN_METADATA_PRIORITY == ["ss", "igdb"]
    assert reloaded.config.SCAN_ARTWORK_PRIORITY == ["igdb", "ss"]
    # Only the "cover" override was provided; the others fall back to artwork.
    assert reloaded.config.SCAN_ARTWORK_PRIORITY_OVERRIDES == {"url_cover": ["ss"]}
    assert reloaded.config.SCAN_REGION_PRIORITY == ["jp", "us"]
    # region_mode is not runtime-editable but must survive the rewrite.
    assert reloaded.config.SCAN_REGION_MODE == "prefer_config"
    assert reloaded.config.SCAN_LANGUAGE_PRIORITY == ["ja", "en"]
    assert reloaded.config.SCAN_MEDIA == ["box2d", "screenshot", "manual"]
    assert reloaded.config.GAMELIST_AUTO_EXPORT_ON_SCAN is True
    assert reloaded.config.GAMELIST_MEDIA_THUMBNAIL == "box3d"
    assert reloaded.config.GAMELIST_MEDIA_IMAGE == "title_screen"
    assert reloaded.config.PEGASUS_AUTO_EXPORT_ON_SCAN is True


def _write_config(tmp_path: Path, system_block: str) -> ConfigManager:
    config_file = tmp_path / "config.yml"
    config_file.write_text(f"system:\n{system_block}")
    return ConfigManager(str(config_file))


def test_platform_folder_names_are_lowercased(tmp_path):
    loader = _write_config(
        tmp_path,
        '  platforms:\n    GameCube: "ngc"\n  versions:\n    NAOMI: "arcade"\n',
    )

    assert loader.config.PLATFORMS_BINDING == {"gamecube": "ngc"}
    assert loader.config.PLATFORMS_VERSIONS == {"naomi": "arcade"}


def test_null_platforms_block_means_empty(tmp_path):
    loader = _write_config(tmp_path, "  platforms:\n  versions:\n")

    assert loader.config.PLATFORMS_BINDING == {}
    assert loader.config.PLATFORMS_VERSIONS == {}


@pytest.mark.parametrize("value", ['""', "5", "~"])
def test_platform_binding_must_be_a_non_empty_string(tmp_path, value):
    with pytest.raises(SystemExit) as excinfo:
        _write_config(tmp_path, f"  platforms:\n    gamecube: {value}\n")

    assert excinfo.value.code == 3


def test_platform_binding_lookup_ignores_case(tmp_path):
    loader = _write_config(tmp_path, '  platforms:\n    GameCube: "ngc"\n')

    loader.remove_platform_binding("GAMECUBE")
    assert loader.config.PLATFORMS_BINDING == {}


def test_case_variant_folder_keys_collapse_with_a_warning(caplog, tmp_path):
    """One key covers both, so the dropped mapping must not vanish silently."""
    with capture_romm_logs(caplog):
        loader = _write_config(
            tmp_path, '  platforms:\n    PSX: "ps2"\n    psx: "psx"\n'
        )

    assert loader.config.PLATFORMS_BINDING == {"psx": "psx"}
    assert "case variant" in caplog.text
    assert "ps2" in caplog.text


def test_identical_case_variant_mappings_do_not_warn(caplog, tmp_path):
    with capture_romm_logs(caplog):
        loader = _write_config(
            tmp_path, '  platforms:\n    PSX: "psx"\n    psx: "psx"\n'
        )

    assert loader.config.PLATFORMS_BINDING == {"psx": "psx"}
    assert "case variant" not in caplog.text


def test_rebinding_a_folder_replaces_the_existing_platform(tmp_path):
    loader = _write_config(tmp_path, '  platforms:\n    GameCube: "ngc"\n')

    loader.add_platform_binding("GameCube", "wii")

    assert loader.config.PLATFORMS_BINDING == {"gamecube": "wii"}
    reloaded = ConfigManager(loader.config_file)
    assert reloaded.config.PLATFORMS_BINDING == {"gamecube": "wii"}


def test_reparenting_a_folder_replaces_the_existing_version(tmp_path):
    loader = _write_config(tmp_path, '  versions:\n    NAOMI: "arcade"\n')

    loader.add_platform_version("naomi", "dc")

    assert loader.config.PLATFORMS_VERSIONS == {"naomi": "dc"}
    reloaded = ConfigManager(loader.config_file)
    assert reloaded.config.PLATFORMS_VERSIONS == {"naomi": "dc"}


def test_converto_config_from_yaml(tmp_path):
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        "converto:\n"
        "  download_conversion_enabled: true\n"
        "  scan_metadata: false\n"
        "  cache_ttl_hours: 48\n"
        "  cache_max_size_gb: 0\n"
        "  platform_formats:\n"
        "    PSP: iso\n"
        "    ngc: rvz\n"
    )
    loader = ConfigManager(str(config_file))

    # Slugs and targets are normalized to lowercase.
    assert loader.config.CONVERTO == ConvertoConfig(
        download_conversion_enabled=True,
        scan_metadata=False,
        cache_ttl_hours=48,
        cache_max_size_gb=0,
        platform_formats={"psp": "iso", "ngc": "rvz"},
    )


def test_null_converto_platform_formats_means_empty(tmp_path):
    config_file = tmp_path / "config.yml"
    config_file.write_text("converto:\n  platform_formats:\n")

    assert ConfigManager(str(config_file)).config.CONVERTO.platform_formats == {}


def test_update_converto_settings_round_trip(tmp_path):
    config_file = tmp_path / "config.yml"
    config_file.write_text("converto:\n  cache_ttl_hours: 12\n")
    loader = ConfigManager(str(config_file))
    converto = ConvertoConfig(
        download_conversion_enabled=True,
        scan_metadata=True,
        cache_ttl_hours=72,
        cache_max_size_gb=50,
        platform_formats={"psp": "iso", "ngc": "rvz"},
    )

    loader.update_converto_settings(converto)

    assert ConfigManager(str(config_file)).config.CONVERTO == converto


@pytest.mark.parametrize(
    "block",
    [
        "  platform_formats:\n    psvita: iso\n",
        "  platform_formats:\n    psp: rvz\n",
        "  platform_formats:\n    xbox: xiso\n",
        "  cache_ttl_hours: 0\n",
        "  cache_max_size_gb: -1\n",
        "  cache_max_size_gb: true\n",
    ],
)
def test_invalid_converto_setting_exits(tmp_path, block):
    config_file = tmp_path / "config.yml"
    config_file.write_text(f"converto:\n{block}")

    with pytest.raises(SystemExit) as excinfo:
        ConfigManager(str(config_file))

    assert excinfo.value.code == 3


@pytest.fixture
def critical(mocker):
    """The last message the config manager logged before exiting."""
    spy = mocker.patch("config.config_manager.log.critical")
    return lambda: str(spy.call_args[0][0])


EXCLUDE_LIST_PATHS = (
    "exclude.platforms",
    "exclude.roms.single_file.extensions",
    "exclude.roms.single_file.names",
    "exclude.roms.multi_file.names",
    "exclude.roms.multi_file.parts.extensions",
    "exclude.roms.multi_file.parts.names",
)


def _write_exclude_config(tmp_path: Path, path: str, value: str) -> ConfigManager:
    """Write `value` at the dotted `path`, nesting one YAML level per segment."""
    lines = [f"{'  ' * depth}{key}:" for depth, key in enumerate(path.split("."))]
    lines[-1] += f" {value}"
    config_file = tmp_path / "config.yml"
    config_file.write_text("\n".join(lines) + "\n")
    return ConfigManager(str(config_file))


@pytest.mark.parametrize("path", EXCLUDE_LIST_PATHS)
@pytest.mark.parametrize("value", ["ps2", "5", "{ps2: true}"])
def test_exclude_list_rejects_a_non_list(tmp_path, critical, path, value):
    """A bare string would otherwise be split into one exclusion per character."""
    with pytest.raises(SystemExit) as excinfo:
        _write_exclude_config(tmp_path, path, value)

    assert excinfo.value.code == 3
    assert critical() == f"Invalid config.yml: {path} must be a list"


@pytest.mark.parametrize("path", EXCLUDE_LIST_PATHS)
@pytest.mark.parametrize("value", ["[7z, 001]", "[ps2, ~]"])
def test_exclude_list_rejects_a_non_string_entry(tmp_path, critical, path, value):
    with pytest.raises(SystemExit) as excinfo:
        _write_exclude_config(tmp_path, path, value)

    assert excinfo.value.code == 3
    assert critical().startswith(f"Invalid config.yml: {path} must only hold strings")


def test_empty_exclude_list_keeps_the_defaults(tmp_path):
    loader = _write_exclude_config(tmp_path, "exclude.platforms", "")

    assert loader.config.EXCLUDED_PLATFORMS == sorted(DEFAULT_EXCLUDED_PLATFORM_DIRS)


def _write_filesystem_config(tmp_path: Path, block: str) -> ConfigManager:
    config_file = tmp_path / "config.yml"
    config_file.write_text(f"filesystem:\n{block}")
    return ConfigManager(str(config_file))


@pytest.fixture
def library(tmp_path, mocker):
    library = tmp_path / "library"
    library.mkdir()
    mocker.patch("config.config_manager.LIBRARY_BASE_PATH", str(library))
    return library


def test_loading_a_config_with_retired_folder_keys_never_rewrites_it(tmp_path, library):
    """Every process loads the config, so only startup writes the migration."""
    (library / "roms").mkdir()

    loader = _write_filesystem_config(tmp_path, "  roms_folder: roms\n")

    assert loader.get_config().STRUCTURE_TEMPLATES["default"] == (
        "roms/{platform}/{game}"
    )
    assert (tmp_path / "config.yml").read_text() == "filesystem:\n  roms_folder: roms\n"


def test_retired_folder_keys_migrate_in_memory_when_read_only(
    tmp_path, library, mocker
):
    (library / "games").mkdir()
    warning = mocker.patch("config.config_manager.log.warning")
    mocker.patch("config.config_manager.os.access", return_value=False)
    config_file = tmp_path / "config.yml"
    config_file.write_text("filesystem:\n  roms_folder: games\n")

    loader = ConfigManager(str(config_file))
    loader.migrate_retired_filesystem_keys()
    loader.get_config()

    assert loader.config.STRUCTURE_TEMPLATES["default"] == "games/{platform}/{game}"
    assert "roms_folder" in config_file.read_text()
    assert warning.call_count == 1
    assert 'default: "games/{platform}/{game}"' in warning.call_args[0][0]


def test_a_failed_migration_write_marks_the_config_read_only(tmp_path, library, mocker):
    (library / "roms").mkdir()
    write = mocker.patch.object(
        ConfigManager, "_write_raw_config", side_effect=ConfigNotWritableException
    )

    loader = _write_filesystem_config(tmp_path, "  roms_folder: roms\n")
    loader.migrate_retired_filesystem_keys()
    config = loader.get_config()

    assert write.call_count == 1
    assert config.CONFIG_FILE_WRITABLE is False
    assert config.STRUCTURE_TEMPLATES["default"] == "roms/{platform}/{game}"


def test_an_unmigratable_folder_exits_without_rewriting_the_config(
    tmp_path, library, critical
):
    block = "  roms_folder: games{old}\n"
    with pytest.raises(SystemExit) as excinfo:
        _write_filesystem_config(tmp_path, block)

    assert excinfo.value.code == 3
    assert "games{old}" in critical()
    assert (tmp_path / "config.yml").read_text() == f"filesystem:\n{block}"


@pytest.mark.parametrize("value", ['""', "42"])
def test_an_invalid_retired_folder_key_exits(tmp_path, library, value, critical):
    with pytest.raises(SystemExit) as excinfo:
        _write_filesystem_config(tmp_path, f"  roms_folder: {value}\n")

    assert excinfo.value.code == 3
    assert "filesystem.roms_folder" in critical()


def test_an_override_may_not_move_the_platform_folder(tmp_path, critical):
    """A platform outside the folder platforms are enumerated in would never be
    discovered."""
    with pytest.raises(SystemExit) as excinfo:
        _write_filesystem_config(
            tmp_path,
            "  structure:\n"
            '    default: "roms/{platform}/{game}"\n'
            '    ps3: "disc-games/{platform}/{game}"\n',
        )

    assert excinfo.value.code == 3
    assert "disc-games" in critical()


def test_the_retired_library_layout_check_names_the_template(
    tmp_path, library, critical
):
    """A `{platform}/roms` library used to be auto-detected; now it has to say so
    rather than scan as empty and mark every rom missing."""
    (library / "n64" / "roms").mkdir(parents=True)

    loader = _write_filesystem_config(tmp_path, "  skip_hash_calculation: false\n")
    with pytest.raises(SystemExit) as excinfo:
        loader.check_library_layout()

    assert excinfo.value.code == 3
    assert 'default: "{platform}/roms/{game}"' in critical()


def test_the_retired_library_layout_check_passes_once_declared(tmp_path, library):
    (library / "n64" / "roms").mkdir(parents=True)

    loader = _write_filesystem_config(
        tmp_path, '  structure:\n    default: "{platform}/roms/{game}"\n'
    )
    loader.check_library_layout()
