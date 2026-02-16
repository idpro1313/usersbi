<script setup>
import { ref, computed, watch } from 'vue'
import { sortRows } from '../utils/format'
import { useExport } from '../composables/useExport'
import LoadingSpinner from './LoadingSpinner.vue'

const props = defineProps({
  columns: { type: Array, required: true },
  rows: { type: Array, default: () => [] },
  dateKeys: { type: Object, default: () => ({}) },
  emptyMessage: { type: String, default: 'Нет данных' },
  exportFilename: { type: String, default: '' },
  exportSheet: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})

const sortCol = ref(null)
const sortDir = ref('asc')

const sorted = computed(() => sortRows(props.rows, sortCol.value, sortDir.value, props.dateKeys))

function onSort(key) {
  if (sortCol.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortCol.value = key
    sortDir.value = 'asc'
  }
}

watch(() => props.rows, () => {
  sortCol.value = null
  sortDir.value = 'asc'
})

function sortIcon(key) {
  if (key !== sortCol.value) return ''
  return sortDir.value === 'asc' ? ' \u25B2' : ' \u25BC'
}

const { exportToXLSX } = useExport()

function doExport() {
  if (props.exportFilename) {
    exportToXLSX(props.columns, sorted.value, props.exportFilename, props.exportSheet)
  }
}

defineExpose({ doExport })
</script>

<template>
  <table class="data-table members-table">
    <thead>
      <tr>
        <th v-for="col in columns" :key="col.key" class="sortable" @click="onSort(col.key)">
          {{ col.label }} <span class="sort-icon">{{ sortIcon(col.key) }}</span>
        </th>
      </tr>
    </thead>
    <tbody>
      <tr v-if="loading">
        <td :colspan="columns.length"><LoadingSpinner /></td>
      </tr>
      <tr v-else-if="!sorted.length">
        <td :colspan="columns.length" class="muted-text">{{ emptyMessage }}</td>
      </tr>
      <tr v-else v-for="(row, i) in sorted" :key="i"
        :class="{ 'uz-inactive': row.enabled === 'Нет' || row.uz_active === 'Нет' }">
        <td v-for="col in columns" :key="col.key">{{ row[col.key] ?? '' }}</td>
      </tr>
    </tbody>
  </table>
</template>

<style>
.members-table th {
  position: sticky;
  top: 0;
  background: var(--surface);
  z-index: 4;
  cursor: pointer;
  user-select: none;
}
.members-table th:hover {
  color: var(--accent);
}
.members-table th .sort-icon {
  font-size: 0.65rem;
  color: var(--accent);
}
</style>
