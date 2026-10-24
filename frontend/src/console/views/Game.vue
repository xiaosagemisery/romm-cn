<script setup lang="ts">
import {
  computed,
  onMounted,
  onUnmounted,
  ref,
  watch,
  nextTick,
  useTemplateRef,
} from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import BackButton from "@/console/components/BackButton.vue";
import NavigationHint from "@/console/components/NavigationHint.vue";
import NavigationText from "@/console/components/NavigationText.vue";
import ScreenshotLightbox from "@/console/components/ScreenshotLightbox.vue";
import { useInputScope } from "@/console/composables/useInputScope";
import type { InputAction } from "@/console/input/actions";
import { ROUTES } from "@/plugins/router";
import romApi from "@/services/api/rom";
import storeHeartbeat from "@/stores/heartbeat";
import type { DetailedRom } from "@/stores/roms";
import { toBrowserLocale } from "@/utils";
import {
  getMissingCoverImage,
  getUnmatchedCoverImage,
  EXTENSION_REGEX,
} from "@/utils/covers";

type FocusZone = "description" | "details" | "shots" | "lightbox";

type LoadState = "loading" | "error" | "ready";

const heartbeatStore = storeHeartbeat();
const route = useRoute();
const router = useRouter();
const { t, locale } = useI18n();

const rom = ref<DetailedRom | null>(null);
const loadState = ref<LoadState>("loading");
const errorMessage = ref<string | null>(null);

const selectedZone = ref<FocusZone>("details");
const showDescription = ref(false);
const showDetails = ref(false);
const showLightbox = ref(false);
const selectedShot = ref(0);
const screenshotsRef = useTemplateRef<HTMLDivElement>("screenshots-ref");
const screenshotELs = ref<HTMLButtonElement[]>([]);
const descriptionOverlayRef = useTemplateRef<HTMLDivElement>(
  "description-overlay-ref",
);
const detailsOverlayRef = useTemplateRef<HTMLDivElement>("details-overlay-ref");

