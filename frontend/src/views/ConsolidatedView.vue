<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { fetchJSON } from '../api'
import { useExport } from '../composables/useExport'
import { dateSortKey, debounce } from '../utils/format'
import LoadingSpinner from '../components/LoadingSpinner.vue'

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

const DATE_KEYS = { password_last_set: true, account_expires: true, mfa_created_at: true, mfa_last_login: true }
const CHUNK = 200
const COL_STORAGE_KEY = 'consolidated-hidden-cols'

const hiddenCols = ref(new Set(JSON.parse(localStorage.getItem(COL_STORAGE_KEY) || '[]')))
const showColManager = ref(false)

const visibleColumns = computed(() => COLUMNS.filter(c => !hiddenCols.value.has(c.key)))
const TOTAL_COLS = computed(() => visibleColumns.value.length + 1)

function toggleColumn(key) {
  const s = new Set(hiddenCols.value)
  if (s.has(key)) s.delete(key); else s.add(key)
  hiddenCols.value = s
  localStorage.setItem(COL_STORAGE_KEY, JSON.stringify([...s]))
}

const cachedRows = ref([])
const filteredRows = ref([])
const renderedCount = ref(0)
const sortCol = ref(null)
const sortDir = ref('asc')
const colFilters = ref({})
const globalFilter = ref('')
const loading = ref(true)

const discFilter = ref(new Set())
const showDiscDropdown = ref(false)
const discBtnRef = ref(null)
const discDropdownPos = ref({ top: '0px', left: '0px' })

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

function _isStub(v) {
  return typeof v === 'string' && v.indexOf('НЕТ') === 0
}

function _isEmpty(v) {
  return v == null || v === ''
}

function _applyColFilter(rows, key, f) {
  if (f === '__EMPTY__') return rows.filter(row => _isEmpty(row[key]))
  if (f === '__NOT_EMPTY__') return rows.filter(row => { const v = row[key]; return !_isEmpty(v) && !_isStub(v) })
  return rows.filter(row => String(row[key] ?? '') === f)
}

function _splitDisc(v) {
  if (!v) return []
  return String(v).split(';').map(s => s.trim()).filter(Boolean)
}

function _matchDisc(row) {
  const sel = discFilter.value
  if (sel.size === 0) return true
  const v = row.discrepancies
  if (sel.has('__NONE__') && _isEmpty(v)) return true
  if (_isEmpty(v)) return false
  const parts = _splitDisc(v)
  return parts.some(p => sel.has(p))
}

function rowsFilteredExcept(excludeKey) {
  const gf = globalFilter.value.trim().toLowerCase()
  let rows = cachedRows.value
  if (gf) rows = rows.filter(row => getSearchString(row).indexOf(gf) !== -1)
  for (const col of COLUMNS) {
    if (col.key === excludeKey) continue
    if (col.key === 'discrepancies') continue
    const f = colFilters.value[col.key] || ''
    if (!f) continue
    rows = _applyColFilter(rows, col.key, f)
  }
  if (excludeKey !== 'discrepancies' && discFilter.value.size > 0) {
    rows = rows.filter(row => _matchDisc(row))
  }
  return rows
}

function discrepancyOptions() {
  const rows = rowsFilteredExcept('discrepancies')
  const tags = new Map()
  let noneCount = 0
  for (const row of rows) {
    const v = row.discrepancies
    if (_isEmpty(v)) { noneCount++; continue }
    const parts = _splitDisc(v)
    for (const p of parts) tags.set(p, (tags.get(p) || 0) + 1)
  }
  const sorted = [...tags.entries()].sort((a, b) => a[0].localeCompare(b[0], 'ru'))
  return { noneCount, total: rows.length, tags: sorted }
}

function toggleDiscTag(tag) {
  const s = new Set(discFilter.value)
  if (s.has(tag)) s.delete(tag); else s.add(tag)
  discFilter.value = s
  applyFilters()
}

function clearDiscFilter() {
  discFilter.value = new Set()
  applyFilters()
}

