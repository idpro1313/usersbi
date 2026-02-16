<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { fetchJSON } from '../api'
import { useExport } from '../composables/useExport'
import { escapeHtml, dateSortKey } from '../utils/format'

const COLUMNS = [
  { key: 'source',             label: 'Источник' },
  { key: 'account_type',       label: 'Тип УЗ' },
  { key: 'login',              label: 'Логин' },
  { key: 'domain',             label: 'Домен' },
  { key: 'uz_active',          label: 'УЗ активна' },
  { key: 'password_last_set',  label: 'Пароль' },
  { key: 'must_change_password', label: 'Треб. смена' },
  { key: 'account_expires',    label: 'Срок УЗ' },
  { key: 'staff_uuid',         label: 'StaffUUID' },
  { key: 'mfa_enabled',        label: 'MFA' },
  { key: 'mfa_created_at',     label: 'MFA с' },
  { key: 'mfa_last_login',     label: 'Вход MFA' },
  { key: 'mfa_authenticators', label: 'Способ' },
  { key: 'fio_ad',             label: 'ФИО (AD)' },
  { key: 'fio_mfa',            label: 'ФИО (MFA)' },
  { key: 'fio_people',         label: 'ФИО (Кадры)' },
  { key: 'email_ad',           label: 'Email (AD)' },
  { key: 'email_mfa',          label: 'Email (MFA)' },
  { key: 'email_people',       label: 'Email (Кадры)' },
  { key: 'phone_ad',           label: 'Тел. (AD)' },
  { key: 'mobile_ad',          label: 'Моб. (AD)' },
  { key: 'phone_mfa',          label: 'Тел. (MFA)' },
  { key: 'phone_people',       label: 'Тел. (Кадры)' },
  { key: 'discrepancies',      label: 'Расхождения' },
]

const TOTAL_COLS = COLUMNS.length + 1
const DATE_KEYS = { password_last_set: true, account_expires: true, mfa_created_at: true, mfa_last_login: true }
const CHUNK = 200

const cachedRows = ref([])
const filteredRows = ref([])
const renderedCount = ref(0)
const sortCol = ref(null)
const sortDir = ref('asc')
const colFilters = ref({})
const globalFilter = ref('')
const loading = ref(true)

const tableContainer = ref(null)
const searchCache = new Map()

function getSearchString(row) {
  let cached = searchCache.get(row)
  if (cached !== undefined) return cached
  const parts = []
  for (const col of COLUMNS) {
    const v = row[col.key]
    if (v != null && v !== '') parts.push(String(v))
  }
  cached = parts.join(' ').toLowerCase()
  searchCache.set(row, cached)
  return cached
}

function rowClass(source) {
  if (!source) return ''
  if (source.indexOf('AD') === 0) return 'source-ad'
  if (source === 'MFA') return 'source-mfa'
  if (source === 'Кадры') return 'source-people'
  return ''
}

function rowsFilteredExcept(excludeKey) {
  const gf = globalFilter.value.trim().toLowerCase()
  let rows = cachedRows.value
  if (gf) rows = rows.filter(row => getSearchString(row).indexOf(gf) !== -1)
  for (const col of COLUMNS) {
    if (col.key === excludeKey) continue
    const f = colFilters.value[col.key] || ''
    if (!f) continue
    if (f === '__EMPTY__') rows = rows.filter(row => { const v = row[col.key]; return v == null || v === '' })
    else if (f === '__NOT_EMPTY__') rows = rows.filter(row => { const v = row[col.key]; return v != null && v !== '' })
    else rows = rows.filter(row => String(row[col.key] ?? '') === f)
  }
  return rows
}

function filterOptions(key) {
  const available = rowsFilteredExcept(key)
  const vals = {}
  let hasEmpty = false
  for (const row of available) {
    const v = row[key]
    if (v == null || v === '') { hasEmpty = true; continue }
    vals[String(v)] = true
  }
  const isDate = !!DATE_KEYS[key]
  const sorted = Object.keys(vals).sort((a, b) => {
    const aStub = a.indexOf('НЕТ') === 0 ? 0 : 1
    const bStub = b.indexOf('НЕТ') === 0 ? 0 : 1
    if (aStub !== bStub) return aStub - bStub
    if (isDate) { return dateSortKey(a) < dateSortKey(b) ? -1 : dateSortKey(a) > dateSortKey(b) ? 1 : 0 }
    return a.localeCompare(b, 'ru')
  })
  const opts = [{ value: '', label: '— все (' + (sorted.length + (hasEmpty ? 1 : 0)) + ')' }]
  if (hasEmpty) opts.push({ value: '__EMPTY__', label: 'ПУСТО' })
  if (hasEmpty && sorted.length) opts.push({ value: '__NOT_EMPTY__', label: 'НЕ ПУСТО' })
  for (const v of sorted) opts.push({ value: v, label: v })
  return opts
}

