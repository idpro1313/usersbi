<script setup>
import { ref, reactive, onMounted } from 'vue'
import { fetchJSON, postForm, del } from '../api'
import { useToast } from '../composables/useToast'

const toast = useToast()

const SyncIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>`
const UploadIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>`
const TrashIcon = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>`
const TrashBigIcon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>`

const adDomains = ['izhevsk', 'kostroma', 'moscow']
const adCityNames = { izhevsk: 'AD — Ижевск', kostroma: 'AD — Кострома', moscow: 'AD — Москва' }

const ldapMode = ref(false)
const ldapConfigured = reactive({})
const statuses = reactive({})
const stats = ref('')
const fileRefs = {}

const dragOver = reactive({})

function setStatus(key, ok, msg) {
  statuses[key] = { ok, msg }
}

async function doUpload(statusKey, endpoint, file) {
  const form = new FormData()
  form.append('file', file)
  try {
    const data = await postForm(endpoint, form)
    let msg = 'Загружено: ' + data.rows + ' записей (' + data.filename + ')'
    if (data.skipped) msg += ' | пропущено ' + data.skipped + ' чужих'
    setStatus(statusKey, true, msg)
    loadStats()
  } catch (e) {
    setStatus(statusKey, false, e.message)
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
  setStatus(key, true, 'Синхронизация…')
  try {
    const r = await fetch('/api/sync/ad/' + key, { method: 'POST' })
    const data = await r.json()
    if (!r.ok) { setStatus(key, false, data.detail || 'Ошибка'); return }
    setStatus(key, true, 'Синхронизировано: ' + data.rows + ' записей')
    loadStats()
  } catch (e) {
    setStatus(key, false, 'Ошибка сети: ' + e.message)
  }
}

async function syncAll() {
  adDomains.forEach(k => setStatus(k, true, 'Синхронизация…'))
  try {
    const r = await fetch('/api/sync/ad', { method: 'POST' })
    const data = await r.json()
    if (data.domains) {
      adDomains.forEach(k => {
        const info = data.domains[k]
        if (!info) return
        if (info.error) setStatus(k, false, info.error)
        else if (info.skipped) setStatus(k, false, 'Пропущено: ' + info.reason)
        else setStatus(k, true, 'Синхронизировано: ' + info.rows + ' записей')
      })
    }
    loadStats()
  } catch (e) {
    adDomains.forEach(k => setStatus(k, false, 'Ошибка сети: ' + e.message))
  }
}

async function clearData(endpoint, label, statusKey) {
  if (!confirm('Очистить данные ' + label + '?')) return
  try {
    const data = await del(endpoint)
    setStatus(statusKey, true, 'Удалено: ' + data.deleted + ' записей')
    loadStats()
  } catch (e) {
    setStatus(statusKey, false, e.message)
  }
}

async function clearAll() {
  if (!confirm('Очистить ВСЮ базу данных (AD + MFA + Кадры)?')) return
  try {
    const data = await del('/api/clear/all')
    const d = data.deleted
    toast.success('Удалено: AD ' + d.ad + ', MFA ' + d.mfa + ', Кадры ' + d.people)
    loadStats()
  } catch (e) {
    toast.error('Ошибка: ' + e.message)
  }
}

async function loadStats() {
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

onMounted(async () => {
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
  loadStats()
})

</script>

<template>
  <div class="page-scroll">
    <div class="page-inner">
      <h1 class="page-title">Загрузка файлов</h1>
      <p class="page-subtitle">Загрузите выгрузки из AD, MFA и кадровой системы</p>

      <div class="upload-section-label">Active Directory</div>

      <!-- LDAP Section -->
      <div v-if="ldapMode">
        <div class="upload-cards">
          <div v-for="key in adDomains" :key="key" v-show="ldapConfigured[key]" class="card card-ad">
            <h3>{{ adCityNames[key] }}</h3>
            <p>LDAP-синхронизация</p>
            <button type="button" class="btn-icon btn-accent" :title="'Синхронизировать'"
              @click="syncDomain(key)" v-html="SyncIcon"></button>
            <button type="button" class="btn-icon btn-danger" title="Очистить"
              @click="clearData('/api/clear/ad/' + key, adCityNames[key], key)" v-html="TrashIcon"></button>
            <div v-if="statuses[key]" class="upload-status" :class="statuses[key].ok ? 'ok' : 'err'">
              {{ statuses[key].msg }}
            </div>
          </div>
        </div>
        <div style="margin-top: 0.5rem;">
          <button type="button" class="btn" @click="syncAll">Синхронизировать все домены</button>
        </div>
      </div>

      <!-- File Upload Section -->
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
            <div v-if="statuses[key + '-f']" class="upload-status" :class="statuses[key + '-f'].ok ? 'ok' : 'err'">
              {{ statuses[key + '-f'].msg }}
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
          <div v-if="statuses['mfa']" class="upload-status" :class="statuses['mfa'].ok ? 'ok' : 'err'">
            {{ statuses['mfa'].msg }}
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
          <div v-if="statuses['people']" class="upload-status" :class="statuses['people'].ok ? 'ok' : 'err'">
            {{ statuses['people'].msg }}
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
</template>
