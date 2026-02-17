<script setup>
import { ref, onMounted } from 'vue'
import PopupOverlay from '../components/PopupOverlay.vue'
import UserCardPopup from '../components/UserCardPopup.vue'
import DnPopup from '../components/DnPopup.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import { fetchJSON } from '../api'
import { escapeHtml } from '../utils/format'

const SEVERITY_LABEL = { critical: 'Критич.', high: 'Высокий', medium: 'Средний', info: 'Инфо' }
const SEVERITY_CLASS = { critical: 'sec-sev-critical', high: 'sec-sev-high', medium: 'sec-sev-medium', info: 'sec-sev-info' }

const summaryCards = ref([])
const findings = ref([])
const error = ref('')
const collapsed = ref({})

const cardPopup = ref(null)
const dnPopup = ref(null)

onMounted(async () => {
  try {
    const data = await fetchJSON('/api/security/findings')
    summaryCards.value = [
      { label: 'Всего УЗ', value: data.total_accounts, cls: '' },
      { label: 'Активных', value: data.total_enabled, cls: '' },
      { label: 'Критичных', value: data.critical_count, cls: data.critical_count > 0 ? 'sec-card-critical' : '' },
      { label: 'Высоких', value: data.high_count, cls: data.high_count > 0 ? 'sec-card-high' : '' },
      { label: 'Всего замечаний', value: data.total_issues, cls: data.total_issues > 0 ? 'sec-card-warn' : 'sec-card-ok' },
    ]
    findings.value = data.findings || []
    findings.value.forEach(f => {
      collapsed.value[f.id] = f.count > 20
    })
  } catch (e) {
    error.value = e.message
  }
})

function toggleFinding(id) {
  collapsed.value[id] = !collapsed.value[id]
}

function openCard(key, name) {
  cardPopup.value = { key, name }
}

function openDn(dn, name) {
  dnPopup.value = { dn, name }
}

function onDnOpenCard(key, name) {
  dnPopup.value = null
  openCard(key, name)
}

function onTableClick(e) {
  const link = e.target.closest('[data-user-key]')
  if (!link) return
  e.preventDefault()
  openCard(link.dataset.userKey, link.textContent.trim())
}

function buildTableHtml(items, extraCols) {
  const baseCols = [
    { key: 'display_name', label: 'ФИО' },
    { key: 'login', label: 'Логин' },
    { key: 'domain', label: 'Домен' },
    { key: 'enabled', label: 'Активна' },
    { key: 'account_type', label: 'Тип УЗ' },
  ]
  const cols = baseCols.concat(extraCols || [])
  let html = '<table class="data-table sec-table"><thead><tr><th>#</th>'
  cols.forEach(c => { html += '<th>' + escapeHtml(c.label) + '</th>' })
  html += '</tr></thead><tbody>'
  items.forEach((item, i) => {
    const rowCls = item.enabled === 'Нет' ? ' class="row-inactive"' : ''
    html += '<tr' + rowCls + '><td class="col-num">' + (i + 1) + '</td>'
    cols.forEach(c => {
      const val = item[c.key] || ''
      if (c.key === 'display_name' && item.key) {
        html += '<td><a href="#" class="ucard-link" data-user-key="' + escapeHtml(item.key) + '">' + escapeHtml(val || item.login) + '</a></td>'
      } else if (c.key === 'account_type' && val) {
        html += '<td><span class="at-badge at-' + escapeHtml(val.toLowerCase()) + '">' + escapeHtml(val) + '</span></td>'
      } else {
        html += '<td>' + escapeHtml(val) + '</td>'
      }
    })
    html += '</tr>'
  })
  html += '</tbody></table>'
  return html
}
</script>

<template>
  <div class="page-scroll">
    <div class="page-inner page-inner-wide">
      <h1 class="page-title">Аналитика безопасности</h1>
      <p class="page-subtitle">Проверки учётных записей AD, требующие внимания администраторов</p>

      <p v-if="error" class="muted-text">Ошибка: {{ error }}</p>

      <!-- Summary -->
      <div class="sec-summary">
        <LoadingSpinner v-if="!summaryCards.length && !error" text="Анализ безопасности…" />
        <div v-for="(c, i) in summaryCards" :key="i" class="sec-card" :class="c.cls">
          <div class="sec-card-value">{{ c.value }}</div>
          <div class="sec-card-label">{{ c.label }}</div>
        </div>
      </div>

      <!-- Findings -->
      <div>
        <div v-for="f in findings" :key="f.id"
          class="sec-finding" :class="[SEVERITY_CLASS[f.severity] || '', f.count > 0 ? '' : 'sec-finding-ok']">
          <div class="sec-finding-header" @click="toggleFinding(f.id)">
            <span class="sec-finding-sev">{{ SEVERITY_LABEL[f.severity] || f.severity }}</span>
            <span class="sec-finding-title">{{ f.title }}</span>
            <span class="sec-finding-count">{{ f.count }}</span>
            <span class="sec-finding-arrow">{{ f.count > 0 ? (collapsed[f.id] ? '▸' : '▾') : '✓' }}</span>
          </div>
          <div class="sec-finding-desc">{{ f.description }}</div>
          <div v-if="f.count > 0 && !collapsed[f.id]" class="sec-finding-body"
            @click="onTableClick" v-html="buildTableHtml(f.items, f.extra_columns)">
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Popups -->
  <UserCardPopup v-if="cardPopup" :userKey="cardPopup.key" :displayName="cardPopup.name"
    @close="cardPopup = null" @open-dn="openDn" @open-card="openCard" />
  <DnPopup v-if="dnPopup" :dn="dnPopup.dn" :displayName="dnPopup.name"
    @close="dnPopup = null" @open-card="onDnOpenCard" />
</template>
