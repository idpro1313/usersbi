<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { fetchJSON, postJSON, putJSON, postForm, del } from '../api'
import { useToast } from '../composables/useToast'
import { useAuth } from '../composables/useAuth'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const toast = useToast()
const auth = useAuth()

const activeTab = ref('ldap')
const tabs = [
  { key: 'ldap', label: 'LDAP-подключения' },
  { key: 'users', label: 'Пользователи' },
  { key: 'upload', label: 'Загрузка данных' },
]

// ─── LDAP settings ──────────────────────────────────────

const ldapLoading = ref(false)
const ldapSaving = ref(false)
const ldap = reactive({
  domains: {
    izhevsk: { server: '', search_base: '', enabled: 'false' },
    kostroma: { server: '', search_base: '', enabled: 'false' },
    moscow: { server: '', search_base: '', enabled: 'false' },
  },
  user: '',
  password: '',
  use_ssl: 'false',
  auth_domain: 'izhevsk',
  bind_user_format: '{username}',
  jwt_expire_hours: '12',
})
const ldapTestResults = reactive({})

const domainLabels = { izhevsk: 'Ижевск', kostroma: 'Кострома', moscow: 'Москва' }

async function loadLdapSettings() {
  ldapLoading.value = true
  try {
    const data = await fetchJSON('/api/settings/ldap')
    if (data.domains) {
      for (const key of ['izhevsk', 'kostroma', 'moscow']) {
        const d = data.domains[key] || {}
        ldap.domains[key].server = d.server || ''
        ldap.domains[key].search_base = d.search_base || ''
        ldap.domains[key].enabled = d.enabled || 'false'
      }
    }
    ldap.user = data.user || ''
    ldap.password = data.password || ''
    ldap.use_ssl = data.use_ssl || 'false'
    ldap.auth_domain = data.auth_domain || 'izhevsk'
    ldap.bind_user_format = data.bind_user_format || '{username}'
    ldap.jwt_expire_hours = data.jwt_expire_hours || '12'
  } catch (e) {
    toast.error('Ошибка загрузки настроек: ' + e.message)
  } finally {
    ldapLoading.value = false
  }
}

async function saveLdapSettings() {
  ldapSaving.value = true
  try {
    await putJSON('/api/settings/ldap', {
      domains: ldap.domains,
      user: ldap.user,
      password: ldap.password,
      use_ssl: ldap.use_ssl,
      auth_domain: ldap.auth_domain,
      bind_user_format: ldap.bind_user_format,
      jwt_expire_hours: ldap.jwt_expire_hours,
    })
    toast.success('Настройки LDAP сохранены')
  } catch (e) {
    toast.error('Ошибка сохранения: ' + e.message)
  } finally {
    ldapSaving.value = false
  }
}

async function testLdap(domainKey) {
  ldapTestResults[domainKey] = { testing: true }
  try {
    const data = await postJSON('/api/settings/ldap/test', {
      domain: domainKey,
      server: ldap.domains[domainKey].server,
      user: ldap.user,
      password: ldap.password,
      use_ssl: ldap.use_ssl,
    })
    ldapTestResults[domainKey] = { ok: data.ok, msg: data.message }
  } catch (e) {
    ldapTestResults[domainKey] = { ok: false, msg: e.message }
  }
}

// ─── Users management ────────────────────────────────────

const usersLoading = ref(false)
const appUsers = ref([])
const showAddUser = ref(false)
const newUser = reactive({ username: '', display_name: '', password: '', role: 'viewer', domain: 'izhevsk' })

async function loadUsers() {
  usersLoading.value = true
  try {
    appUsers.value = await fetchJSON('/api/settings/users')
  } catch (e) {
    toast.error('Ошибка загрузки пользователей: ' + e.message)
  } finally {
    usersLoading.value = false
  }
}

async function addUser() {
  if (!newUser.username.trim()) { toast.warn('Укажите логин'); return }
  try {
    await postJSON('/api/settings/users', { ...newUser, username: newUser.username.trim() })
    toast.success('Пользователь добавлен')
    showAddUser.value = false
    newUser.username = ''
    newUser.display_name = ''
    newUser.password = ''
    newUser.role = 'viewer'
    loadUsers()
  } catch (e) {
    toast.error(e.message)
  }
}

