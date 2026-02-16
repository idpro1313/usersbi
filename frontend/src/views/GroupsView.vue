<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
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
  { key: 'staff_uuid',   label: 'StaffUUID' },
]
const DATE_KEYS = { password_last_set: true }

const route = useRoute()
const treeData = ref([])
const members = ref([])
const membersLoading = ref(false)
const selectedGroup = ref(null)
const selectedDomain = ref(null)
const groupsTitle = ref('')
const groupsCount = ref('')
const searchText = ref('')
const { exportToXLSX } = useExport()

async function loadTree() {
  try {
    const data = await fetchJSON('/api/groups/tree')
    treeData.value = data.domains || []
  } catch (_) {}
}

async function loadMembers(group, domain) {
  selectedGroup.value = group
  selectedDomain.value = domain
  groupsTitle.value = group
  groupsCount.value = 'загрузка…'
  membersLoading.value = true
  try {
    const data = await fetchJSON('/api/groups/members?group=' + encodeURIComponent(group) + '&domain=' + encodeURIComponent(domain))
    members.value = data.members || []
    groupsCount.value = data.count + ' уч. (' + data.city + ')'
  } catch (e) {
    members.value = []
    groupsCount.value = ''
  } finally {
    membersLoading.value = false
  }
}

function filteredTree() {
  const filter = searchText.value.trim().toLowerCase()
  return treeData.value.map(domain => {
    let groups = domain.groups
    if (filter) groups = groups.filter(g => g.name.toLowerCase().includes(filter))
    return { ...domain, groups }
  })
}

function toggleDomain(e) {
  const el = e.currentTarget.parentElement
  el.classList.toggle('collapsed')
}

function doExport() {
  const safeName = (selectedGroup.value || 'group').replace(/[\\/:*?"<>|]/g, '_')
  exportToXLSX(COLUMNS, members.value, 'Group_' + safeName + '.xlsx', safeName)
}

onMounted(async () => {
  await loadTree()
  const pGroup = route.query.group
  const pDomain = route.query.domain
  if (pGroup && pDomain) loadMembers(pGroup, pDomain)
})
</script>

<template>
  <div class="groups-layout">
    <!-- Sidebar -->
    <div class="groups-sidebar">
      <div class="sidebar-search">
        <input type="text" v-model="searchText" placeholder="Поиск групп…">
      </div>
      <div class="sidebar-tree">
        <template v-for="domain in filteredTree()" :key="domain.key">
          <div class="tree-domain">
            <div class="tree-domain-header" @click="toggleDomain">
              <span class="tree-arrow">&#9660;</span>
              {{ domain.city }}
              <span class="tree-badge">{{ domain.groups.length }} гр. / {{ domain.total_users }} уч.</span>
            </div>
            <div class="tree-group-list">
              <div v-for="g in domain.groups" :key="g.name"
                class="tree-group"
                :class="{ active: g.name === selectedGroup && domain.key === selectedDomain }"
                @click="loadMembers(g.name, domain.key)">
                {{ g.name }} <span class="tree-group-count">({{ g.count }})</span>
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
        <h2 class="groups-title">{{ groupsTitle || 'Выберите группу' }}</h2>
        <span class="groups-count">{{ groupsCount }}</span>
        <button v-if="members.length" type="button" class="btn-icon btn-export" title="Выгрузить XLSX" @click="doExport">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
        </button>
      </div>
      <div class="groups-table-wrap">
        <MembersTable
          :columns="COLUMNS" :rows="members" :dateKeys="DATE_KEYS"
          :loading="membersLoading" emptyMessage="Нет участников" />
      </div>
    </div>
  </div>
</template>
