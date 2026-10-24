/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConvertoConfig } from './ConvertoConfig';
import type { MetadataMediaType } from './MetadataMediaType';
export type ConfigResponse = {
    CONFIG_FILE_MOUNTED: boolean;
    CONFIG_FILE_WRITABLE: boolean;
    CONFIG_FILE_PARSE_ERROR: (string | null);
    EXCLUDED_PLATFORMS: Array<string>;
    EXCLUDED_SINGLE_EXT: Array<string>;
    EXCLUDED_SINGLE_FILES: Array<string>;
    EXCLUDED_MULTI_FILES: Array<string>;
    EXCLUDED_MULTI_PARTS_EXT: Array<string>;
    EXCLUDED_MULTI_PARTS_FILES: Array<string>;
    DEFAULT_EXCLUDED_PLATFORM_DIRS: Array<string>;
    DEFAULT_EXCLUDED_MULTI_FILE_DIRS: Array<string>;
    DEFAULT_EXCLUDED_FILES: Array<string>;
    DEFAULT_EXCLUDED_EXTENSIONS: Array<string>;
    PLATFORMS_BINDING: Record<string, string>;
    PLATFORMS_VERSIONS: Record<string, string>;
    SKIP_HASH_CALCULATION: boolean;
    SCAN_METADATA_PRIORITY: Array<string>;
    SCAN_ARTWORK_PRIORITY: Array<string>;
    SCAN_ARTWORK_PRIORITY_OVERRIDES: Record<string, Array<string>>;
    SCAN_REGION_PRIORITY: Array<string>;
    SCAN_LANGUAGE_PRIORITY: Array<string>;
    SCAN_MEDIA: Array<string>;
    GAMELIST_AUTO_EXPORT_ON_SCAN: boolean;
    GAMELIST_MEDIA_THUMBNAIL: MetadataMediaType;
    GAMELIST_MEDIA_IMAGE: MetadataMediaType;
    PEGASUS_AUTO_EXPORT_ON_SCAN: boolean;
    CONVERTO: ConvertoConfig;
    CONVERTO_LIBRARY_TARGETS: Record<string, Array<string>>;
};

