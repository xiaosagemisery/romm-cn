import { beforeEach, describe, expect, it } from "vitest";
import { effectScope, nextTick, ref } from "vue";
import { usePageTitle } from "./index";

describe("usePageTitle", () => {
  beforeEach(() => {
    document.title = "Route title";
  });

  it("follows the source, falling back to RomM-CN while it is empty", async () => {
    const name = ref<string | null>(null);
    effectScope().run(() => usePageTitle(() => name.value));
    expect(document.title).toBe("RomM-CN");

    name.value = "Chrono Trigger";
    await nextTick();
    expect(document.title).toBe("Chrono Trigger");
  });

  // The router has already titled the next route when the old view unmounts.
  it("leaves the title alone when its scope ends", () => {
    const scope = effectScope();
    scope.run(() => usePageTitle(() => "Chrono Trigger"));
    document.title = "Next route";

    scope.stop();

    expect(document.title).toBe("Next route");
  });
});