function openDiscDropdown(e) {
  showDiscDropdown.value = !showDiscDropdown.value
  if (showDiscDropdown.value) {
    const btn = e.currentTarget
    const rect = btn.getBoundingClientRect()
    const dropWidth = 240
    let left = rect.left
    if (left + dropWidth > window.innerWidth - 8) {
      left = rect.right - dropWidth
    }
    if (left < 8) left = 8
    discDropdownPos.value = {
      top: rect.bottom + 2 + 'px',
      left: left + 'px',
    }
  }
}

function onClickOutsideDisc(e) {
  if (!showDiscDropdown.value) return
  const btnEl = Array.isArray(discBtnRef.value) ? discBtnRef.value[0] : discBtnRef.value
  if (btnEl && btnEl.contains(e.target)) return
  const dd = document.getElementById('disc-dropdown-portal')
  if (dd && dd.contains(e.target)) return
  showDiscDropdown.value = false
}

const discFilterLabel = computed(() => {
  const n = discFilter.value.size
  if (n === 0) return '— все'
  return 'Выбрано: ' + n
})

function filterOptions(key) {
  const available = rowsFilteredExcept(key)
  const counts = {}
  let emptyCount = 0
  let realCount = 0
  for (const row of available) {
    const v = row[key]
    if (_isEmpty(v)) { emptyCount++; continue }
    const s = String(v)
    counts[s] = (counts[s] || 0) + 1
    if (!_isStub(s)) realCount++
  }
  const isDate = !!DATE_KEYS[key]
  const sorted = Object.keys(counts).sort((a, b) => {
    if (isDate) { return dateSortKey(a) < dateSortKey(b) ? -1 : dateSortKey(a) > dateSortKey(b) ? 1 : 0 }
    return a.localeCompare(b, 'ru')
  })
  const total = emptyCount + Object.values(counts).reduce((s, c) => s + c, 0)
  const opts = [{ value: '', label: '— все (' + total + ')' }]
  if (total > 0) {
    opts.push({ value: '__EMPTY__', label: 'ПУСТО (' + emptyCount + ')' })
    opts.push({ value: '__NOT_EMPTY__', label: 'ЕСТЬ ДАННЫЕ (' + realCount + ')' })
  }
  for (const v of sorted) opts.push({ value: v, label: v + ' (' + counts[v] + ')' })
  return opts
}