function applyFilters() {
  const gf = globalFilter.value.trim().toLowerCase()
  let rows = cachedRows.value
  if (gf) rows = rows.filter(row => getSearchString(row).indexOf(gf) !== -1)
  for (const col of COLUMNS) {
    const f = colFilters.value[col.key] || ''
    if (!f) continue
    if (f === '__EMPTY__') rows = rows.filter(row => { const v = row[col.key]; return v == null || v === '' })
    else if (f === '__NOT_EMPTY__') rows = rows.filter(row => { const v = row[col.key]; return v != null && v !== '' })
    else rows = rows.filter(row => String(row[col.key] ?? '') === f)
  }
  if (sortCol.value) {
    const dir = sortDir.value === 'asc' ? 1 : -1
    const isDate = !!DATE_KEYS[sortCol.value]
    const col = sortCol.value
    rows = rows.slice().sort((a, b) => {
      let va = a[col] == null ? '' : String(a[col])
      let vb = b[col] == null ? '' : String(b[col])
      if (isDate) { va = dateSortKey(va); vb = dateSortKey(vb) }
      else { va = va.toLowerCase(); vb = vb.toLowerCase() }
      if (va < vb) return -1 * dir
      if (va > vb) return 1 * dir
      return 0
    })
  }
  filteredRows.value = rows
  renderedCount.value = 0
  nextTick(renderChunk)
}

function renderChunk() {
  const end = Math.min(renderedCount.value + CHUNK, filteredRows.value.length)
  renderedCount.value = end
}

function onSort(key) {
  if (sortCol.value === key) sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  else { sortCol.value = key; sortDir.value = 'asc' }
  applyFilters()
}

function sortIcon(key) {
  if (key !== sortCol.value) return ''
  return sortDir.value === 'asc' ? ' \u25B2' : ' \u25BC'
}

function onColFilter(key, val) {
  colFilters.value[key] = val
  applyFilters()
}

function resetFilters() {
  colFilters.value = {}
  sortCol.value = null
  sortDir.value = 'asc'
  globalFilter.value = ''
  applyFilters()
}

const footerText = computed(() => {
  const total = cachedRows.value.length
  const filtered = filteredRows.value.length
  const shown = renderedCount.value
  const parts = ['Всего: ' + total]
  if (filtered < total) parts.push('найдено: ' + filtered)
  if (shown < filtered) parts.push('показано: ' + shown)
  return parts.join(' · ')
})

const visibleRows = computed(() => filteredRows.value.slice(0, renderedCount.value))

let scrollTimeout = null
function onScroll() {
  if (scrollTimeout) return
  scrollTimeout = setTimeout(() => {
    scrollTimeout = null
    if (renderedCount.value >= filteredRows.value.length) return
    const el = tableContainer.value
    if (el && el.scrollTop + el.clientHeight >= el.scrollHeight - 300) {
      renderChunk()
    }
  }, 50)
}

const { exportToXLSX } = useExport()
function doExport() {
  const data = filteredRows.value.length ? filteredRows.value : cachedRows.value
  exportToXLSX(COLUMNS, data, 'Svodka_AD_MFA_People.xlsx', 'Сводная')
}

onMounted(async () => {
  try {
    const data = await fetchJSON('/api/consolidated')
    cachedRows.value = data.rows || []
    searchCache.clear()
    applyFilters()
  } catch (e) {
    // error displayed via empty rows
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <!-- Toolbar -->
  <div class="table-toolbar">
    <h2>Сводная таблица</h2>
    <div class="toolbar-right">
      <span class="table-info">{{ footerText }}</span>
      <div class="filter-wrap">
        <input type="text" v-model="globalFilter" @input="applyFilters" placeholder="Поиск…">
      </div>
      <button type="button" class="btn-icon" title="Сбросить фильтры" @click="resetFilters">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
        </svg>
      </button>
      <button type="button" class="btn-icon btn-export" title="Выгрузить XLSX" @click="doExport">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
      </button>
    </div>
  </div>

  <!-- Table -->
  <div class="table-container" ref="tableContainer" @scroll="onScroll">
    <table class="data-table">
      <thead>
        <!-- Labels row -->
        <tr class="thead-labels">
          <th class="col-num">#</th>
          <th v-for="col in COLUMNS" :key="col.key" class="sortable" :data-key="col.key"
            :class="{ 'filter-active': !!colFilters[col.key] }" @click="onSort(col.key)">
            {{ col.label }} <span class="sort-icon">{{ sortIcon(col.key) }}</span>
          </th>
        </tr>
        <!-- Filters row -->
        <tr class="thead-filters">
          <th class="col-num"></th>
          <th v-for="col in COLUMNS" :key="col.key">
            <select class="col-filter" :value="colFilters[col.key] || ''"
              @change="onColFilter(col.key, ($event.target).value)">
              <option v-for="opt in filterOptions(col.key)" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading"><td :colspan="TOTAL_COLS" class="muted-text">Загрузка…</td></tr>
        <tr v-else-if="!visibleRows.length"><td :colspan="TOTAL_COLS" class="muted-text">Нет данных</td></tr>
        <tr v-else v-for="(row, idx) in visibleRows" :key="idx"
          :class="[
            rowClass(row.source),
            row.uz_active === 'Нет' ? 'uz-inactive' : '',
            row.account_type === 'Service' ? 'uz-service' : '',
            row.account_type === 'Contractor' ? 'uz-contractor' : '',
          ]">
          <td class="col-num">{{ idx + 1 }}</td>
          <td v-for="col in COLUMNS" :key="col.key"
            :class="{ discrepancy: col.key === 'discrepancies' }">
            {{ row[col.key] ?? '' }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
