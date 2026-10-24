<script setup lang="ts">
// ScreenshotsSubtab — the Media tab's Screenshots panel: shared library
// screenshots stored in the ROM's `screenshots/` folder (RomFile, category
// SCREENSHOT). Only folder-based multi-file ROMs can host them. Public to every
// user who can see the ROM. Upload → `romApi.uploadScreenshots`. Uses
// RDropzone (CTA when empty, overlay over the grid when filled).
import { RBtn, RDropzone } from "@v2/lib";
import { computed, defineAsyncComponent, ref } from "vue";
import { useI18n } from "vue-i18n";
import romApi from "@/services/api/rom";
import type { DetailedRom } from "@/stores/roms";
import storeUpload from "@/stores/upload";
import type { ScreenshotItem } from "@/v2/components/GameDetails/ScreenshotsTab.vue";
import { useCan } from "@/v2/composables/useCan";
import { useConfirm } from "@/v2/composables/useConfirm";
import { useRomSync } from "@/v2/composables/useRomSync";
import { useSnackbar } from "@/v2/composables/useSnackbar";
import { errorMessage } from "@/v2/utils/errorMessage";

const ScreenshotsTab = defineAsyncComponent(
  () => import("@/v2/components/GameDetails/ScreenshotsTab.vue"),
);

// Previewable image extensions for the per-ROM (RomFile) gallery. Mirrors the
// canonical "Web Images" set.
const IMAGE_EXTENSIONS = new Set([
  "png",
  "jpg",
  "jpeg",
  "webp",
  "gif",
  "bmp",
  "avif",
]);

const props = defineProps<{ rom: DetailedRom }>();

const { t } = useI18n();
const snackbar = useSnackbar();
const confirm = useConfirm();
const { refetchRom } = useRomSync();
const uploadStore = storeUpload();

// Screenshots are written to the ROM itself (roms.write).
const canEditRom = useCan("rom.edit");

// Uploading per-ROM screenshots to a single-file ROM promotes it to a folder
// ROM in place (the backend converts on upload); warn before that happens.
async function confirmFolderConversionIfNeeded(): Promise<boolean> {
  if (!props.rom.has_simple_single_file) return true;
  return confirm({
    title: t("rom.convert-to-folder-title"),
    body: t("rom.convert-to-folder-body"),
    tone: "warning",
  });
}