const releaseDate = computed(() => {
  if (!rom.value?.metadatum.first_release_date) return null;
  return new Date(
    Number(rom.value.metadatum.first_release_date),
  ).toLocaleDateString(toBrowserLocale(locale.value), {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
});

const companies = computed(() => rom.value?.metadatum.companies ?? []);
const genres = computed(() => rom.value?.metadatum.genres ?? []);
const regions = computed(() => rom.value?.regions ?? []);

// Only return merged screenshots from IGDB/external sources, exclude user screenshots
const screenshotUrls = computed(() => {
  return rom.value?.merged_screenshots || [];
});

const fallbackCoverImage = computed(() =>
  rom.value?.igdb_id || rom.value?.moby_id || rom.value?.ss_id
    ? getMissingCoverImage(rom.value?.name || rom.value?.slug || "")
    : getUnmatchedCoverImage(rom.value?.name || rom.value?.slug || ""),
);

const isWebpEnabled = computed(
  () => heartbeatStore.value.TASKS?.ENABLE_SCHEDULED_CONVERT_IMAGES_TO_WEBP,
);

const largeCover = computed(() => {
  const pathCoverLarge = isWebpEnabled.value
    ? rom.value?.path_cover_large?.replace(EXTENSION_REGEX, ".webp")
    : rom.value?.path_cover_large;
  return pathCoverLarge || "";
});

const smallCover = computed(() => {
  const pathCoverSmall = isWebpEnabled.value
    ? rom.value?.path_cover_small?.replace(EXTENSION_REGEX, ".webp")
    : rom.value?.path_cover_small;
  return pathCoverSmall || "";
});

function openDescription() {
  showDescription.value = true;
}

function openDetails() {
  showDetails.value = true;
}

function goBackToPlatform() {
  const qp = route.query as Record<string, string | undefined>;
  if (qp.collection) {
    router.push({
      name: ROUTES.CONSOLE_COLLECTION,
      params: { id: qp.collection },
    });
    return;
  }

  if (qp.smartCollection) {
    router.push({
      name: ROUTES.CONSOLE_SMART_COLLECTION,
      params: { id: qp.smartCollection },
    });
    return;
  }

  if (qp.virtualCollection) {
    router.push({
      name: ROUTES.CONSOLE_VIRTUAL_COLLECTION,
      params: { id: qp.virtualCollection },
    });
    return;
  }

  if (rom.value?.platform_id) {
    router.push({
      name: ROUTES.CONSOLE_PLATFORM,
      params: { id: rom.value.platform_id },
    });
  } else {
    router.push({ name: ROUTES.CONSOLE_HOME });
  }
}

const { subscribe } = useInputScope();
function handleAction(action: InputAction): boolean {
  // Lightbox handling
  if (showLightbox.value) {
    if (action === "moveRight") {
      selectedShot.value =
        (selectedShot.value + 1) % Math.max(1, screenshotUrls.value.length);
      return true;
    }
    if (action === "moveLeft") {
      selectedShot.value =
        (selectedShot.value - 1 + Math.max(1, screenshotUrls.value.length)) %
        Math.max(1, screenshotUrls.value.length);
      return true;
    }
    if (action === "back") {
      showLightbox.value = false;
      return true;
    }
    return false;
  }

  // Modal handling (description/details)
  if (showDescription.value || showDetails.value) {
    if (action === "back") {
      showDescription.value = false;
      showDetails.value = false;
      return true;
    }
    // if (action === "moveUp" || action === "moveDown") {
    //   const body = document.querySelector(".modal-body") as HTMLElement | null;
    //   if (!body) return true;
    //   const amt = 40;
    //   if (action === "moveUp") body.scrollTop -= amt;
    //   else body.scrollTop += amt;
    //   return true;
    // }
    return false;
  }

  // Main focus navigation
  switch (selectedZone.value) {
    case "description":
      if (action === "moveDown") {
        selectedZone.value = "details";
        return true;
      }
      if (action === "confirm") {
        openDescription();
        return true;
      }
      if (action === "back") {
        goBackToPlatform();
        return true;
      }
      return false;
    case "details":
      if (action === "moveUp" && rom.value?.summary) {
        selectedZone.value = "description";
        return true;
      }
      if (action === "moveDown") {
        if (screenshotUrls.value.length) {
          selectedZone.value = "shots";
          selectedShot.value = 0;
          nextTick(scrollShotsToSelected);
        }
        return true;
      }
      if (action === "confirm") {
        openDetails();
        return true;
      }
      if (action === "back") {
        goBackToPlatform();
        return true;
      }
      return false;
    case "shots":
      if (action === "moveUp") {
        selectedZone.value = "details";
        return true;
      }
      if (action === "moveRight") {
        if (screenshotUrls.value.length) {
          selectedShot.value =
            (selectedShot.value + 1) % screenshotUrls.value.length;
          nextTick(scrollShotsToSelected);
        }
        return true;
      }
      if (action === "moveLeft") {
        if (screenshotUrls.value.length) {
          selectedShot.value =
            (selectedShot.value - 1 + screenshotUrls.value.length) %
            screenshotUrls.value.length;
          nextTick(scrollShotsToSelected);
        }
        return true;
      }
      if (action === "confirm") {
        showLightbox.value = true;
        return true;
      }
      if (action === "back") {
        goBackToPlatform();
        return true;
      }
      return false;
    default:
      return false;
  }
}

function registerShotEl(el: HTMLButtonElement | null, idx: number) {
  if (!el) return;
  screenshotELs.value[idx] = el;
}

function scrollShotsToSelected() {
  const container = screenshotsRef.value;
  const el = screenshotELs.value[selectedShot.value];
  if (!container || !el) return;
  const cr = container.getBoundingClientRect();
  const er = el.getBoundingClientRect();
  const desiredLeft = el.offsetLeft - cr.width / 2 + er.width / 2;
  container.scrollTo({ left: desiredLeft, behavior: "smooth" });
}

function openLightbox(index: number) {
  selectedShot.value = index;
  showLightbox.value = true;
}

onMounted(async () => {
  try {
    const { data: romData } = await romApi.getRom({
      romId: parseInt(route.params.rom as string),
    });
    if (romData.files.length === 0) {
      loadState.value = "error";
      errorMessage.value = "No game files found";
      throw new Error("No game files found");
    }
    rom.value = romData;
  } catch (err) {
    loadState.value = "error";
    errorMessage.value =
      err instanceof Error ? err.message : "Failed to load game";
  } finally {
    loadState.value = "ready";
  }
  selectedZone.value = rom.value?.summary ? "description" : "details";
  off = subscribe(handleAction);
});

// Focus overlays when opened so Esc works even if window handlers exist
watch(showDescription, (v) => {
  if (v) nextTick(() => descriptionOverlayRef.value?.focus?.());
});
watch(showDetails, (v) => {
  if (v) nextTick(() => detailsOverlayRef.value?.focus?.());
});

let off: (() => void) | null = null;

onUnmounted(() => {
  off?.();
  off = null;
});
</script>

<template>
  <div class="w-full h-screen flex flex-col overflow-hidden cursor-none">
    <template v-if="!rom">
      <!-- States -->
      <div
        v-if="loadState === 'loading'"
        class="m-auto text-lg"
        :style="{ color: 'var(--console-loading-text)' }"
      >
        Loading…
      </div>
      <div v-else-if="loadState === 'error'" class="m-auto text-red-400 p-4">
        {{ errorMessage }}
      </div>
    </template>
    <template v-else>
      <!-- Main content -->
      <div
        class="relative w-full h-full overflow-y-auto overflow-x-hidden pb-28 md:pb-32"
      >
        <BackButton :on-back="goBackToPlatform" />

        <!-- Backdrop -->
        <div class="absolute inset-0 z-0 overflow-hidden">
          <img
            :src="largeCover || fallbackCoverImage"
            :lazy-src="smallCover || fallbackCoverImage"
            :alt="`${rom.name} background`"
            class="w-full h-full object-cover blur-xl brightness-75 saturate-[1.25] contrast-110 scale-110"
          />
        </div>
        <div
          class="absolute inset-0 bg-gradient-to-b from-black/70 via-black/20 to-black/80 pointer-events-none z-0"
        />

        <div class="relative z-10">
          <!-- HERO -->
          <section class="relative min-h-[65vh] flex items-end">
            <div
              class="w-full max-w-[1400px] mx-auto px-8 md:px-12 lg:px-16 pb-10 flex flex-col md:flex-row gap-8 md:gap-12 items-end"
            >
              <!-- Poster -->
              <div class="shrink-0 self-center md:self-end">
                <v-img
                  :src="largeCover || fallbackCoverImage"
                  :lazy-src="smallCover || fallbackCoverImage"
                  :alt="`${rom.name} cover`"
                  class="w-[220px] md:w-[260px] h-auto rounded-2xl shadow-[0_10px_40px_rgba(0,0,0,0.8),_0_0_0_1px_rgba(255,255,255,0.1)]"
                />
              </div>

              <!-- Content -->
              <div class="flex-1 max-w-[900px]">
                <h1
                  class="text-4xl md:text-5xl font-extrabold mb-3 drop-shadow"
                  :style="{ color: 'var(--console-game-title-text)' }"
                >
                  {{ rom.name }}
                </h1>

                <div
                  class="flex flex-wrap items-center gap-2 md:gap-4 mb-5 text-sm"
                >
                  <span
                    class="bg-[var(--console-game-platform-badge-bg)] px-3 py-1 rounded text-xs font-semibold"
                    :style="{
                      color: 'var(--console-game-platform-badge-text)',
                    }"
                  >
                    {{
                      rom.platform_display_name ||
                      (rom.platform_slug || "RETRO")?.toString().toUpperCase()
                    }}
                  </span>
                  <span
                    v-if="releaseDate"
                    class="font-medium"
                    :style="{ color: 'var(--console-game-metadata-text)' }"
                  >
                    {{ releaseDate }}
                  </span>
                  <span
                    v-if="regions.length"
                    class="font-medium"
                    :style="{ color: 'var(--console-game-metadata-text)' }"
                  >
                    {{ regions[0] }}
                  </span>
                  <span
                    v-if="genres.length"
                    class="font-medium truncate max-w-[50%]"
                    :style="{ color: 'var(--console-game-metadata-text)' }"
                  >
                    {{ genres.join(", ") }}
                  </span>
                </div>

                <div
                  v-if="rom.summary"
                  class="text-base leading-6 mb-6 line-clamp-3 cursor-pointer"
                  :style="{ color: 'var(--console-game-description-text)' }"
                  :class="{
                    'ring-2 ring-white/30 rounded-md px-1 -translate-y-0.5':
                      selectedZone === 'description',
                  }"
                  tabindex="0"
                  @click="openDescription()"
                  @keydown.enter="openDescription()"
                >
                  {{ rom.summary }}
                </div>

                <div class="flex gap-3 md:gap-4 mb-2">
                  <button
                    class="px-5 md:px-6 py-3 md:py-4 rounded-lg font-semibold transition-all"
                    style="
                      background-color: var(
                        --console-game-details-button-bg
                      ) !important;
                      color: var(--console-game-details-button-text) !important;
                      border: none !important;
                    "
                    :class="{
                      'scale-105 shadow-[0_8px_28px_rgba(0,0,0,0.35),_0_0_0_2px_var(--console-game-details-button-focus-border),_0_0_16px_var(--console-game-details-button-focus-border)]':
                        selectedZone === 'details',
                    }"
                    @click="openDetails()"
                  >
                    {{ t("console.game-detail") }}
                  </button>
                </div>
              </div>
            </div>
          </section>

          <!-- SCREENSHOTS -->
          <section
            v-if="screenshotUrls.length"
            :style="{
              backgroundColor: 'var(--console-game-screenshot-panel-bg)',
              borderTopColor: 'var(--console-game-screenshot-panel-border)',
            }"
            class="fixed bottom-0 inset-x-0 z-30 py-3 md:py-4 backdrop-blur-md border-t"
          >
            <div class="w-full max-w-[1400px] mx-auto px-8 md:px-12 lg:px-16">
              <h3
                class="text-xs md:text-sm font-semibold uppercase tracking-wide"
                :style="{ color: 'var(--console-game-section-header)' }"
              >
                {{ t("console.screenshots") }}
              </h3>
              <div
                ref="screenshots-ref"
                class="w-full overflow-x-auto overflow-y-hidden no-scrollbar"
              >
                <div
                  class="flex items-center gap-3 md:gap-4 py-6 px-2 min-w-max"
                >
                  <button
                    v-for="(src, idx) in screenshotUrls"
                    :key="`${idx}-${src}`"
                    :ref="
                      (el) =>
                        registerShotEl(el as HTMLButtonElement | null, idx)
                    "
                    class="relative h-32 md:h-40 aspect-[16/9] rounded-md flex-none overflow-hidden cursor-pointer transition-all duration-200 border-2"
                    :class="{
                      'scale-[1.03] shadow-[0_8px_28px_rgba(0,0,0,0.35),_0_0_0_2px_var(--console-game-screenshot-thumbnail-focus-border),_0_0_16px_var(--console-game-screenshot-thumbnail-focus-border)]':
                        selectedZone === 'shots' && selectedShot === idx,
                    }"
                    tabindex="0"
                    @click="openLightbox(idx)"
                    @focus="selectedShot = idx"
                    @keydown.enter.prevent="openLightbox(idx)"
                  >
                    <v-img
                      cover
                      :src="src"
                      :alt="`${rom.name} screenshot ${idx + 1}`"
                      class="w-full h-full object-cover select-none"
                    >
                      <template #placeholder>
                        <div
                          :style="{
                            borderColor:
                              'var(--console-game-screenshot-thumbnail-border)',
                          }"
                          class="w-full h-full overflow-hidden border-2"
                        >
                          <v-icon>mdi-image-outline</v-icon>
                        </div>
                      </template>
                      <template #error>
                        <div
                          :style="{
                            borderColor:
                              'var(--console-game-screenshot-thumbnail-border)',
                          }"
                          class="w-full h-full overflow-hidden border-2"
                        >
                          <v-icon>mdi-image-outline</v-icon>
                        </div>
                      </template>
                    </v-img>
                  </button>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>

      <!-- Description Modal -->
      <v-dialog
        ref="description-overlay-ref"
        :model-value="showDescription"
        :width="1000"
        scroll-strategy="block"
        no-click-animation
        persistent
        z-index="9999"
        scrim="black"
        class="lightbox-dialog"
      >
        <template #default>
          <div class="lightbox-header">
            <h2 class="text-h6" :style="{ color: 'var(--console-modal-text)' }">
              Description
            </h2>
            <v-btn
              icon="mdi-close"
              aria-label="Close"
              size="small"
              @click="showDescription = false"
            />
          </div>
          <div class="pa-4" :style="{ color: 'var(--console-modal-text)' }">
            <p>{{ rom.summary }}</p>
          </div>
          <div class="lightbox-footer pa-4">
            <NavigationText
              :show-navigation="true"
              :show-select="false"
              :show-back="true"
              :show-toggle-favorite="false"
              :show-menu="false"
              :is-modal="true"
            />
          </div>
        </template>
      </v-dialog>

      <!-- Details Modal -->
      <v-dialog
        ref="details-overlay-ref"
        :model-value="showDetails"
        :width="1000"
        scroll-strategy="block"
        no-click-animation
        persistent
        z-index="9999"
        scrim="black"
        class="lightbox-dialog"
      >
        <template #default>
          <div class="lightbox-header">
            <h2 class="text-h6" :style="{ color: 'var(--console-modal-text)' }">
              {{ t("console.game-detail") }}
            </h2>
            <v-btn
              icon="mdi-close"
              aria-label="Close"
              size="small"
              @click="showDetails = false"
            />
          </div>
          <div class="pa-4">
            <div
              class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 md:gap-6"
            >
              <div
                v-if="companies.length"
                :style="{
                  backgroundColor: 'var(--console-modal-tile-bg)',
                  borderColor: 'var(--console-modal-tile-border)',
                }"
                class="rounded-md pa-2 md:p-5 border"
              >
                <div
                  class="text-xs font-semibold mb-1 uppercase tracking-wide"
                  :style="{ color: 'var(--console-modal-text-secondary)' }"
                >
                  Companies
                </div>
                <div
                  class="text-sm md:text-base leading-6 break-words"
                  :style="{ color: 'var(--console-modal-text)' }"
                >
                  {{ companies.join(", ") }}
                </div>
              </div>
              <div
                v-if="genres.length"
                :style="{
                  backgroundColor: 'var(--console-modal-tile-bg)',
                  borderColor: 'var(--console-modal-tile-border)',
                }"
                class="rounded-md pa-2 md:p-5 border"
              >
                <div
                  class="text-xs font-semibold mb-1 uppercase tracking-wide"
                  :style="{ color: 'var(--console-modal-text-secondary)' }"
                >
                  Genres
                </div>
                <div
                  class="text-sm md:text-base leading-6 break-words"
                  :style="{ color: 'var(--console-modal-text)' }"
                >
                  {{ genres.join(", ") }}
                </div>
              </div>
              <div
                v-if="releaseDate"
                :style="{
                  backgroundColor: 'var(--console-modal-tile-bg)',
                  borderColor: 'var(--console-modal-tile-border)',
                }"
                class="rounded-md pa-2 md:p-5 border"
              >
                <div
                  class="text-xs font-semibold mb-1 uppercase tracking-wide"
                  :style="{ color: 'var(--console-modal-text-secondary)' }"
                >
                  Release Date
                </div>
                <div
                  class="text-sm md:text-base leading-6 break-words"
                  :style="{ color: 'var(--console-modal-text)' }"
                >
                  {{ releaseDate }}
                </div>
              </div>
              <div
                v-if="regions.length"
                :style="{
                  backgroundColor: 'var(--console-modal-tile-bg)',
                  borderColor: 'var(--console-modal-tile-border)',
                }"
                class="rounded-md pa-2 md:p-5 border"
              >
                <div
                  class="text-xs font-semibold mb-1 uppercase tracking-wide"
                  :style="{ color: 'var(--console-modal-text-secondary)' }"
                >
                  Regions
                </div>
                <div
                  class="text-sm md:text-base leading-6 break-words"
                  :style="{ color: 'var(--console-modal-text)' }"
                >
                  {{ regions.join(", ") }}
                </div>
              </div>
              <div
                :style="{
                  backgroundColor: 'var(--console-modal-tile-bg)',
                  borderColor: 'var(--console-modal-tile-border)',
                }"
                class="rounded-md pa-2 md:p-5 border"
              >
                <div
                  class="text-xs font-semibold mb-1 uppercase tracking-wide"
                  :style="{ color: 'var(--console-modal-text-secondary)' }"
                >
                  {{ t("console.detail-size") }}
                </div>
                <div
                  class="text-sm md:text-base leading-6 break-words"
                  :style="{ color: 'var(--console-modal-text)' }"
                >
                  {{ Math.round(rom.files[0].file_size_bytes / 1024) }}
                  KB
                </div>
              </div>
              <div
                :style="{
                  backgroundColor: 'var(--console-modal-tile-bg)',
                  borderColor: 'var(--console-modal-tile-border)',
                }"
                class="rounded-md pa-2 md:p-5 border"
              >
                <div
                  class="text-xs font-semibold mb-1 uppercase tracking-wide"
                  :style="{ color: 'var(--console-modal-text-secondary)' }"
                >
                  {{ t("console.detail-file") }}
                </div>
                <div
                  class="text-sm md:text-base leading-6 break-words"
                  :style="{ color: 'var(--console-modal-text)' }"
                >
                  {{ rom.files[0].file_name || "Unknown" }}
                </div>
              </div>
            </div>
          </div>
          <div class="lightbox-footer pa-4">
            <NavigationText
              :show-navigation="false"
              :show-select="false"
              :show-back="true"
              :show-toggle-favorite="false"
              :show-menu="false"
              :is-modal="true"
            />
          </div>
        </template>
      </v-dialog>

      <ScreenshotLightbox
        v-if="showLightbox"
        :urls="screenshotUrls"
        :start-index="selectedShot"
        @close="showLightbox = false"
      />

      <NavigationHint
        :show-navigation="true"
        :show-select="true"
        :show-back="true"
        :show-toggle-favorite="false"
        :show-menu="false"
      />
    </template>
  </div>
</template>

<style>
.lightbox-dialog {
  backdrop-filter: blur(10px);
  cursor: none;
}

.lightbox-dialog .v-overlay__content {
  max-height: 80vh;
  border: 1px solid var(--console-modal-border);
  background-color: var(--console-modal-bg);
  border-radius: 16px;
  animation: slideUp 0.3s ease;
  cursor: none;
}

.lightbox-dialog * {
  cursor: none !important;
}

.lightbox-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  background-color: var(--console-modal-header-bg);
  border-bottom: 1px solid var(--console-modal-border-secondary);
  border-top-left-radius: 16px;
  border-top-right-radius: 16px;
}

.lightbox-footer {
  border-top: 1px solid var(--console-modal-border-secondary);
  background-color: var(--console-modal-header-bg);
  border-bottom-left-radius: 16px;
  border-bottom-right-radius: 16px;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
