<script setup lang="ts">
// LibraryStatsWidget: counts overview of what's in RomM.
//
// Two display modes (driven by `libraryStatsMode` UI setting):
//   • compact  - games / platforms / favorites (3 rows, mock parity)
//   • extended - adds disk size. The card grows wider (not taller)
//                and renders the rows in a 2-column grid so every
//                stat fits inside the rail's shared height.
//
// Source: GET /stats (counts) + the favorite collection's rom_ids
// length (already loaded by the collections store on app boot).
import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { StatsReturn } from "@/__generated__/models/StatsReturn";
import { useFetchState } from "@/composables/useFetchState";
import { RIcon } from "@/lib";
import api from "@/services/api";
import storeCollections from "@/stores/collections";
import { formatBytes } from "@/utils";
import WidgetCard from "./WidgetCard.vue";

defineOptions({ inheritAttrs: false });

const props = withDefaults(
  defineProps<{
    mode?: "compact" | "extended";
  }>(),
  { mode: "compact" },
);

const { t } = useI18n();
const collectionsStore = storeCollections();
const { favoriteCollection } = storeToRefs(collectionsStore);

const { state: stats, isLoading: loading } = useFetchState<StatsReturn | null>(
  () => api.get<StatsReturn>("/stats").then(({ data }) => data),
  null,
);

const favoritesCount = computed(
  () => favoriteCollection.value?.rom_ids?.length ?? 0,
);

interface Row {
  icon: string;
  label: string;
  value: string;
}

const allRows = computed<Row[]>(() => {
  const s = stats.value;
  if (!s) return [];
  const base: Row[] = [
    {
      icon: "mdi-disc",
      label: t("common.games"),
      value: (s.ROMS ?? 0).toLocaleString(),
    },
    {
      icon: "mdi-controller",
      label: t("common.platforms"),
      value: (s.PLATFORMS ?? 0).toLocaleString(),
    },
    {
      icon: "mdi-heart",
      label: t("home.widget-library-favorites"),
      value: favoritesCount.value.toLocaleString(),
    },
  ];
  if (props.mode !== "extended") return base;
  return [
    ...base,
    {
      icon: "mdi-harddisk",
      label: t("common.size-on-disk"),
      value: formatBytes(s.TOTAL_FILESIZE_BYTES ?? 0, 1),
    },
  ];
});
</script>

<template>
  <WidgetCard
    :title="t('home.widget-library-stats')"
    :loading="loading"
    :width="mode === 'extended' ? 'max-content' : '220px'"
  >
    <div
      class="r-widget-lib__stats"
      :class="{ 'r-widget-lib__stats--multi-col': mode === 'extended' }"
    >
      <div v-for="row in allRows" :key="row.label" class="r-widget-lib__row">
        <span class="r-widget-lib__label">
          <RIcon :icon="row.icon" size="12" />
          {{ row.label }}
        </span>
        <span class="r-widget-lib__val">{{ row.value }}</span>
      </div>
    </div>
  </WidgetCard>
</template>

<style scoped>
.r-widget-lib__stats {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

/* Columns size to their content (paired with the card's `max-content`
   width) so labels never get clipped by large values. */
.r-widget-lib__stats--multi-col {
  display: grid;
  grid-template-columns: repeat(2, auto);
  column-gap: 20px;
  row-gap: 6px;
}

.r-widget-lib__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12.5px;
  min-width: 0;
}

.r-widget-lib__label {
  color: var(--r-color-fg-muted);
  display: flex;
  align-items: center;
  gap: 5px;
  /* Grow to fill the (content-sized) column so the value stays pinned
     to the column's right edge across every row. */
  flex: 1;
  min-width: 0;
  white-space: nowrap;
}

.r-widget-lib__val {
  font-weight: var(--r-font-weight-bold);
  color: var(--r-color-fg);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
</style>