// ---------- ROM screenshots — RomFile-backed ----------
const romScreenshots = computed<ScreenshotItem[]>(() => {
  const cacheBust = encodeURIComponent(props.rom.updated_at);
  const out: ScreenshotItem[] = [];
  for (const file of props.rom.files ?? []) {
    const rel = file.full_path
      .replace(props.rom.full_path, "")
      .replace(/^\//, "");
    const firstSegment = rel.split("/")[0]?.toLowerCase();
    if (firstSegment !== "screenshots" && firstSegment !== "screenshot") {
      continue;
    }
    const ext = file.file_name.split(".").pop()?.toLowerCase() ?? "";
    if (!IMAGE_EXTENSIONS.has(ext)) continue;
    out.push({
      id: file.id,
      url: `/api/roms/${file.id}/files/content/${encodeURIComponent(
        file.file_name,
      )}?v=${cacheBust}`,
    });
  }
  return out;
});

async function refreshRom() {
  await refetchRom(props.rom.id);
}

// ---------- Upload result toast ----------
function reportUpload(responses: PromiseSettledResult<unknown>[]) {
  const successful = responses.filter((r) => r.status === "fulfilled").length;
  const failed = responses.length - successful;
  if (failed === 0) uploadStore.reset();
  if (successful > 0) {
    snackbar.success(
      failed
        ? t("rom.screenshots-uploaded-with-failed", successful, {
            named: { n: successful, failed },
          })
        : t("rom.screenshots-uploaded-n", successful, {
            named: { n: successful },
          }),
      { icon: "mdi-check-bold", timeout: 3000 },
    );
  } else {
    snackbar.warning(t("rom.no-screenshots-uploaded"), {
      icon: "mdi-close-circle",
      timeout: 5000,
    });
  }
}

// ---------- Upload handlers (wired to RDropzone @files) ----------
const romDz = ref<InstanceType<typeof RDropzone> | null>(null);

async function handleRomFiles(files: File[]) {
  if (files.length === 0) return;
  if (!(await confirmFolderConversionIfNeeded())) return;
  const responses = await romApi.uploadScreenshots({
    romId: props.rom.id,
    filesToUpload: files,
  });
  reportUpload(responses);
  if (responses.some((r) => r.status === "fulfilled")) await refreshRom();
}

// ---------- Delete ----------
async function deleteRomScreenshot(fileId: number) {
  const file = (props.rom.files ?? []).find((f) => f.id === fileId);
  const name = file?.file_name ?? "";
  const ok = await confirm({
    title: t("rom.delete-screenshot-title"),
    body: name
      ? t("rom.delete-screenshot-body-named", { name })
      : t("rom.delete-screenshot-body"),
    confirmText: t("common.delete"),
    tone: "danger",
  });
  if (!ok) return;
  try {
    await romApi.removeScreenshot({ romId: props.rom.id, fileId });
    await refreshRom();
    snackbar.success(t("rom.screenshot-removed"), { icon: "mdi-check-bold" });
  } catch (error: unknown) {
    snackbar.error(
      t("rom.screenshot-remove-failed", { error: errorMessage(error) }),
      { icon: "mdi-close-circle" },
    );
  }
}
</script>

<template>
  <div class="r-v2-shots">
    <!-- ROM screenshots — the whole section drops away for a
         read-only user with nothing to show, since there is neither art to
         look at nor an upload they're allowed to make. -->
    <section
      v-if="canEditRom || romScreenshots.length > 0"
      class="r-v2-shots__section"
    >
      <header class="r-v2-shots__head">
        <div class="r-v2-shots__head-text">
          <h3 class="r-v2-shots__title">
            {{ t("rom.screenshots-section-rom") }}
          </h3>
          <p class="r-v2-shots__subtitle">
            {{ t("rom.screenshots-section-rom-desc") }}
          </p>
        </div>
        <RBtn
          v-if="romScreenshots.length > 0 && canEditRom"
          variant="outlined"
          size="small"
          prepend-icon="mdi-cloud-upload-outline"
          @click="romDz?.open()"
        >
          {{ t("common.upload") }}
        </RBtn>
      </header>

      <RDropzone
        v-if="romScreenshots.length === 0"
        :title="t('rom.screenshots-empty')"
        :hint="t('common.dropzone-hint')"
        :active-title="t('common.dropzone-drag-over')"
        :input-label="t('rom.upload-screenshots')"
        accept="image/*"
        multiple
        @files="handleRomFiles"
      />
      <RDropzone
        v-else
        ref="romDz"
        overlay
        :disabled="!canEditRom"
        :release-label="t('common.dropzone-drag-over')"
        :input-label="t('rom.upload-screenshots')"
        accept="image/*"
        multiple
        @files="handleRomFiles"
      >
        <ScreenshotsTab
          :screenshots="romScreenshots"
          :deletable="canEditRom"
          @delete="deleteRomScreenshot"
        />
      </RDropzone>
    </section>
  </div>
</template>

<style scoped>
.r-v2-shots {
  display: flex;
  flex-direction: column;
  gap: 24px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--r-color-border-strong) transparent;
  padding-right: 4px;
}

.r-v2-shots__section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.r-v2-shots__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.r-v2-shots__title {
  margin: 0;
  font-size: 14px;
  font-weight: var(--r-font-weight-semibold);
  color: var(--r-color-fg);
}
.r-v2-shots__subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--r-color-fg-muted);
}
</style>
