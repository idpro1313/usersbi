<script setup>
import { ref, computed, onMounted } from 'vue'
import MembersTable from '../components/MembersTable.vue'
import { fetchJSON } from '../api'
import { useExport } from '../composables/useExport'

const COLUMNS = [
  { key: 'login',        label: 'Логин' },
  { key: 'display_name', label: 'ФИО' },
  { key: 'email',        label: 'Email' },
  { key: 'enabled',      label: 'УЗ активна' },
  { key: 'password_last_set', label: 'Смена пароля' },
  { key: 'title',        label: 'Должность' },
  { key: 'department',   label: 'Отдел' },
  { key: 'company',      label: 'Компания' },
  { key: 'location',     label: 'Город' },
  { key: 'domain',       label: 'Домен' },
  { key: 'staff_uuid',   label: 'StaffUUID' },
]
const DATE_KEYS = { password_last_set: true }

const treeData = ref([])
const allMembers = ref([])
const membersLoading = ref(false)
const selectedCompany = ref(null)
const selectedDepartment = ref(null)
const hideDisabled = ref(false)
const searchText = ref('')
const orgTitle = ref('')
const orgCount = ref('')
const { exportToXLSX } = useExport()

const visibleMembers = computed(() => {
  if (!hideDisabled.value) return allMembers.value
  return allMembers.value.filter(m => (m.enabled || '').toLowerCase() !== 'нет')
})

const countText = computed(() => {
  const total = allMembers.value.length
  const visible = visibleMembers.value.length
  let text = visible + ' чел.'
  if (hideDisabled.value && visible < total) text += ' (скрыто ' + (total - visible) + ' откл.)'
  return text
})

async function loadTree() {
  try {
    const data = await fetchJSON('/api/org/tree')
    treeData.value = data.companies || []
  } catch (_) {}
}

async function loadMembers(company, department) {
  selectedCompany.value = company
  selectedDepartment.value = department || null
  const parts = []
  if (company) parts.push(company)
  if (department) parts.push(department)
  orgTitle.value = parts.join(' → ') || 'Все'
  membersLoading.value = true
  try {
    let url = '/api/org/members?'
    if (company) url += 'company=' + encodeURIComponent(company) + '&'
    if (department) url += 'department=' + encodeURIComponent(department)
    const data = await fetchJSON(url)
    allMembers.value = data.members || []
  } catch (e) {
    allMembers.value = []
  } finally {
    membersLoading.value = false
  }
}

function filteredTree() {
  const filter = searchText.value.trim().toLowerCase()
  let companies = treeData.value
  if (filter) {
    companies = companies.filter(c =>
      c.name.toLowerCase().includes(filter) ||
      c.departments.some(d => d.name.toLowerCase().includes(filter))
    )
  }
  if (hideDisabled.value) {
    companies = companies.filter(c => (c.enabled_count || 0) > 0)
  }
  return companies.map(comp => {
    let depts = comp.departments
    if (filter) {
      depts = depts.filter(d =>
        d.name.toLowerCase().includes(filter) || comp.name.toLowerCase().includes(filter)
      )
    }
    if (hideDisabled.value) {
      depts = depts.filter(d => (d.enabled_count || 0) > 0)
    }
    return { ...comp, departments: depts }
  })
}

function toggleDomain(e) {
  const arrowEl = e.target.closest('.tree-arrow')
  const header = e.currentTarget
  if (arrowEl) {
    const domainEl = header.parentElement
    domainEl.classList.toggle('collapsed')
    arrowEl.innerHTML = domainEl.classList.contains('collapsed') ? '&#9654;' : '&#9660;'
  } else {
    loadMembers(header.dataset.company || '', '')
  }
}

function doExport() {
  const name = (selectedDepartment.value || selectedCompany.value || 'org').replace(/[\\/:*?"<>|]/g, '_')
  const data = hideDisabled.value
    ? allMembers.value.filter(m => (m.enabled || '').toLowerCase() !== 'нет')
    : allMembers.value
  exportToXLSX(COLUMNS, data, 'Org_' + name + '.xlsx', name)
}

onMounted(loadTree)
</script>

<template>
  <div class="groups-layout">
    <!-- Sidebar -->
    <div class="groups-sidebar">
      <div class="sidebar-search">
        <input type="text" v-model="searchText" placeholder="Поиск компании/отдела…">
      </div>
      <div class="sidebar-controls">
        <label class="sidebar-checkbox">
          <input type="checkbox" v-model="hideDisabled"> Скрыть заблокированные
        </label>
      </div>
      <div class="sidebar-tree">
        <template v-for="comp in filteredTree()" :key="comp.name">
          <div class="tree-domain">
            <div class="tree-domain-header tree-org-header" :data-company="comp.name"
              :class="{ active: comp.name === selectedCompany && !selectedDepartment }"
              @click="toggleDomain">
              <span class="tree-arrow">&#9660;</span>
              <span class="tree-org-name">{{ comp.name }}</span>
              <span class="tree-badge">
                {{ comp.departments.length }} отд. / {{ hideDisabled ? (comp.enabled_count || 0) : comp.count }} чел.
              </span>
            </div>
            <div class="tree-group-list">
              <div v-for="dept in comp.departments" :key="dept.name"
                class="tree-group tree-org-dept"
                :class="{ active: comp.name === selectedCompany && dept.name === selectedDepartment }"
                @click="loadMembers(comp.name, dept.name)">
                {{ dept.name }}
                <span class="tree-group-count">({{ hideDisabled ? (dept.enabled_count || 0) : dept.count }})</span>
              </div>
            </div>
          </div>
        </template>
        <p v-if="!treeData.length" class="muted-text">Нет данных AD</p>
      </div>
    </div>

    <!-- Main -->
    <div class="groups-main">
      <div class="groups-header">
        <h2 class="groups-title">{{ orgTitle || 'Выберите организацию' }}</h2>
        <span class="groups-count">{{ countText }}</span>
        <button v-if="allMembers.length" type="button" class="btn-icon btn-export" title="Выгрузить XLSX"
          style="margin-left: auto;" @click="doExport">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
        </button>
      </div>
      <div class="groups-table-wrap">
        <MembersTable :columns="COLUMNS" :rows="visibleMembers" :dateKeys="DATE_KEYS"
          :loading="membersLoading" emptyMessage="Нет пользователей" />
      </div>
    </div>
  </div>
</template>
