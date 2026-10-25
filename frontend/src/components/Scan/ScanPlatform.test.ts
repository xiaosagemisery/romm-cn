import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { ScanningPlatform } from "@/stores/scanning";
import ScanPlatform from "./ScanPlatform.vue";

vi.mock("vue-i18n");

function mountPlatform(overrides: Partial<ScanningPlatform> = {}) {
  const platform: ScanningPlatform = {
    id: 1,
    name: "Game Boy Color",
    display_name: "Game Boy Color",
    slug: "gbc",
    fs_slug: "gbc",
    is_identified: true,
    roms: [],
    ...overrides,
  };

  return mount(ScanPlatform, {
    props: { platform, open: true },
    global: {
      stubs: {
        RCollapsible: {
          template: "<div><slot /><slot name='header-append' /></div>",
        },
        PlatformIcon: true,
        RTag: {
          props: ["text"],
          template: "<span class='r-tag'>{{ text }}</span>",
        },
        RVirtualScroller: true,
      },
    },
  });
}

describe("ScanPlatform", () => {
  it("shows only the rom count tag for a platform with nothing to flag", () => {
    const wrapper = mountPlatform();

    expect(wrapper.findAll(".r-tag")).toHaveLength(1);
  });

  it("reports no new roms for an empty platform", () => {
    const wrapper = mountPlatform();

    expect(wrapper.text()).toContain("scan.no-new-roms");
  });
});
