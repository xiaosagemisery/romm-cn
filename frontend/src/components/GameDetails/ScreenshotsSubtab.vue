<script setup lang="ts">
// ScreenshotsSubtab: the Media tab's Screenshots panel. Two sections, each
// screenshot pinnable to the Overview tab:
//
//   * Scraped: screenshots fetched from metadata providers (read-only).
//   * ROM: shared library screenshots stored in the ROM's
//                  `screenshots/` folder (RomFile, category SCREENSHOT). A
//                  single-file ROM is promoted to a folder on upload. Public to
//                  every user who can see the ROM. Upload → `useRomFileUpload`.
//
// The ROM section uses RDropzone (CTA when empty, overlay over the grid when
// filled).
import { computed, defineAsyncComponent, ref } from "vue";
import { useI18n } from "vue-i18n";
import type { ScreenshotItem } from "@/components/GameDetails/ScreenshotsTab.vue";
import { useCan } from "@/composables/useCan";
import { useConfirm } from "@/composables/useConfirm";
import { usePinnedMedia } from "@/composables/usePinnedMedia";
import {
  ROM_UPLOAD_FOLDERS,
  useRomFileUpload,
} from "@/composables/useRomFileUpload";
import { useRomSync } from "@/composables/useRomSync";
import { useSnackbar } from "@/composables/useSnackbar";
import { RBtn, RDropzone } from "@/lib";
import romApi from "@/services/api/rom";
import type { DetailedRom } from "@/stores/roms";
import { errorMessage } from "@/utils/errorMessage";
import { mediaKey } from "@/utils/mediaKeys";
import { romFolderScreenshots } from "@/utils/pinnedMedia";
import { versionedRomFileUrl } from "@/utils/romFiles";

const ScreenshotsTab = defineAsyncComponent(
  () => import("@/components/GameDetails/ScreenshotsTab.vue"),
);

const props = defineProps<{ rom: DetailedRom }>();

const { t } = useI18n();
const snackbar = useSnackbar();
const confirm = useConfirm();
const { refetchRom } = useRomSync();
const { uploadFiles } = useRomFileUpload();

// Screenshots are written to the ROM itself (roms.write).
const canEditRom = useCan("rom.edit");

const { isPinned, togglePin } = usePinnedMedia(() => props.rom);

const scrapedScreenshots = computed<ScreenshotItem[]>(() =>
  (props.rom.merged_screenshots ?? []).map((url) => ({
    url,
    pinKey: mediaKey.scraped(url),
  })),
);

// ---------- ROM (shared) screenshots, RomFile-backed ----------
const romScreenshots = computed<ScreenshotItem[]>(() =>
  romFolderScreenshots(props.rom).map((file) => ({
    id: file.id,
    url: versionedRomFileUrl(file),
    pinKey: mediaKey.file(file.id),
  })),
);

async function refreshRom() {
  await refetchRom(props.rom.id);
}

// ---------- Upload handlers (wired to RDropzone @files) ----------
const romDz = ref<InstanceType<typeof RDropzone> | null>(null);

async function handleRomFiles(files: File[]) {
  await uploadFiles(props.rom, ROM_UPLOAD_FOLDERS.screenshots, files);
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
  <div class="r-shots">
    <section v-if="scrapedScreenshots.length > 0" class="r-shots__section">
      <header class="r-shots__head">
        <div class="r-shots__head-text">
          <h3 class="r-shots__title">
            {{ t("rom.screenshots-section-scraped") }}
          </h3>
          <p class="r-shots__subtitle">
            {{ t("rom.screenshots-section-scraped-desc") }}
          </p>
        </div>
      </header>
      <ScreenshotsTab
        :screenshots="scrapedScreenshots"
        :is-pinned="isPinned"
        @toggle-pin="togglePin"
      />
    </section>

    <!-- ROM (shared) screenshots, the whole section drops away for a
         read-only user with nothing to show, since there is neither art to
         look at nor an upload they're allowed to make. -->
    <section
      v-if="canEditRom || romScreenshots.length > 0"
      class="r-shots__section"
    >
      <header class="r-shots__head">
        <div class="r-shots__head-text">
          <h3 class="r-shots__title">
            {{ t("rom.screenshots-section-rom") }}
          </h3>
          <p class="r-shots__subtitle">
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
          :is-pinned="isPinned"
          @delete="deleteRomScreenshot"
          @toggle-pin="togglePin"
        />
      </RDropzone>
    </section>
  </div>
</template>

<style scoped>
.r-shots {
  display: flex;
  flex-direction: column;
  gap: 24px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--r-color-border-strong) transparent;
}

.r-shots__section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.r-shots__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.r-shots__title {
  margin: 0;
  font-size: 14px;
  font-weight: var(--r-font-weight-semibold);
  color: var(--r-color-fg);
}
.r-shots__subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--r-color-fg-muted);
}
</style>
