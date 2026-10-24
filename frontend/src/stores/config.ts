import { defineStore } from "pinia";
import type { ConfigResponse, ExclusionType } from "@/__generated__";
import api from "@/services/api";

export type Config = ConfigResponse;

// The backend lowercases folder names before writing them to config.yml, so
// every read and write of a mapping normalizes the on-disk name the same way.
function normalizeFsSlug(fsSlug: string): string {
  return fsSlug.toLowerCase();
}

const defaultConfig = {
  CONFIG_FILE_MOUNTED: false,
  CONFIG_FILE_WRITABLE: false,
  CONFIG_FILE_PARSE_ERROR: null,
  EXCLUDED_PLATFORMS: [],
  EXCLUDED_SINGLE_EXT: [],
  EXCLUDED_SINGLE_FILES: [],
  EXCLUDED_MULTI_FILES: [],
  EXCLUDED_MULTI_PARTS_EXT: [],
  EXCLUDED_MULTI_PARTS_FILES: [],
  DEFAULT_EXCLUDED_PLATFORM_DIRS: [],
  DEFAULT_EXCLUDED_MULTI_FILE_DIRS: [],
  DEFAULT_EXCLUDED_FILES: [],
  DEFAULT_EXCLUDED_EXTENSIONS: [],
  PLATFORMS_BINDING: {},
  PLATFORMS_VERSIONS: {},
  SKIP_HASH_CALCULATION: false,
  SCAN_METADATA_PRIORITY: [],
  SCAN_ARTWORK_PRIORITY: [],
  SCAN_ARTWORK_PRIORITY_OVERRIDES: {},
  SCAN_REGION_PRIORITY: [],
  SCAN_LANGUAGE_PRIORITY: [],
  SCAN_MEDIA: [],
  GAMELIST_AUTO_EXPORT_ON_SCAN: false,
  GAMELIST_MEDIA_THUMBNAIL: "box2d",
  GAMELIST_MEDIA_IMAGE: "screenshot",
  PEGASUS_AUTO_EXPORT_ON_SCAN: false,
  CONVERTO: {
    download_conversion_enabled: false,
    scan_metadata: true,
    cache_ttl_hours: 24,
    cache_max_size_gb: 20,
    platform_formats: {},
  },
  CONVERTO_LIBRARY_TARGETS: {},
} as ConfigResponse;

export default defineStore("config", {
  state: () => ({
    config: { ...defaultConfig },
  }),

  actions: {
    async fetchConfig({
      rethrow = false,
    }: { rethrow?: boolean } = {}): Promise<ConfigResponse> {
      try {
        const response = await api.get("/config");
        this.config = response.data;
        return this.config;
      } catch (error) {
        console.error("Error fetching config: ", error);
        if (rethrow) throw error;
        return this.config;
      }
    },
    getPlatformBinding(fsSlug: string): string | undefined {
      return this.config.PLATFORMS_BINDING[normalizeFsSlug(fsSlug)];
    },
    addPlatformBinding(fsSlug: string, slug: string) {
      this.config.PLATFORMS_BINDING[normalizeFsSlug(fsSlug)] = slug;
    },
    removePlatformBinding(fsSlug: string) {
      delete this.config.PLATFORMS_BINDING[normalizeFsSlug(fsSlug)];
    },
    getPlatformVersion(fsSlug: string): string | undefined {
      return this.config.PLATFORMS_VERSIONS[normalizeFsSlug(fsSlug)];
    },
    addPlatformVersion(fsSlug: string, slug: string) {
      this.config.PLATFORMS_VERSIONS[normalizeFsSlug(fsSlug)] = slug;
    },
    removePlatformVersion(fsSlug: string) {
      delete this.config.PLATFORMS_VERSIONS[normalizeFsSlug(fsSlug)];
    },
    addExclusion(exclusionType: ExclusionType, exclusionValue: string) {
      this.config[exclusionType].push(exclusionValue);
    },
    removeExclusion(exclusionValue: string, exclusionType: ExclusionType) {
      const index = this.config[exclusionType].indexOf(exclusionValue);
      if (index !== -1) {
        this.config[exclusionType].splice(index, 1);
      } else {
        console.error(
          `Value '${exclusionValue}' not found in exclusion type '${exclusionType}'`,
        );
      }
    },
    isExclusionType(type: string): type is ExclusionType {
      return Object.keys(this.config).includes(type);
    },
    reset() {},
  },
});