async function toggleRole(u) {
  const newRole = u.role === 'admin' ? 'viewer' : 'admin'
  try {
    await putJSON('/api/settings/users/' + u.id, { role: newRole })
    toast.success('Роль изменена')
    loadUsers()
  } catch (e) {
    toast.error(e.message)
  }
}

async function toggleActive(u) {
  try {
    await putJSON('/api/settings/users/' + u.id, { is_active: !u.is_active })
    toast.success(u.is_active ? 'Заблокирован' : 'Разблокирован')
    loadUsers()
  } catch (e) {
    toast.error(e.message)
  }
}

async function deleteUser(u) {
  if (!confirm('Удалить пользователя ' + u.username + '?')) return
  try {
    await del('/api/settings/users/' + u.id)
    toast.success('Пользователь удалён')
    loadUsers()
  } catch (e) {
    toast.error(e.message)
  }
}

function isSelf(u) {
  return u.username === auth.user.value?.username
}

// ─── Upload (перенос из UploadView) ────────────────────

const SyncIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>`
const UploadIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>`
const TrashIcon = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>`
const TrashBigIcon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>`

const adDomains = ['izhevsk', 'kostroma', 'moscow']
const adCityNames = { izhevsk: 'AD — Ижевск', kostroma: 'AD — Кострома', moscow: 'AD — Москва' }

const ldapMode = ref(false)
const ldapConfigured = reactive({})
const uploadStatuses = reactive({})
const stats = ref('')
const fileRefs = {}
const dragOver = reactive({})

function setUploadStatus(key, ok, msg) {
  uploadStatuses[key] = { ok, msg }
}

async function doUpload(statusKey, endpoint, file) {
  const form = new FormData()
  form.append('file', file)
  try {
    const data = await postForm(endpoint, form)
    let msg = 'Загружено: ' + data.rows + ' записей (' + data.filename + ')'
    if (data.skipped) msg += ' | пропущено ' + data.skipped + ' чужих'
    setUploadStatus(statusKey, true, msg)
    loadUploadStats()
  } catch (e) {
    setUploadStatus(statusKey, false, e.message)
  }
}

async function uploadFile(key, endpoint) {
  const input = fileRefs[key]
  if (!input) return
  input.click()
  await new Promise(resolve => { input.onchange = resolve })
  const file = input.files[0]
  if (!file) return
  await doUpload(key, endpoint, file)
  input.value = ''
}

function onDrop(e, statusKey, endpoint) {
  e.preventDefault()
  dragOver[statusKey] = false
  const file = e.dataTransfer?.files?.[0]
  if (file) doUpload(statusKey, endpoint, file)
}
function onDragOver(e, key) { e.preventDefault(); dragOver[key] = true }
function onDragLeave(key) { dragOver[key] = false }

async function syncDomain(key) {
  setUploadStatus(key, true, 'Синхронизация…')
  try {
    const data = await postJSON('/api/sync/ad/' + key, {})
    setUploadStatus(key, true, 'Синхронизировано: ' + data.rows + ' записей')
    loadUploadStats()
  } catch (e) {
    setUploadStatus(key, false, e.message)
  }
}

async function syncAll() {
  adDomains.forEach(k => setUploadStatus(k, true, 'Синхронизация…'))
  try {
    const data = await postJSON('/api/sync/ad', {})
    if (data.domains) {
      adDomains.forEach(k => {
        const info = data.domains[k]
        if (!info) return
        if (info.error) setUploadStatus(k, false, info.error)
        else if (info.skipped) setUploadStatus(k, false, 'Пропущено: ' + info.reason)
        else setUploadStatus(k, true, 'Синхронизировано: ' + info.rows + ' записей')
      })
    }
    loadUploadStats()
  } catch (e) {
    adDomains.forEach(k => setUploadStatus(k, false, 'Ошибка: ' + e.message))
  }
}

async function clearData(endpoint, label, statusKey) {
  if (!confirm('Очистить данные ' + label + '?')) return
  try {
    const data = await del(endpoint)
    setUploadStatus(statusKey, true, 'Удалено: ' + data.deleted + ' записей')
    loadUploadStats()
  } catch (e) {
    setUploadStatus(statusKey, false, e.message)
  }
}

async function clearAll() {
  if (!confirm('Очистить ВСЮ базу данных (AD + MFA + Кадры)?')) return
  try {
    const data = await del('/api/clear/all')
    const d = data.deleted
    toast.success('Удалено: AD ' + d.ad + ', MFA ' + d.mfa + ', Кадры ' + d.people)
    loadUploadStats()
  } catch (e) {
    toast.error('Ошибка: ' + e.message)
  }
}

