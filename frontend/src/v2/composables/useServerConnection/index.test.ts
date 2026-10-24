import {
  afterAll,
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import { nextTick, reactive } from "vue";
import { shouldRefreshOnReconnect } from "./index";

// Each install() leaves an app-lifetime watcher behind, so every test gets
// fresh store objects rather than sharing one the old watchers still see.
function makeHeartbeatStore() {
  return reactive({
    connected: true,
    setConnected(value: boolean) {
      this.connected = value;
    },
    fetchHeartbeat: vi.fn().mockResolvedValue({}),
  });
}

let heartbeatStore = makeHeartbeatStore();

vi.mock("@/stores/heartbeat", () => ({ default: () => heartbeatStore }));

const reload = vi.fn();
let originalLocation: Location;

// `installed` is module state, so each test needs a fresh module to install
// its own watchers.
async function install() {
  vi.resetModules();
  const { useServerConnection } = await import("./index");
  return useServerConnection();
}

/** Drive a full offline → online round trip through the store. */
async function goOfflineThenOnline() {
  heartbeatStore.connected = false;
  await nextTick();
  heartbeatStore.connected = true;
  await nextTick();
}

beforeAll(() => {
  originalLocation = window.location;
  Object.defineProperty(window, "location", {
    configurable: true,
    value: { ...originalLocation, reload },
  });
});

afterAll(() => {
  Object.defineProperty(window, "location", {
    configurable: true,
    value: originalLocation,
  });
});

beforeEach(() => {
  vi.useFakeTimers();
  reload.mockClear();
  heartbeatStore = makeHeartbeatStore();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("shouldRefreshOnReconnect", () => {
  it("refreshes only on a real reconnect (offline → online)", () => {
    expect(shouldRefreshOnReconnect(true, false)).toBe(true);
  });

  it("does not refresh on the initial reading (no prior state)", () => {
    expect(shouldRefreshOnReconnect(true, undefined)).toBe(false);
  });

  it("does not refresh while staying online", () => {
    expect(shouldRefreshOnReconnect(true, true)).toBe(false);
  });

  it("does not refresh when going offline", () => {
    expect(shouldRefreshOnReconnect(false, true)).toBe(false);
  });

  it("does not refresh while staying offline", () => {
    expect(shouldRefreshOnReconnect(false, false)).toBe(false);
  });
});

describe("useServerConnection recovery", () => {
  it("refreshes on reconnect", async () => {
    await install();
    await goOfflineThenOnline();
    expect(reload).toHaveBeenCalledOnce();
  });
});
