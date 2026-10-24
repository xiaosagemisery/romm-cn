from typing import TypedDict

from config.config_manager import (
    ConvertoConfig,
    MetadataMediaType,
)


class ConfigResponse(TypedDict):
    CONFIG_FILE_MOUNTED: bool
    CONFIG_FILE_WRITABLE: bool
    CONFIG_FILE_PARSE_ERROR: str | None
    EXCLUDED_PLATFORMS: list[str]
    EXCLUDED_SINGLE_EXT: list[str]
    EXCLUDED_SINGLE_FILES: list[str]
    EXCLUDED_MULTI_FILES: list[str]
    EXCLUDED_MULTI_PARTS_EXT: list[str]
    EXCLUDED_MULTI_PARTS_FILES: list[str]
    DEFAULT_EXCLUDED_PLATFORM_DIRS: list[str]
    DEFAULT_EXCLUDED_MULTI_FILE_DIRS: list[str]
    DEFAULT_EXCLUDED_FILES: list[str]
    DEFAULT_EXCLUDED_EXTENSIONS: list[str]
    PLATFORMS_BINDING: dict[str, str]
    PLATFORMS_VERSIONS: dict[str, str]
    SKIP_HASH_CALCULATION: bool
    SCAN_METADATA_PRIORITY: list[str]
    SCAN_ARTWORK_PRIORITY: list[str]
    SCAN_ARTWORK_PRIORITY_OVERRIDES: dict[str, list[str]]
    SCAN_REGION_PRIORITY: list[str]
    SCAN_LANGUAGE_PRIORITY: list[str]
    SCAN_MEDIA: list[str]
    GAMELIST_AUTO_EXPORT_ON_SCAN: bool
    GAMELIST_MEDIA_THUMBNAIL: MetadataMediaType
    GAMELIST_MEDIA_IMAGE: MetadataMediaType
    PEGASUS_AUTO_EXPORT_ON_SCAN: bool
    CONVERTO: ConvertoConfig
    # Platform slug -> the formats its library can be stored in.
    CONVERTO_LIBRARY_TARGETS: dict[str, list[str]]