async function loadUploadStats() {
  try {
    const s = await fetchJSON('/api/stats')
    const parts = []
    if (s.ad_domains) {
      const adParts = []
      for (const key in s.ad_domains) {
        adParts.push(s.ad_domains[key].city + ': ' + s.ad_domains[key].rows)
      }
      parts.push('AD: ' + s.ad_total + ' (' + adParts.join(', ') + ')')
    }
    parts.push('MFA: ' + s.mfa_rows)
    parts.push('Кадры: ' + s.people_rows)
    stats.value = parts.join(' · ')
  } catch (_) {
    stats.value = 'Не удалось загрузить статистику'
  }
}

async function loadUploadSyncStatus() {
  try {
    const data = await fetchJSON('/api/sync/status')
    if (data.available && data.domains) {
      let anyConfigured = false
      adDomains.forEach(k => {
        if (data.domains[k]?.configured) {
          anyConfigured = true
          ldapConfigured[k] = true
        }
      })
      if (anyConfigured) ldapMode.value = true
    }
  } catch (_) {}
  loadUploadStats()
}

// ─── Init ───────────────────────────────────────────────

onMounted(() => {
  loadLdapSettings()
  loadUsers()
  loadUploadSyncStatus()
})
</script>

<template>
  <div class="page-scroll">
    <div class="page-inner">
      <h1 class="page-title">Настройки</h1>

      <div class="settings-tabs">
        <button v-for="tab in tabs" :key="tab.key"
          class="settings-tab" :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key">
          {{ tab.label }}
        </button>
      </div>

      <!-- ═══ Tab: LDAP ═══ -->
      <div v-show="activeTab === 'ldap'" class="settings-panel">
        <LoadingSpinner v-if="ldapLoading" text="Загрузка настроек…" />
        <template v-else>
          <div class="ldap-grid">
            <div v-for="key in ['izhevsk', 'kostroma', 'moscow']" :key="key" class="card ldap-card">
              <h3>{{ domainLabels[key] }}</h3>
              <div class="form-group">
                <label>Сервер LDAP</label>
                <input v-model="ldap.domains[key].server" placeholder="ldap.example.com">
              </div>
              <div class="form-group">
                <label>Search Base (DN)</label>
                <input v-model="ldap.domains[key].search_base" placeholder="DC=example,DC=com">
              </div>
              <div class="form-group form-check">
                <label>
                  <input type="checkbox"
                    :checked="ldap.domains[key].enabled === 'true'"
                    @change="ldap.domains[key].enabled = $event.target.checked ? 'true' : 'false'">
                  Включить синхронизацию
                </label>
              </div>
              <button class="btn btn-sm" @click="testLdap(key)">
                {{ ldapTestResults[key]?.testing ? 'Проверка…' : 'Проверить подключение' }}
              </button>
              <div v-if="ldapTestResults[key] && !ldapTestResults[key].testing"
                class="ldap-test-result" :class="ldapTestResults[key].ok ? 'ok' : 'err'">
                {{ ldapTestResults[key].msg }}
              </div>
            </div>
          </div>

          <div class="ldap-common">
            <h3>Общие настройки</h3>
            <div class="form-row">
              <div class="form-group">
                <label>LDAP-пользователь</label>
                <input v-model="ldap.user" placeholder="CN=user,DC=example,DC=com">
              </div>
              <div class="form-group">
                <label>Пароль</label>
                <input v-model="ldap.password" type="password" placeholder="••••••">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Формат bind-пользователя при авторизации</label>
                <input v-model="ldap.bind_user_format" placeholder="{username}@domain.com">
              </div>
              <div class="form-group">
                <label>Домен для авторизации</label>
                <select v-model="ldap.auth_domain">
                  <option v-for="key in ['izhevsk', 'kostroma', 'moscow']" :key="key" :value="key">
                    {{ domainLabels[key] }}
                  </option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group form-check">
                <label>
                  <input type="checkbox"
                    :checked="ldap.use_ssl === 'true'"
                    @change="ldap.use_ssl = $event.target.checked ? 'true' : 'false'">
                  Использовать SSL (порт 636)
                </label>
              </div>
              <div class="form-group">
                <label>Время жизни токена (часов)</label>
                <input v-model="ldap.jwt_expire_hours" type="number" min="1" max="720" style="width: 100px">
              </div>
            </div>
            <button class="btn btn-accent" :disabled="ldapSaving" @click="saveLdapSettings">
              {{ ldapSaving ? 'Сохранение…' : 'Сохранить настройки' }}
            </button>
          </div>
        </template>
      </div>

      <!-- ═══ Tab: Users ═══ -->
      <div v-show="activeTab === 'users'" class="settings-panel">
        <div class="users-toolbar">
          <button class="btn btn-accent" @click="showAddUser = !showAddUser">
            {{ showAddUser ? 'Отмена' : '+ Добавить пользователя' }}
          </button>
        </div>

        <div v-if="showAddUser" class="card add-user-card">
          <div class="form-row">
            <div class="form-group">
              <label>Логин</label>
              <input v-model="newUser.username" placeholder="ivanov">
            </div>
            <div class="form-group">
              <label>Отображаемое имя</label>
              <input v-model="newUser.display_name" placeholder="Иванов И.И.">
            </div>
            <div class="form-group">
              <label>Пароль (локальный вход)</label>
              <input v-model="newUser.password" type="password" placeholder="Оставьте пустым для входа через LDAP">
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Роль</label>
              <select v-model="newUser.role">
                <option value="admin">Администратор</option>
                <option value="viewer">Просмотр</option>
              </select>
            </div>
            <div class="form-group">
              <label>Домен</label>
              <select v-model="newUser.domain">
                <option v-for="key in ['izhevsk', 'kostroma', 'moscow']" :key="key" :value="key">
                  {{ domainLabels[key] }}
                </option>
              </select>
            </div>
          </div>
          <button class="btn btn-accent" @click="addUser">Добавить</button>
        </div>

        <LoadingSpinner v-if="usersLoading" text="Загрузка пользователей…" />
        <table v-else-if="appUsers.length" class="data-table users-table">
          <thead>
            <tr>
              <th>Логин</th>
              <th>Имя</th>
              <th>Тип</th>
              <th>Роль</th>
              <th>Домен</th>
              <th>Активен</th>
              <th>Последний вход</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in appUsers" :key="u.id" :class="{ 'row-inactive': !u.is_active }">
              <td>{{ u.username }}</td>
              <td>{{ u.display_name }}</td>
              <td>
                <span class="type-badge" :class="u.is_local ? 'type-local' : 'type-ldap'">
                  {{ u.is_local ? 'Локальный' : 'LDAP' }}
                </span>
              </td>
              <td>
                <span class="role-badge" :class="'role-' + u.role">
                  {{ u.role === 'admin' ? 'Админ' : 'Просмотр' }}
                </span>
              </td>
              <td>{{ domainLabels[u.domain] || u.domain }}</td>
              <td>{{ u.is_active ? 'Да' : 'Нет' }}</td>
              <td>{{ u.last_login ? new Date(u.last_login).toLocaleString('ru') : '—' }}</td>
              <td class="actions-cell">
                <button v-if="!isSelf(u)" class="btn-sm" @click="toggleRole(u)"
                  :title="u.role === 'admin' ? 'Понизить до viewer' : 'Повысить до admin'">
                  {{ u.role === 'admin' ? '↓' : '↑' }}
                </button>
                <button v-if="!isSelf(u)" class="btn-sm" @click="toggleActive(u)"
                  :title="u.is_active ? 'Заблокировать' : 'Разблокировать'">
                  {{ u.is_active ? '🔒' : '🔓' }}
                </button>
                <button v-if="!isSelf(u)" class="btn-sm btn-danger" @click="deleteUser(u)" title="Удалить">
                  ✕
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else class="empty-msg">Пользователей пока нет. Первый аутентифицированный пользователь станет администратором.</p>
      </div>

      <!-- ═══ Tab: Upload ═══ -->
      <div v-show="activeTab === 'upload'" class="settings-panel">
        <div class="upload-section-label">Active Directory</div>

        <div v-if="ldapMode">
          <div class="upload-cards">
            <div v-for="key in adDomains" :key="key" v-show="ldapConfigured[key]" class="card card-ad">
              <h3>{{ adCityNames[key] }}</h3>
              <p>LDAP-синхронизация</p>
              <button type="button" class="btn-icon btn-accent" title="Синхронизировать"
                @click="syncDomain(key)" v-html="SyncIcon"></button>
              <button type="button" class="btn-icon btn-danger" title="Очистить"
                @click="clearData('/api/clear/ad/' + key, adCityNames[key], key)" v-html="TrashIcon"></button>
              <div v-if="uploadStatuses[key]" class="upload-status" :class="uploadStatuses[key].ok ? 'ok' : 'err'">
                {{ uploadStatuses[key].msg }}
              </div>
            </div>
          </div>
          <div style="margin-top: 0.5rem;">
            <button type="button" class="btn" @click="syncAll">Синхронизировать все домены</button>
          </div>
        </div>

        <div v-else>
          <div class="upload-cards">
            <div v-for="key in adDomains" :key="key" class="card card-ad"
              :class="{ 'drop-active': dragOver['ad-' + key] }"
              @dragover="onDragOver($event, 'ad-' + key)"
              @dragleave="onDragLeave('ad-' + key)"
              @drop="onDrop($event, 'ad-' + key, '/api/upload/ad/' + key)">
              <h3>{{ adCityNames[key] }}</h3>
              <p>Excel / CSV — или перетащите файл сюда</p>
              <input type="file" :ref="el => { if (el) fileRefs['ad-' + key] = el }" accept=".csv,.xlsx,.xls" hidden>
              <button type="button" class="btn-icon btn-accent" title="Загрузить"
                @click="uploadFile('ad-' + key, '/api/upload/ad/' + key)" v-html="UploadIcon"></button>
              <button type="button" class="btn-icon btn-danger" title="Очистить"
                @click="clearData('/api/clear/ad/' + key, adCityNames[key], key + '-f')" v-html="TrashIcon"></button>
              <div v-if="uploadStatuses[key + '-f']" class="upload-status" :class="uploadStatuses[key + '-f'].ok ? 'ok' : 'err'">
                {{ uploadStatuses[key + '-f'].msg }}
              </div>
            </div>
          </div>
        </div>

        <div class="upload-section-label">Другие источники</div>
        <div class="upload-cards">
          <div class="card"
            :class="{ 'drop-active': dragOver['mfa'] }"
            @dragover="onDragOver($event, 'mfa')"
            @dragleave="onDragLeave('mfa')"
            @drop="onDrop($event, 'mfa', '/api/upload/mfa')">
            <h3>MFA</h3>
            <p>CSV (разделитель «;») — или перетащите файл</p>
            <input type="file" :ref="el => { if (el) fileRefs['mfa'] = el }" accept=".csv" hidden>
            <button type="button" class="btn-icon btn-accent" title="Загрузить"
              @click="uploadFile('mfa', '/api/upload/mfa')" v-html="UploadIcon"></button>
            <button type="button" class="btn-icon btn-danger" title="Очистить"
              @click="clearData('/api/clear/mfa', 'MFA', 'mfa')" v-html="TrashIcon"></button>
            <div v-if="uploadStatuses['mfa']" class="upload-status" :class="uploadStatuses['mfa'].ok ? 'ok' : 'err'">
              {{ uploadStatuses['mfa'].msg }}
            </div>
          </div>
          <div class="card"
            :class="{ 'drop-active': dragOver['people'] }"
            @dragover="onDragOver($event, 'people')"
            @dragleave="onDragLeave('people')"
            @drop="onDrop($event, 'people', '/api/upload/people')">
            <h3>Кадры</h3>
            <p>Excel, первый лист — или перетащите файл</p>
            <input type="file" :ref="el => { if (el) fileRefs['people'] = el }" accept=".xlsx,.xls" hidden>
            <button type="button" class="btn-icon btn-accent" title="Загрузить"
              @click="uploadFile('people', '/api/upload/people')" v-html="UploadIcon"></button>
            <button type="button" class="btn-icon btn-danger" title="Очистить"
              @click="clearData('/api/clear/people', 'Кадры', 'people')" v-html="TrashIcon"></button>
            <div v-if="uploadStatuses['people']" class="upload-status" :class="uploadStatuses['people'].ok ? 'ok' : 'err'">
              {{ uploadStatuses['people'].msg }}
            </div>
          </div>
        </div>

        <div class="stats" v-html="stats"></div>
        <div style="margin-top: 1rem;">
          <button type="button" class="btn-icon btn-danger-fill" title="Очистить всю БД"
            @click="clearAll" v-html="TrashBigIcon"></button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-tabs {
  display: flex;
  gap: .25rem;
  border-bottom: 2px solid var(--border);
  margin-bottom: 1.5rem;
}
.settings-tab {
  padding: .6rem 1.2rem;
  border: none;
  background: none;
  cursor: pointer;
  font-size: .95rem;
  font-weight: 500;
  color: var(--muted);
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: color .2s, border-color .2s;
}
.settings-tab:hover { color: var(--text); }
.settings-tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}
.settings-panel {
  min-height: 200px;
}

