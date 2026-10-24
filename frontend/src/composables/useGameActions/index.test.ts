import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ActionKey } from "@/__generated__";
import storeFormatConversions from "@/stores/formatConversions";
import type { DetailedRom, SimpleRom } from "@/stores/roms";
import {
  detailedRomFixture,
  romFileFixture,
  romFixture,
  romUserFixture,
} from "@/utils/rom.fixtures";
import { useGameActions } from "./index";

// Controllable stubs shared with the mocked modules below.
const push = vi.fn();
const confirmFn = vi.fn();
const startScan = vi.fn(() => true);
const snackbarInfo = vi.fn();
const snackbarError = vi.fn();
const probeFormatDownload = vi.fn();
const downloadRom = vi.fn();
const grantedActions: { value: Set<ActionKey> | null } = { value: null };
const { clipboardCopy, emitterEmit } = vi.hoisted(() => ({
  clipboardCopy: vi.fn(),
  emitterEmit: vi.fn(),
}));

vi.mock("vue", async (importOriginal) => ({
  ...(await importOriginal<typeof import("vue")>()),
  inject: () => ({ emit: emitterEmit }),
}));
vi.mock("vue-i18n");
vi.mock("vue-router", () => ({
  useRouter: () => ({ push }),
}));
vi.mock("@/composables/useFavoriteToggle", () => ({
  useFavoriteToggle: () => ({
    isFavorite: () => false,
    toggleFavorite: vi.fn(),
  }),
}));
vi.mock("@/services/api/rom", () => ({
  default: {
    updateUserRomProps: vi.fn(),
    probeFormatDownload: (href: string) => probeFormatDownload(href),
    downloadRom: (opts: unknown) => downloadRom(opts),
  },
}));

const authScopes: string[] = [];
vi.mock("@/stores/auth", () => ({
  default: () => ({ scopes: authScopes }),
}));
vi.mock("@/stores/roms", () => ({
  default: () => ({ update: vi.fn(), removeFromContinuePlaying: vi.fn() }),
}));
vi.mock("@/utils", async () => {
  const actual = await vi.importActual<typeof import("@/utils/downloadPath")>(
    "@/utils/downloadPath",
  );
  return {
    getDownloadLink: vi.fn(
      () => "http://romm.local/api/roms/1/content/game.zip",
    ),
    getDownloadPath: vi.fn(() => "/api/roms/1/content/game.chd?format=iso"),
    getSoleRomFile: actual.getSoleRomFile,
    isNintendoDSRom: () => false,
  };
});
vi.mock("@/composables/useCan", () => ({
  useCan: (action: ActionKey) => ({
    get value() {
      return grantedActions.value?.has(action) ?? true;
    },
  }),
}));
vi.mock("@/composables/useClipboard", () => ({
  useClipboard: () => ({ copy: clipboardCopy }),
}));
vi.mock("@/composables/useConfirm", () => ({
  useConfirm: () => confirmFn,
}));
vi.mock("@/composables/useRomSync", () => ({
  useRomSync: () => ({
    syncCachedRom: vi.fn(),
    applyRomWrite: vi.fn(),
    refreshAfterUserStateChange: vi.fn(),
    refreshIfOrderedBy: vi.fn(),
  }),
}));
vi.mock("@/composables/useScanTrigger", () => ({
  useScanTrigger: () => ({ startScan }),
}));
vi.mock("@/composables/useSnackbar", () => ({
  useSnackbar: () => ({
    success: vi.fn(),
    error: snackbarError,
    info: snackbarInfo,
  }),
}));

function romWithStatus(
  status: SimpleRom["rom_user"]["status"] = null,
): SimpleRom {
  return romFixture({
    name: "Chrono Trigger",
    fs_name_no_ext: "Chrono Trigger",
    platform_slug: "snes",
    has_file_on_disk: true,
    rom_user: romUserFixture({ status }),
  });
}

