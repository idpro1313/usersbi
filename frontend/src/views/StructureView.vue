<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import MembersTable from '../components/MembersTable.vue'
import OuTreeNode from '../components/OuTreeNode.vue'
import { fetchJSON } from '../api'
import { useExport } from '../composables/useExport'
import { debounce } from '../utils/format'

const COLUMNS = [
  { key: 'login',        label: 'Логин' },
  { key: 'display_name', label: 'ФИО' },
  { key: 'email',        label: 'Email' },
  { key: 'enabled',      label: 'УЗ активна' },
  { key: 'account_type', label: 'Тип УЗ' },
  { key: 'password_last_set', label: 'Смена пароля' },
  { key: 'title',        label: 'Должность' },
  { key: 'department',   label: 'Отдел' },
  { key: 'company',      label: 'Компания' },
  { key: 'staff_uuid',   label: 'StaffUUID' },
]
const DATE_KEYS = { password_last_set: true }

const route = useRoute()
const treeData = ref([])
const members = ref([])
const membersLoading = ref(false)
const selectedPath = ref(null)
const selectedDomain = ref(null)
const ouTitle = ref('')
const ouCount = ref('')
const searchText = ref('')
const debouncedSearch = ref('')
const _syncSearch = debounce(() => { debouncedSearch.value = searchText.value }, 200)
watch(searchText, _syncSearch)
const { exportToXLSX } = useExport()

const breadcrumbParts = ref([])

async function loadTree() {
  try {
    const data = await fetchJSON('/api/structure/tree')
    treeData.value = data.domains || []
  } catch (_) {}
}

async function loadMembers(path, domain) {
  selectedPath.value = path
  selectedDomain.value = domain
  ouTitle.value = path.split('/').pop()
  ouCount.value = 'загрузка…'
  membersLoading.value = true
  buildBreadcrumb(path, domain)
  try {
    const data = await fetchJSON('/api/structure/members?path=' + encodeURIComponent(path) + '&domain=' + encodeURIComponent(domain))
    members.value = data.members || []
    ouCount.value = data.count + ' уч. (' + data.city + ')'
  } catch (e) {
    members.value = []
    ouCount.value = ''
  } finally {
    membersLoading.value = false
  }
}

function buildBreadcrumb(path, domain) {
  if (!path) { breadcrumbParts.value = []; return }
  const parts = path.split('/')
  breadcrumbParts.value = parts.map((p, i) => ({
    label: p,
    path: parts.slice(0, i + 1).join('/'),
    domain,
  }))
}

function doExport() {
  const ouName = (selectedPath.value || 'ou').split('/').pop().replace(/[\\/:*?"<>|]/g, '_')
  exportToXLSX(COLUMNS, members.value, 'OU_' + ouName + '.xlsx', ouName)
}

function toggleDomain(e) {
  const el = e.currentTarget.parentElement
  el.classList.toggle('collapsed')
  const arrow = e.currentTarget.querySelector('.tree-arrow')
  if (arrow) arrow.innerHTML = el.classList.contains('collapsed') ? '&#9654;' : '&#9660;'
}

onMounted(async () => {
  await loadTree()
  const pPath = route.query.path
  const pDomain = route.query.domain
  if (pPath && pDomain) loadMembers(pPath, pDomain)
})
</script>

<template>
  <div class="groups-layout">
    <!-- Sidebar -->
    <div class="groups-sidebar">
      <div class="sidebar-search">
        <input type="text" v-model="searchText" placeholder="Поиск OU…">
      </div>
      <div class="sidebar-tree">
        <template v-for="domain in treeData" :key="domain.key">
          <div v-if="domain.tree?.length" class="tree-domain">
            <div class="tree-domain-header" @click="toggleDomain">
              <span class="tree-arrow">&#9660;</span>
              {{ domain.city }}
              <span class="tree-badge">{{ domain.total_users }} уч.</span>
            </div>
            <OuTreeNode v-for="node in domain.tree" :key="node.name"
              :node="node" parentPath="" :domainKey="domain.key"
              :filter="debouncedSearch.trim().toLowerCase()"
              :selectedPath="selectedPath" :selectedDomain="selectedDomain"
              @select="loadMembers" />
          </div>
        </template>
        <p v-if="!treeData.length" class="muted-text">Нет данных AD</p>
      </div>
    </div>

    <!-- Main -->
    <div class="groups-main">
      <div class="groups-header">
        <h2 class="groups-title">{{ ouTitle || 'Выберите OU' }}</h2>
        <span class="groups-count">{{ ouCount }}</span>
        <div v-if="breadcrumbParts.length" class="ou-breadcrumb" style="margin-left: 0.75rem;">
          <template v-for="(crumb, i) in breadcrumbParts" :key="i">
            <span v-if="i > 0" class="ou-crumb-sep">›</span>
            <span class="ou-crumb" @click="loadMembers(crumb.path, crumb.domain)">{{ crumb.label }}</span>
          </template>
        </div>
        <button v-if="members.length" type="button" class="btn-icon btn-export" title="Выгрузить XLSX"
          style="margin-left: auto;" @click="doExport">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
        </button>
      </div>
      <div class="groups-table-wrap">
        <MembersTable :columns="COLUMNS" :rows="members" :dateKeys="DATE_KEYS"
          :loading="membersLoading" emptyMessage="Нет пользователей в этом OU" />
      </div>
    </div>
  </div>
</template>
