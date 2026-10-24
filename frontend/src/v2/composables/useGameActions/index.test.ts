import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ActionKey } from "@/__generated__";
import type { SimpleRom } from "@/stores/roms";
import { useGameActions } from "./index";

// Controllable stubs shared with the mocked modules below.
const push = vi.fn();
const startScan = vi.fn(() => true);
const snackbarInfo = vi.fn();
// Granted action keys — `null` means "everything" (the default).
const grantedActions: { value: Set<ActionKey> | null } = { value: null };

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));
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
  default: { updateUserRomProps: vi.fn() },
}));
vi.mock("@/stores/auth", () => ({
  default: () => ({ scopes: [] as string[] }),
}));
vi.mock("@/stores/roms", () => ({
  default: () => ({ update: vi.fn(), removeFromContinuePlaying: vi.fn() }),
}));
vi.mock("@/utils", () => ({
  getDownloadLink: vi.fn(),
  getDownloadPath: vi.fn(),
  isNintendoDSRom: () => false,
}));
vi.mock("@/v2/composables/useCan", () => ({
  useCan: (action: ActionKey) => ({
    get value() {
      return grantedActions.value?.has(action) ?? true;
    },
  }),
}));
vi.mock("@/v2/composables/useClipboard", () => ({
  useClipboard: () => ({ copy: vi.fn() }),
}));
vi.mock("@/v2/composables/useRomSync", () => ({
  useRomSync: () => ({
    syncCachedRom: vi.fn(),
    applyRomWrite: vi.fn(),
    refreshAfterUserStateChange: vi.fn(),
    refreshIfOrderedBy: vi.fn(),
  }),
}));
vi.mock("@/v2/composables/useScanTrigger", () => ({
  useScanTrigger: () => ({ startScan }),
}));
vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({ success: vi.fn(), error: vi.fn(), info: snackbarInfo }),
}));
function makeRom(status: SimpleRom["rom_user"]["status"] = null): SimpleRom {
  return {
    id: 1,
    name: "Chrono Trigger",
    fs_name_no_ext: "Chrono Trigger",
    platform_slug: "snes",
    has_file_on_disk: true,
    rom_user: { status },
  } as unknown as SimpleRom;
}

beforeEach(() => {
  push.mockClear();
  startScan.mockClear();
  snackbarInfo.mockClear();
  grantedActions.value = null;
});

describe("useGameActions: downloads", () => {
  it("offers no download without a file behind the rom", () => {
    const fileless = { ...makeRom(), has_file_on_disk: false } as SimpleRom;
    const actions = useGameActions(() => fileless);

    expect(actions.canDownload.value).toBe(false);
  });
});

describe("useGameActions — write/destructive gates", () => {
  it("exposes every write action when the grants allow it", () => {
    const actions = useGameActions(() => makeRom());
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
    const actions = useGameActions(() => makeRom());
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
    const actions = useGameActions(() => makeRom());
    expect(actions.canEdit.value).toBe(true);
    expect(actions.canDelete.value).toBe(false);
  });

  // A bare DELETE grant projects to no scope, so `POST /roms/delete` (which
  // gates on ROMS_WRITE) would 403, so the menu must not offer it.
  it("hides delete when the delete grant is held without the write grant", () => {
    grantedActions.value = new Set<ActionKey>(["rom.view", "rom.delete"]);
    const actions = useGameActions(() => makeRom());
    expect(actions.canDelete.value).toBe(false);
  });

  it("shows delete when both the delete and write grants are held", () => {
    grantedActions.value = new Set<ActionKey>(["rom.delete", "rom.edit"]);
    const actions = useGameActions(() => makeRom());
    expect(actions.canDelete.value).toBe(true);
  });
});

describe("useGameActions.refreshFiles", () => {
  it("refreshes the rom files without any provider", () => {
    const rom = { ...makeRom(null), platform_id: 7 } as SimpleRom;
    const actions = useGameActions(() => rom);

    actions.refreshFiles();

    expect(startScan).toHaveBeenCalledWith([
      { platforms: [7], roms_ids: [1], type: "quick", apis: [] },
    ]);
    expect(snackbarInfo).toHaveBeenCalledWith(
      "rom.refreshing-files",
      expect.anything(),
    );
  });

  it("stays quiet when a scan is already running", () => {
    startScan.mockReturnValueOnce(false);
    const actions = useGameActions(() => makeRom(null));

    actions.refreshFiles();

    expect(snackbarInfo).not.toHaveBeenCalled();
  });
});