function applyFilters() {
  const gf = globalFilter.value.trim().toLowerCase()
  let rows = cachedRows.value
  if (gf) rows = rows.filter(row => getSearchString(row).indexOf(gf) !== -1)
  for (const col of COLUMNS) {
    if (col.key === 'discrepancies') continue
    const f = colFilters.value[col.key] || ''
    if (!f) continue
    rows = _applyColFilter(rows, col.key, f)
  }
  if (discFilter.value.size > 0) {
    rows = rows.filter(row => _matchDisc(row))
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

const debouncedApplyFilters = debounce(applyFilters, 300)

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
  discFilter.value = new Set()
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

onBeforeUnmount(() => {
  if (scrollTimeout) { clearTimeout(scrollTimeout); scrollTimeout = null }
  document.removeEventListener('mousedown', onClickOutsideDisc)
})

const { exportToXLSX } = useExport()
function doExport() {
  const data = filteredRows.value.length ? filteredRows.value : cachedRows.value
  exportToXLSX(COLUMNS, data, 'Svodka_AD_MFA_People.xlsx', 'Сводная')
}

onMounted(async () => {
  document.addEventListener('mousedown', onClickOutsideDisc)
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
        <input type="text" v-model="globalFilter" @input="debouncedApplyFilters" placeholder="Поиск…">
      </div>
      <button type="button" class="btn-icon" title="Сбросить фильтры" @click="resetFilters">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
          <line x1="18" y1="14" x2="23" y2="19"/><line x1="23" y1="14" x2="18" y2="19"/>
        </svg>
      </button>
      <div class="col-manager-wrap">
        <button type="button" class="btn-icon" title="Настройка колонок"
          @click="showColManager = !showColManager">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/>
            <line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/>
            <line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>
            <line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/>
            <line x1="17" y1="16" x2="23" y2="16"/>
          </svg>
        </button>
        <div v-if="showColManager" class="col-manager-dropdown">
          <label v-for="col in COLUMNS" :key="col.key" class="col-manager-item">
            <input type="checkbox" :checked="!hiddenCols.has(col.key)"
              @change="toggleColumn(col.key)">
            {{ col.label }}
          </label>
        </div>
      </div>
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
    <table class="data-table consolidated-table">
      <thead>
        <!-- Labels row -->
        <tr class="thead-labels">
          <th class="col-num">#</th>
          <th v-for="col in visibleColumns" :key="col.key" class="sortable" :data-key="col.key"
            :class="{ 'filter-active': col.key === 'discrepancies' ? discFilter.size > 0 : !!colFilters[col.key] }"
            @click="onSort(col.key)">
            {{ col.label }} <span class="sort-icon">{{ sortIcon(col.key) }}</span>
          </th>
        </tr>
        <!-- Filters row -->
        <tr class="thead-filters">
          <th class="col-num"></th>
          <th v-for="col in visibleColumns" :key="col.key">
            <!-- Multi-select for discrepancies -->
            <div v-if="col.key === 'discrepancies'" class="disc-filter-wrap">
              <button ref="discBtnRef" class="disc-filter-btn" :class="{ active: discFilter.size > 0 }"
                @click.stop="openDiscDropdown($event)">
                {{ discFilterLabel }}
                <span class="disc-filter-arrow">{{ showDiscDropdown ? '▴' : '▾' }}</span>
              </button>
            </div>
            <!-- Standard select for other columns -->
            <select v-else class="col-filter" :value="colFilters[col.key] || ''"
              @change="onColFilter(col.key, ($event.target).value)">
              <option v-for="opt in filterOptions(col.key)" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading"><td :colspan="TOTAL_COLS"><LoadingSpinner text="Загрузка данных…" /></td></tr>
        <tr v-else-if="!visibleRows.length"><td :colspan="TOTAL_COLS" class="muted-text">Нет данных</td></tr>
        <tr v-else v-for="(row, idx) in visibleRows" :key="idx"
          :class="[
            rowClass(row.source),
            row.uz_active === 'Нет' ? 'uz-inactive' : '',
            row.account_type === 'Service' ? 'uz-service' : '',
            row.account_type === 'Contractor' ? 'uz-contractor' : '',
          ]">
          <td class="col-num">{{ idx + 1 }}</td>
          <td v-for="col in visibleColumns" :key="col.key"
            :class="{ discrepancy: col.key === 'discrepancies' }">
            <span v-if="col.key === 'account_type' && row[col.key]"
              class="at-badge" :class="'at-' + (row[col.key] || '').toLowerCase()">{{ row[col.key] }}</span>
            <template v-else>{{ row[col.key] ?? '' }}</template>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- Discrepancy multi-select dropdown (teleported out of overflow container) -->
  <Teleport to="body">
    <div v-if="showDiscDropdown" id="disc-dropdown-portal" class="disc-dropdown"
      :style="{ position: 'fixed', top: discDropdownPos.top, left: discDropdownPos.left }">
      <div class="disc-dropdown-actions">
        <button @click="clearDiscFilter" class="disc-dropdown-link">Сбросить</button>
      </div>
      <label class="disc-dropdown-item" @click.stop>
        <input type="checkbox" :checked="discFilter.has('__NONE__')"
          @change="toggleDiscTag('__NONE__')">
        <span>Нет расхождений ({{ discrepancyOptions().noneCount }})</span>
      </label>
      <div class="disc-dropdown-sep"></div>
      <label v-for="[tag, cnt] in discrepancyOptions().tags" :key="tag"
        class="disc-dropdown-item" @click.stop>
        <input type="checkbox" :checked="discFilter.has(tag)"
          @change="toggleDiscTag(tag)">
        <span>{{ tag }} ({{ cnt }})</span>
      </label>
    </div>
  </Teleport>
</template>
