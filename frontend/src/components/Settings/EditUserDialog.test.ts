import { flushPromises, mount } from "@vue/test-utils";
import mitt, { type Emitter } from "mitt";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Events } from "@/types/emitter";
import { userFixture } from "@/utils/user.fixtures";
import EditUserDialog from "./EditUserDialog.vue";

const {
  fetchCatalog,
  fetchUserPermissions,
  getPlatforms,
  updateUserPermissions,
  updateUser,
} = vi.hoisted(() => ({
  fetchCatalog: vi.fn(),
  getPlatforms: vi.fn(),
  fetchUserPermissions: vi.fn(),
  updateUserPermissions: vi.fn(),
  updateUser: vi.fn(),
}));

vi.mock("vue-i18n");
vi.mock("@/services/api/permissions", () => ({
  default: {
    fetchUserPermissions,
    updateUserPermissions,
    fetchCatalog,
  },
}));
vi.mock("@/services/api/user", () => ({ default: { updateUser } }));
vi.mock("@/services/api/platform", () => ({
  default: { getPlatforms },
}));
vi.mock("@/stores/permissionGroups", () => ({
  default: () => ({ groups: [], ensureLoaded: () => Promise.resolve() }),
}));
vi.mock("@/composables/useSnackbar", () => ({
  useSnackbar: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const RDialog = {
  props: { modelValue: { type: Boolean, default: false } },
  template: `<div v-if="modelValue"><slot name="content" /><slot name="footer" /></div>`,
};

// The access section loads behind the avatar; leave it pending by default.
beforeEach(() => {
  vi.resetAllMocks();
  fetchUserPermissions.mockReturnValue(new Promise(() => undefined));
  fetchCatalog.mockReturnValue(new Promise(() => undefined));
  getPlatforms.mockReturnValue(new Promise(() => undefined));
});

async function mountDialog(role: "admin" | "user" = "admin") {
  const emitter: Emitter<Events> = mitt<Events>();
  const wrapper = mount(EditUserDialog, {
    global: {
      provide: { emitter },
      stubs: {
        RDialog,
        RBtn: {
          emits: ["click"],
          template: `<button @click="$emit('click')"><slot /></button>`,
        },
        RIcon: true,
        RSelect: true,
        RSpinner: true,
        RSwitch: true,
        RTextField: true,
        HiddenGamesPicker: true,
        HiddenPlatformsPicker: true,
        OverridesMatrix: true,
      },
    },
  });
  const open = (id = 4) => {
    emitter.emit("showEditUserDialog", userFixture({ id, role }));
    return flushPromises();
  };
  await open();
  return { wrapper, open };
}

async function pick(
  wrapper: Awaited<ReturnType<typeof mountDialog>>["wrapper"],
) {
  const input = wrapper.get<HTMLInputElement>("input[type='file']");
  Object.defineProperty(input.element, "files", {
    value: [new File(["a"], "a.png")],
    configurable: true,
  });
  await input.trigger("change");
}

describe("EditUserDialog avatar preview", () => {
  let urls = 0;

  beforeEach(() => {
    urls = 0;
    vi.spyOn(URL, "createObjectURL").mockImplementation(() => `blob:${++urls}`);
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
  });

  it("previews the picked file and drops it when the dialog reopens", async () => {
    const { wrapper, open } = await mountDialog();
    const avatar = () => wrapper.get("img").attributes("src");
    const saved = avatar();

    await pick(wrapper);
    expect(avatar()).toBe("blob:1");

    await open();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:1");
    expect(avatar()).toBe(saved);
  });

  it("revokes the preview on unmount", async () => {
    const { wrapper } = await mountDialog();
    await pick(wrapper);

    wrapper.unmount();

    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:1");
  });
});
