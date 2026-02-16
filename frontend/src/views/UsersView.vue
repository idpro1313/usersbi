<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import FieldsTable from '../components/FieldsTable.vue'
import AdSections from '../components/AdSections.vue'
import PopupOverlay from '../components/PopupOverlay.vue'
import UserCardPopup from '../components/UserCardPopup.vue'
import DnPopup from '../components/DnPopup.vue'
import { fetchJSON } from '../api'
import { escapeHtml } from '../utils/format'

const allUsers = ref([])
const selectedKey = ref(null)
const hideDisabled = ref(false)
const searchText = ref('')
const cardData = ref(null)
const cardLoading = ref(false)
const cardError = ref('')

const CHUNK = 100
const renderedCount = ref(0)

const filteredUsers = computed(() => {
  let base = allUsers.value
  if (hideDisabled.value) base = base.filter(u => !u.all_disabled)
  const filter = searchText.value.trim().toLowerCase()
  if (filter) {
    base = base.filter(u =>
      [u.fio, u.staff_uuid, ...u.logins].join(' ').toLowerCase().includes(filter)
    )
  }
  return base
})

const visibleUsers = computed(() => filteredUsers.value.slice(0, renderedCount.value))

const sidebarInfo = computed(() => {
  const total = allUsers.value.length
  const count = filteredUsers.value.length
  const hiddenCount = hideDisabled.value ? allUsers.value.filter(u => u.all_disabled).length : 0
  let info = 'Найдено: ' + count + ' из ' + total
  if (hiddenCount > 0) info += ' (скрыто ' + hiddenCount + ' откл.)'
  return info
})

function onSearch() {
  renderedCount.value = Math.min(CHUNK, filteredUsers.value.length)
}

function loadMore() {
  renderedCount.value = Math.min(renderedCount.value + CHUNK, filteredUsers.value.length)
}

let scrollTimer = null
function onSidebarScroll(e) {
  if (scrollTimer) return
  scrollTimer = setTimeout(() => {
    scrollTimer = null
    if (renderedCount.value >= filteredUsers.value.length) return
    const el = e.target
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 200) loadMore()
  }, 50)
}

onBeforeUnmount(() => {
  if (scrollTimer) { clearTimeout(scrollTimer); scrollTimer = null }
})

async function loadList() {
  try {
    const data = await fetchJSON('/api/users/list')
    allUsers.value = data.users || []
    renderedCount.value = Math.min(CHUNK, allUsers.value.length)
  } catch (e) { /* */ }
}

async function loadCard(key) {
  selectedKey.value = key
  cardLoading.value = true
  cardError.value = ''
  cardData.value = null
  try {
    cardData.value = await fetchJSON('/api/users/card?key=' + encodeURIComponent(key))
  } catch (e) {
    cardError.value = e.message
  } finally {
    cardLoading.value = false
  }
}

function summaryParts() {
  if (!cardData.value) return []
  const d = cardData.value
  const sp = []
  if (d.city) sp.push(['Город', d.city])
  if (d.hub) sp.push(['Локация', d.hub])
  if (d.dp_unit) sp.push(['Подразделение DP', d.dp_unit])
  if (d.rm) sp.push(['RM', d.rm])
  return sp
}

function renderGroupLinks(groupsStr) {
  if (!groupsStr) return ''
  return groupsStr.split(';').map(g => g.trim()).filter(Boolean).map(g => {
    return '<a class="ucard-link" href="#" data-popup-type="group" data-popup-name="' + escapeHtml(g) + '">' + escapeHtml(g) + '</a>'
  }).join('; ')
}

function renderManagerLink(a) {
  if (!a.manager) return ''
  const displayName = a.manager_name || (() => {
    const cn = a.manager.match(/^CN=([^,]+)/i)
    return cn ? cn[1] : a.manager
  })()
  if (a.manager_key) {
    return '<a class="ucard-link" href="#" data-popup-type="manager" data-manager-key="' + escapeHtml(a.manager_key) + '">' + escapeHtml(displayName) + '</a>'
  }
  return dnLinksHtml(a.manager)
}

function dnLinksHtml(dnString) {
  if (!dnString) return ''
  return dnString.split(';').map(s => s.trim()).filter(Boolean).map(dn => {
    const cn = dn.match(/^CN=([^,]+)/i)
    const display = cn ? cn[1] : dn
    return '<a class="ucard-link dn-link" href="#" data-dn="' + escapeHtml(dn) + '">' + escapeHtml(display) + '</a>'
  }).join('; ')
}

// Popup state
const membersPopup = ref(null)
const membersData = ref([])
const membersLoading = ref(false)
const cardPopup = ref(null)
const dnPopupData = ref(null)