beforeEach(() => {
  probeFormatDownload.mockReset();
  downloadRom.mockReset();
  clipboardCopy.mockReset();
  emitterEmit.mockReset();
  grantedActions.value = null;
  authScopes.splice(0, authScopes.length);
});

describe("useGameActions — write/destructive gates", () => {
  it("exposes every write action when the grants allow it", () => {
    const actions = useGameActions(() => romWithStatus());
    expect(actions.canEdit.value).toBe(true);
    expect(actions.canDelete.value).toBe(true);
    expect(actions.canMatch.value).toBe(true);
    expect(actions.canRefresh.value).toBe(true);
  });

  it("denies them for a read-only user", () => {
    grantedActions.value = new Set<ActionKey>([
      "rom.view",
      "rom.play",
      "rom.download",
      "rom.favorite",
    ]);
    const actions = useGameActions(() => romWithStatus());
    expect(actions.canEdit.value).toBe(false);
    expect(actions.canDelete.value).toBe(false);
    expect(actions.canMatch.value).toBe(false);
    expect(actions.canRefresh.value).toBe(false);
  });

  it("hides delete when only the write grants are held", () => {
    grantedActions.value = new Set<ActionKey>([
      "rom.edit",
      "rom.match",
      "rom.refresh",
    ]);
    const actions = useGameActions(() => romWithStatus());
    expect(actions.canEdit.value).toBe(true);
    expect(actions.canDelete.value).toBe(false);
  });

  // A bare DELETE grant projects to no scope, so `POST /roms/delete` (which
  // gates on ROMS_WRITE) would 403, so the menu must not offer it.
  it("hides delete when the delete grant is held without the write grant", () => {
    grantedActions.value = new Set<ActionKey>(["rom.view", "rom.delete"]);
    const actions = useGameActions(() => romWithStatus());
    expect(actions.canDelete.value).toBe(false);
  });

  it("shows delete when both the delete and write grants are held", () => {
    grantedActions.value = new Set<ActionKey>(["rom.delete", "rom.edit"]);
    const actions = useGameActions(() => romWithStatus());
    expect(actions.canDelete.value).toBe(true);
  });
});

describe("useGameActions.refreshFiles", () => {
  it("refreshes the rom files without any provider", () => {
    const rom = { ...romWithStatus(null), platform_id: 7 };
    const actions = useGameActions(() => rom);

    actions.refreshFiles();

    expect(startScan).toHaveBeenCalledWith([
      { platforms: [7], roms_ids: [1], type: "quick", apis: [] },
    ]);
    expect(snackbarInfo).toHaveBeenCalledWith(
      'rom.refreshing-files:{"name":"Chrono Trigger"}',
      expect.anything(),
    );
  });

  it("stays quiet when a scan is already running", () => {
    startScan.mockReturnValueOnce(false);
    const actions = useGameActions(() => romWithStatus(null));

    actions.refreshFiles();

    expect(snackbarInfo).not.toHaveBeenCalled();
  });
});