/* LDAP */
.ldap-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.ldap-card {
  padding: 1.25rem;
}
.ldap-card h3 {
  margin: 0 0 .75rem;
  font-size: 1.05rem;
}
.ldap-common {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.25rem;
  margin-top: 1rem;
}
.ldap-common h3 {
  margin: 0 0 1rem;
  font-size: 1.05rem;
}
.ldap-test-result {
  margin-top: .5rem;
  font-size: .85rem;
  padding: .35rem .6rem;
  border-radius: 4px;
}
.ldap-test-result.ok { background: #e8f5e9; color: #2e7d32; }
.ldap-test-result.err { background: #ffebee; color: #c62828; }
html[data-theme="dark"] .ldap-test-result.ok { background: rgba(46,125,50,.15); }
html[data-theme="dark"] .ldap-test-result.err { background: rgba(198,40,40,.15); }

.form-row {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: .75rem;
}
.form-row .form-group {
  flex: 1;
  min-width: 200px;
}
.form-group {
  display: flex;
  flex-direction: column;
  gap: .3rem;
  margin-bottom: .75rem;
}
.form-group label {
  font-size: .85rem;
  font-weight: 500;
  color: var(--text);
}
.form-group input,
.form-group select {
  padding: .5rem .65rem;
  border: 1.5px solid var(--border);
  border-radius: 6px;
  font-size: .9rem;
  background: var(--bg);
  color: var(--text);
  transition: border-color .2s;
}
.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--accent);
}
.form-check label {
  flex-direction: row;
  display: flex;
  align-items: center;
  gap: .5rem;
  cursor: pointer;
}
.form-check input[type="checkbox"] {
  width: 16px;
  height: 16px;
}