function onCardClick(e) {
  const dnLink = e.target.closest('[data-dn]')
  if (dnLink) {
    e.preventDefault()
    dnPopupData.value = { dn: dnLink.dataset.dn, name: dnLink.textContent.trim() }
    return
  }
  const link = e.target.closest('[data-popup-type]')
  if (!link) return
  e.preventDefault()
  const type = link.dataset.popupType
  if (type === 'manager') {
    cardPopup.value = { key: link.dataset.managerKey, name: 'Руководитель' }
    return
  }
  const name = link.dataset.popupName
  openMembersPopup(type, name)
}

async function openMembersPopup(type, name) {
  let apiUrl, title
  if (type === 'group') {
    const domain = cardData.value?.ad?.[0]?.ad_source || ''
    apiUrl = '/api/groups/members?domain=' + encodeURIComponent(domain) + '&group=' + encodeURIComponent(name)
    title = 'Группа: ' + name
  } else {
    const domain = cardData.value?.ad?.[0]?.ad_source || ''
    apiUrl = '/api/structure/members?domain=' + encodeURIComponent(domain) + '&path=' + encodeURIComponent(name)
    title = 'OU: ' + name.replace(/\//g, ' › ')
  }
  membersPopup.value = { title }
  membersLoading.value = true
  membersData.value = []
  try {
    const data = await fetchJSON(apiUrl)
    membersData.value = data.members || []
  } catch (_) {}
  membersLoading.value = false
}

function onDnOpenCard(key, name) {
  dnPopupData.value = null
  cardPopup.value = { key, name }
}

const MEMBERS_COLS = [
  { key: 'display_name', label: 'ФИО' },
  { key: 'login', label: 'Логин' },
  { key: 'email', label: 'Email' },
  { key: 'enabled', label: 'Активна' },
  { key: 'password_last_set', label: 'Смена пароля' },
  { key: 'title', label: 'Должность' },
  { key: 'department', label: 'Отдел' },
  { key: 'company', label: 'Компания' },
]

onMounted(loadList)
</script>

<template>
  <div class="groups-layout">
    <!-- Sidebar -->
    <div class="groups-sidebar">
      <div class="sidebar-search">
        <input type="text" v-model="searchText" @input="onSearch" placeholder="Поиск пользователей…">
      </div>
      <div class="sidebar-controls">
        <label class="sidebar-checkbox">
          <input type="checkbox" v-model="hideDisabled" @change="onSearch"> Скрыть заблокированные
        </label>
      </div>
      <div class="sidebar-info">{{ sidebarInfo }}</div>
      <div class="sidebar-tree" @scroll="onSidebarScroll" style="padding: 0;">
        <div v-for="u in visibleUsers" :key="u.key"
          class="user-list-item"
          :class="{ active: u.key === selectedKey, 'user-disabled': u.all_disabled }"
          @click="loadCard(u.key)">
          <div class="user-item-name">{{ u.fio || u.logins[0] || u.staff_uuid || '—' }}</div>
          <div class="user-item-meta">{{ [u.logins.join(', '), u.staff_uuid ? 'UUID: ' + u.staff_uuid : ''].filter(Boolean).join(' · ') }}</div>
          <div class="user-item-sources">{{ u.sources.join(', ') }}</div>
        </div>
        <p v-if="!filteredUsers.length" class="muted-text">Нет результатов</p>
      </div>
    </div>

    <!-- Card -->
    <div class="groups-main">
      <div class="user-card-wrap" @click="onCardClick">
        <p v-if="cardLoading" class="muted-text">Загрузка…</p>
        <p v-else-if="cardError" class="muted-text">Ошибка: {{ cardError }}</p>
        <p v-else-if="!cardData" class="muted-text">Выберите пользователя</p>
        <template v-else>
          <!-- Header -->
          <div class="ucard-header">
            <h2 class="ucard-fio">{{ cardData.fio || '—' }}</h2>
            <span v-if="cardData.staff_uuid" class="ucard-uuid">StaffUUID: {{ cardData.staff_uuid }}</span>
            <span v-if="cardData.logins?.length" class="ucard-logins">Логины: {{ cardData.logins.join(', ') }}</span>
            <div v-if="summaryParts().length" class="ucard-summary">
              <span v-for="sp in summaryParts()" :key="sp[0]" class="ucard-summary-item">
                <b>{{ sp[0] }}:</b> {{ sp[1] }}
              </span>
            </div>
          </div>

          <!-- People -->
          <div class="ucard-section">
            <h3 class="ucard-section-title">Кадры (Develonica.People)</h3>
            <template v-if="cardData.people">
              <FieldsTable :pairs="[
                ['ФИО', cardData.people.fio], ['Email', cardData.people.email],
                ['Телефон', cardData.people.phone], ['Подразделение', cardData.people.unit],
                ['Хаб', cardData.people.hub], ['Статус', cardData.people.employment_status],
                ['Руководитель', cardData.people.unit_manager], ['Формат работы', cardData.people.work_format],
                ['HR BP', cardData.people.hr_bp], ['StaffUUID', cardData.people.staff_uuid],
              ]" />
            </template>
            <p v-else class="muted-text">Нет данных в кадрах</p>
          </div>

          <!-- AD -->
          <div class="ucard-section">
            <h3 class="ucard-section-title">Учётные записи AD ({{ cardData.ad.length }})</h3>
            <template v-if="cardData.ad.length">
              <div v-for="(a, i) in cardData.ad" :key="i"
                class="ucard-ad-block" :class="{ 'uz-inactive': a.enabled === 'Нет' }">
                <div class="ucard-ad-domain">{{ a.domain }} — {{ a.login }}</div>
                <AdSections :account="a"
                  :renderGroupsHtml="renderGroupLinks"
                  :renderManagerHtml="renderManagerLink"
                  @open-dn="(dn, name) => { dnPopupData = { dn, name } }" />
              </div>
            </template>
            <p v-else class="muted-text">Нет учётных записей в AD</p>
          </div>

          <!-- MFA -->
          <div class="ucard-section">
            <h3 class="ucard-section-title">MFA ({{ cardData.mfa.length }})</h3>
            <template v-if="cardData.mfa.length">
              <div v-for="(m, j) in cardData.mfa" :key="j" class="ucard-mfa-block">
                <FieldsTable :pairs="[
                  ['Identity', m.identity], ['ФИО', m.name],
                  ['Email', m.email], ['Телефон', m.phones],
                  ['Статус', m.status], ['Зарегистрирован', m.is_enrolled],
                  ['Аутентификаторы', m.authenticators], ['Последний вход', m.last_login],
                  ['Создан', m.created_at], ['Группы MFA', m.mfa_groups],
                  ['LDAP', m.ldap],
                ]" />
              </div>
            </template>
            <p v-else class="muted-text">Нет записи MFA</p>
          </div>

          <!-- Matches -->
          <div v-if="cardData.matches?.length" class="ucard-section">
            <h3 class="ucard-section-title ucard-matches-title">Возможные совпадения ({{ cardData.matches.length }})</h3>
            <table class="data-table ucard-matches-table">
              <thead><tr>
                <th>Причина</th><th>Источник</th><th>ФИО</th><th>Email</th>
                <th>Логин</th><th>StaffUUID</th><th>Активна</th>
              </tr></thead>
              <tbody>
                <tr v-for="(mt, k) in cardData.matches" :key="k">
                  <td><span class="match-reason">{{ mt.reason }}</span></td>
                  <td>{{ mt.source }}</td><td>{{ mt.fio }}</td><td>{{ mt.email }}</td>
                  <td>{{ mt.login }}</td><td>{{ mt.staff_uuid }}</td><td>{{ mt.enabled }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>
    </div>
  </div>

  <!-- Members popup -->
  <PopupOverlay v-if="membersPopup" :title="membersPopup.title" @close="membersPopup = null">
    <p v-if="membersLoading" class="muted-text">Загрузка…</p>
    <template v-else-if="membersData.length">
      <p class="popup-count">Участников: {{ membersData.length }}</p>
      <table class="data-table popup-table">
        <thead><tr><th v-for="c in MEMBERS_COLS" :key="c.key">{{ c.label }}</th></tr></thead>
        <tbody>
          <tr v-for="(m, i) in membersData" :key="i" :class="{ 'row-inactive': (m.enabled || '').toLowerCase() === 'нет' }">
            <td v-for="c in MEMBERS_COLS" :key="c.key">{{ m[c.key] || '' }}</td>
          </tr>
        </tbody>
      </table>
    </template>
    <p v-else class="muted-text">Нет участников</p>
  </PopupOverlay>

  <!-- Card popup (manager) -->
  <UserCardPopup v-if="cardPopup" :userKey="cardPopup.key" :displayName="cardPopup.name"
    @close="cardPopup = null" @open-dn="(dn, name) => { dnPopupData = { dn, name } }" @open-card="(key, name) => { cardPopup = { key, name } }" />

  <!-- DN popup -->
  <DnPopup v-if="dnPopupData" :dn="dnPopupData.dn" :displayName="dnPopupData.name"
    @close="dnPopupData = null" @open-card="onDnOpenCard" />
</template>
