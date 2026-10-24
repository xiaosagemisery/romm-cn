<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import AdminMenu from "@/components/common/Game/AdminMenu.vue";
import romApi from "@/services/api/rom";
import storeAuth from "@/stores/auth";
import storeDownload from "@/stores/download";
import type { SimpleRom } from "@/stores/roms";

const props = defineProps<{ rom: SimpleRom; sizeActionBar: number }>();
const { t } = useI18n();
const emit = defineEmits(["menu-open", "menu-close"]);
const downloadStore = storeDownload();
const auth = storeAuth();

const computedSize = computed(() => {
  return props.sizeActionBar === 1 ? "small" : "x-small";
});

const menuOpen = ref(false);

watch(menuOpen, (val) => {
  emit(val ? "menu-open" : "menu-close");
});
</script>

<template>
  <v-row no-gutters>
    <v-col class="d-flex">
      <v-btn
        class="action-bar-btn-small flex-grow-1"
        :size="computedSize"
        :disabled="downloadStore.value.includes(rom.id) || rom.missing_from_fs"
        icon="mdi-download"
        variant="text"
        rounded="0"
        :aria-label="`${t('rom.download')} ${rom.name}`"
        @click.prevent="romApi.downloadRom({ rom })"
      />
    </v-col>
    <v-col
      v-if="
        auth.scopes.includes('roms.write') ||
        auth.scopes.includes('roms.user.write') ||
        auth.scopes.includes('collections.write')
      "
      class="d-flex"
    >
      <v-menu v-model="menuOpen" location="bottom">
        <template #activator="{ props: menuProps }">
          <v-btn
            class="action-bar-btn-small flex-grow-1"
            :size="computedSize"
            v-bind="menuProps"
            icon="mdi-dots-vertical"
            variant="text"
            rounded="0"
            :aria-label="`${rom.name} admin menu`"
            @click.prevent
          />
        </template>
        <AdminMenu :rom="rom" />
      </v-menu>
    </v-col>
  </v-row>
</template>

<style scoped>
.action-bar-btn-small {
  max-height: 250px;
  width: unset;
}
</style>