describe("useGameActions.downloadAs", () => {
  function pspRom(
    files: { id: number; file_name: string }[],
    downloadFormats = ["cso", "iso", "zso"],
  ): DetailedRom {
    return detailedRomFixture({
      platform_slug: "psp",
      has_file_on_disk: true,
      files: files.map((file) => romFileFixture(file)),
      download_formats: downloadFormats,
    });
  }

  it("offers the formats the detailed rom lists", () => {
    const rom = pspRom([{ id: 1, file_name: "Game.CHD" }]);
    expect(useGameActions(() => rom).downloadFormats.value).toEqual([
      "cso",
      "iso",
      "zso",
    ]);
  });

  it("offers nothing for a rom without the list or without a file", () => {
    const simple = romFixture({ platform_slug: "psp", has_file_on_disk: true });
    expect(useGameActions(() => simple).downloadFormats.value).toEqual([]);

    const missing = { ...pspRom([]), has_file_on_disk: false };
    expect(useGameActions(() => missing).downloadFormats.value).toEqual([]);
  });

  it("downloads straight away when the format can be served", async () => {
    probeFormatDownload.mockResolvedValue({
      status: 206,
      retryAfterSeconds: null,
    });
    const rom = pspRom([{ id: 7, file_name: "game.chd" }]);
    const addConversion = vi.spyOn(storeFormatConversions(), "add");

    await useGameActions(() => rom).downloadAs("iso");

    expect(downloadRom).toHaveBeenCalledWith({
      rom,
      fileIDs: [7],
      format: "iso",
    });
    expect(snackbarInfo).not.toHaveBeenCalled();
    expect(addConversion).not.toHaveBeenCalled();
  });

  it("polls while it converts, then downloads", async () => {
    vi.useFakeTimers();
    probeFormatDownload
      .mockResolvedValueOnce({ status: 202, retryAfterSeconds: 5 })
      .mockResolvedValueOnce({ status: 206, retryAfterSeconds: null });
    const rom = pspRom([{ id: 7, file_name: "game.chd" }]);

    const conversions = storeFormatConversions();

    const pending = useGameActions(() => rom).downloadAs("iso");
    await vi.advanceTimersByTimeAsync(0);
    expect(conversions.conversions).toEqual([
      expect.objectContaining({
        romId: rom.id,
        romName: "Game",
        format: "ISO",
      }),
    ]);
    await vi.advanceTimersByTimeAsync(5000);
    await pending;

    expect(conversions.conversions).toEqual([]);
    expect(snackbarInfo).toHaveBeenCalledWith(
      'rom.download-as-preparing:{"format":"ISO"}',
    );
    expect(probeFormatDownload).toHaveBeenCalledTimes(2);
    expect(downloadRom).toHaveBeenCalledOnce();
  });

  it("reports a format the server refuses", async () => {
    probeFormatDownload.mockResolvedValue({
      status: 406,
      retryAfterSeconds: null,
    });
    const rom = pspRom([{ id: 7, file_name: "game.chd" }]);

    await useGameActions(() => rom).downloadAs("iso");

    expect(downloadRom).not.toHaveBeenCalled();
    expect(snackbarError).toHaveBeenCalledWith(
      'rom.download-as-unavailable:{"format":"ISO"}',
      {
        persist: { body: "Game", link: "/rom/1" },
      },
    );
  });

  it("ignores a second click while the first is still waiting", async () => {
    vi.useFakeTimers();
    probeFormatDownload
      .mockResolvedValueOnce({ status: 202, retryAfterSeconds: 5 })
      .mockResolvedValueOnce({ status: 206, retryAfterSeconds: null });
    const rom = pspRom([{ id: 7, file_name: "game.chd" }]);
    const actions = useGameActions(() => rom);

    const first = actions.downloadAs("iso");
    await actions.downloadAs("iso");
    await vi.advanceTimersByTimeAsync(5000);
    await first;

    expect(probeFormatDownload).toHaveBeenCalledTimes(2);
    expect(downloadRom).toHaveBeenCalledOnce();
  });
});

describe("useGameActions.copyDownloadLink", () => {
  const LINK = "http://romm.local/api/roms/1/content/game.zip";

  it("copies the download link with a success toast", async () => {
    await useGameActions(() => romWithStatus()).copyDownloadLink();

    expect(clipboardCopy).toHaveBeenCalledWith(
      LINK,
      expect.objectContaining({
        successMessage: "rom.snackbar-download-link-copied",
      }),
    );
  });

  it("opens the manual-copy dialog when the copy fails", async () => {
    clipboardCopy.mockImplementation(
      (_text: string, opts: { fallback?: () => void }) => {
        opts.fallback?.();
        return Promise.resolve(false);
      },
    );

    await useGameActions(() => romWithStatus()).copyDownloadLink();

    expect(emitterEmit).toHaveBeenCalledWith(
      "showCopyDownloadLinkDialog",
      LINK,
    );
  });
});