.btn-sm {
  padding: .25rem .5rem;
  font-size: .8rem;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
  transition: background .15s;
}
.btn-sm:hover { background: var(--bg); }
.btn-sm.btn-danger { color: var(--danger, #e53935); border-color: var(--danger, #e53935); }
.btn-sm.btn-danger:hover { background: rgba(229,57,53,.08); }

.btn-accent {
  background: var(--accent);
  color: #fff;
  border: none;
  padding: .5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: opacity .2s;
}
.btn-accent:hover { opacity: .9; }
.btn-accent:disabled { opacity: .5; cursor: not-allowed; }

/* Users table */
.users-toolbar {
  margin-bottom: 1rem;
}
.add-user-card {
  padding: 1rem;
  margin-bottom: 1rem;
}
.users-table {
  width: 100%;
}
.users-table th, .users-table td {
  padding: .5rem .65rem;
  text-align: left;
  font-size: .9rem;
}
.role-badge {
  display: inline-block;
  padding: .15rem .5rem;
  border-radius: 10px;
  font-size: .8rem;
  font-weight: 600;
}
.role-admin { background: #e3f2fd; color: #1565c0; }
.role-viewer { background: #f3e5f5; color: #7b1fa2; }
html[data-theme="dark"] .role-admin { background: rgba(21,101,192,.15); }
html[data-theme="dark"] .role-viewer { background: rgba(123,31,162,.15); }
.type-badge {
  display: inline-block;
  padding: .15rem .5rem;
  border-radius: 10px;
  font-size: .8rem;
  font-weight: 500;
}
.type-local { background: #e8f5e9; color: #2e7d32; }
.type-ldap { background: #fff3e0; color: #e65100; }
html[data-theme="dark"] .type-local { background: rgba(46,125,50,.15); }
html[data-theme="dark"] .type-ldap { background: rgba(230,81,0,.15); }
.row-inactive { opacity: .5; }
.actions-cell {
  display: flex;
  gap: .3rem;
  align-items: center;
}
.empty-msg {
  color: var(--muted);
  text-align: center;
  padding: 2rem;
}
</style>
